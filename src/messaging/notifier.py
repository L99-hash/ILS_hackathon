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
    def wait_for_telegram_approval(bot_token: str, chat_id: str, timeout: int = 300) -> str:
        """
        Wait for user approval response via Telegram

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to monitor
            timeout: Maximum seconds to wait for response (default 300 = 5 minutes)

        Returns:
            'APPROVE' or 'REJECT' based on user response, or 'TIMEOUT' if no response
        """
        import requests
        import time

        if not bot_token or 'your_bot_token_here' in bot_token:
            print("Error: No valid Telegram bot token configured.")
            return 'TIMEOUT'

        if not chat_id or 'your_chat_id_here' in chat_id:
            print("Error: No valid Telegram chat ID configured.")
            return 'TIMEOUT'

        print(f"\nWaiting for approval via Telegram (timeout: {timeout}s)...")
        print("Please respond in Telegram with 'APPROVE' or 'REJECT'")

        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        start_time = time.time()
        last_update_id = None

        # Get the latest update_id to ignore old messages
        try:
            response = requests.get(url, params={"offset": -1}, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("ok") and data.get("result"):
                last_update_id = data["result"][-1]["update_id"]
        except Exception as e:
            print(f"Warning: Could not get initial update ID: {e}")

        # Poll for new messages
        while time.time() - start_time < timeout:
            try:
                params = {}
                if last_update_id is not None:
                    params["offset"] = last_update_id + 1
                params["timeout"] = 10  # Long polling timeout

                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()

                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        last_update_id = update["update_id"]

                        # Check if it's a message from the correct chat
                        if "message" in update:
                            msg = update["message"]
                            if str(msg.get("chat", {}).get("id")) == str(chat_id):
                                text = msg.get("text", "").strip().upper()

                                if text == "APPROVE":
                                    print("\n✓ Schedule APPROVED via Telegram")
                                    return "APPROVE"
                                elif text == "REJECT":
                                    print("\n✗ Schedule REJECTED via Telegram")
                                    return "REJECT"
                                elif text in ["APPROVE", "REJECT"]:
                                    # In case there are variations
                                    print(f"\nReceived: {text}")
                                    return text

                # Small delay to avoid hammering the API
                time.sleep(1)

            except Exception as e:
                print(f"Error polling Telegram: {e}")
                time.sleep(2)

        print(f"\n⚠ Timeout: No response received within {timeout} seconds")
        return "TIMEOUT"

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
