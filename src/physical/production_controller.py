"""
Production Controller

Manages production orders based on real-time camera classification
Integrates with Arke API to complete orders and handle defects
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime


class ProductionController:
    """
    Controls production flow based on camera classification results

    Workflow:
    1. Track current production order
    2. Complete order when correct product is detected
    3. Create rework order when defective product is detected
    """

    def __init__(self, api_client, scheduled_orders, notifier=None):
        """
        Initialize production controller

        Args:
            api_client: ArkeAPIClient instance for API calls
            scheduled_orders: List of (prod_order, scheduled_response) tuples
            notifier: ScheduleNotifier for sending updates to Telegram
        """
        self.api_client = api_client
        self.scheduled_orders = scheduled_orders
        self.notifier = notifier

        # Track current active order
        self.current_order_index = 0
        self.completed_orders = []

        # Defect tracking
        self.defects_detected = []
        self.rework_orders = []

        print("🎮 Production Controller initialized")
        print(f"   Total orders in schedule: {len(scheduled_orders)}")

        # Display first order
        if self.scheduled_orders:
            self.display_current_order()

    def display_current_order(self):
        """Display information about the current order"""
        if self.current_order_index >= len(self.scheduled_orders):
            print("\n🎉 All orders completed!")
            return

        prod_order, _ = self.scheduled_orders[self.current_order_index]
        print(f"\n📋 Current Order ({self.current_order_index + 1}/{len(self.scheduled_orders)}):")
        print(f"   Product: {prod_order.product_name}")
        print(f"   Quantity: {prod_order.quantity}")
        print(f"   Deadline: {prod_order.ends_at.strftime('%Y-%m-%d %H:%M')}")

    def get_current_order_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current order"""
        if self.current_order_index >= len(self.scheduled_orders):
            return None

        prod_order, scheduled_response = self.scheduled_orders[self.current_order_index]
        return {
            'product_name': prod_order.product_name,
            'quantity': prod_order.quantity,
            'order_index': self.current_order_index,
            'total_orders': len(self.scheduled_orders),
            'production_order_id': scheduled_response.get('id')
        }

    def handle_classification_result(self, classified_product: str, confidence: float,
                                     is_defect: bool = False) -> Tuple[bool, str]:
        """
        Handle camera classification result

        Args:
            classified_product: Product class from classifier
            confidence: Classification confidence (0-1)
            is_defect: Whether this is a defect variant

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check if we detected a defect
        if is_defect or "_defect" in classified_product:
            return self.handle_defect(classified_product, confidence)
        else:
            return self.handle_correct_product(classified_product, confidence)

    def handle_correct_product(self, classified_product: str, confidence: float) -> Tuple[bool, str]:
        """
        Handle detection of a correct (non-defective) product
        Complete the current order and move to next

        Args:
            classified_product: Product class from classifier
            confidence: Classification confidence

        Returns:
            Tuple of (success: bool, message: str)
        """
        if self.current_order_index >= len(self.scheduled_orders):
            return False, "No active orders"

        prod_order, scheduled_response = self.scheduled_orders[self.current_order_index]
        production_order_id = scheduled_response.get('id')

        print(f"\n✓ Correct product detected: {classified_product} ({confidence:.1%})")
        print(f"   Completing order: {prod_order.product_name} (ID: {production_order_id})")

        # Mark order as completed
        self.completed_orders.append({
            'order': prod_order,
            'completed_at': datetime.now().isoformat(),
            'classified_as': classified_product,
            'confidence': confidence
        })

        # Move to next order
        self.current_order_index += 1

        message = f"✓ Order completed: {prod_order.product_name}\n"
        message += f"Completed orders: {len(self.completed_orders)}/{len(self.scheduled_orders)}"

        print(f"   {message}")

        # Display next order
        if self.current_order_index < len(self.scheduled_orders):
            self.display_current_order()
            next_order, _ = self.scheduled_orders[self.current_order_index]
            message += f"\n📋 Next order: {next_order.product_name}"
        else:
            print("\n🎉 All orders completed!")
            message += "\n🎉 All orders completed!"

        return True, message

    def handle_defect(self, classified_product: str, confidence: float) -> Tuple[bool, str]:
        """
        Handle detection of a defective product
        Log defect and create rework order

        Args:
            classified_product: Defect class from classifier
            confidence: Classification confidence

        Returns:
            Tuple of (success: bool, message: str)
        """
        print(f"\n⚠️  DEFECT DETECTED: {classified_product} ({confidence:.1%})")

        # Extract base product name (remove _defect suffix)
        base_product = classified_product.replace("_defect", "").replace("_", "-")

        # Record defect
        defect_record = {
            'detected_at': datetime.now().isoformat(),
            'product': base_product,
            'classified_as': classified_product,
            'confidence': confidence,
            'order_index': self.current_order_index
        }
        self.defects_detected.append(defect_record)

        print(f"   Base product: {base_product}")
        print(f"   Defects recorded: {len(self.defects_detected)}")
        print(f"   Order remains in queue (not completed)")

        # Try to create rework order
        rework_created = False
        try:
            print(f"\n📝 Creating rework order for: {base_product}")

            # Find the original order to get product details
            original_order = None
            for prod_order, scheduled_response in self.scheduled_orders:
                if prod_order.product_name == base_product or base_product in prod_order.product_name:
                    original_order = (prod_order, scheduled_response)
                    break

            if not original_order:
                print(f"   ✗ Could not find original order for: {base_product}")
                raise ValueError(f"Original order not found for {base_product}")

            prod_order, scheduled_response = original_order

            # Get the actual product UUID from the scheduled response
            # The product_id in prod_order might be the product name, not UUID
            actual_product_id = scheduled_response.get('product_id')

            if not actual_product_id:
                print(f"   ✗ No product_id found in scheduled response")
                print(f"   Available keys: {list(scheduled_response.keys())}")
                raise ValueError(f"Cannot find product_id for {base_product}")

            # Create rework order (quantity = 1 to replace the defective unit)
            from datetime import timedelta, timezone
            now = datetime.now(timezone.utc)
            rework_start = now + timedelta(minutes=5)  # Start in 5 minutes
            rework_end = rework_start + timedelta(minutes=60)  # 1 hour for rework

            rework_order_data = {
                "product_id": actual_product_id,
                "quantity": 1,  # Replace 1 defective unit
                "starts_at": rework_start.isoformat(),
                "ends_at": rework_end.isoformat()
            }

            print(f"   Product ID: {actual_product_id}")
            print(f"   Quantity: 1")
            print(f"   Start: {rework_start.isoformat()}")
            print(f"   End: {rework_end.isoformat()}")

            try:
                response = self.api_client.create_production_order(rework_order_data)
                rework_order_id = response.get('id')
                print(f"   ✓ Production order created: {rework_order_id}")

                # Schedule the rework order
                self.api_client.schedule_production_order(rework_order_id)
                print(f"   ✓ Production order scheduled")

                # Confirm/start the rework order
                self.api_client.confirm_production_order(rework_order_id)
                print(f"   ✓ Production order started")

                self.rework_orders.append({
                    'order_id': rework_order_id,
                    'product': base_product,
                    'defect_record': defect_record
                })

                print(f"   ✓ Rework order created: {rework_order_id}")
                rework_created = True

            except Exception as api_error:
                print(f"   ✗ API error: {api_error}")
                # Try to get more error details
                if hasattr(api_error, 'response'):
                    print(f"   Response: {api_error.response.text[:500]}")
                raise

        except Exception as e:
            print(f"   ✗ Failed to create rework order: {e}")

        # Build message
        message = f"⚠️ Defect detected: {classified_product}\n"
        message += f"Order NOT completed (defective piece)\n"
        message += f"Defects logged: {len(self.defects_detected)}\n"
        if rework_created:
            message += f"✓ Rework order created ({len(self.rework_orders)} total)"
        else:
            message += "⚠️ Rework order creation failed"

        print(f"   {message}")

        return True, message

    def get_current_phase_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current active order
        (kept for backward compatibility)

        Returns:
            Order info dict or None
        """
        return self.get_current_order_info()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get production statistics

        Returns:
            Statistics dict
        """
        return {
            'completed_orders': len(self.completed_orders),
            'total_orders': len(self.scheduled_orders),
            'remaining_orders': len(self.scheduled_orders) - len(self.completed_orders),
            'defects_detected': len(self.defects_detected),
            'rework_orders_created': len(self.rework_orders),
            'current_order': self.get_current_order_info()
        }
