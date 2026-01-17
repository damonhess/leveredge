#!/usr/bin/env python3
"""
SWORD Module - Response Enhancement for ARIA

Enhances ARIA responses for maximum impact:
- Improves clarity and structure
- Adds persuasive elements (ethically)
- Strengthens calls-to-action
- Adjusts tone for impact
- Ensures responses drive action

All enhancements are ethical and serve the user's genuine interests.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import log_llm_usage

# Load prompt template
PROMPT_PATH = Path("/opt/leveredge/control-plane/agents/shield-sword/prompts/sword_prompt.txt")


class SwordEnhancer:
    """Enhances ARIA responses for clarity, impact, and action"""

    def __init__(self, anthropic_client, cost_tracker):
        self.client = anthropic_client
        self.cost_tracker = cost_tracker
        self._prompt_template = None

    @property
    def prompt_template(self) -> str:
        """Lazy load prompt template"""
        if self._prompt_template is None:
            if PROMPT_PATH.exists():
                self._prompt_template = PROMPT_PATH.read_text()
            else:
                self._prompt_template = self._default_prompt()
        return self._prompt_template

    def _default_prompt(self) -> str:
        """Default prompt if file not found"""
        return """You are SWORD, an enhancement layer for ARIA (an AI assistant).

Your job is to enhance ARIA's response for maximum positive impact while maintaining:
- Honesty and accuracy
- Ethical persuasion only
- User's genuine best interests

Enhancement areas:
1. CLARITY - Make structure clearer, remove ambiguity
2. IMPACT - Strengthen key points, improve memorability
3. PERSUASION - Add ethical persuasive elements (social proof, authority, scarcity if genuine)
4. CALL-TO-ACTION - Ensure clear next steps
5. TONE - Match requested tone (warm, balanced, direct, assertive)

INTENSITY LEVEL: {intensity}
- low: Light polish, preserve original voice
- medium: Moderate enhancement, improve structure
- high: Significant restructuring for maximum impact

TONE PREFERENCE: {tone}
- warm: Empathetic, supportive, encouraging
- balanced: Professional, helpful, neutral
- direct: Concise, no fluff, to the point
- assertive: Confident, authoritative, action-oriented

USER'S ORIGINAL INPUT:
{user_input}

ARIA'S ORIGINAL RESPONSE:
{aria_response}

CONTEXT:
{context}

Return a JSON object with:
{{
    "enhanced_response": "the improved response",
    "changes_made": ["list", "of", "enhancements"],
    "impact_score": 0.0-1.0,
    "tone_applied": "the tone used",
    "analysis": "brief explanation of changes"
}}

IMPORTANT:
- Do NOT change factual content
- Do NOT add false claims
- Do NOT make promises ARIA didn't make
- Preserve ARIA's helpful nature
- Enhance, don't replace the core message

