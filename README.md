# LEVEREDGE

*AI Automation Agency Infrastructure*
*Launch: March 1, 2026*

---

## Quick Status

| Component | Status |
|-----------|--------|
| Control Plane | ✅ 9 agents active |
| Data Plane PROD | ✅ n8n + Supabase |
| Data Plane DEV | ✅ n8n + Supabase |
| ARIA | ✅ Working |
| Monitoring | ✅ Prometheus + Grafana |

---

## Documentation

| File | Purpose | Update Frequency |
|------|---------|------------------|
| **ARCHITECTURE.md** | System design, agent registry, networks | Major changes |
| **MASTER-LAUNCH-CALENDAR.md** | Timeline, milestones, weekly tasks | Weekly |
| **LOOSE-ENDS.md** | All tasks, priorities, technical debt | After each session |
| **LESSONS-LEARNED.md** | Technical knowledge base | After each session |
| **LESSONS-SCRATCH.md** | Quick debug capture | During debugging |
| **FUTURE-VISION.md** | Business roadmap, autonomy plans | Monthly |

---

## Directory Structure

```
/opt/leveredge/
├── gaia/                          # Tier 0 - Emergency restore
├── control-plane/
│   ├── n8n/                       # control.n8n.leveredgeai.com
│   └── agents/                    # FastAPI backends
├── data-plane/
│   ├── prod/
│   │   ├── n8n/                   # n8n.leveredgeai.com
│   │   └── supabase/              # api.leveredgeai.com
│   └── dev/
│       ├── n8n/                   # dev.n8n.leveredgeai.com
│       └── supabase/
├── shared/
│   ├── scripts/                   # CLI tools
│   └── backups/                   # CHRONOS destination
└── monitoring/                    # Prometheus + Grafana
```

---

## Agent Fleet

| Agent | Port | Purpose |
|-------|------|---------|
| GAIA | 8000 | Emergency bootstrap |
| ATLAS | n8n | Master orchestrator |
| HEPHAESTUS | 8011 | Builder (MCP) |
| AEGIS | 8012 | Credential vault |
| CHRONOS | 8010 | Backup manager |
| HADES | 8008 | Rollback system |
| HERMES | 8014 | Notifications |
| ARGUS | 8016 | Monitoring |
| ALOY | 8015 | Audit/anomaly |
| ATHENA | 8013 | Documentation |
| Event Bus | 8099 | Inter-agent communication |

---

## Key URLs

### Control Plane
- control.n8n.leveredgeai.com

### Production
- n8n.leveredgeai.com
- aria.leveredgeai.com
- api.leveredgeai.com
- studio.leveredgeai.com
- grafana.leveredgeai.com

### Development
- dev.n8n.leveredgeai.com
- dev-aria.leveredgeai.com

---

## Execution Workflow

```
1. Claude Web writes spec via HEPHAESTUS
2. CHRONOS backup
3. Dispatch to GSD: /gsd [spec path]
4. Verify via HEPHAESTUS
5. HADES rollback if needed
6. Git commit
```

---

## MCP Server Mapping

| MCP | Port | Target |
|-----|------|--------|
| n8n-control | 5679 | Control plane agents |
| n8n-troubleshooter | 5678 | PROD data plane |
| n8n-troubleshooter-dev | 5680 | DEV data plane |
