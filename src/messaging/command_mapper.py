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

    def clear_cache(self):
        """Clear the command interpretation cache"""
        self.cache.clear()
