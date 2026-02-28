#!/usr/bin/env python3
"""
NovaBoard Electronics Production Scheduling Agent
Step 1: Read Sales Orders from Arke API
Step 2: Choose Planning Policy
"""

from src.api.client import ArkeAPIClient
from src.models.order import SalesOrderLine
from src.scheduler.planner import ProductionPlanner
from src.messaging.notifier import ScheduleNotifier
import json
import os
import time
import requests


def main():
    """Main entry point for the scheduling agent"""

    print("=" * 60)
    print("NovaBoard Electronics - Production Scheduling Agent")
    print("=" * 60)
    print()

    # Load Telegram credentials (needed for interactive prompts)
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    notifier = ScheduleNotifier()

    # Step 1: Initialize API client
    print("Step 1: Initializing Arke API client...")
    try:
        client = ArkeAPIClient()
        print("API client initialized successfully")
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease ensure you have:")
        print("1. Copied .env.example to .env")
        print("2. Filled in your API credentials in .env")
        return

    print()

    # Step 2: Fetch accepted sales orders
    print("Step 2: Fetching accepted sales orders...")
    try:
        sales_orders = client.get_sales_orders(status="accepted")
        print(f"Successfully retrieved {len(sales_orders)} sales orders")
        print()

        # Fetch detailed information for each order (product and quantity)
        print("Step 3: Fetching order details (products and quantities)...")
        orders_with_details = []
        for order in sales_orders:
            order_id = order.get('id')
            try:
                details = client.get_sales_order_details(order_id)
                order['details'] = details
                orders_with_details.append(order)
            except Exception as e:
                print(f"Warning: Could not fetch details for {order.get('internal_id')}: {e}")
                orders_with_details.append(order)

        print(f"Successfully retrieved details for {len(orders_with_details)} orders")
        print()


        # Display complete order summary
        print("=" * 80)
        print("SALES ORDER SUMMARY (Sorted by Urgency - Earliest Deadline First)")
        print("=" * 80)

        # Sort by deadline
        sorted_orders = sorted(orders_with_details, key=lambda x: x.get('expected_shipping_time', ''))

        for i, order in enumerate(sorted_orders, 1):
            internal_id = order.get('internal_id', 'N/A')
            customer = order.get('customer_attr', {}).get('name', 'Unknown')
            deadline = order.get('expected_shipping_time', 'N/A')[:16].replace('T', ' ')
            priority = order.get('priority', 'N/A')

            print(f"\n{i}. Order: {internal_id}")
            print(f"   Customer: {customer}")
            print(f"   Deadline: {deadline}")
            print(f"   Priority: P{priority}")

            # Extract product and quantity from order details
            if 'details' in order and order['details']:
                products = order['details'].get('products', [])
                if products:
                    print(f"   Products:")
                    for item in products:
                        product_name = item.get('name', 'Unknown Product')
                        product_id = item.get('extra_id', 'N/A')
                        quantity = item.get('quantity', 'N/A')
                        print(f"     - {product_name} (ID: {product_id}): {quantity} units")
                else:
                    print(f"   Products: No products found")
            else:
                print(f"   Products: Details not available")

        print()
        print("=" * 80)
        print()

        # Analyze for conflicts
        print("=" * 60)
        print("CONFLICT ANALYSIS:")
        print("=" * 60)
        print()

        # Sort orders by deadline (EDF - Earliest Deadline First)
        sorted_by_deadline = sorted(sales_orders, key=lambda x: x.get('expected_shipping_time', ''))

        # Sort orders by priority (higher priority first)
        sorted_by_priority = sorted(sales_orders, key=lambda x: x.get('priority', 999))

        print("Orders sorted by DEADLINE (EDF Strategy):")
        print("-" * 60)
        for i, order in enumerate(sorted_by_deadline[:5], 1):
            customer = order.get('customer_attr', {}).get('name', 'Unknown')
            deadline = order.get('expected_shipping_time', 'N/A')[:16].replace('T', ' ')  # Date and time
            priority = order.get('priority', 'N/A')
            internal_id = order.get('internal_id', 'N/A')
            print(f"{i}. {internal_id} - {customer}")
            print(f"   Deadline: {deadline}, Priority: P{priority}")

        print()
        print("Orders sorted by PRIORITY (Traditional Strategy):")
        print("-" * 60)
        for i, order in enumerate(sorted_by_priority[:5], 1):
            customer = order.get('customer_attr', {}).get('name', 'Unknown')
            deadline = order.get('expected_shipping_time', 'N/A')[:16].replace('T', ' ')  # Date and time
            priority = order.get('priority', 'N/A')
            internal_id = order.get('internal_id', 'N/A')
            print(f"{i}. {internal_id} - {customer}")
            print(f"   Deadline: {deadline}, Priority: P{priority}")

        # Identify specific conflicts where priority and deadline disagree
        print()
        print("SCHEDULING CONFLICTS DETECTED:")
        print("-" * 60)

        conflicts_found = False
        for i, deadline_order in enumerate(sorted_by_deadline):
            priority_rank = sorted_by_priority.index(deadline_order)
            if abs(i - priority_rank) > 2:  # Significant difference in ranking
                customer = deadline_order.get('customer_attr', {}).get('name', 'Unknown')
                deadline = deadline_order.get('expected_shipping_time', 'N/A')[:16].replace('T', ' ')
                priority = deadline_order.get('priority', 'N/A')
                internal_id = deadline_order.get('internal_id', 'N/A')
                print(f"Conflict: {internal_id} - {customer}")
                print(f"  Deadline rank: #{i+1}, Priority rank: #{priority_rank+1}")
                print(f"  Deadline: {deadline}, Priority: P{priority}")
                print()
                conflicts_found = True

        if not conflicts_found:
            print("No significant conflicts detected.")

        print()
        print("RECOMMENDATION:")
        print("-" * 60)
        print("Use EDF (Earliest Deadline First) scheduling to minimize late deliveries.")
        print("This ensures orders are completed by their deadline, regardless of priority.")

        # STEP 2: Choose Planning Policy
        print()
        print("=" * 80)
        print("STEP 2: CHOOSE PLANNING POLICY")
        print("=" * 80)
        print()
        print("Available planning policies:")
        print("1. Level 1 (REQUIRED) - EDF: One production order per sales order line")
        print("2. Level 2 (OPTIONAL) - Group by Product: Merge orders for same product")
        print("3. Level 2 (OPTIONAL) - Split in Batches: Cap batch size (e.g., 10 units)")
        print()

        # Get user choice via Telegram or console
        choice = None
        batch_size = 10

        if telegram_bot_token and telegram_chat_id and 'your_bot_token_here' not in telegram_bot_token:
            # Send policy selection prompt to Telegram
            policy_prompt = """🏭 *STEP 2: Choose Planning Policy*

Please select a planning policy:

*1.* Level 1 (REQUIRED) - EDF
   → One production order per sales order line
   → Sorted by deadline (earliest first)

*2.* Level 2 (OPTIONAL) - Group by Product
   → Merge orders for same product
   → Reduces machine changeovers

*3.* Level 2 (OPTIONAL) - Split in Batches
   → Cap batch size (e.g., max 10 units)
   → Better for large orders

Reply with: *1*, *2*, or *3*

For option 3, you can also specify batch size: *3:15* (for max 15 units)"""

            notifier.send_to_telegram(telegram_bot_token, telegram_chat_id, policy_prompt, None, None)
            print("\nWaiting for policy selection via Telegram...")

            # Wait for response
            url = f"https://api.telegram.org/bot{telegram_bot_token}/getUpdates"
            start_time = time.time()
            last_update_id = None
            timeout = 300  # 5 minutes

            # Get latest update_id
            try:
                response = requests.get(url, params={"offset": -1}, timeout=10)
                response.raise_for_status()
                data = response.json()
                if data.get("ok") and data.get("result"):
                    last_update_id = data["result"][-1]["update_id"]
            except Exception as e:
                print(f"Warning: Could not get initial update ID: {e}")

            while time.time() - start_time < timeout:
                try:
                    params = {}
                    if last_update_id is not None:
                        params["offset"] = last_update_id + 1
                    params["timeout"] = 10

                    response = requests.get(url, params=params, timeout=15)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("ok") and data.get("result"):
                        for update in data["result"]:
                            last_update_id = update["update_id"]

                            if "message" in update:
                                msg = update["message"]
                                if str(msg.get("chat", {}).get("id")) == str(telegram_chat_id):
                                    text = msg.get("text", "").strip()

                                    # Parse response: "1", "2", "3", or "3:15"
                                    if ':' in text:
                                        parts = text.split(':')
                                        if parts[0] == '3' and parts[1].isdigit():
                                            choice = '3'
                                            batch_size = int(parts[1])
                                            print(f"✓ Received: Policy 3 with batch size {batch_size}")
                                            break
                                    elif text in ['1', '2', '3']:
                                        choice = text
                                        print(f"✓ Received: Policy {choice}")
                                        break

                    if choice:
                        break
                    time.sleep(1)

                except Exception as e:
                    print(f"Error polling Telegram: {e}")
                    time.sleep(2)

            if not choice:
                print("⚠ Timeout: No response received. Defaulting to Policy 1 (EDF)")
                choice = '1'
        else:
            # Console input fallback
            while True:
                choice = input("Select planning policy (1, 2, or 3): ").strip()
                if choice in ['1', '2', '3']:
                    break
                print("Invalid choice. Please enter 1, 2, or 3.")

            if choice == '3':
                batch_input = input("Enter maximum batch size (default 10): ").strip()
                batch_size = int(batch_input) if batch_input.isdigit() else 10

        # Extract sales order lines from the detailed orders
        sales_order_lines = []
        for order in orders_with_details:
            if 'details' in order and order['details']:
                products = order['details'].get('products', [])
                for item in products:
                    try:
                        line = SalesOrderLine.from_api_response(order, item)
                        sales_order_lines.append(line)
                    except Exception as e:
                        print(f"Warning: Could not parse product line: {e}")
                        import traceback
                        traceback.print_exc()

        print(f"\nTotal sales order lines to plan: {len(sales_order_lines)}")
        print()

        # Apply selected planning policy
        planner = ProductionPlanner()
        policy_name = ""  # Track which policy was selected

        if choice == '1':
            print("Applying LEVEL 1: EDF (Earliest Deadline First)")
            print("One production order per sales order line, sorted by deadline")
            print()
            production_orders = planner.level1_edf(sales_order_lines)
            planner.display_production_plan(production_orders, "Level 1: EDF")
            policy_name = "EDF (Earliest Deadline First)"

        elif choice == '2':
            print("Applying LEVEL 2: Group by Product")
            print("Merging orders with the same product to reduce changeovers")
            print()
            production_orders = planner.level2_group_by_product(sales_order_lines)
            planner.display_production_plan(production_orders, "Level 2: Group by Product")
            policy_name = "Group by Product"

        elif choice == '3':
            batch_size = input("Enter maximum batch size (default 10): ").strip()
            batch_size = int(batch_size) if batch_size.isdigit() else 10
            print(f"\nApplying LEVEL 2: Split in Batches (max {batch_size} units)")
            print("Splitting large orders into smaller batches")
            print()
            production_orders = planner.level2_split_batches(sales_order_lines, batch_size)
            planner.display_production_plan(production_orders, f"Level 2: Split in Batches (max {batch_size})")
            policy_name = f"Split in Batches (max {batch_size} units)"

        # Store production orders for next steps
        print()
        print("=" * 80)
        print("STEP 2 COMPLETE")
        print("=" * 80)
        print(f"Generated {len(production_orders)} production orders using the selected policy.")
        print()

        # STEP 3: Create Production Orders in Arke
        print("=" * 80)
        print("STEP 3: CREATE PRODUCTION ORDERS IN ARKE")
        print("=" * 80)
        print()

        # First, fetch all products to map names to IDs
        print("Fetching product catalog...")
        try:
            products_catalog = client.get_products()
            print(f"Found {len(products_catalog)} products in catalog")

            # Map by internal_id (which matches the product names in sales orders)
            product_map_by_internal_id = {p.get('internal_id', ''): p.get('id', '') for p in products_catalog}
            product_map = {p.get('name', ''): p.get('id', '') for p in products_catalog}
            product_map_by_extra = {p.get('extra_id', ''): p.get('id', '') for p in products_catalog}
            print()
        except Exception as e:
            print(f"Error fetching products: {e}")
            print("Will attempt to create production orders with available product info")
            product_map = {}
            product_map_by_extra = {}
            print()

        # Confirm with user before creating
        confirm = input(f"Create {len(production_orders)} production orders in Arke? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("Production order creation cancelled.")
            return

        print()
        print("Creating production orders...")
        from datetime import datetime, timezone, timedelta

        created_orders = []
        failed_orders = []

        # Track the cumulative end time for sequential scheduling
        current_start_time = datetime.now(timezone.utc)

        for i, prod_order in enumerate(production_orders, 1):
            try:
                # Look up actual product ID from catalog
                # Try internal_id first (matches product name from sales order), then name, then extra_id
                product_id = (product_map_by_internal_id.get(prod_order.product_name) or
                            product_map_by_internal_id.get(prod_order.product_id) or
                            product_map.get(prod_order.product_name) or
                            product_map_by_extra.get(prod_order.product_id) or
                            prod_order.product_id)

                if not product_id:
                    print(f"  {i}/{len(production_orders)}: SKIPPED - No product ID for {prod_order.product_name}")
                    failed_orders.append(prod_order)
                    continue

                # Prepare API payload with sequential start times
                # Calculate estimated production end time (API will provide actual duration)
                # Estimate: ~9 minutes per unit minimum 1 hour
                estimated_duration_hours = max(1, prod_order.quantity * 0.15)
                estimated_end_time = current_start_time + timedelta(hours=estimated_duration_hours)

                payload = {
                    "product_id": product_id,
                    "quantity": prod_order.quantity,
                    "starts_at": current_start_time.isoformat(),
                    "ends_at": estimated_end_time.isoformat()
                }

                # Create production order
                response = client.create_production_order(payload)
                created_orders.append((prod_order, response))

                order_id = response.get('id', 'Unknown')
                print(f"  {i}/{len(production_orders)}: Created - {prod_order.product_name} x{prod_order.quantity} (ID: {order_id})")

                # Update start time for next order (sequential scheduling)
                # The next order should start when this one ends
                duration_minutes = response.get('duration')
                if duration_minutes is None:
                    raise Exception(f"API did not return duration for order {order_id}. Cannot schedule sequentially.")

                # Calculate actual production end time
                production_end_time = current_start_time + timedelta(minutes=duration_minutes)

                # Next order starts when this one ends
                current_start_time = production_end_time

            except Exception as e:
                print(f"  {i}/{len(production_orders)}: FAILED - {prod_order.product_name}: {str(e)[:50]}")
                failed_orders.append(prod_order)

        print()
        print("=" * 80)
        print("STEP 3 COMPLETE")
        print("=" * 80)
        print(f"Successfully created: {len(created_orders)}/{len(production_orders)} production orders")
        if failed_orders:
            print(f"Failed: {len(failed_orders)} orders")
        print()

        # STEP 4: Schedule Production Phases
        scheduled_orders = []
        if len(created_orders) > 0:
            print("=" * 80)
            print("STEP 4: SCHEDULE PRODUCTION PHASES")
            print("=" * 80)
            print()
            print("Generating phase sequences for production orders...")

            # Track sequential timing across all production orders
            # Constraint: 480 minutes (8 hours) workday from 9 AM to 5 PM
            WORKDAY_MINUTES = 480
            WORKDAY_START_HOUR = 9  # 9 AM
            WORKDAY_END_HOUR = 17    # 5 PM

            # Start scheduling from next available workday slot
            now = datetime.now(timezone.utc)
            if now.hour < WORKDAY_START_HOUR:
                # Before work starts today - start at 9 AM today
                next_phase_start = now.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0)
            elif now.hour >= WORKDAY_END_HOUR:
                # After work ends today - start at 9 AM tomorrow
                tomorrow = now + timedelta(days=1)
                next_phase_start = tomorrow.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0)
            else:
                # During work hours - start now
                next_phase_start = now

            current_day_minutes_used = 0
            if WORKDAY_START_HOUR <= now.hour < WORKDAY_END_HOUR:
                # Calculate how many minutes already used today
                current_day_minutes_used = (now.hour - WORKDAY_START_HOUR) * 60 + now.minute

            def schedule_with_workday_constraint(start_time, duration_minutes, day_minutes_used):
                """
                Schedule a phase respecting 8-hour workday (9 AM - 5 PM).
                Work stops at 5 PM and resumes at 9 AM next day.
                Uses partial days - if work doesn't fit in remaining time,
                it starts today and continues tomorrow.
                """
                phase_start = start_time
                remaining_duration = duration_minutes

                # Calculate end time accounting for workday breaks (9 AM - 5 PM)
                current_time = phase_start
                current_day_used = day_minutes_used

                while remaining_duration > 0:
                    available_today = WORKDAY_MINUTES - current_day_used

                    if remaining_duration <= available_today:
                        # Phase completes today
                        current_time = current_time + timedelta(minutes=remaining_duration)
                        current_day_used += remaining_duration
                        remaining_duration = 0
                    else:
                        # Use remaining time today, continue tomorrow at 9 AM
                        remaining_duration -= available_today
                        # Move to next workday at 9 AM
                        next_day = current_time + timedelta(days=1)
                        current_time = next_day.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0)
                        current_day_used = 0

                phase_end = current_time
                new_day_minutes = current_day_used

                return phase_start, phase_end, new_day_minutes

            for i, (prod_order, response) in enumerate(created_orders, 1):
                order_id = response.get('id')
                try:
                    # Generate phase sequence from BOM
                    scheduled_response = client.schedule_production_order(order_id)

                    # Get total duration from production order response (not from summing phases)
                    base_duration = scheduled_response.get('duration', 0)
                    quantity = prod_order.quantity

                    # WORKAROUND: API returns duration per batch (not scaled by quantity)
                    # Multiply by quantity to get realistic total production time
                    total_duration = base_duration * quantity

                    phases = scheduled_response.get('phases', [])
                    print(f"    Base duration: {base_duration} min × {quantity} units = {total_duration} minutes ({len(phases)} phases)")

                    # Apply workday constraint to get production start/end times
                    production_start, production_end, current_day_minutes_used = schedule_with_workday_constraint(
                        next_phase_start, total_duration, current_day_minutes_used
                    )

                    # Update production order dates (API will reschedule phases accordingly)
                    print(f"    → Setting: {production_start.strftime('%Y-%m-%d %H:%M')} to {production_end.strftime('%Y-%m-%d %H:%M')}")
                    try:
                        client.update_production_start_date(order_id, production_start.isoformat())
                        client.update_production_end_date(order_id, production_end.isoformat())

                        # Fetch updated production order
                        scheduled_response = client.get_production_order(order_id)
                        actual_start = scheduled_response.get('starts_at', 'N/A')[:16].replace('T', ' ')
                        actual_end = scheduled_response.get('ends_at', 'N/A')[:16].replace('T', ' ')
                        print(f"    ✓ API returned: {actual_start} to {actual_end}")
                    except Exception as update_error:
                        print(f"    ⚠ Warning: Could not update API dates: {update_error}")
                        scheduled_response = client.get_production_order(order_id)

                    # Override API times with our calculated sequential times
                    scheduled_response['starts_at'] = production_start.isoformat()
                    scheduled_response['ends_at'] = production_end.isoformat()
                    scheduled_response['duration'] = total_duration  # Store our calculated duration

                    # Next order starts when this one ends
                    next_phase_start = production_end

                    scheduled_orders.append((prod_order, scheduled_response))
                    print(f"    ✓ Using calculated times: {production_start.strftime('%Y-%m-%d %H:%M')} to {production_end.strftime('%Y-%m-%d %H:%M')}")
                    print(f"  {i}/{len(created_orders)}: Scheduled - {prod_order.product_name} (ID: {order_id})")
                except Exception as e:
                    print(f"  {i}/{len(created_orders)}: Failed to schedule {order_id}: {e}")

            print()
            print("=" * 80)
            print("STEP 4 COMPLETE")
            print("=" * 80)
            print(f"Successfully scheduled: {len(scheduled_orders)}/{len(created_orders)} production orders")
            print()

            # Validate deadlines are met
            print("=" * 80)
            print("DEADLINE VALIDATION")
            print("=" * 80)
            print()

            late_orders = []
            on_time_orders = []

            for prod_order, scheduled_response in scheduled_orders:
                production_end = scheduled_response.get('ends_at')
                customer_deadline = prod_order.ends_at.isoformat()

                if production_end and production_end > customer_deadline:
                    late_orders.append((prod_order, scheduled_response, production_end, customer_deadline))
                else:
                    on_time_orders.append((prod_order, scheduled_response))

            print(f"✓ On-time orders: {len(on_time_orders)}/{len(scheduled_orders)}")

            if late_orders:
                print(f"⚠ LATE orders: {len(late_orders)}/{len(scheduled_orders)}")
                print()
                print("Orders that will miss their deadline:")
                for prod_order, scheduled_response, prod_end, deadline in late_orders:
                    from datetime import datetime
                    prod_end_dt = datetime.fromisoformat(prod_end.replace('Z', '+00:00'))
                    deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    delay_hours = (prod_end_dt - deadline_dt).total_seconds() / 3600

                    print(f"  - {prod_order.product_name} (Order: {', '.join(prod_order.source_sales_orders)})")
                    print(f"    Production ends: {prod_end[:16].replace('T', ' ')}")
                    print(f"    Customer deadline: {deadline[:16].replace('T', ' ')}")
                    print(f"    Delay: {delay_hours:.1f} hours")
                    print()
            else:
                print("✓ All orders will be completed before their deadlines!")

            print()

        # STEP 5: Human in the Loop - Present Schedule for Approval
        if len(scheduled_orders) > 0:
            print("=" * 80)
            print("STEP 5: HUMAN IN THE LOOP - SCHEDULE APPROVAL")
            print("=" * 80)
            print()

            # Loop until schedule is approved
            approved = False

            while not approved:
                # Format and display schedule
                notifier.print_schedule(production_orders, scheduled_orders)

                # Send to Telegram and wait for approval
                approval = None
                rejection_reason = None

                if telegram_bot_token and telegram_chat_id and 'your_bot_token_here' not in telegram_bot_token:
                    message, scheduled_orders = notifier.format_schedule_message(production_orders, scheduled_orders, policy_name)
                    fig = ScheduleNotifier.build_gantt_chart(scheduled_orders, policy_name)
                    print("\nSending schedule to Telegram...")
                    if notifier.send_to_telegram(telegram_bot_token, telegram_chat_id, message, scheduled_orders, fig):
                        # Wait for approval via Telegram
                        approval, rejection_reason = notifier.wait_for_telegram_approval(telegram_bot_token, telegram_chat_id)
                        if approval == "TIMEOUT":
                            print("\nFalling back to terminal input...")
                            approval = None

                # Fallback to terminal input if Telegram not configured or timed out
                if approval is None:
                    print()
                    user_input = input("Planner approval (APPROVE/REJECT): ").strip().upper()
                    if user_input.startswith("REJECT"):
                        approval = "REJECT"
                        rejection_reason = input("Reason for rejection: ").strip()
                    else:
                        approval = user_input

                if approval == "APPROVE":
                    approved = True  # Break the loop
                    print()
                    print("Confirming production orders...")
                    print()

                    confirmed_count = 0
                    for prod_order, scheduled_response in scheduled_orders:
                        order_id = scheduled_response.get('id')
                        try:
                            confirm_response = client.confirm_production_order(order_id)
                            if confirm_response.get('status') == 'in_progress':
                                print(f"  ✓ Confirmed: {prod_order.product_name} (ID: {order_id}) → IN_PROGRESS")
                                confirmed_count += 1
                            else:
                                print(f"  → {prod_order.product_name} (ID: {order_id}) - {confirm_response.get('status', 'scheduled')}")
                        except Exception as e:
                            print(f"  ✗ Failed to confirm {order_id}: {e}")

                    print()
                    print("=" * 80)
                    print("STEP 5 COMPLETE")
                    print("=" * 80)
                    print(f"Production schedule APPROVED!")
                    if confirmed_count > 0:
                        print(f"✓ Confirmed: {confirmed_count}/{len(scheduled_orders)} orders moved to IN_PROGRESS")
                        print("  First phase is now READY TO START for confirmed orders")
                    else:
                        print(f"⚠ Note: _confirm endpoint not available on this API instance")
                        print(f"  All {len(scheduled_orders)} orders remain in SCHEDULED status")
                        print(f"  Orders are ready - phases can be started manually when needed")
                    print()
                    print("=" * 60)
                    print("SUMMARY:")
                    print(f"  Total Production Orders: {len(scheduled_orders)}")
                    print(f"  Total Phases Created: {len(scheduled_orders) * 7}")
                    print(f"  Status: {'IN_PROGRESS' if confirmed_count > 0 else 'SCHEDULED'}")
                    print(f"  Ready for: Step 6-7 (Physical Integration)")
                    print("=" * 60)
                    print()

                    # STEP 6: Physical Integration - Camera Monitoring
                    print("\n" + "=" * 80)
                    print("STEP 6: PHYSICAL INTEGRATION - PRODUCTION LINE MONITORING")
                    print("=" * 80)
                    print()

                    # Ask if user wants to enable camera monitoring
                    enable_monitoring = input("Enable camera monitoring? (yes/no): ").strip().lower()

                    if enable_monitoring in ['yes', 'y']:
                        from src.monitoring.camera import SimpleLineMonitor

                        # Ask which cameras to use
                        camera_input = input("Which camera(s) to use? (0, 1, 2 or '0,1' for multiple): ").strip()
                        # Strip quotes if user included them
                        camera_input = camera_input.strip("'\"")

                        # Parse camera indices
                        camera_indices = []
                        if ',' in camera_input:
                            # Multiple cameras
                            for idx_str in camera_input.split(','):
                                try:
                                    camera_indices.append(int(idx_str.strip()))
                                except ValueError:
                                    pass
                        else:
                            # Single camera
                            try:
                                camera_indices = [int(camera_input)]
                            except ValueError:
                                camera_indices = [0]
                                print(f"Invalid input, using camera 0")

                        if not camera_indices:
                            camera_indices = [0]
                            print(f"No valid cameras, using camera 0")

                        print(f"\nStarting camera monitoring (Camera(s): {camera_indices})...")
                        print("A window will open showing live production line feed")
                        if len(camera_indices) > 1:
                            print(f"Multiple cameras will be shown side-by-side")
                        print("Press 'q' in the camera window to stop monitoring a phase")
                        if telegram_bot_token and telegram_chat_id:
                            print("Send 'CAPTURE' via Telegram to take photos from all cameras!")
                        print()

                        monitor = SimpleLineMonitor(
                            camera_indices=camera_indices,
                            telegram_bot_token=telegram_bot_token,
                            telegram_chat_id=telegram_chat_id
                        )

                        try:
                            monitor.start_camera()

                            # Monitor each production order
                            for prod_order, scheduled_response in scheduled_orders:
                                order_id = scheduled_response.get('id')
                                phases = scheduled_response.get('phases', [])

                                if not phases:
                                    print(f"\nNo phases found for {prod_order.product_name}, skipping...")
                                    continue

                                print(f"\n{'='*60}")
                                print(f"Monitoring Order: {prod_order.product_name}")
                                print(f"Order ID: {order_id}")
                                print(f"Phases: {len(phases)}")
                                print(f"{'='*60}")

                                # Monitor each phase
                                for i, phase in enumerate(phases, 1):
                                    phase_name = phase.get('name', f'Phase {i}')

                                    print(f"\n[{i}/{len(phases)}] Monitoring phase: {phase_name}")

                                    # Monitor for 30 seconds per phase (adjust as needed)
                                    monitor.monitor_phase(
                                        phase_name=phase_name,
                                        order_id=order_id,
                                        duration_seconds=30,
                                        save_interval=10
                                    )

                                    # Brief pause between phases
                                    if i < len(phases):
                                        print("\nPreparing next phase...")
                                        time.sleep(2)

                            print("\n" + "=" * 80)
                            print("CAMERA MONITORING COMPLETE")
                            print("=" * 80)
                            print(f"Frames saved in: monitoring_frames/")
                            print()

                        except Exception as e:
                            print(f"\nError during monitoring: {e}")
                            print("Continuing without monitoring...")

                        finally:
                            monitor.stop_camera()
                    else:
                        print("Camera monitoring skipped")
                        print()

                else:  # REJECT - continue loop with adjustments
                    print()
                    print("=" * 80)
                    print("SCHEDULE REJECTED")
                    print("=" * 80)
                    print()
                    print(f"The production planner has rejected the proposed schedule.")
                    if rejection_reason:
                        print(f"Reason: {rejection_reason}")

                    # Ask if they want to make adjustments
                    if telegram_bot_token and telegram_chat_id and 'your_bot_token_here' not in telegram_bot_token:
                        adjustment_prompt = f"""Schedule rejected: {rejection_reason or 'No reason provided'}

Would you like to adjust the schedule?

Options:
1. SWAP <order1_num> <order2_num> - Swap order positions
2. MOVE <order_num> TO <position> - Move order to position
3. DATES <order_num> +<days> - Delay order by days
4. EXIT - Cancel and restart

Example: "SWAP 1 3" to swap orders 1 and 3
Example: "MOVE 5 TO 2" to move order 5 to position 2
Example: "DATES 3 +2" to delay order 3 by 2 days

Please send your adjustment command:"""

                    notifier.send_to_telegram(telegram_bot_token, telegram_chat_id, adjustment_prompt, None, None)

                    print("\nWaiting for adjustment command via Telegram...")
                    print("Supported commands:")
                    print("  - SWAP <num1> <num2>")
                    print("  - MOVE <num> TO <pos>")
                    print("  - DATES <num> +<days>")
                    print("  - EXIT")

                    # Wait for adjustment command
                    url = f"https://api.telegram.org/bot{telegram_bot_token}/getUpdates"
                    last_update_id = None
                    timeout = 300
                    start_time = time.time()

                    # Get current update ID
                    try:
                        response = requests.get(url, params={"offset": -1}, timeout=10)
                        data = response.json()
                        if data.get("ok") and data.get("result"):
                            last_update_id = data["result"][-1]["update_id"]
                    except:
                        pass

                    adjustment_cmd = None
                    while time.time() - start_time < timeout and adjustment_cmd is None:
                        try:
                            params = {"offset": last_update_id + 1 if last_update_id else None, "timeout": 10}
                            response = requests.get(url, params=params, timeout=15)
                            data = response.json()

                            if data.get("ok") and data.get("result"):
                                for update in data["result"]:
                                    last_update_id = update["update_id"]
                                    if "message" in update:
                                        msg = update["message"]
                                        if str(msg.get("chat", {}).get("id")) == str(telegram_chat_id):
                                            adjustment_cmd = msg.get("text", "").strip().upper()
                                            break

                            time.sleep(1)
                        except:
                            time.sleep(2)

                    if adjustment_cmd and adjustment_cmd != "EXIT":
                        print(f"\nReceived adjustment: {adjustment_cmd}")

                        # Parse and apply adjustment
                        try:
                            if adjustment_cmd.startswith("SWAP"):
                                parts = adjustment_cmd.split()
                                if len(parts) >= 3:
                                    idx1 = int(parts[1]) - 1
                                    idx2 = int(parts[2]) - 1
                                    if 0 <= idx1 < len(scheduled_orders) and 0 <= idx2 < len(scheduled_orders):
                                        scheduled_orders[idx1], scheduled_orders[idx2] = scheduled_orders[idx2], scheduled_orders[idx1]
                                        production_orders[idx1], production_orders[idx2] = production_orders[idx2], production_orders[idx1]

                                        result_msg = f"✓ Swapped orders {idx1+1} and {idx2+1}\n\nPlease review the updated schedule..."
                                        fig = notifier.build_gantt_chart(scheduled_orders, policy_name)
                                        notifier.send_to_telegram(telegram_bot_token, telegram_chat_id, result_msg, scheduled_orders, fig)

                                        # Re-display and ask for approval again
                                        print("\nSchedule adjusted. Re-presenting for approval...")
                                        # (This would loop back to display schedule again - simplified for now)

                            elif adjustment_cmd.startswith("MOVE"):
                                # Similar logic for MOVE command
                                result_msg = "MOVE command parsing not fully implemented yet"
                                notifier.send_to_telegram(telegram_bot_token, telegram_chat_id, result_msg, None, None)

                            elif adjustment_cmd.startswith("DATES"):
                                # Similar logic for DATES command
                                result_msg = "DATES command parsing not fully implemented yet"
                                notifier.send_to_telegram(telegram_bot_token, telegram_chat_id, result_msg, None, None)

                        except Exception as e:
                            error_msg = f"Error applying adjustment: {e}\n\nPlease restart and try again."
                            notifier.send_to_telegram(telegram_bot_token, telegram_chat_id, error_msg, None, None)
                            print(f"Error: {e}")

                        print("\nSchedule adjusted. Looping back for re-presentation...")
                        # Continue the while loop to re-present the schedule
                        continue
                    else:
                        # User chose EXIT or timeout
                        print()
                        print("Exiting. Please restart the script if you want to make changes.")
                        return

    except Exception as e:
        print(f"Error in process: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 60)
    print("Next steps:")
    print("6. Physical integration")
    print("7. Execute production phases")
    print("=" * 60)


if __name__ == "__main__":
    main()
