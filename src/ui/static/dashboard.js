/**
 * Production Dashboard - Real-time Updates
 * Fetches data from Flask API and updates the UI
 */

// Configuration
const REFRESH_INTERVAL = 2000; // 2 seconds
const API_BASE = '';

// State
let isConnected = false;
let lastUpdateTime = null;

/**
 * Fetch all data from API
 */
async function fetchData() {
    try {
        const [status, currentOrder, completedOrders, defects, gantt] = await Promise.all([
            fetch(`${API_BASE}/api/status`).then(r => r.json()),
            fetch(`${API_BASE}/api/current-order`).then(r => r.json()),
            fetch(`${API_BASE}/api/completed-orders`).then(r => r.json()),
            fetch(`${API_BASE}/api/defects`).then(r => r.json()),
            fetch(`${API_BASE}/api/gantt`).then(r => r.json())
        ]);

        // Update connection status
        updateConnectionStatus(true);

        // Update all UI components
        updateStatistics(status);
        updateCurrentOrder(currentOrder, status);
        updateCompletedOrders(completedOrders);
        updateDefectLog(defects);
        updateGanttChart(gantt);

        // Update timestamp
        const now = new Date();
        lastUpdateTime = now;
        document.getElementById('last-update').textContent =
            `Last update: ${now.toLocaleTimeString()}`;

    } catch (error) {
        console.error('Failed to fetch data:', error);
        updateConnectionStatus(false);
    }
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connection-indicator');
    const text = document.getElementById('connection-text');

    if (connected) {
        indicator.className = 'indicator connected';
        text.textContent = 'Connected';
        isConnected = true;
    } else {
        indicator.className = 'indicator disconnected';
        text.textContent = 'Disconnected';
        isConnected = false;
    }
}

/**
 * Update statistics cards
 */
function updateStatistics(status) {
    if (!status) return;

    document.getElementById('completed-count').textContent = status.completed_orders || 0;
    document.getElementById('defect-count').textContent = status.defects_detected || 0;
    document.getElementById('rework-count').textContent = status.rework_orders_created || 0;
    document.getElementById('remaining-count').textContent = status.remaining_orders || 0;
}

/**
 * Update current order section
 */
function updateCurrentOrder(currentOrder, status) {
    const orderName = document.getElementById('order-name');
    const orderDetails = document.getElementById('order-details');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    if (currentOrder && currentOrder.product_name) {
        // Active order
        orderName.textContent = currentOrder.product_name;
        orderDetails.textContent = `Quantity: ${currentOrder.quantity} | Order ${currentOrder.order_index + 1} of ${currentOrder.total_orders}`;
        orderName.style.color = 'white';
    } else {
        // All orders completed
        orderName.textContent = '🎉 All Orders Completed!';
        orderDetails.textContent = 'Production schedule finished';
        orderName.style.color = '#2ecc71';
    }

    // Update progress bar
    if (status && status.total_orders > 0) {
        const progress = (status.completed_orders / status.total_orders) * 100;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${status.completed_orders} / ${status.total_orders} orders completed (${progress.toFixed(0)}%)`;
    } else {
        progressBar.style.width = '0%';
        progressText.textContent = '0 / 0 orders completed';
    }
}

/**
 * Update completed orders table
 */
function updateCompletedOrders(completedOrders) {
    const tbody = document.getElementById('completed-tbody');
    tbody.innerHTML = '';

    if (!completedOrders || completedOrders.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="5" class="empty-message">No orders completed yet</td></tr>';
        return;
    }

    completedOrders.forEach(order => {
        const row = tbody.insertRow();
        const completedTime = new Date(order.completed_at);

        row.innerHTML = `
            <td><strong>${escapeHtml(order.product_name)}</strong></td>
            <td>${order.quantity}</td>
            <td>${completedTime.toLocaleTimeString()}</td>
            <td>${escapeHtml(order.classified_as)}</td>
            <td><span class="badge badge-success">${(order.confidence * 100).toFixed(1)}%</span></td>
        `;
    });
}

/**
 * Update defect log table
 */
function updateDefectLog(defects) {
    const tbody = document.getElementById('defect-tbody');
    tbody.innerHTML = '';

    if (!defects || defects.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="4" class="empty-message">No defects detected yet</td></tr>';
        return;
    }

    // Show most recent defects first
    const sortedDefects = [...defects].reverse();

    sortedDefects.forEach(defect => {
        const row = tbody.insertRow();
        const detectedTime = new Date(defect.detected_at);

        row.innerHTML = `
            <td>${detectedTime.toLocaleTimeString()}</td>
            <td><strong>${escapeHtml(defect.product)}</strong></td>
            <td><span class="badge badge-warning">${(defect.confidence * 100).toFixed(1)}%</span></td>
            <td><span class="badge badge-info">Logged</span></td>
        `;
    });
}

/**
 * Update Gantt chart
 */
function updateGanttChart(ganttData) {
    const chartDiv = document.getElementById('gantt-chart');

    if (!ganttData || ganttData.error) {
        chartDiv.innerHTML = '<div class="loading">Chart data unavailable</div>';
        return;
    }

    try {
        // Configure layout for better visibility
        const layout = {
            ...ganttData.layout,
            autosize: true,
            margin: { l: 150, r: 50, t: 80, b: 80 },
            font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
        };

        Plotly.newPlot(chartDiv, ganttData.data, layout, config);
    } catch (error) {
        console.error('Error rendering Gantt chart:', error);
        chartDiv.innerHTML = '<div class="loading">Error loading chart</div>';
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize dashboard
 */
function initialize() {
    console.log('🚀 Production Dashboard initializing...');

    // Set initial connection status
    updateConnectionStatus(false);
    document.getElementById('connection-text').textContent = 'Connecting';
    document.getElementById('connection-indicator').className = 'indicator connecting';

    // Fetch data immediately
    fetchData();

    // Set up periodic refresh
    setInterval(fetchData, REFRESH_INTERVAL);

    console.log('✅ Dashboard initialized');
    console.log(`📡 Auto-refresh every ${REFRESH_INTERVAL / 1000} seconds`);
}

// Start when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}
