"""Production planning policies for converting sales orders to production orders"""

from typing import List, Dict
from collections import defaultdict
from src.models.order import SalesOrderLine, ProductionOrder


class ProductionPlanner:
    """Implements different planning policies for production scheduling"""

    @staticmethod
    def level1_edf(sales_order_lines: List[SalesOrderLine]) -> List[ProductionOrder]:
        """
        LEVEL 1 - REQUIRED: Earliest Deadline First (EDF)

        One production order per sales order line.
        Sort by expected_shipping_time (nearest first).
        Ties broken by priority (lowest number = highest priority wins).

        Args:
            sales_order_lines: List of sales order line items

        Returns:
            List of production orders, one per sales order line
        """
        # Sort by deadline first, then by priority (lower number = higher priority)
        sorted_lines = sorted(
            sales_order_lines,
            key=lambda x: (x.deadline, x.priority)
        )

        production_orders = []
        for line in sorted_lines:
            prod_order = ProductionOrder(
                product_id=line.product_id,
                product_name=line.product_name,
                quantity=line.quantity,
                ends_at=line.deadline,
                priority=line.priority,
                source_sales_orders=[line.sales_order_internal_id]
            )
            production_orders.append(prod_order)

        return production_orders

    @staticmethod
    def level2_group_by_product(sales_order_lines: List[SalesOrderLine]) -> List[ProductionOrder]:
        """
        LEVEL 2 - OPTIONAL: Group by Product

        Merge all lines with the same product into one production order.
        Reduces machine changeovers.
        quantity = sum of all quantities
        ends_at = earliest deadline among grouped orders
        priority = highest priority (lowest number) among grouped orders

        Args:
            sales_order_lines: List of sales order line items

        Returns:
            List of production orders, grouped by product
        """
        # Group lines by product
        product_groups: Dict[str, List[SalesOrderLine]] = defaultdict(list)
        for line in sales_order_lines:
            product_groups[line.product_id].append(line)

        production_orders = []
        for product_id, lines in product_groups.items():
            # Sum quantities
            total_quantity = sum(line.quantity for line in lines)

            # Earliest deadline
            earliest_deadline = min(line.deadline for line in lines)

            # Highest priority (lowest number)
            highest_priority = min(line.priority for line in lines)

            # Collect all source sales orders
            source_orders = [line.sales_order_internal_id for line in lines]

            prod_order = ProductionOrder(
                product_id=product_id,
                product_name=lines[0].product_name,
                quantity=total_quantity,
                ends_at=earliest_deadline,
                priority=highest_priority,
                source_sales_orders=source_orders
            )
            production_orders.append(prod_order)

        # Sort by deadline, then priority
        production_orders.sort(key=lambda x: (x.ends_at, x.priority))

        return production_orders

    @staticmethod
    def level2_split_batches(sales_order_lines: List[SalesOrderLine],
                            max_batch_size: int = 10) -> List[ProductionOrder]:
        """
        LEVEL 2 - OPTIONAL: Split in Batches

        Cap batch size to reduce WIP and improve flow.
        Large orders split into multiple batches.
        Each batch inherits the original order's deadline.

        Args:
            sales_order_lines: List of sales order line items
            max_batch_size: Maximum units per production batch

        Returns:
            List of production orders with capped batch sizes
        """
        # Sort by deadline first, then priority
        sorted_lines = sorted(
            sales_order_lines,
            key=lambda x: (x.deadline, x.priority)
        )

        production_orders = []
        for line in sorted_lines:
            quantity_remaining = line.quantity
            batch_count = (quantity_remaining + max_batch_size - 1) // max_batch_size  # Ceiling division

            for batch_num in range(1, batch_count + 1):
                batch_quantity = min(max_batch_size, quantity_remaining)
                quantity_remaining -= batch_quantity

                prod_order = ProductionOrder(
                    product_id=line.product_id,
                    product_name=line.product_name,
                    quantity=batch_quantity,
                    ends_at=line.deadline,
                    priority=line.priority,
                    source_sales_orders=[line.sales_order_internal_id],
                    batch_number=batch_num,
                    total_batches=batch_count
                )
                production_orders.append(prod_order)

        return production_orders

    @staticmethod
    def display_production_plan(production_orders: List[ProductionOrder], policy_name: str):
        """
        Display a formatted production plan

        Args:
            production_orders: List of production orders
            policy_name: Name of the planning policy used
        """
        print("=" * 80)
        print(f"PRODUCTION PLAN - {policy_name}")
        print("=" * 80)
        print(f"Total production orders: {len(production_orders)}")
        print()

        for i, order in enumerate(production_orders, 1):
            sources_str = ', '.join(order.source_sales_orders)
            batch_info = f" [Batch {order.batch_number}/{order.total_batches}]" if order.batch_number else ""

            print(f"{i}. {order.product_name}{batch_info}")
            print(f"   Quantity: {order.quantity} units")
            print(f"   Deadline: {order.ends_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Priority: P{order.priority}")
            print(f"   Source Orders: {sources_str}")
            print()

        print("=" * 80)
