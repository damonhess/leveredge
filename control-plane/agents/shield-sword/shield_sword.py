#!/usr/bin/env python3
"""
SHIELD-SWORD - ARIA Pre/Post Processing Agent
Port: 8067

SHIELD: Pre-process user input for manipulation detection
SWORD: Post-process ARIA output for maximum impact

This agent wraps ARIA conversations to:
1. Detect manipulation attempts, emotional manipulation, scope creep
2. Enhance responses for clarity, persuasion, and call-to-action
"""

import os
import sys
import json
import yaml
import httpx
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

# Import local modules
from shield import ShieldAnalyzer
from sword import SwordEnhancer

app = FastAPI(
    title="SHIELD-SWORD",
    description="ARIA Pre/Post Processing - Shield analyzes input, Sword enhances output",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
CONFIG_PATH = Path("/opt/leveredge/control-plane/agents/shield-sword/config.yaml")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("SHIELD-SWORD")

# Load configuration
def load_config() -> dict:
    """Load configuration from YAML file"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    return {
        "shield_intensity": "medium",
        "sword_intensity": "medium",
        "alert_threshold": 0.7,
        "enabled": True
    }

def save_config(config: dict) -> None:
    """Save configuration to YAML file"""
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

# Global config
config = load_config()

# Initialize analyzers
shield = ShieldAnalyzer(client, cost_tracker)
sword = SwordEnhancer(client, cost_tracker)

# =============================================================================
# MODELS
# =============================================================================

class ShieldRequest(BaseModel):
    user_input: str
    context: Optional[Dict[str, Any]] = {}
    conversation_history: Optional[List[Dict[str, str]]] = []

class SwordRequest(BaseModel):
    aria_response: str
    user_input: str
    context: Optional[Dict[str, Any]] = {}
    tone_preference: Optional[str] = "balanced"  # warm, balanced, direct, assertive

class ConfigUpdate(BaseModel):
    shield_intensity: Optional[str] = None  # off, low, medium, high
    sword_intensity: Optional[str] = None   # off, low, medium, high
    alert_threshold: Optional[float] = None

class FullProcessRequest(BaseModel):
    user_input: str
    aria_response: str
    context: Optional[Dict[str, Any]] = {}
    conversation_history: Optional[List[Dict[str, str]]] = []
    tone_preference: Optional[str] = "balanced"

# =============================================================================
# HELPERS
# =============================================================================

async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    """Log event to Event Bus"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "SHIELD-SWORD",
                    "action": action,
                    "target": target,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "SHIELD-SWORD",
        "port": 8067,
        "shield_enabled": config.get("shield_intensity", "medium") != "off",
        "sword_enabled": config.get("sword_intensity", "medium") != "off",
        "shield_intensity": config.get("shield_intensity", "medium"),
        "sword_intensity": config.get("sword_intensity", "medium"),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "config": config,
        "valid_intensities": ["off", "low", "medium", "high"],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.put("/config")
async def update_config(update: ConfigUpdate):
    """Update configuration"""
    global config

    valid_intensities = ["off", "low", "medium", "high"]

    if update.shield_intensity is not None:
        if update.shield_intensity not in valid_intensities:
            raise HTTPException(status_code=400, detail=f"Invalid shield_intensity. Must be one of: {valid_intensities}")
        config["shield_intensity"] = update.shield_intensity

    if update.sword_intensity is not None:
        if update.sword_intensity not in valid_intensities:
            raise HTTPException(status_code=400, detail=f"Invalid sword_intensity. Must be one of: {valid_intensities}")
        config["sword_intensity"] = update.sword_intensity

    if update.alert_threshold is not None:
        if not 0 <= update.alert_threshold <= 1:
            raise HTTPException(status_code=400, detail="alert_threshold must be between 0 and 1")
        config["alert_threshold"] = update.alert_threshold

    # Save to file
    save_config(config)

    await log_to_event_bus("config_updated", details=config)

    return {
        "status": "updated",
        "config": config,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/shield/analyze")
async def analyze_shield(req: ShieldRequest):
    """
    SHIELD: Analyze user input for manipulation attempts

    Returns:
    - risk_score: 0-1 indicating manipulation risk
    - flags: List of detected issues
    - recommendations: How ARIA should handle this
    - sanitized_input: Cleaned version if needed
    """
    if config.get("shield_intensity") == "off":
        return {
            "status": "disabled",
            "risk_score": 0,
            "flags": [],
            "recommendations": [],
            "original_input": req.user_input,
            "sanitized_input": req.user_input
        }

    result = await shield.analyze(
        user_input=req.user_input,
        context=req.context,
        conversation_history=req.conversation_history,
        intensity=config.get("shield_intensity", "medium")
    )

    # Log if high risk
    if result["risk_score"] >= config.get("alert_threshold", 0.7):
        await log_to_event_bus(
            "shield_alert",
            target="user_input",
            details={
                "risk_score": result["risk_score"],
                "flags": result["flags"],
                "input_preview": req.user_input[:100]
            }
        )

    return result

@app.post("/sword/enhance")
async def enhance_sword(req: SwordRequest):
    """
    SWORD: Enhance ARIA response for maximum impact

    Returns:
    - enhanced_response: Improved response
    - changes_made: List of enhancements applied
    - impact_score: Estimated improvement
    """
    if config.get("sword_intensity") == "off":
        return {
            "status": "disabled",
            "original_response": req.aria_response,
            "enhanced_response": req.aria_response,
            "changes_made": [],
            "impact_score": 0
        }

    result = await sword.enhance(
        aria_response=req.aria_response,
        user_input=req.user_input,
        context=req.context,
        tone_preference=req.tone_preference,
        intensity=config.get("sword_intensity", "medium")
    )

    await log_to_event_bus(
        "sword_enhanced",
        details={
            "changes_count": len(result.get("changes_made", [])),
            "impact_score": result.get("impact_score", 0)
        }
    )

    return result

@app.post("/process")
async def full_process(req: FullProcessRequest):
    """
    Full Shield+Sword pipeline:
    1. Analyze user input with Shield
    2. Enhance ARIA response with Sword

    Returns combined analysis and enhancement.
    """
    # Shield analysis
    shield_result = None
    if config.get("shield_intensity") != "off":
        shield_result = await shield.analyze(
            user_input=req.user_input,
            context=req.context,
            conversation_history=req.conversation_history,
            intensity=config.get("shield_intensity", "medium")
        )

    # Sword enhancement
    sword_result = None
    if config.get("sword_intensity") != "off":
        sword_result = await sword.enhance(
            aria_response=req.aria_response,
            user_input=req.user_input,
            context=req.context,
            tone_preference=req.tone_preference,
            intensity=config.get("sword_intensity", "medium")
        )

    # Log combined action
    await log_to_event_bus(
        "full_process",
        details={
            "shield_risk": shield_result.get("risk_score", 0) if shield_result else None,
            "sword_impact": sword_result.get("impact_score", 0) if sword_result else None
        }
    )

    return {
        "shield": shield_result,
        "sword": sword_result,
        "final_response": sword_result.get("enhanced_response", req.aria_response) if sword_result else req.aria_response,
        "warnings": shield_result.get("flags", []) if shield_result else [],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/stats")
async def get_stats():
    """Get processing statistics"""
    # In production, these would come from a database
    return {
        "agent": "SHIELD-SWORD",
        "config": config,
        "description": "Statistics would be tracked via Event Bus and Supabase",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8067)
