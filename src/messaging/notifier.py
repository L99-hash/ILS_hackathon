"""Human-in-the-loop messaging for production schedule approval"""

from typing import List
from datetime import datetime
import plotly.express as px
import plotly.io as pio
import pandas as pd


class ScheduleNotifier:
    """Sends production schedule to planner for approval"""

    @staticmethod
    def build_gantt_chart(scheduled_orders: List, policy_name: str = "EDF (Earliest Deadline First)"):
        """
        Build a Plotly Gantt chart from scheduled orders.

        Args:
            scheduled_orders: List of (ProductionOrder, scheduled_response) tuples
            policy_name: Name of the scheduling policy used

        Returns:
            A Plotly Figure object, or None if no valid orders
        """
        rows = []
        task_counts = {}  # track how many times each product name appears

        for prod_order, scheduled_response in scheduled_orders:
            starts_at = scheduled_response.get("starts_at")
            ends_at = scheduled_response.get("ends_at")
            if not starts_at or not ends_at:
                continue

            product_name = prod_order.product_name

            # --- FIX: assign sub-row label if product appears more than once ---
            task_counts[product_name] = task_counts.get(product_name, 0) + 1
            count = task_counts[product_name]
            task_label = f"{product_name} #{count}" if count > 1 else product_name

            # Include order ID and quantity in the task label so it's always visible
            order_id = scheduled_response.get("id", "Unknown")
            quantity = prod_order.quantity
            task_label_with_id = f"{task_label} (x{quantity}) [{order_id}]"

            rows.append(
                dict(
                    Task=task_label_with_id,
                    Start=starts_at,
                    Finish=ends_at,
                    Priority=f"P{prod_order.priority}",
                    Deadline=prod_order.ends_at.strftime("%Y-%m-%d %H:%M"),
                    SalesOrder=", ".join(prod_order.source_sales_orders),
                    Quantity=prod_order.quantity,
                    OrderID=order_id,
                )
            )

        # --- FIX: retroactively rename the first occurrence to "#1" if there are duplicates ---
        # e.g. if "PCB-IND-100" appears twice, rename the first entry from "PCB-IND-100" to "PCB-IND-100 #1"
        final_task_counts = task_counts  # already has final counts after the loop
        for row in rows:
            # Extract base name (before # and before [OrderID])
            task_part = row["Task"].split(" [")[0]  # Remove [OrderID] part
            base_name = task_part.split(" #")[0]
            if final_task_counts.get(base_name, 1) > 1 and " #" not in task_part:
                order_id_part = row["Task"].split(" [")[1] if " [" in row["Task"] else ""
                row["Task"] = f"{base_name} #1 [{order_id_part}" if order_id_part else f"{base_name} #1"

        if not rows:
            return None

        df = pd.DataFrame(rows)

        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color="Priority",
            hover_data=["SalesOrder", "Quantity", "Deadline", "OrderID"],
            title=f"Production Schedule — {policy_name}",
            labels={"Task": "Product", "Priority": "Priority"},
        )

        # No text inside bars - Order ID is now in the task label on the left

        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            xaxis_title="Timeline",
            yaxis_title="Production Order",
            legend_title="Priority",
            height=max(300, 80 * len(rows)),
        )

        # Add deadline markers as vertical lines positioned at each task's row
        from datetime import timezone

        # Get task labels in order (for Y-axis positioning)
        task_labels = df["Task"].tolist()

        for idx, row in enumerate(rows):
            deadline_str = row["Deadline"]
            deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            deadline_ms = deadline_dt.timestamp() * 1000
            task_name = row["Task"]

            # Add a vertical line shape at this specific task's row
            # Y coordinates: idx (top of bar) to idx+0.9 (bottom of bar)
            fig.add_shape(
                type="line",
                x0=deadline_ms,
                x1=deadline_ms,
                y0=idx - 0.4,  # Slightly above the bar
                y1=idx + 0.4,  # Slightly below the bar
                line=dict(
                    color="red",
                    width=2,
                    dash="dot",
                ),
                yref="y",
                xref="x",
            )

        return fig
    

    @staticmethod
    def send_gantt_to_telegram(bot_token: str, chat_id: str, scheduled_orders: List) -> bool:
        """
        Render the Gantt chart as a PNG and send it to Telegram as a photo.

        Requires: kaleido

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to send to
            scheduled_orders: List of (ProductionOrder, scheduled_response) tuples

        Returns:
            True if photo sent successfully, False otherwise
        """
        import requests
        import tempfile
        import os

        if not bot_token or "your_bot_token_here" in bot_token:
            print("Note: No valid Telegram bot token configured.")
            return False

        if not chat_id or "your_chat_id_here" in chat_id:
            print("Note: No valid Telegram chat ID configured.")
            return False

        fig = ScheduleNotifier.build_gantt_chart(scheduled_orders)
        if fig is None:
            print("⚠ No schedulable orders found — Gantt chart skipped.")
            return False

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            pio.write_image(
                fig,
                tmp_path,
                format="png",
                width=1400,
                height=max(400, 80 * len(scheduled_orders)),
            )

            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            with open(tmp_path, "rb") as photo:
                response = requests.post(
                    url,
                    data={
                        "chat_id": chat_id,
                        "caption": "📊 Production Schedule — Gantt Chart\nRed lines indicate customer deadlines.",
                    },
                    files={"photo": photo},
                )
            response.raise_for_status()
            print("📊 Gantt chart sent to Telegram successfully!")
            return True

        except Exception as e:
            print(f"Failed to send Gantt chart to Telegram: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    print(f"Telegram API error: {e.response.json()}")
                except Exception:
                    pass
            return False

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)


    @staticmethod
    def format_schedule_message(production_orders: List, scheduled_orders: List, policy_name: str = "EDF (Earliest Deadline First)"):
        """
        Format production schedule for human approval

        Args:
            production_orders: List of ProductionOrder objects from planning
            scheduled_orders: List of (ProductionOrder, scheduled_response) tuples from API
            policy_name: Name of the scheduling policy used

        Returns:
            Formatted message string
            scheduled_orders (used to build the gantt chart)
        """
        message = []
        message.append("=" * 60)
        message.append("📋 *Production Schedule* - Awaiting your approval")
        message.append("=" * 60)
        message.append("")
        message.append(f"Total Orders: {len(scheduled_orders)}")
        message.append(f"Scheduling Policy: {policy_name}")
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
            message.append("⚠️ Key scheduling decisions:")
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

        return "\n".join(message), scheduled_orders

    @staticmethod
    def print_schedule(production_orders: List, created_order_ids: List):
        """Print formatted schedule to console"""
        message, scheduled_orders = ScheduleNotifier.format_schedule_message(production_orders, created_order_ids)
        fig = ScheduleNotifier.build_gantt_chart(scheduled_orders)
        if fig is None:
            print("⚠ No schedulable orders found — Gantt chart skipped.")
            return False
        print(message)

    @staticmethod
    def send_to_telegram(bot_token: str, chat_id: str, message: str, scheduled_orders, fig) -> bool:
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
        import tempfile
        import time

        if not bot_token or 'your_bot_token_here' in bot_token:
            print("Note: No valid Telegram bot token configured. Displaying message only.")
            return False

        if not chat_id or 'your_chat_id_here' in chat_id:
            print("Note: No valid Telegram chat ID configured. Displaying message only.")
            return False
        
        if fig is not None:
            try: 
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name

                pio.write_image(
                    fig,
                    tmp_path,
                    format="png",
                    width=1400,
                    height=max(400, 80 * len(scheduled_orders)),
                )

                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(tmp_path, "rb") as photo:
                    response = requests.post(
                        url,
                        data={
                            "chat_id": chat_id,
                            "caption": "📊 Production Schedule — Gantt Chart\nRed lines indicate customer deadlines.",
                        },
                        files={"photo": photo},
                    )
                response.raise_for_status()
                print("📊 Gantt chart sent to Telegram successfully!")

            except Exception as e:
                print(f"Failed to send Gantt chart to Telegram: {e}")
                if hasattr(e, "response") and e.response is not None:
                    try:
                        print(f"Telegram API error: {e.response.json()}")
                    except Exception:
                        pass

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
