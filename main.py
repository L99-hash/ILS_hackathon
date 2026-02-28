#!/usr/bin/env python3
"""
NovaBoard Electronics Production Scheduling Agent
Step 1: Read Sales Orders from Arke API
"""

from src.api.client import ArkeAPIClient
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
                line_items = order['details'].get('line_items', [])
                if line_items:
                    print(f"   Products:")
                    for item in line_items:
                        product_name = item.get('product_attr', {}).get('name', 'Unknown Product')
                        quantity = item.get('quantity', 'N/A')
                        print(f"     - {product_name}: {quantity} units")
                else:
                    print(f"   Products: No line items found")
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

    except Exception as e:
        print(f"Error fetching sales orders: {e}")
        return

    print()
    print("=" * 60)
    print("Next steps:")
    print("1. Choose planning policy (Level 1 or Level 2 batching)")
    print("2. Create production orders")
    print("3. Schedule phases")
    print("=" * 60)


if __name__ == "__main__":
    main()
