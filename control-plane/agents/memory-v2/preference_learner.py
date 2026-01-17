#!/usr/bin/env python3
"""
ARIA Memory V2 - Preference Learner Module

Detects and learns user preferences from conversations and behavior patterns.
Tracks preference confidence over time with confirmation/contradiction tracking.
"""

import os
import json
import anthropic
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PreferenceCategory(str, Enum):
    """Categories for learned preferences"""
    COMMUNICATION = "communication"     # How they prefer to be communicated with
    SCHEDULING = "scheduling"           # Time preferences, meeting preferences
    TOOLS = "tools"                     # Software, tools, platforms
    WORKFLOW = "workflow"               # How they like to work
    CONTENT = "content"                 # Content format, style preferences
    INTERACTION = "interaction"         # Interaction style with AI
    TECHNICAL = "technical"             # Technical preferences
    LIFESTYLE = "lifestyle"             # Food, activities, hobbies
    INFORMATION = "information"         # How they like information presented
    GENERAL = "general"                 # Other preferences


@dataclass
class LearnedPreference:
    """Represents a learned preference"""
    preference_key: str                 # Unique key for this preference
    preference_value: str               # The preference value
    category: PreferenceCategory
    confidence: float                   # 0.0-1.0 confidence score
    evidence: List[str] = field(default_factory=list)  # Supporting evidence
    source_excerpt: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "preference_key": self.preference_key,
            "preference_value": self.preference_value,
            "category": self.category.value if isinstance(self.category, PreferenceCategory) else self.category,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "source_excerpt": self.source_excerpt
        }


class PreferenceLearner:
    """
    Learns and tracks user preferences from conversations.

    This module:
    - Detects explicit preference statements ("I prefer X")
    - Infers implicit preferences from behavior
    - Tracks preference changes over time
    - Maintains confidence scores based on confirmation/contradiction
    """

    LEARNING_PROMPT = """You are a preference learning system for a personal AI assistant named ARIA.
Your job is to identify user preferences from conversations - both explicit statements and implicit patterns.

WHAT TO LOOK FOR:

1. EXPLICIT PREFERENCES:
   - "I prefer..." / "I like..." / "I don't like..."
   - "Please always..." / "Please never..."
   - "I'd rather..." / "I want..."
   - "My favorite is..." / "I hate..."

2. IMPLICIT PREFERENCES (inferred from behavior):
   - Communication style they respond well to
   - Times they seem to be active
   - Level of detail they ask for
   - Topics they engage with most
   - How they make decisions

3. CORRECTION PATTERNS:
   - When they correct the assistant
   - When they re-explain something
   - When they express frustration about something

OUTPUT FORMAT:
Return a JSON array of preferences. Each preference object should have:
- "preference_key": A unique, consistent key for this preference (snake_case)
- "preference_value": The actual preference value
- "category": One of: communication, scheduling, tools, workflow, content, interaction, technical, lifestyle, information, general
- "confidence": Float 0.0-1.0 (1.0 = explicitly stated, 0.6-0.8 = clearly implied, below 0.6 = tentative)
- "evidence": Array of evidence strings supporting this preference
- "source_excerpt": Relevant text from the conversation

PREFERENCE KEY NAMING:
Use consistent, descriptive keys that can be matched across conversations:
- "preferred_communication_style"
- "response_detail_level"
- "meeting_time_preference"
- "favorite_programming_language"
- "preferred_explanation_format"

Example output:
[
  {
    "preference_key": "response_format_preference",
    "preference_value": "bullet_points",
    "category": "content",
    "confidence": 0.9,
    "evidence": ["User asked to use bullet points", "User thanked assistant for bullet format"],
    "source_excerpt": "Can you give me that in bullet points instead?"
  },
  {
    "preference_key": "meeting_time_preference",
    "preference_value": "morning",
    "category": "scheduling",
    "confidence": 0.7,
    "evidence": ["User mentioned starting work at 7am"],
    "source_excerpt": "I usually start my day around 7am"
  }
]

IMPORTANT:
- Create meaningful, specific preference keys that can be referenced later
- Don't create overly specific one-time preferences
- Focus on patterns that would help personalize future interactions
- If no clear preferences detected, return empty array: []
"""

    COMPARISON_PROMPT = """Compare new information against existing preferences to detect:
1. CONFIRMATIONS: New evidence that supports existing preferences
2. CONTRADICTIONS: Information that conflicts with existing preferences
3. NEW PREFERENCES: Completely new preferences not yet tracked

EXISTING PREFERENCES:
{existing_preferences}

NEW CONVERSATION:
{conversation}

For each preference, indicate:
- "action": "confirm" | "contradict" | "new"
- "preference_key": The key (existing or new)
- "preference_value": Current value
- "evidence": New evidence from this conversation
- "confidence_adjustment": Float to add/subtract from confidence (-0.2 to +0.2)

Return JSON array of findings."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the preference learner with Anthropic API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    async def learn_preferences(
        self,
        conversation: str,
        user_id: str = "default",
        existing_preferences: Optional[Dict[str, str]] = None,
        max_preferences: int = 10
    ) -> List[LearnedPreference]:
        """
        Learn preferences from a conversation.

        Args:
            conversation: The conversation text to analyze
            user_id: User identifier for context
            existing_preferences: Dict of existing preference_key -> value
            max_preferences: Maximum preferences to extract

        Returns:
            List of LearnedPreference objects
        """
        if not conversation or len(conversation.strip()) < 20:
            return []

        # Build context for existing preferences
        existing_context = ""
        if existing_preferences:
            existing_context = f"""
