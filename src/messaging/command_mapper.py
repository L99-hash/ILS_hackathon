"""
Natural Language Command Interpreter using Gemini AI

Maps user messages to predefined commands (CAPTURE, GANTT, policy selection, etc.)
"""

import os
import re
import google.generativeai as genai
from typing import Optional, Literal, Tuple


class CommandMapper:
    """
    Uses Gemini AI to interpret natural language and map to special commands

    Supported commands:
    - CAPTURE: Take photo, capture frame, snap image, etc.
    - GANTT: Show schedule, production plan, timeline, etc.
    - Policy selection: EDF, GROUP_BY_PRODUCT, SPLIT_IN_BATCHES
    - UNKNOWN: Anything else
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CommandMapper with Gemini API

        Args:
            api_key: Gemini API key (if None, loads from GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key and 'your_gemini_api_key_here' not in self.api_key)

        # Simple cache to avoid redundant API calls
        self.cache = {}

        if self.enabled:
            try:
                genai.configure(api_key=self.api_key)
                # Use Gemini 2.5 Flash (fast, accurate, great for command classification)
                self.model = genai.GenerativeModel('models/gemini-2.5-flash')
                print("✓ Gemini AI command interpreter enabled (gemini-2.5-flash)")
            except Exception as e:
                print(f"✗ Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            print("✗ Gemini API key not configured (using exact keyword matching)")

    def interpret_command(self, user_text: str) -> Literal["CAPTURE", "GANTT", "UNKNOWN"]:
        """
        Interpret user's natural language message and map to a command

        Args:
            user_text: The message from the user

        Returns:
            One of: "CAPTURE", "GANTT", "UNKNOWN"
        """
        if not user_text or not user_text.strip():
            return "UNKNOWN"

        # Normalize input
        normalized = user_text.strip().upper()

        # Check cache first
        if normalized in self.cache:
            return self.cache[normalized]

        # Fallback to exact matching if Gemini not enabled
        if not self.enabled:
            result = self._exact_match(normalized)
            self.cache[normalized] = result
            return result

        # Use Gemini AI for interpretation
        try:
            result = self._gemini_interpret(user_text)
            self.cache[normalized] = result
            return result
        except Exception as e:
            print(f"⚠️ Gemini API error: {e}, falling back to exact match")
            result = self._exact_match(normalized)
            self.cache[normalized] = result
            return result

    def _exact_match(self, normalized_text: str) -> Literal["CAPTURE", "GANTT", "UNKNOWN"]:
        """
        Fallback exact keyword matching (original behavior)

        Args:
            normalized_text: Uppercase text to match

        Returns:
            Matched command or UNKNOWN
        """
        # CAPTURE keywords
        if normalized_text in ["CAPTURE", "PHOTO", "SNAP", "PICTURE", "IMAGE", "TAKE", "SHOT"]:
            return "CAPTURE"

        # GANTT keywords
        if normalized_text in ["GANTT", "SCHEDULE", "PLAN", "TIMELINE", "CHART"]:
            return "GANTT"

        return "UNKNOWN"

    def _gemini_interpret(self, user_text: str) -> Literal["CAPTURE", "GANTT", "UNKNOWN"]:
        """
        Use Gemini AI to interpret the command

        Args:
            user_text: Raw user message

        Returns:
            Interpreted command
        """
        prompt = f"""You are a command interpreter for a production monitoring system.

The user can send two types of commands:

1. CAPTURE - Request to take a photo/image from the camera
   Examples: "take a photo", "capture frame", "snap picture", "grab image", "take a shot", "get a pic"

2. GANTT - Request to see the production schedule/timeline
   Examples: "show schedule", "production plan", "gantt chart", "timeline", "show me the plan", "what's the schedule"

User message: "{user_text}"

