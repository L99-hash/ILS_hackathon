"""
Flask Dashboard Server

Provides REST API endpoints for the production dashboard
Serves static HTML/CSS/JS files
"""

from flask import Flask, jsonify, send_from_directory, render_template_string
import threading
import os
import json
from src.messaging.notifier import ScheduleNotifier
import plotly

# Get the directory where static files are located
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')

# Global references (set by start_dashboard_server)
_production_controller = None
_notifier = None
_scheduled_orders = None
_policy_name = None


@app.route('/')
def index():
    """Serve the main dashboard HTML"""
    try:
        html_path = os.path.join(STATIC_DIR, 'dashboard.html')
        with open(html_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error loading dashboard: {e}", 500


@app.route('/style.css')
def serve_css():
    """Serve CSS file"""
    try:
        css_path = os.path.join(STATIC_DIR, 'style.css')
        with open(css_path, 'r') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/css'}
    except Exception as e:
        return f"Error loading CSS: {e}", 500


@app.route('/dashboard.js')
def serve_js():
    """Serve JavaScript file"""
    try:
        js_path = os.path.join(STATIC_DIR, 'dashboard.js')
        with open(js_path, 'r') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'application/javascript'}
    except Exception as e:
        return f"Error loading JS: {e}", 500


@app.route('/debug/files')
def debug_files():
    """Debug endpoint to check if files exist"""
    files_status = {
        'static_dir': STATIC_DIR,
        'static_dir_exists': os.path.exists(STATIC_DIR),
        'files': {}
    }

    for filename in ['dashboard.html', 'style.css', 'dashboard.js']:
        filepath = os.path.join(STATIC_DIR, filename)
        files_status['files'][filename] = {
            'path': filepath,
            'exists': os.path.exists(filepath),
            'readable': os.access(filepath, os.R_OK) if os.path.exists(filepath) else False
        }

    return jsonify(files_status)


@app.route('/api/status')
def get_status():
    """Get overall production status and statistics"""
    if not _production_controller:
        return jsonify({'error': 'Production controller not initialized'}), 503

    try:
        stats = _production_controller.get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/current-order')
def get_current_order():
    """Get current order being produced"""
    if not _production_controller:
        return jsonify(None)

    try:
        order_info = _production_controller.get_current_order_info()
        return jsonify(order_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/completed-orders')
def get_completed():
    """Get list of completed orders"""
    if not _production_controller:
        return jsonify([])

    try:
        completed = _production_controller.completed_orders
        # Convert to serializable format
        result = []
        for item in completed:
            result.append({
                'product_name': item['order'].product_name,
                'quantity': item['order'].quantity,
                'completed_at': item['completed_at'],
                'classified_as': item['classified_as'],
                'confidence': item['confidence']
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/defects')
def get_defects():
    """Get list of defects detected"""
    if not _production_controller:
        return jsonify([])

    try:
        defects = _production_controller.defects_detected
        return jsonify(defects)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rework-orders')
def get_rework_orders():
    """Get list of rework orders created"""
    if not _production_controller:
        return jsonify([])

    try:
        rework = _production_controller.rework_orders
        return jsonify(rework)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/gantt')
def get_gantt():
    """Get Gantt chart data"""
    if not _notifier or not _scheduled_orders:
        return jsonify({'error': 'Chart data not available'}), 503

    try:
        # Build Gantt chart using static method
        fig = ScheduleNotifier.build_gantt_chart(_scheduled_orders, _policy_name or "Production Schedule")

        if fig is None:
            return jsonify({'error': 'No chart data available'}), 404

        # Convert Plotly figure to JSON using plotly's JSON encoder
        # This properly handles numpy arrays and other non-JSON-serializable types
        fig_json = json.loads(plotly.io.to_json(fig))
        return jsonify(fig_json)
    except Exception as e:
        import traceback
        print(f"ERROR in /api/gantt: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedule')
def get_schedule():
    """Get full production schedule"""
    if not _scheduled_orders:
        return jsonify([])

    try:
        result = []
        for prod_order, scheduled_response in _scheduled_orders:
            result.append({
                'product_name': prod_order.product_name,
                'quantity': prod_order.quantity,
                'deadline': prod_order.ends_at.isoformat(),
                'starts_at': scheduled_response.get('starts_at'),
                'ends_at': scheduled_response.get('ends_at'),
                'order_id': scheduled_response.get('id')
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def start_dashboard_server(production_controller, notifier, scheduled_orders, policy_name="Production Schedule", port=5000):
    """
    Start Flask dashboard server in background thread

    Args:
        production_controller: ProductionController instance
        notifier: ScheduleNotifier instance
        scheduled_orders: List of (prod_order, scheduled_response) tuples
        policy_name: Name of scheduling policy
        port: Port to run server on (default: 5000)
    """
    global _production_controller, _notifier, _scheduled_orders, _policy_name

    _production_controller = production_controller
    _notifier = notifier
    _scheduled_orders = scheduled_orders
    _policy_name = policy_name

    # Verify static files exist
    print(f"\n{'='*60}")
    print(f"📊 Starting Production Dashboard")
    print(f"{'='*60}")
    print(f"   Static directory: {STATIC_DIR}")

    for filename in ['dashboard.html', 'style.css', 'dashboard.js']:
        filepath = os.path.join(STATIC_DIR, filename)
        exists = os.path.exists(filepath)
        print(f"   {filename}: {'✓' if exists else '✗ MISSING'}")

    # Disable Flask logging for cleaner output
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    # Start Flask in daemon thread (won't block main program)
    def run_server():
        try:
            app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"   ✗ Dashboard server error: {e}")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # Give Flask a moment to start
    import time
    time.sleep(0.5)

    print(f"{'='*60}")
    print(f"✓ Dashboard server started successfully")
    print(f"   URL: http://localhost:{port}")
    print(f"   Debug: http://localhost:{port}/debug/files")
    print(f"{'='*60}\n")
