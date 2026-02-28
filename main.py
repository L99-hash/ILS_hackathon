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


def main():
    """Main entry point for the scheduling agent"""

    print("=" * 60)
    print("NovaBoard Electronics - Production Scheduling Agent")
    print("=" * 60)
    print()

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

        # Get user choice
        while True:
            choice = input("Select planning policy (1, 2, or 3): ").strip()
            if choice in ['1', '2', '3']:
                break
            print("Invalid choice. Please enter 1, 2, or 3.")

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

        if choice == '1':
            print("Applying LEVEL 1: EDF (Earliest Deadline First)")
            print("One production order per sales order line, sorted by deadline")
            print()
            production_orders = planner.level1_edf(sales_order_lines)
            planner.display_production_plan(production_orders, "Level 1: EDF")

        elif choice == '2':
            print("Applying LEVEL 2: Group by Product")
            print("Merging orders with the same product to reduce changeovers")
            print()
            production_orders = planner.level2_group_by_product(sales_order_lines)
            planner.display_production_plan(production_orders, "Level 2: Group by Product")

        elif choice == '3':
            batch_size = input("Enter maximum batch size (default 10): ").strip()
            batch_size = int(batch_size) if batch_size.isdigit() else 10
            print(f"\nApplying LEVEL 2: Split in Batches (max {batch_size} units)")
            print("Splitting large orders into smaller batches")
            print()
            production_orders = planner.level2_split_batches(sales_order_lines, batch_size)
            planner.display_production_plan(production_orders, f"Level 2: Split in Batches (max {batch_size})")

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
        from datetime import datetime, timezone

        created_orders = []
        failed_orders = []

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

                # Prepare API payload
                payload = {
                    "product_id": product_id,
                    "quantity": prod_order.quantity,
                    "starts_at": datetime.now(timezone.utc).isoformat(),
                    "ends_at": prod_order.ends_at.isoformat()
                }

                # Create production order
                response = client.create_production_order(payload)
                created_orders.append((prod_order, response))

                order_id = response.get('id', 'Unknown')
                print(f"  {i}/{len(production_orders)}: Created - {prod_order.product_name} x{prod_order.quantity} (ID: {order_id})")

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

        # STEP 5: Human in the Loop - Present Schedule for Approval
        if len(created_orders) > 0:
            print("=" * 80)
            print("STEP 5: HUMAN IN THE LOOP - SCHEDULE APPROVAL")
            print("=" * 80)
            print()

            # Format and display schedule
            notifier = ScheduleNotifier()
            notifier.print_schedule(production_orders, created_orders)

            # Send to Telegram and wait for approval
            telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

            approval = None
            if telegram_bot_token and telegram_chat_id and 'your_bot_token_here' not in telegram_bot_token:
                message = notifier.format_schedule_message(production_orders, created_orders)
                print("\nSending schedule to Telegram...")
                if notifier.send_to_telegram(telegram_bot_token, telegram_chat_id, message):
                    # Wait for approval via Telegram
                    approval = notifier.wait_for_telegram_approval(telegram_bot_token, telegram_chat_id)
                    if approval == "TIMEOUT":
                        print("\nFalling back to terminal input...")
                        approval = None

            # Fallback to terminal input if Telegram not configured or timed out
            if approval is None:
                print()
                approval = input("Planner approval (APPROVE/REJECT): ").strip().upper()

            if approval == "APPROVE":
                print()
                print("Confirming production orders...")

                confirmed_count = 0
                for prod_order, response in created_orders:
                    order_id = response.get('id')
                    try:
                        client.confirm_production_order(order_id)
                        print(f"  Confirmed: {prod_order.product_name} (ID: {order_id})")
                        confirmed_count += 1
                    except Exception as e:
                        print(f"  Failed to confirm {order_id}: {e}")

                print()
                print("=" * 80)
                print("STEP 5 COMPLETE")
                print("=" * 80)
                print(f"Confirmed {confirmed_count}/{len(created_orders)} production orders")
                print("All confirmed orders moved to IN_PROGRESS status")
                print("First phase is now READY TO START for each order")
                print()

            else:
                print()
                print("Schedule rejected by planner.")
                print("Adjustments requested. Please modify planning parameters and rerun.")
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