Respond with ONLY one word: CAPTURE, GANTT, or UNKNOWN (if neither)
"""

        response = self.model.generate_content(prompt)
        result = response.text.strip().upper()

        # Validate response
        if result in ["CAPTURE", "GANTT", "UNKNOWN"]:
            return result

        # If Gemini returns unexpected response, try to extract
        if "CAPTURE" in result:
            return "CAPTURE"
        elif "GANTT" in result:
            return "GANTT"
        else:
            return "UNKNOWN"

    def interpret_policy(self, user_text: str) -> Tuple[str, Optional[int]]:
        """
        Interpret user's policy selection and extract batch size if applicable

        Args:
            user_text: The message from the user (e.g., "1", "EDF", "split batches", "3:15")

        Returns:
            Tuple of (policy_choice, batch_size)
            - policy_choice: "1", "2", or "3"
            - batch_size: int if policy 3 with custom size, else None
        """
        if not user_text or not user_text.strip():
            return ("UNKNOWN", None)

        text = user_text.strip()

        # Check for batch size specification (e.g., "3:15" or "batch:20")
        batch_size = None
        batch_match = re.search(r'[:\s](\d+)', text)
        if batch_match:
            batch_size = int(batch_match.group(1))
            # Remove batch size from text for policy interpretation
            text = re.sub(r'[:\s]\d+', '', text).strip()

        # Normalize input
        normalized = text.upper()

        # Check cache
        cache_key = f"policy_{normalized}"
        if cache_key in self.cache:
            return (self.cache[cache_key], batch_size)

        # Exact matching first (fast path)
        if normalized in ["1", "FIRST", "1ST", "ONE", "EDF", "EARLIEST", "DEADLINE"]:
            self.cache[cache_key] = "1"
            return ("1", batch_size)
        elif normalized in ["2", "SECOND", "2ND", "TWO", "GROUP", "MERGE", "PRODUCT"]:
            self.cache[cache_key] = "2"
            return ("2", batch_size)
        elif normalized in ["3", "THIRD", "3RD", "THREE", "BATCH", "SPLIT", "BATCHES"]:
            self.cache[cache_key] = "3"
            return ("3", batch_size)

        # Use Gemini AI for interpretation if enabled
        if self.enabled:
            try:
                result = self._gemini_interpret_policy(text)
                self.cache[cache_key] = result
                return (result, batch_size)
            except Exception as e:
                print(f"⚠️ Gemini API error for policy interpretation: {e}")
                return ("UNKNOWN", batch_size)

        return ("UNKNOWN", batch_size)

    def _gemini_interpret_policy(self, user_text: str) -> str:
        """
        Use Gemini AI to interpret the policy selection

        Args:
            user_text: Raw user message

        Returns:
            "1", "2", "3", or "UNKNOWN"
        """
        prompt = f"""You are interpreting a production planning policy selection.

The user can choose from 3 policies:

1. EDF (Earliest Deadline First)
   Keywords: "EDF", "deadline", "earliest", "by deadline", "1"

2. Group by Product
   Keywords: "group", "merge", "by product", "same product", "2"

3. Split in Batches
   Keywords: "batch", "split", "batches", "cap size", "3"

User message: "{user_text}"

Respond with ONLY one character: 1, 2, or 3
If you cannot determine the policy, respond with: UNKNOWN
"""

        response = self.model.generate_content(prompt)
        result = response.text.strip().upper()

        # Validate response
        if result in ["1", "2", "3"]:
            return result

        # Try to extract from response
        if "1" in result or "EDF" in result:
            return "1"
        elif "2" in result or "GROUP" in result:
            return "2"
        elif "3" in result or "BATCH" in result:
            return "3"
        else:
            return "UNKNOWN"

    def interpret_confirmation(self, user_text: str) -> Literal["YES", "NO", "UNKNOWN"]:
        """
        Interpret user's confirmation response (YES/NO)

        Args:
            user_text: The message from the user (e.g., "yes", "sure", "go ahead", "no", "cancel")

        Returns:
            "YES", "NO", or "UNKNOWN"
        """
        if not user_text or not user_text.strip():
            return "UNKNOWN"

        # Normalize input
        normalized = user_text.strip().upper()

        # Check cache
        cache_key = f"confirm_{normalized}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Exact matching first (fast path)
        # YES variations
        if normalized in ["YES", "Y", "YEP", "YEAH", "YA", "SURE", "OK", "OKAY", "CONFIRM", "CONFIRMED",
                         "GO", "GO AHEAD", "PROCEED", "CONTINUE", "DO IT", "APPROVE", "APPROVED",
                         "ACCEPT", "ACCEPTED", "AGREE", "AFFIRMATIVE", "👍", "✓", "✅"]:
            self.cache[cache_key] = "YES"
            return "YES"

        # NO variations
        elif normalized in ["NO", "N", "NOPE", "NAH", "NAH", "CANCEL", "CANCELLED", "STOP", "ABORT",
                           "REJECT", "REJECTED", "DECLINE", "DECLINED", "DISAGREE", "NEGATIVE",
                           "DENY", "DENIED", "👎", "❌", "✗"]:
            self.cache[cache_key] = "NO"
            return "NO"

        # Use Gemini AI for interpretation if enabled
        if self.enabled:
            try:
                result = self._gemini_interpret_confirmation(user_text)
                self.cache[cache_key] = result
                return result
            except Exception as e:
                print(f"⚠️ Gemini API error for confirmation interpretation: {e}")
                return "UNKNOWN"

        return "UNKNOWN"

    def _gemini_interpret_confirmation(self, user_text: str) -> Literal["YES", "NO", "UNKNOWN"]:
        """
        Use Gemini AI to interpret the confirmation response

        Args:
            user_text: Raw user message

        Returns:
            "YES", "NO", or "UNKNOWN"
        """
        prompt = f"""You are interpreting a YES/NO confirmation response.

