#!/usr/bin/env python3
"""
ARIA Memory V2 - Fact Extractor Module

Uses Claude to extract factual information from conversations.
Identifies personal facts, preferences, context, and important details
that ARIA should remember for future interactions.
"""

import os
import json
import anthropic
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class FactCategory(str, Enum):
    """Categories for extracted facts"""
    PERSONAL = "personal"           # Name, age, location, family
    PROFESSIONAL = "professional"   # Job, company, industry, skills
    PREFERENCE = "preference"       # Likes, dislikes, preferences
    CONTEXT = "context"             # Current situation, goals, challenges
    HEALTH = "health"               # Health conditions, medications, fitness
    TECHNICAL = "technical"         # Tech stack, tools, systems they use
    RELATIONSHIP = "relationship"   # People they mention, relationships
    SCHEDULE = "schedule"           # Work hours, timezone, availability
    FINANCIAL = "financial"         # Budget constraints, financial goals
    PROJECT = "project"             # Active projects, deadlines
    GENERAL = "general"             # Other facts


@dataclass
class ExtractedFact:
    """Represents a single extracted fact"""
    fact: str
    category: FactCategory
    confidence: float
    source_excerpt: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "fact": self.fact,
            "category": self.category.value if isinstance(self.category, FactCategory) else self.category,
            "confidence": self.confidence,
            "source_excerpt": self.source_excerpt
        }


class FactExtractor:
    """
    Extracts factual information from conversation text using Claude.

    This module analyzes conversation content to identify:
    - Personal information (name, location, family)
    - Professional context (job, company, skills)
    - Preferences and opinions
    - Current situation and goals
    - Any other memorable facts
    """

    EXTRACTION_PROMPT = """You are a fact extraction system for a personal AI assistant named ARIA.
Your job is to identify factual information from conversations that would be valuable to remember for future interactions.

IMPORTANT GUIDELINES:
1. Only extract FACTS - concrete, specific information, not opinions or speculation
2. Each fact should be a single, clear statement
3. Assign a confidence score (0.0-1.0) based on how explicit the information is
4. Categorize each fact appropriately
5. Include the relevant excerpt from the conversation as evidence
6. Do NOT extract:
   - Generic statements or greetings
   - Temporary states ("I'm tired today")
   - Information that's clearly hypothetical
   - Sensitive information without clear consent (passwords, specific financial amounts)

CATEGORIES:
- personal: Name, age, birthday, location, family members, pets
- professional: Job title, company, industry, skills, work experience
- preference: Likes, dislikes, preferences for things (food, music, tools, etc.)
- context: Current situation, active goals, ongoing challenges
- health: Health conditions, medications, fitness routines (be careful with sensitivity)
- technical: Technologies they use, programming languages, tools, systems
- relationship: People they mention, relationships to those people
- schedule: Work hours, timezone, typical availability
- financial: Budget preferences, financial goals (avoid specific amounts)
- project: Active projects, deadlines, project goals
- general: Other factual information worth remembering

OUTPUT FORMAT:
Return a JSON array of facts. Each fact object should have:
- "fact": The extracted fact as a clear statement
- "category": One of the categories above
- "confidence": Float 0.0-1.0 (1.0 = explicitly stated, 0.5 = implied, below 0.5 = uncertain)
- "source_excerpt": The relevant text from the conversation

Example output:
[
  {
    "fact": "User's name is Alex",
    "category": "personal",
    "confidence": 1.0,
    "source_excerpt": "Hi, I'm Alex"
  },
  {
    "fact": "User works as a software engineer at TechCorp",
    "category": "professional",
    "confidence": 0.9,
    "source_excerpt": "In my role as a software engineer at TechCorp..."
  }
]

If no facts can be extracted, return an empty array: []
"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the fact extractor with Anthropic API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    async def extract_facts(
        self,
        conversation: str,
        user_id: str = "default",
        existing_facts: Optional[List[str]] = None,
        max_facts: int = 10
    ) -> List[ExtractedFact]:
        """
        Extract facts from a conversation.

        Args:
            conversation: The conversation text to analyze
            user_id: User identifier for context
            existing_facts: List of facts already known (to avoid duplicates)
            max_facts: Maximum number of facts to extract

        Returns:
            List of ExtractedFact objects
        """
        if not conversation or len(conversation.strip()) < 10:
            return []

        # Build the prompt with existing facts context
        context_prompt = ""
        if existing_facts:
            context_prompt = f"""
