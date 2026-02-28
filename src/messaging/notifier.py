"""Human-in-the-loop messaging for production schedule approval"""

from typing import List
from datetime import datetime


class ScheduleNotifier:
    """Sends production schedule to planner for approval"""

    @staticmethod
    def format_schedule_message(production_orders: List, scheduled_orders: List) -> str:
        """
        Format production schedule for human approval

        Args:
            production_orders: List of ProductionOrder objects from planning
            scheduled_orders: List of (ProductionOrder, scheduled_response) tuples from API

        Returns:
            Formatted message string
        """
        message = []
        message.append("=" * 60)
        message.append("PRODUCTION SCHEDULE - APPROVAL REQUIRED")
        message.append("=" * 60)
        message.append("")
        message.append(f"Total Orders: {len(scheduled_orders)}")
        message.append(f"Scheduling Policy: EDF (Earliest Deadline First)")
        message.append("")

        # Display schedule with actual start/end dates from phases
        message.append("PROPOSED SCHEDULE:")
        message.append("-" * 60)

        for i, (prod_order, scheduled_response) in enumerate(scheduled_orders, 1):
            order_id = scheduled_response.get('id', 'Unknown')
            starts_at = scheduled_response.get('starts_at', 'N/A')
            ends_at = scheduled_response.get('ends_at', 'N/A')
            status = scheduled_response.get('status', 'unknown')
            duration = scheduled_response.get('duration', 0)

            # Format dates
            if starts_at != 'N/A':
                starts_at = starts_at[:16].replace('T', ' ')
            if ends_at != 'N/A':
                ends_at = ends_at[:16].replace('T', ' ')

            # Get deadline from production order
            deadline = prod_order.ends_at.strftime('%Y-%m-%d %H:%M')

            message.append(f"\n{i}. {prod_order.product_name}")
            message.append(f"   Production Order: {order_id}")
            message.append(f"   Source Sales Order: {', '.join(prod_order.source_sales_orders)}")
            message.append(f"   Quantity: {prod_order.quantity} units")
            message.append(f"   Production Start: {starts_at}")
            message.append(f"   Production End: {ends_at}")
            message.append(f"   Duration: {duration} minutes ({duration/60:.1f} hours)")
            message.append(f"   Customer Deadline: {deadline}")
            message.append(f"   Priority: P{prod_order.priority}")
            message.append(f"   Status: {status}")

        # EDF Reasoning with specific examples
        message.append("")
        message.append("=" * 60)
        message.append("EDF SCHEDULING REASONING")
        message.append("=" * 60)
        message.append("")
        message.append("This schedule prioritizes orders by DEADLINE, not priority level.")
        message.append("")

        # Find examples of priority conflicts resolved by EDF
        conflicts_found = []
        for i in range(len(scheduled_orders) - 1):
            current_order, _ = scheduled_orders[i]
            next_order, _ = scheduled_orders[i + 1]

            # Check if lower priority scheduled before higher priority due to deadline
            if current_order.priority > next_order.priority:
                current_so = current_order.source_sales_orders[0] if current_order.source_sales_orders else "Unknown"
                next_so = next_order.source_sales_orders[0] if next_order.source_sales_orders else "Unknown"
                current_deadline = current_order.ends_at.strftime('%b %d')
                next_deadline = next_order.ends_at.strftime('%b %d')

                reason = (f"- {current_so} (deadline {current_deadline}, P{current_order.priority}) "
                         f"scheduled before {next_so} (deadline {next_deadline}, P{next_order.priority}) "
                         f"— EDF prioritizes tighter deadlines")
                conflicts_found.append(reason)

        if conflicts_found:
            message.append("Key scheduling decisions:")
            for conflict in conflicts_found[:3]:  # Show up to 3 examples
                message.append(conflict)
            message.append("")

        message.append("EDF ensures:")
        message.append("- Orders with earlier deadlines are produced first")
        message.append("- All customer delivery deadlines are met")
        message.append("- No late deliveries due to priority-only scheduling")
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
        Automatically splits long messages into multiple parts

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to send message to
            message: Formatted message

        Returns:
            True if all messages sent successfully, False otherwise
        """
        import requests
        import time

        if not bot_token or 'your_bot_token_here' in bot_token:
            print("Note: No valid Telegram bot token configured. Displaying message only.")
            return False

        if not chat_id or 'your_chat_id_here' in chat_id:
            print("Note: No valid Telegram chat ID configured. Displaying message only.")
            return False

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            max_length = 4000  # Telegram limit is 4096, leave margin

            # Split message into chunks if needed
            message_parts = []
            if len(message) <= max_length:
                message_parts = [message]
            else:
                # Split at newlines to keep message readable
                lines = message.split('\n')
                current_part = ""

                for line in lines:
                    if len(current_part) + len(line) + 1 <= max_length:
                        current_part += line + '\n'
                    else:
                        if current_part:
                            message_parts.append(current_part)
                        current_part = line + '\n'

                if current_part:
                    message_parts.append(current_part)

            # Send all parts
            for i, part in enumerate(message_parts, 1):
                if len(message_parts) > 1:
                    # Add part indicator
                    prefix = f"[Part {i}/{len(message_parts)}]\n\n"
                    part = prefix + part

                payload = {
                    "chat_id": chat_id,
                    "text": part
                }
                response = requests.post(url, json=payload)
                response.raise_for_status()

                # Small delay between messages to avoid rate limiting
                if i < len(message_parts):
                    time.sleep(0.5)

            if len(message_parts) > 1:
                print(f"Schedule sent to Telegram in {len(message_parts)} parts successfully!")
            else:
                print("Schedule sent to Telegram successfully!")
            return True

        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"Telegram API error: {error_detail}")
                except:
                    pass
            return False

    @staticmethod
    def wait_for_telegram_approval(bot_token: str, chat_id: str, timeout: int = 300) -> tuple:
        """
        Wait for user approval response via Telegram

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to monitor
            timeout: Maximum seconds to wait for response (default 300 = 5 minutes)

        Returns:
            Tuple of (decision, reason) where:
            - decision: 'APPROVE', 'REJECT', or 'TIMEOUT'
            - reason: None for APPROVE, rejection reason for REJECT, None for TIMEOUT
        """
        import requests
        import time

        if not bot_token or 'your_bot_token_here' in bot_token:
            print("Error: No valid Telegram bot token configured.")
            return ('TIMEOUT', None)

        if not chat_id or 'your_chat_id_here' in chat_id:
            print("Error: No valid Telegram chat ID configured.")
            return ('TIMEOUT', None)

        print(f"\nWaiting for approval via Telegram (timeout: {timeout}s)...")
        print("Please respond in Telegram with:")
        print("  - 'APPROVE' to confirm")
        print("  - 'REJECT: <reason>' to reject with explanation")

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
                                text = msg.get("text", "").strip()
                                text_upper = text.upper()

                                if text_upper == "APPROVE":
                                    print("\n✓ Schedule APPROVED via Telegram")
                                    return ("APPROVE", None)
                                elif text_upper.startswith("REJECT"):
                                    # Extract reason after "REJECT:" or "REJECT "
                                    reason = text[6:].strip() if len(text) > 6 else "No reason provided"
                                    if reason.startswith(':'):
                                        reason = reason[1:].strip()
                                    print(f"\n✗ Schedule REJECTED via Telegram")
                                    print(f"  Reason: {reason}")
                                    return ("REJECT", reason)

                # Small delay to avoid hammering the API
                time.sleep(1)

            except Exception as e:
                print(f"Error polling Telegram: {e}")
                time.sleep(2)

        print(f"\n⚠ Timeout: No response received within {timeout} seconds")
        return ("TIMEOUT", None)

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