The user is being asked to confirm an action (like creating production orders).

YES responses include: "yes", "sure", "go ahead", "confirm", "do it", "ok", "proceed", "I agree"
NO responses include: "no", "cancel", "stop", "don't", "nope", "abort", "reject", "I disagree"

User message: "{user_text}"

Respond with ONLY one word: YES, NO, or UNKNOWN (if unclear)
"""

        response = self.model.generate_content(prompt)
        result = response.text.strip().upper()

        # Validate response
        if result in ["YES", "NO", "UNKNOWN"]:
            return result

        # Try to extract from response
        if "YES" in result or "CONFIRM" in result or "APPROVE" in result:
            return "YES"
        elif "NO" in result or "CANCEL" in result or "REJECT" in result:
            return "NO"
        else:
            return "UNKNOWN"

    def interpret_approval(self, user_text: str) -> Literal["APPROVE", "REJECT", "UNKNOWN"]:
        """
        Interpret user's approval/rejection response for schedule

        Args:
            user_text: The message from the user (e.g., "approve", "looks good", "reject", "change it")

        Returns:
            "APPROVE", "REJECT", or "UNKNOWN"
        """
        if not user_text or not user_text.strip():
            return "UNKNOWN"

        # Normalize input
        normalized = user_text.strip().upper()

        # Check cache
        cache_key = f"approve_{normalized}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Exact matching first (fast path)
        # APPROVE variations
        if normalized in ["APPROVE", "APPROVED", "YES", "Y", "ACCEPT", "ACCEPTED", "CONFIRM", "CONFIRMED",
                         "OK", "OKAY", "GOOD", "LOOKS GOOD", "PERFECT", "GO", "GO AHEAD", "PROCEED",
                         "START", "START PRODUCTION", "CONTINUE", "AGREE", "👍", "✓", "✅"]:
            self.cache[cache_key] = "APPROVE"
            return "APPROVE"

        # REJECT variations
        elif normalized in ["REJECT", "REJECTED", "NO", "N", "DECLINE", "DECLINED", "CANCEL", "CANCELLED",
                           "STOP", "CHANGE", "MODIFY", "REVISE", "REDO", "NOT GOOD", "DISAGREE",
                           "👎", "❌", "✗"]:
            self.cache[cache_key] = "REJECT"
            return "REJECT"

        # Use Gemini AI for interpretation if enabled
        if self.enabled:
            try:
                result = self._gemini_interpret_approval(user_text)
                self.cache[cache_key] = result
                return result
            except Exception as e:
                print(f"⚠️ Gemini API error for approval interpretation: {e}")
                return "UNKNOWN"

        return "UNKNOWN"

    def _gemini_interpret_approval(self, user_text: str) -> Literal["APPROVE", "REJECT", "UNKNOWN"]:
        """
        Use Gemini AI to interpret the approval/rejection response

        Args:
            user_text: Raw user message

        Returns:
            "APPROVE", "REJECT", or "UNKNOWN"
        """
        prompt = f"""You are interpreting an APPROVE/REJECT response for a production schedule.

The user is being asked to review and approve or reject a proposed production schedule.

APPROVE responses include: "approve", "looks good", "yes", "ok", "accept", "confirm", "go ahead", "start production", "I agree with this schedule"
REJECT responses include: "reject", "no", "change it", "modify", "not good", "I disagree", "needs changes", "redo this"

User message: "{user_text}"

