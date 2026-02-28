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

        # Display orders
        print("=" * 60)
        print("SALES ORDERS:")
        print("=" * 60)
        print(json.dumps(sales_orders, indent=2))
        print()

        # Analyze for conflicts
        print("=" * 60)
        print("CONFLICT ANALYSIS:")
        print("=" * 60)

        # Look for SO-003 and SO-005 specifically
        so_003 = next((order for order in sales_orders if order.get('id') == 'SO-003'), None)
        so_005 = next((order for order in sales_orders if order.get('id') == 'SO-005'), None)

        if so_003 and so_005:
            print("\nKey conflict identified:")
            print(f"  SO-003 (AgriBot):")
            print(f"    - Deadline: {so_003.get('deadline')}")
            print(f"    - Priority: {so_003.get('priority')}")
            print(f"  SO-005 (SmartHome IoT):")
            print(f"    - Deadline: {so_005.get('deadline')}")
            print(f"    - Priority: {so_005.get('priority')}")
            print("\nRecommendation: Use EDF (Earliest Deadline First) scheduling")
            print("SO-003 should be scheduled before SO-005 despite lower priority")

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
