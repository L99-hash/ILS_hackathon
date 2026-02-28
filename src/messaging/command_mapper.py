"""
Natural Language Command Interpreter using Gemini AI

Maps user messages to predefined commands (CAPTURE, GANTT, etc.)
"""

import os
import google.generativeai as genai
from typing import Optional, Literal


class CommandMapper:
    """
    Uses Gemini AI to interpret natural language and map to special commands

    Supported commands:
    - CAPTURE: Take photo, capture frame, snap image, etc.
    - GANTT: Show schedule, production plan, timeline, etc.
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

    def clear_cache(self):
        """Clear the command interpretation cache"""
        self.cache.clear()