KNOWN PREFERENCES (look for confirmations or contradictions):
{json.dumps(existing_preferences, indent=2)}

Identify if any statements confirm or contradict these existing preferences.
"""

        prompt = f"""{self.LEARNING_PROMPT}

{existing_context}

CONVERSATION TO ANALYZE:
---
{conversation}
---

Extract up to {max_preferences} preferences. Return ONLY the JSON array, no other text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text.strip()
            preferences_data = self._parse_json_response(response_text)

            learned_preferences = []
            for pref_dict in preferences_data[:max_preferences]:
                try:
                    category = pref_dict.get("category", "general")
                    if category not in [c.value for c in PreferenceCategory]:
                        category = "general"

                    evidence = pref_dict.get("evidence", [])
                    if isinstance(evidence, str):
                        evidence = [evidence]

                    pref = LearnedPreference(
                        preference_key=pref_dict.get("preference_key", "unknown"),
                        preference_value=str(pref_dict.get("preference_value", "")),
                        category=PreferenceCategory(category),
                        confidence=min(1.0, max(0.0, float(pref_dict.get("confidence", 0.7)))),
                        evidence=evidence,
                        source_excerpt=pref_dict.get("source_excerpt")
                    )

                    if pref.preference_key and pref.preference_value:
                        learned_preferences.append(pref)
                except (ValueError, KeyError) as e:
                    print(f"[PreferenceLearner] Error parsing preference: {e}")
                    continue

            return learned_preferences

        except Exception as e:
            print(f"[PreferenceLearner] Learning error: {e}")
            return []

    async def detect_preference_changes(
        self,
        conversation: str,
        existing_preferences: Dict[str, Dict[str, Any]],
        user_id: str = "default"
    ) -> Tuple[List[str], List[str], List[LearnedPreference]]:
        """
        Detect preference confirmations, contradictions, and new preferences.

        Args:
            conversation: New conversation to analyze
            existing_preferences: Dict of preference_key -> {value, confidence, ...}
            user_id: User identifier

        Returns:
            Tuple of (confirmed_keys, contradicted_keys, new_preferences)
        """
        if not conversation or not existing_preferences:
            return [], [], []

        # Format existing preferences for the prompt
        pref_summary = "\n".join([
            f"- {key}: {data.get('value', data)} (confidence: {data.get('confidence', 0.5) if isinstance(data, dict) else 0.5})"
            for key, data in existing_preferences.items()
        ])

        prompt = f"""Analyze this conversation against known preferences.

KNOWN PREFERENCES:
{pref_summary}

CONVERSATION:
---
{conversation}
---

Identify:
1. Which existing preferences are CONFIRMED by this conversation
2. Which existing preferences are CONTRADICTED
3. Any NEW preferences to add

Return JSON:
{{
  "confirmations": ["preference_key1", "preference_key2"],
  "contradictions": [
    {{"key": "preference_key", "new_value": "different value", "evidence": "quote"}}
  ],
  "new_preferences": [
    {{"preference_key": "key", "preference_value": "value", "category": "cat", "confidence": 0.7, "evidence": ["e1"]}}
  ]
}}
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            result = self._parse_json_response(response.content[0].text.strip())

            if not isinstance(result, dict):
                return [], [], []

            confirmed = result.get("confirmations", [])
            contradicted_data = result.get("contradictions", [])
            new_prefs_data = result.get("new_preferences", [])

            # Convert contradictions to just keys
            contradicted_keys = [c.get("key") for c in contradicted_data if c.get("key")]

            # Convert new preferences to LearnedPreference objects
            new_preferences = []
            for pref in new_prefs_data:
                try:
                    category = pref.get("category", "general")
                    if category not in [c.value for c in PreferenceCategory]:
                        category = "general"

                    new_preferences.append(LearnedPreference(
                        preference_key=pref.get("preference_key", ""),
                        preference_value=str(pref.get("preference_value", "")),
                        category=PreferenceCategory(category),
                        confidence=float(pref.get("confidence", 0.7)),
                        evidence=pref.get("evidence", [])
                    ))
                except Exception:
                    continue

            return confirmed, contradicted_keys, new_preferences

        except Exception as e:
            print(f"[PreferenceLearner] Change detection error: {e}")
            return [], [], []

    def _parse_json_response(self, text: str) -> Any:
        """Parse JSON from Claude's response."""
        import re

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in the response
        json_patterns = [
            r'\{[\s\S]*\}',  # Object
            r'\[[\s\S]*\]',  # Array
        ]

        for pattern in json_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        # Try code blocks
        code_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass

        print(f"[PreferenceLearner] Could not parse: {text[:200]}...")
        return []

    async def infer_communication_preference(
        self,
        messages: List[Dict[str, str]]
    ) -> Optional[LearnedPreference]:
        """
        Infer communication style preference from message patterns.

        Analyzes:
        - Message length patterns
        - Formality level
        - Question style
        - Response preferences
        """
        if len(messages) < 3:
            return None

        # Analyze user messages
        user_messages = [m["content"] for m in messages if m.get("role") == "user"]
        if not user_messages:
            return None

        avg_length = sum(len(m) for m in user_messages) / len(user_messages)

        # Simple heuristics
        if avg_length < 50:
            style = "brief"
            confidence = 0.6
        elif avg_length > 200:
            style = "detailed"
            confidence = 0.6
        else:
            style = "moderate"
            confidence = 0.5

        return LearnedPreference(
            preference_key="communication_length_preference",
            preference_value=style,
            category=PreferenceCategory.COMMUNICATION,
            confidence=confidence,
            evidence=[f"Average message length: {avg_length:.0f} characters"]
        )


