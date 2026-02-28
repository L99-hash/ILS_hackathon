"""Human-in-the-loop messaging for production schedule approval"""

from typing import List
from datetime import datetime


class ScheduleNotifier:
    """Sends production schedule to planner for approval"""

    @staticmethod
    def format_schedule_message(production_orders: List, created_order_ids: List) -> str:
        """
        Format production schedule for human approval

        Args:
            production_orders: List of ProductionOrder objects from planning
            created_order_ids: List of (ProductionOrder, response) tuples from API

        Returns:
            Formatted message string
        """
        message = []
        message.append("=" * 60)
        message.append("PRODUCTION SCHEDULE - APPROVAL REQUIRED")
        message.append("=" * 60)
        message.append("")
        message.append(f"Total Orders: {len(production_orders)}")
        message.append(f"Scheduling Policy: EDF (Earliest Deadline First)")
        message.append("")

        # Display schedule
        message.append("PROPOSED SCHEDULE:")
        message.append("-" * 60)

        for i, (prod_order, response) in enumerate(created_order_ids, 1):
            order_id = response.get('id', 'Unknown')
            starts = prod_order.ends_at.strftime('%Y-%m-%d %H:%M')  # Using ends_at as reference
            ends = prod_order.ends_at.strftime('%Y-%m-%d %H:%M')

            message.append(f"\n{i}. {prod_order.product_name}")
            message.append(f"   Order ID: {order_id}")
            message.append(f"   Quantity: {prod_order.quantity} units")
            message.append(f"   Deadline: {ends}")
            message.append(f"   Priority: P{prod_order.priority}")
            message.append(f"   Source: {', '.join(prod_order.source_sales_orders)}")

        # EDF Reasoning
        message.append("")
        message.append("=" * 60)
        message.append("EDF SCHEDULING REASONING")
        message.append("=" * 60)
        message.append("")
        message.append("This schedule prioritizes orders by DEADLINE, not priority level.")
        message.append("")
        message.append("Key scheduling decisions:")
        message.append("- Orders are sequenced by earliest deadline first")
        message.append("- When deadlines are equal, lower priority number (P1 > P2) takes precedence")
        message.append("- This ensures all orders meet their delivery deadlines")
        message.append("")
        message.append("This approach prevents late deliveries that would occur with")
        message.append("priority-only scheduling.")
        message.append("")

        # Footer
        message.append("=" * 60)
        message.append("Please review and respond:")
        message.append("  - Type 'APPROVE' to confirm and start production")
        message.append("  - Type 'REJECT' to request changes")
        message.append("=" * 60)

        return "\n".join(message)

    @staticmethod
    def print_schedule(production_orders: List, created_order_ids: List):
        """Print formatted schedule to console"""
        message = ScheduleNotifier.format_schedule_message(production_orders, created_order_ids)
        print(message)

    @staticmethod
    def send_to_telegram(bot_token: str, chat_id: str, message: str) -> bool:
        """
        Send message to Telegram using Bot API

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to send message to
            message: Formatted message

        Returns:
            True if successful, False otherwise
        """
        import requests

        if not bot_token or 'your_bot_token_here' in bot_token:
            print("Note: No valid Telegram bot token configured. Displaying message only.")
            return False

        if not chat_id or 'your_chat_id_here' in chat_id:
            print("Note: No valid Telegram chat ID configured. Displaying message only.")
            return False

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
            print("Schedule sent to Telegram successfully!")
            return True
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return False

    @staticmethod
    def send_to_webhook(webhook_url: str, message: str) -> bool:
        """
        Send message to webhook (Slack, Discord, etc.)

        Args:
            webhook_url: Webhook URL
            message: Formatted message

        Returns:
            True if successful, False otherwise
        """
        import requests

        if not webhook_url or 'example.com' in webhook_url:
            print("Note: No valid webhook URL configured. Displaying message only.")
            return False

        try:
            payload = {"text": message}
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to send webhook: {e}")
            return False