Respond with ONLY one word: APPROVE, REJECT, or UNKNOWN (if unclear)
"""

        response = self.model.generate_content(prompt)
        result = response.text.strip().upper()

        # Validate response
        if result in ["APPROVE", "REJECT", "UNKNOWN"]:
            return result

        # Try to extract from response
        if "APPROVE" in result or "ACCEPT" in result or "CONFIRM" in result:
            return "APPROVE"
        elif "REJECT" in result or "DECLINE" in result or "CANCEL" in result:
            return "REJECT"
        else:
            return "UNKNOWN"

    def interpret_adjustment(self, user_text: str) -> Tuple[str, list]:
        """
        Interpret user's schedule adjustment command

        Args:
            user_text: The message from the user (e.g., "SWAP 1 3", "swap orders 1 and 3", "move 5 to 2")

        Returns:
            Tuple of (command_type, parameters)
            - command_type: "SWAP", "MOVE", "DATES", "EXIT", or "UNKNOWN"
            - parameters: List of extracted parameters (order numbers, positions, days)
        """
        if not user_text or not user_text.strip():
            return ("UNKNOWN", [])

        text = user_text.strip()
        normalized = text.upper()

        # Check cache
        cache_key = f"adjust_{normalized}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            return (cached_result[0], cached_result[1])

        # Exact matching first (fast path) - parse standard format
        # SWAP format: "SWAP 1 3" or "SWAP <num1> <num2>"
        swap_match = re.match(r'SWAP\s+(\d+)\s+(\d+)', normalized)
        if swap_match:
            params = [int(swap_match.group(1)), int(swap_match.group(2))]
            self.cache[cache_key] = ("SWAP", params)
            return ("SWAP", params)

        # MOVE format: "MOVE 5 TO 2" or "MOVE <num> TO <pos>"
        move_match = re.match(r'MOVE\s+(\d+)\s+TO\s+(\d+)', normalized)
        if move_match:
            params = [int(move_match.group(1)), int(move_match.group(2))]
            self.cache[cache_key] = ("MOVE", params)
            return ("MOVE", params)

        # DATES format: "DATES 3 +2" or "DATES <num> +<days>"
        dates_match = re.match(r'DATES\s+(\d+)\s+\+(\d+)', normalized)
        if dates_match:
            params = [int(dates_match.group(1)), int(dates_match.group(2))]
            self.cache[cache_key] = ("DATES", params)
            return ("DATES", params)

        # EXIT
        if normalized in ["EXIT", "CANCEL", "QUIT", "STOP", "ABORT"]:
            self.cache[cache_key] = ("EXIT", [])
            return ("EXIT", [])

        # Use Gemini AI for natural language interpretation if enabled
        if self.enabled:
            try:
                result = self._gemini_interpret_adjustment(text)
                self.cache[cache_key] = result
                return result
            except Exception as e:
                print(f"⚠️ Gemini API error for adjustment interpretation: {e}")
                return ("UNKNOWN", [])

        return ("UNKNOWN", [])

    def _gemini_interpret_adjustment(self, user_text: str) -> Tuple[str, list]:
        """
        Use Gemini AI to interpret the adjustment command

        Args:
            user_text: Raw user message

        Returns:
            Tuple of (command_type, parameters)
        """
        prompt = f"""You are interpreting a production schedule adjustment command.

The user can use these commands:

1. SWAP - Swap positions of two orders
   Examples: "swap orders 1 and 3", "switch 2 with 5", "interchange positions 1 and 4"
   Format: Extract two order numbers

2. MOVE - Move an order to a specific position
   Examples: "move order 5 to position 2", "put 3 in slot 1", "move 4 to 2"
   Format: Extract order number and target position

3. DATES - Delay an order by adding days
   Examples: "delay order 3 by 2 days", "push order 1 back 5 days", "add 3 days to order 2"
   Format: Extract order number and number of days

4. EXIT - Cancel adjustments and restart
   Examples: "exit", "cancel", "quit", "stop"

User message: "{user_text}"

Respond ONLY in this exact format:
COMMAND_TYPE|param1|param2

