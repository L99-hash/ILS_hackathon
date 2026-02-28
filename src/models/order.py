"""Data models for sales orders and production orders"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SalesOrderLine:
    """Represents a line item in a sales order"""
    sales_order_id: str
    sales_order_internal_id: str
    product_id: str
    product_name: str
    quantity: int
    deadline: datetime
    priority: int
    customer_name: str

    @classmethod
    def from_api_response(cls, order: Dict[str, Any], line_item: Dict[str, Any]) -> 'SalesOrderLine':
        """Create a SalesOrderLine from API response data"""
        # Extract order data (can be from 'details' wrapper or direct)
        order_data = order.get('details', order)

        return cls(
            sales_order_id=order_data.get('id', ''),
            sales_order_internal_id=order_data.get('internal_id', ''),
            product_id=line_item.get('extra_id', line_item.get('name', '')),
            product_name=line_item.get('name', 'Unknown'),
            quantity=line_item.get('quantity', 0),
            deadline=datetime.fromisoformat(order_data.get('expected_shipping_time', '').replace('Z', '+00:00')),
            priority=order_data.get('priority', 999),
            customer_name=order_data.get('customer_attr', {}).get('name', 'Unknown')
        )


@dataclass
class ProductionOrder:
    """Represents a production order to be created"""
    product_id: str
    product_name: str
    quantity: int
    ends_at: datetime
    priority: int
    source_sales_orders: List[str]  # List of sales order internal IDs
    batch_number: Optional[int] = None
    total_batches: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API submission"""
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'ends_at': self.ends_at.isoformat(),
            'priority': self.priority,
            'source_sales_orders': self.source_sales_orders,
            'batch_info': f"{self.batch_number}/{self.total_batches}" if self.batch_number else None
        }

    def __repr__(self) -> str:
        batch_info = f" [Batch {self.batch_number}/{self.total_batches}]" if self.batch_number else ""
        sources = ', '.join(self.source_sales_orders)
        return (f"ProductionOrder({self.product_name}, qty={self.quantity}, "
                f"deadline={self.ends_at.strftime('%Y-%m-%d %H:%M')}, "
                f"priority=P{self.priority}, sources={sources}{batch_info})")