ALREADY KNOWN FACTS (do not re-extract these):
{chr(10).join(f'- {fact}' for fact in existing_facts[:20])}

Focus on NEW information not already captured above.
"""

        prompt = f"""{self.EXTRACTION_PROMPT}

{context_prompt}

CONVERSATION TO ANALYZE:
---
{conversation}
---

Extract up to {max_facts} facts. Return ONLY the JSON array, no other text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse the response
            response_text = response.content[0].text.strip()

            # Try to extract JSON from the response
            facts_data = self._parse_json_response(response_text)

            # Convert to ExtractedFact objects
            extracted_facts = []
            for fact_dict in facts_data[:max_facts]:
                try:
                    category = fact_dict.get("category", "general")
                    if category not in [c.value for c in FactCategory]:
                        category = "general"

                    fact = ExtractedFact(
                        fact=fact_dict.get("fact", ""),
                        category=FactCategory(category),
                        confidence=min(1.0, max(0.0, float(fact_dict.get("confidence", 0.7)))),
                        source_excerpt=fact_dict.get("source_excerpt")
                    )

                    if fact.fact:  # Only add if fact text exists
                        extracted_facts.append(fact)
                except (ValueError, KeyError) as e:
                    print(f"[FactExtractor] Error parsing fact: {e}")
                    continue

            return extracted_facts

        except Exception as e:
            print(f"[FactExtractor] Extraction error: {e}")
            return []

    def _parse_json_response(self, text: str) -> List[dict]:
        """Parse JSON from Claude's response, handling various formats."""
        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in the response
        import re
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Try to find JSON between code blocks
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass

        print(f"[FactExtractor] Could not parse response: {text[:200]}...")
        return []

    async def extract_facts_from_messages(
        self,
        messages: List[Dict[str, str]],
        user_id: str = "default",
        existing_facts: Optional[List[str]] = None
    ) -> List[ExtractedFact]:
        """
        Extract facts from a list of message objects.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            user_id: User identifier
            existing_facts: Facts already known

        Returns:
            List of ExtractedFact objects
        """
        # Convert messages to conversation string
        conversation_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                conversation_parts.append(f"User: {content}")
            elif role == "assistant":
                conversation_parts.append(f"Assistant: {content}")
            else:
                conversation_parts.append(f"{role}: {content}")

        conversation = "\n\n".join(conversation_parts)
        return await self.extract_facts(conversation, user_id, existing_facts)

    def get_usage_stats(self, response) -> Dict[str, int]:
        """Extract usage statistics from API response."""
        usage = getattr(response, 'usage', None)
        if usage:
            return {
                "input_tokens": getattr(usage, 'input_tokens', 0),
                "output_tokens": getattr(usage, 'output_tokens', 0)
            }
        return {"input_tokens": 0, "output_tokens": 0}


# Convenience function for quick extraction
async def extract_facts_from_text(
    text: str,
    api_key: Optional[str] = None
) -> List[ExtractedFact]:
    """
    Quick helper to extract facts from text.

    Args:
        text: Text to analyze
        api_key: Optional Anthropic API key

    Returns:
        List of ExtractedFact objects
    """
    extractor = FactExtractor(api_key)
    return await extractor.extract_facts(text)


if __name__ == "__main__":
    # Test the extractor
    import asyncio

    test_conversation = """
    User: Hi, I'm Sarah. I work as a product manager at Stripe.

    Assistant: Nice to meet you, Sarah! How can I help you today?

    User: I'm trying to figure out how to prioritize my team's roadmap.
    We're a team of 5 engineers and 2 designers based in San Francisco.
    I've been using Linear for project management but thinking about switching to Notion.

    Assistant: That's a common challenge. What's driving the consideration to switch?

    User: Mainly because my team prefers having docs and tasks in one place.
    We work mostly async since two of our engineers are in Europe.
    I usually start my day around 7am PT to overlap with them.
    """

    async def test():
        extractor = FactExtractor()
        facts = await extractor.extract_facts(test_conversation)
        print("Extracted facts:")
        for fact in facts:
            print(f"  [{fact.category.value}] {fact.fact} (confidence: {fact.confidence})")

    asyncio.run(test())