Return ONLY valid JSON, no other text."""

    async def enhance(
        self,
        aria_response: str,
        user_input: str,
        context: Dict[str, Any] = None,
        tone_preference: str = "balanced",
        intensity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Enhance ARIA response for maximum impact

        Args:
            aria_response: ARIA's original response
            user_input: The user's original input (for context)
            context: Additional context
            tone_preference: Desired tone (warm, balanced, direct, assertive)
            intensity: Enhancement level (low, medium, high)

        Returns:
            Dict with enhanced_response, changes_made, impact_score
        """
        # Skip very short responses
        if len(aria_response.strip()) < 50:
            return {
                "status": "skipped",
                "reason": "Response too short for enhancement",
                "original_response": aria_response,
                "enhanced_response": aria_response,
                "changes_made": [],
                "impact_score": 0.0
            }

        # Build prompt
        prompt = self.prompt_template.format(
            intensity=intensity,
            tone=tone_preference,
            user_input=user_input,
            aria_response=aria_response,
            context=str(context or {})
        )

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-20250514",  # Fast model for enhancement
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            # Log cost
            await log_llm_usage(
                agent="SHIELD-SWORD",
                endpoint="sword/enhance",
                model="claude-haiku-4-20250514",
                response=response,
                metadata={"intensity": intensity, "tone": tone_preference}
            )

            # Parse response
            result = self._parse_response(response.content[0].text)
            result["original_response"] = aria_response
            result["status"] = "enhanced"

            return result

        except Exception as e:
            # On error, return original
            return {
                "status": "error",
                "error": str(e),
                "original_response": aria_response,
                "enhanced_response": aria_response,
                "changes_made": ["enhancement_failed"],
                "impact_score": 0.0,
                "analysis": f"Enhancement error: {str(e)}"
            }

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured result"""
        import json

        # Try to extract JSON from response
        try:
            # Handle potential markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            result = json.loads(text)

            # Ensure required fields
            return {
                "enhanced_response": result.get("enhanced_response", ""),
                "changes_made": result.get("changes_made", []),
                "impact_score": float(result.get("impact_score", 0.0)),
                "tone_applied": result.get("tone_applied", "balanced"),
                "analysis": result.get("analysis", "")
            }

        except json.JSONDecodeError:
            # If parsing fails, return original
            return {
                "enhanced_response": "",
                "changes_made": ["parse_failed"],
                "impact_score": 0.0,
                "tone_applied": "unknown",
                "analysis": f"Failed to parse enhancement response: {response_text[:200]}"
            }

    def quick_enhance(self, aria_response: str, tone: str = "balanced") -> str:
        """
        Quick rule-based enhancement without LLM call

        Use for fast, predictable enhancements
        """
        enhanced = aria_response

        # Add structure if missing
        if "\n\n" not in enhanced and len(enhanced) > 200:
            # Try to add paragraph breaks
            sentences = enhanced.split(". ")
            if len(sentences) > 3:
                mid = len(sentences) // 2
                enhanced = ". ".join(sentences[:mid]) + ".\n\n" + ". ".join(sentences[mid:])

        # Tone adjustments
        if tone == "direct":
            # Remove hedging language
            hedges = [
                ("I think ", ""),
                ("I believe ", ""),
                ("It seems like ", ""),
                ("Maybe ", ""),
                ("Perhaps ", ""),
                ("might want to consider", "should"),
                ("you could potentially", "you should"),
            ]
            for old, new in hedges:
                enhanced = enhanced.replace(old, new)

        elif tone == "warm":
            # Add warmth if response starts abruptly
            if not any(enhanced.startswith(w) for w in ["Great", "Thank", "I understand", "I appreciate"]):
                enhanced = "I understand where you're coming from. " + enhanced

        elif tone == "assertive":
            # Strengthen language
            weak_phrases = [
                ("you might", "you should"),
                ("consider", "do"),
                ("could help", "will help"),
                ("may be useful", "is essential"),
            ]
            for weak, strong in weak_phrases:
                enhanced = enhanced.replace(weak, strong)

        # Ensure call-to-action if missing
        action_indicators = ["next step", "action", "should", "do this", "start by", "begin with"]
        has_cta = any(indicator in enhanced.lower() for indicator in action_indicators)

        if not has_cta and len(enhanced) > 100:
            enhanced += "\n\nYour next step: Take action on the most important point above."

        return enhanced

    def analyze_response(self, aria_response: str) -> Dict[str, Any]:
        """
        Analyze response quality without enhancing

        Returns metrics about the response
        """
        analysis = {
            "length": len(aria_response),
            "word_count": len(aria_response.split()),
            "paragraph_count": aria_response.count("\n\n") + 1,
            "has_structure": "\n" in aria_response,
            "has_bullet_points": any(c in aria_response for c in ["-", "*", "1.", "2."]),
            "has_call_to_action": False,
            "hedging_score": 0.0,
            "clarity_score": 0.0
        }

        # Check for call-to-action
        cta_indicators = ["next step", "action", "should", "do this", "start by", "try", "begin"]
        analysis["has_call_to_action"] = any(ind in aria_response.lower() for ind in cta_indicators)

        # Calculate hedging score (0 = confident, 1 = very hedging)
        hedges = ["maybe", "perhaps", "might", "could", "possibly", "i think", "i believe", "it seems"]
        hedge_count = sum(1 for h in hedges if h in aria_response.lower())
        analysis["hedging_score"] = min(1.0, hedge_count / 5)

        # Basic clarity score based on structure
        clarity = 0.5
        if analysis["has_structure"]:
            clarity += 0.2
        if analysis["has_bullet_points"]:
            clarity += 0.2
        if analysis["word_count"] > 50:
            clarity += 0.1
        analysis["clarity_score"] = min(1.0, clarity)

        return analysis