# Standard preference keys for consistency
STANDARD_PREFERENCE_KEYS = {
    # Communication
    "response_format_preference": "How they prefer responses formatted (bullets, paragraphs, etc.)",
    "response_length_preference": "Preferred response length (brief, moderate, detailed)",
    "formality_preference": "Preferred formality level (casual, professional, mixed)",
    "explanation_depth_preference": "How much explanation they want",

    # Scheduling
    "preferred_work_hours": "When they typically work",
    "timezone": "Their timezone",
    "meeting_time_preference": "Preferred times for meetings",
    "async_vs_sync_preference": "Preference for async vs real-time",

    # Technical
    "preferred_programming_language": "Most used/preferred language",
    "preferred_tools": "Tools they prefer to use",
    "tech_stack_preference": "Preferred technology stack",
    "ide_preference": "Preferred development environment",

    # Workflow
    "task_breakdown_preference": "How they like tasks broken down",
    "planning_style": "How they prefer to plan work",
    "deadline_reminder_preference": "How they want deadline reminders",

    # Content
    "example_preference": "Whether they prefer examples",
    "visual_vs_text_preference": "Visual vs text content preference",
    "code_comment_preference": "How they prefer code commented",
}


async def learn_from_conversation(
    conversation: str,
    api_key: Optional[str] = None
) -> List[LearnedPreference]:
    """
    Quick helper to learn preferences from a conversation.

    Args:
        conversation: Conversation text
        api_key: Optional Anthropic API key

    Returns:
        List of LearnedPreference objects
    """
    learner = PreferenceLearner(api_key)
    return await learner.learn_preferences(conversation)


if __name__ == "__main__":
    import asyncio

    test_conversation = """
    User: Can you summarize this in bullet points? I find long paragraphs hard to read.

    Assistant: Of course! Here's a bullet-point summary:
    - Point 1
    - Point 2
    - Point 3

    User: Perfect, that's exactly what I needed. I always prefer this format.
    Also, can we keep our discussions focused? I have ADHD and get distracted easily.

    Assistant: Absolutely! I'll keep responses focused and concise.

    User: Great. BTW I work best in the mornings, usually 7-11am is my peak focus time.
    After lunch I'm usually doing meetings or lighter tasks.
    """

    async def test():
        learner = PreferenceLearner()
        preferences = await learner.learn_preferences(test_conversation)
        print("Learned preferences:")
        for pref in preferences:
            print(f"  {pref.preference_key}: {pref.preference_value}")
            print(f"    Category: {pref.category.value}, Confidence: {pref.confidence}")
            print(f"    Evidence: {pref.evidence}")
            print()

    asyncio.run(test())