Examples of valid responses:
SWAP|1|3
MOVE|5|2
DATES|3|2
EXIT
UNKNOWN
"""

        response = self.model.generate_content(prompt)
        result = response.text.strip().upper()

        # Parse response
        if "|" in result:
            parts = result.split("|")
            command = parts[0]
            params = [int(p) for p in parts[1:] if p.isdigit()]
            return (command, params)
        elif result in ["EXIT", "CANCEL", "QUIT"]:
            return ("EXIT", [])
        else:
            return ("UNKNOWN", [])

    def interpret_camera_selection(self, user_text: str) -> list:
        """
        Interpret user's camera selection

        Args:
            user_text: The message from the user (e.g., "0", "0,1", "all cameras", "camera 1 and 2")

        Returns:
            List of camera indices (e.g., [0], [0, 1, 2])
            Returns empty list if cannot interpret
        """
        if not user_text or not user_text.strip():
            return []

        text = user_text.strip()
        normalized = text.upper()

        # Check cache
        cache_key = f"camera_{normalized}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Exact matching first (fast path)
        # Simple comma-separated format: "0", "0,1", "0,1,2"
        if re.match(r'^\d+(,\d+)*$', text):
            cameras = [int(x.strip()) for x in text.split(',')]
            self.cache[cache_key] = cameras
            return cameras

        # Use Gemini AI for natural language interpretation if enabled
        if self.enabled:
            try:
                result = self._gemini_interpret_camera(text)
                self.cache[cache_key] = result
                return result
            except Exception as e:
                print(f"⚠️ Gemini API error for camera interpretation: {e}")
                return []

        return []

    def _gemini_interpret_camera(self, user_text: str) -> list:
        """
        Use Gemini AI to interpret camera selection

        Args:
            user_text: Raw user message

        Returns:
            List of camera indices
        """
        prompt = f"""You are interpreting a camera selection command.

The user is selecting which camera(s) to use for monitoring. Available cameras are numbered 0, 1, 2, 3, etc.

Examples of user input and correct interpretation:
- "0" → camera 0 only
- "camera 0" → camera 0 only
- "1" → camera 1 only
- "0,1" → cameras 0 and 1
- "0 and 1" → cameras 0 and 1
- "camera 0 and camera 1" → cameras 0 and 1
- "all cameras" → cameras 0, 1, 2, 3
- "first camera" → camera 0
- "second camera" → camera 1
- "cameras 1 and 2" → cameras 1 and 2
- "use 0,1,2" → cameras 0, 1, 2

User message: "{user_text}"

Respond with ONLY the camera numbers separated by commas.
Examples of valid responses:
0
0,1
0,1,2
1,2,3

If you cannot determine the cameras, respond with: UNKNOWN
"""

        response = self.model.generate_content(prompt)
        result = response.text.strip()

        # Parse response
        if result == "UNKNOWN":
            return []

        # Extract numbers from response
        cameras = []
        for part in result.split(','):
            part = part.strip()
            if part.isdigit():
                cameras.append(int(part))

        return cameras if cameras else []

    def interpret_interval(self, user_text: str) -> int:
        """
        Interpret user's save interval input

        Args:
            user_text: The message from the user (e.g., "5", "10 seconds", "every 30 seconds")

        Returns:
            Number of seconds (e.g., 5, 10, 30)
            Returns 0 if cannot interpret
        """
        if not user_text or not user_text.strip():
            return 0

        text = user_text.strip()
        normalized = text.upper()

        # Check cache
        cache_key = f"interval_{normalized}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Exact matching first (fast path)
        # Simple number: "5", "10", "30"
        if text.isdigit():
            interval = int(text)
            self.cache[cache_key] = interval
            return interval

        # Use Gemini AI for natural language interpretation if enabled
        if self.enabled:
            try:
                result = self._gemini_interpret_interval(text)
                self.cache[cache_key] = result
                return result
            except Exception as e:
                print(f"⚠️ Gemini API error for interval interpretation: {e}")
                return 0

        return 0

    def _gemini_interpret_interval(self, user_text: str) -> int:
        """
        Use Gemini AI to interpret the save interval

        Args:
            user_text: Raw user message

        Returns:
            Number of seconds
        """
        prompt = f"""You are interpreting a time interval for auto-saving camera frames.

The user is setting how often frames should be saved (in seconds).

Examples of user input and correct interpretation:
- "5" → 5 seconds
- "10" → 10 seconds
- "30" → 30 seconds
- "5 seconds" → 5 seconds
- "every 10 seconds" → 10 seconds
- "10s" → 10 seconds
- "half a minute" → 30 seconds
- "one minute" → 60 seconds
- "every second" → 1 second
- "every 5" → 5 seconds

User message: "{user_text}"

Respond with ONLY a number (the number of seconds).
Examples of valid responses:
5
10
30
60

If you cannot determine the interval, respond with: 0
"""

        response = self.model.generate_content(prompt)
        result = response.text.strip()

        # Parse response
        if result.isdigit():
            return int(result)
        else:
            return 0

    def clear_cache(self):
        """Clear the command interpretation cache"""
        self.cache.clear()
