"""
Agent Alias System
==================
Generic names in code, display aliases in UI.

Usage:
    from agent_aliases import get_alias, get_generic, list_agents

    get_alias("builder")  # Returns "HEPHAESTUS"
    get_generic("HEPHAESTUS")  # Returns "builder"
"""

import json
import os
from typing import Optional, Dict, List

ALIAS_FILE = "/opt/leveredge/config/agent-aliases.json"

_registry = None

def _load_registry() -> dict:
    global _registry
    if _registry is None:
        with open(ALIAS_FILE, 'r') as f:
            _registry = json.load(f)
    return _registry

def get_alias(generic_name: str) -> Optional[str]:
    """Get display alias from generic name."""
    registry = _load_registry()
    for domain, agents in registry.get("agents", {}).items():
        if generic_name in agents:
            return agents[generic_name].get("alias")
    return None

def get_generic(alias: str) -> Optional[str]:
    """Get generic name from display alias."""
    registry = _load_registry()
    alias_upper = alias.upper()
    for domain, agents in registry.get("agents", {}).items():
        for generic, info in agents.items():
            if info.get("alias", "").upper() == alias_upper:
                return generic
    return None

def get_agent_info(name: str) -> Optional[dict]:
    """Get full agent info by generic name or alias."""
    registry = _load_registry()
    name_upper = name.upper()

    for domain, agents in registry.get("agents", {}).items():
        # Check generic name
        if name in agents:
            return {**agents[name], "generic": name, "domain": domain}
        # Check alias
        for generic, info in agents.items():
            if info.get("alias", "").upper() == name_upper:
                return {**info, "generic": generic, "domain": domain}
    return None

def get_port(name: str) -> Optional[int]:
    """Get primary port for an agent."""
    info = get_agent_info(name)
    if info and info.get("ports"):
        return info["ports"][0]
    return None

def list_agents(domain: str = None, status: str = "active") -> List[dict]:
    """List all agents, optionally filtered by domain and status."""
    registry = _load_registry()
    agents = []

    for dom, dom_agents in registry.get("agents", {}).items():
        if domain and dom != domain:
            continue
        for generic, info in dom_agents.items():
            if status and info.get("status") != status:
                continue
            agents.append({
                "generic": generic,
                "alias": info.get("alias"),
                "ports": info.get("ports", []),
                "domain": dom,
                "function": info.get("function"),
                "status": info.get("status")
            })

    return agents

def list_domains() -> List[str]:
    """List all domains."""
    registry = _load_registry()
    return list(registry.get("agents", {}).keys())

def get_freed_ports() -> Dict[str, str]:
    """Get list of freed ports available for reuse."""
    registry = _load_registry()
    return registry.get("freed_ports", {})

# Quick lookup tables
ALIAS_TO_GENERIC = {}
GENERIC_TO_ALIAS = {}

def _build_lookup_tables():
    global ALIAS_TO_GENERIC, GENERIC_TO_ALIAS
    registry = _load_registry()
    for domain, agents in registry.get("agents", {}).items():
        for generic, info in agents.items():
            alias = info.get("alias", "")
            ALIAS_TO_GENERIC[alias.upper()] = generic
            GENERIC_TO_ALIAS[generic] = alias

_build_lookup_tables()
