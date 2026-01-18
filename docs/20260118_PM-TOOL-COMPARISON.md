# PM TOOL COMPARISON: Leantime vs OpenProject

**Date:** January 18, 2026
**Purpose:** Choose PM system(s) for CONSUL to manage

---

## Quick Verdict

| Aspect | Leantime | OpenProject | Winner |
|--------|----------|-------------|--------|
| **Complexity** | Simpler | Full enterprise | Depends |
| **ADHD-friendly** | ✅ Yes (designed for neurodivergent) | ❌ Steeper learning curve | Leantime |
| **Complex projects** | Basic | ✅ Advanced | OpenProject |
| **Gantt charts** | Basic | ✅ Advanced | OpenProject |
| **Agile/Scrum** | Kanban | ✅ Full Scrum + Kanban | OpenProject |
| **Self-hosted** | ✅ Docker | ✅ Docker | Tie |
| **Cost** | Free (self-hosted) | Free Community Edition | Tie |
| **API** | REST | ✅ Robust REST | OpenProject |
| **GitHub stars** | 8,856 | 14,073 | OpenProject |
| **Community** | Smaller | ✅ Large, active | OpenProject |
| **Integrations** | Limited | ✅ Git, Slack, Office | OpenProject |

---

## Leantime

### Strengths
- **Neurodivergent-friendly** - Designed using behavioral science and motivational psychology
- **Simpler UI** - Less overwhelming for smaller teams
- **Quick setup** - Docker, minimal config
- **HIPAA compliant** - If health clients later
- **Whiteboarding, research boards** - Creative planning tools

### Weaknesses
- Fewer integrations
- Basic Gantt
- Smaller community
- Limited for complex multi-team projects

### Best For
- Individual planning (your daily work)
- Small creative projects
- When you need simplicity over power

### Docker
```yaml
services:
  leantime:
    image: leantime/leantime:latest
    ports:
      - "8040:80"
    environment:
      LEAN_DB_HOST: db
      LEAN_DB_USER: lean
      LEAN_DB_PASSWORD: secret
      LEAN_DB_DATABASE: leantime
```

---

## OpenProject

### Strengths
- **Enterprise-grade** - Used by large organizations
- **Full methodology support** - Waterfall, Agile, Scrum, Kanban, hybrid
- **Advanced Gantt** - Dependencies, baselines, critical path
- **Resource management** - Allocation, capacity planning
- **Robust API** - Better for CONSUL integration
- **Active community** - 14K+ GitHub stars, frequent updates
- **More integrations** - Git, Slack, SharePoint, Office

### Weaknesses
- Steeper learning curve
- UI can feel clunky
- More setup complexity
- Overkill for simple projects

### Best For
- Client projects (complex)
- Multi-phase, multi-team work
- When you need full PM capabilities

### Docker
```yaml
services:
  openproject:
    image: openproject/openproject:14
    ports:
      - "8041:80"
    environment:
      OPENPROJECT_SECRET_KEY_BASE: <secret>
      OPENPROJECT_HOST__NAME: openproject.leveredgeai.com
    volumes:
      - op_data:/var/openproject/assets
```

---

## Recommendation: BOTH

### Use Case Split

| Tool | Use For |
|------|---------|
| **Leantime** | Personal planning, ADHD-friendly daily work, simple internal projects |
| **OpenProject** | Client projects, complex multi-phase work, enterprise deliverables |

### CONSUL Multi-PM Architecture

```
                    ┌─────────────┐
                    │   CONSUL    │
                    │ (PM Agent)  │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
     ┌─────────────────┐      ┌─────────────────┐
     │    Leantime     │      │   OpenProject   │
     │                 │      │                 │
     │ • Personal      │      │ • Client work   │
     │ • Simple tasks  │      │ • Complex proj  │
     │ • Daily focus   │      │ • Gantt/deps    │
     │ • Creative      │      │ • Resources     │
     └─────────────────┘      └─────────────────┘
```

CONSUL maintains a unified project model internally and syncs to whichever PM system is appropriate for each project type.

---

## Domains

| Service | Domain |
|---------|--------|
| Leantime | leantime.leveredgeai.com |
| OpenProject | openproject.leveredgeai.com |

---

## GSD: Deploy Both

Tell Claude Code:
```
Deploy Leantime and OpenProject to the Docker stack.

1. Add to docker-compose.yml in /home/damon/stack
2. Configure Caddy for leantime.leveredgeai.com and openproject.leveredgeai.com
3. Add DNS A records in Cloudflare
4. Initialize both with admin accounts
5. Document credentials in AEGIS

Ports:
- Leantime: 8040
- OpenProject: 8041
```

---

## Integration Priority

1. **OpenProject first** - More robust API, better for complex projects
2. **Leantime second** - For personal/simple project sync
3. **Abstract layer** - CONSUL treats both through unified interface
