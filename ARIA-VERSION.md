# ARIA Version History

## Current Version: 4.1.0

**Released:** January 20, 2026
**Codename:** Persistence

---

## Changelog

### v4.1.0 (January 20, 2026) - Persistence
- Cross-device message sync via Supabase real-time
- Unified threading architecture (aria-memory service)
- User identity system for device linking
- DEV/PROD environment separation

### v4.0.0 (January 17, 2026) - Omniscience  
- ARIA-OMNISCIENCE integration (knows all agent activity)
- OLYMPUS orchestration (can dispatch to any agent)
- Memory-v2 foundation (fact extraction, preferences)
- 7 operational modes (Shield/Sword framework)

### v3.2.0 (January 15, 2026) - Shield & Sword
- Shield mode: 16 manipulation pattern detection
- Sword mode: 15 ethical influence techniques
- Portfolio injection (knows wins/value)
- Mode-based personality system

### v3.1.0 (January 12, 2026) - Council Ready
- Council participation via CONVENER
- Multi-agent routing via HEPHAESTUS
- Dynamic context injection

### v3.0.0 (January 10, 2026) - Reborn
- Complete rewrite from n8n to FastAPI
- OpenRouter integration (GPT-4o)
- Streaming responses
- Session management

### v2.x (December 2025) - Legacy
- n8n-based chat workflows
- Basic conversation memory
- Single mode operation

### v1.x (November 2025) - Prototype
- Initial concept
- Simple Q&A interface

---

## Version Components

| Component | Current Version | Location |
|-----------|-----------------|----------|
| aria-chat (backend) | 4.1.0 | /control-plane/agents/aria-chat/ |
| aria-frontend (web) | 4.1.0 | /data-plane/[env]/aria-frontend/ |
| aria-memory | 1.0.0 | /control-plane/agents/aria-memory/ |
| aria-omniscience | 1.0.0 | /control-plane/agents/aria-omniscience/ |
| System Prompt | V4 | /prompts/aria_system_prompt.txt |

---

## How to Check Version

**In chat:** Ask "What version are you?"

**Via API:** 
```bash
curl https://aria-api.leveredgeai.com/health
```

**In code:** Check `/opt/leveredge/ARIA-VERSION.md`

---

*Update this file with every ARIA release.*
