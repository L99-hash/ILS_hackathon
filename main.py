#!/usr/bin/env python3
"""
NovaBoard Electronics Production Scheduling Agent
Step 1: Read Sales Orders from Arke API
Step 2: Choose Planning Policy
"""

from src.api.client import ArkeAPIClient
from src.models.order import SalesOrderLine
from src.scheduler.planner import ProductionPlanner
import json


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

        # Debug: Show first few lines
        if sales_order_lines:
            print("\nDEBUG - First 3 sales order lines:")
            for i, line in enumerate(sales_order_lines[:3], 1):
                print(f"  {i}. Product ID: '{line.product_id}', Name: '{line.product_name}', Qty: {line.quantity}")
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

    except Exception as e:
        print(f"Error in planning process: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 60)
    print("Next steps:")
    print("3. Create production orders in Arke")
    print("4. Schedule phases")
    print("=" * 60)


if __name__ == "__main__":
    main()
