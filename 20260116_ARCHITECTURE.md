# LEVEREDGE ARCHITECTURE - January 16, 2026

## System Overview

Multi-agent AI automation infrastructure with control plane / data plane separation.

## Directory Structure

```
/opt/leveredge/                    # System root
├── gaia/                          # Tier 0 - Emergency restore (outside everything)
├── control-plane/                 # The brain
│   ├── n8n/                       # control.n8n.leveredgeai.com
│   ├── agents/                    # FastAPI backends
│   ├── workflows/                 # n8n workflow exports
│   ├── dashboards/                # Web UIs
│   └── event-bus/                 # Agent communication
├── data-plane/
│   ├── prod/                      # Production (n8n, supabase, aria)
│   └── dev/                       # Development (mirror of prod)
├── shared/
│   ├── scripts/                   # CLI tools
│   ├── backups/                   # CHRONOS destination
│   └── credentials/               # AEGIS store
└── monitoring/                    # Prometheus + Grafana
```

## Agent Registry

### Tier 0: Genesis
- GAIA (8000) - Bootstrap/rebuild from nothing

### Tier 1: Control Plane
- ATLAS (8007) - Master Orchestrator
- HEPHAESTUS (8011) - Builder/Deployer
- ATHENA (8013) - Planner/Documenter
- AEGIS (8012) - Credential Vault
- CHRONOS (8010) - Backup Manager
- HADES (8008) - Rollback/Recovery
- HERMES (8014) - Notifications
- ARGUS (8009) - Monitoring
- ALOY (8015) - Auditor/Bug Hunter

### Tier 2: Data Plane
- ARIA - Personal Assistant
- VARYS - Project Manager (future)

### Tier 3: Business (Post-Launch)
- SCHOLAR, ORACLE, LIBRARIAN, SCRIBE, MERCHANT

### Tier 4: Personal (Future)
- APOLLO, DEMETER, MENTOR, EROS

## Key Decisions

1. Agents communicate via Event Bus (not isolated)
2. AEGIS applies credentials (HEPHAESTUS never sees values)
3. ARIA is human liaison (informed of all, doesn't build)
4. Native n8n nodes preferred over Code nodes
5. Every control plane interaction logged
6. Dev/prod identical structure, different credentials

## Domains

### Control Plane
- control.n8n.leveredgeai.com
- aegis.leveredgeai.com
- chronos.leveredgeai.com
- hades.leveredgeai.com
- aloy.leveredgeai.com
- grafana.leveredgeai.com

### Production
- n8n.leveredgeai.com
- aria.leveredgeai.com
- studio.leveredgeai.com
- api.leveredgeai.com

### Development
- dev.n8n.leveredgeai.com
- dev.aria.leveredgeai.com
- dev.studio.leveredgeai.com
- dev.api.leveredgeai.com

## Build Phases

- Phase 0: GAIA + Event Bus (CURRENT)
- Phase 1: Control plane n8n + ATLAS
- Phase 2: HEPHAESTUS + AEGIS
- Phase 3: CHRONOS + HADES
- Phase 4: ARGUS + ALOY + HERMES + ATHENA
- Phase 5: Data plane sync
