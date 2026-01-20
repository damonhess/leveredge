"""
Council Responder - Shared module for generating council meeting responses

This module provides the common logic for agents to participate in council meetings.
Each agent imports this and uses generate_council_response() to create their contributions.
"""

import os
import httpx
from typing import Optional, List, Dict, Any
import anthropic

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Initialize Anthropic client
_client = None

def get_anthropic_client():
    """Lazy initialization of Anthropic client"""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


async def get_agent_profile(agent_name: str) -> Optional[Dict[str, Any]]:
    """Fetch agent profile from database"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/council_agent_profiles",
                params={"agent_name": f"eq.{agent_name}"},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0]
    except Exception as e:
        print(f"Failed to fetch agent profile: {e}")
    return None


def build_council_system_prompt(
    agent_name: str,
    agent_profile: Dict[str, Any]
) -> str:
    """Build the system prompt for council participation"""

    expertise_str = ", ".join(agent_profile.get("expertise", []))
    contributions_str = ", ".join(agent_profile.get("typical_contributions", []))

    return f"""You are {agent_name}, participating in a council meeting.

## YOUR IDENTITY
Domain: {agent_profile.get('domain', 'Unknown')}
Expertise: {expertise_str}
Personality: {agent_profile.get('personality', 'Professional')}
Speaking Style: {agent_profile.get('speaking_style', 'Clear and concise')}
You typically: {contributions_str}

## COUNCIL MEETING RULES
1. Respond in character. Your voice should reflect your expertise and personality.
2. Be concise (2-4 sentences unless asked for detail or the topic demands elaboration).
3. Build on what others have said when relevant.
4. Disagree respectfully if warranted - healthy debate improves outcomes.
5. Stay in your lane - defer to other experts when their domain is more relevant.
6. If asked a direct question, answer it directly.
7. If given a directive, acknowledge and respond appropriately.
8. Add value - don't just agree or repeat what others said.

## YOUR RESPONSE
Speak as {agent_name}. Do not prefix with your name - the system tracks who is speaking.
Be authentic to your character while being helpful to the discussion."""


def generate_council_response(
    agent_name: str,
    agent_profile: Dict[str, Any],
    meeting_context: str,
    current_topic: str,
    previous_statements: List[Dict[str, str]],
    directive: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514"
) -> str:
    """
    Generate a council meeting response for an agent.

    Args:
        agent_name: Name of the agent (e.g., "PRISM", "CATALYST")
        agent_profile: Agent's profile from council_agent_profiles table
        meeting_context: Overall context/purpose of the meeting
        current_topic: The specific topic being discussed right now
        previous_statements: List of dicts with "speaker" and "message" keys
        directive: Optional specific question or request for this agent
        model: Claude model to use (default: claude-sonnet-4-20250514)

    Returns:
        The agent's response as a string
    """

    client = get_anthropic_client()
    system_prompt = build_council_system_prompt(agent_name, agent_profile)

    # Build conversation context
    context_parts = [f"## MEETING CONTEXT\n{meeting_context}"]
    context_parts.append(f"\n## CURRENT TOPIC\n{current_topic}")

    if previous_statements:
        context_parts.append("\n## RECENT DISCUSSION")
        for stmt in previous_statements[-10:]:  # Last 10 statements max
            speaker = stmt.get("speaker", "Unknown")
            message = stmt.get("message", "")
            context_parts.append(f"\n**{speaker}:** {message}")

    user_content = "\n".join(context_parts)

    if directive:
        user_content += f"\n\n## DIRECTIVE FOR YOU\n{directive}"
    else:
        user_content += "\n\n## YOUR TURN\nContribute to the discussion."

    try:
        response = client.messages.create(
            model=model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )
        return response.content[0].text
    except Exception as e:
        return f"[{agent_name} encountered an error: {str(e)}]"


async def generate_council_response_async(
    agent_name: str,
    agent_profile: Dict[str, Any],
    meeting_context: str,
    current_topic: str,
    previous_statements: List[Dict[str, str]],
    directive: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514"
) -> str:
    """
    Async version of generate_council_response.
    Uses synchronous Anthropic client internally (wrapped for async context).
    """
    # Anthropic's Python client is sync, so we just call the sync version
    # In production, consider using asyncio.to_thread() for true async
    return generate_council_response(
        agent_name=agent_name,
        agent_profile=agent_profile,
        meeting_context=meeting_context,
        current_topic=current_topic,
        previous_statements=previous_statements,
        directive=directive,
        model=model
    )


# Pydantic models for FastAPI endpoints
from pydantic import BaseModel
from typing import List as ListType, Optional as OptionalType

class CouncilRespondRequest(BaseModel):
    """Request model for /council/respond endpoint"""
    meeting_context: str
    current_topic: str
    previous_statements: ListType[Dict[str, str]] = []
    directive: OptionalType[str] = None

class CouncilRespondResponse(BaseModel):
    """Response model for /council/respond endpoint"""
    agent: str
    response: str
    domain: str
    expertise: ListType[str]
