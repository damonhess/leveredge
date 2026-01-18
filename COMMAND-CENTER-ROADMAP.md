# COMMAND CENTER ROADMAP
*Last Updated: January 17, 2026 11:30 PM*

## GOAL
Build themed dashboards + Master Control Center using the agent team

---

## PHASE 1: FOUNDATION ✅ COMPLETE

| Step | Description | Status | Date |
|------|-------------|--------|------|
| 1.1 | Define domain architecture + themes | ✅ Done | Jan 17 |
| 1.2 | Approve agent naming scheme | ✅ Done | Jan 17 |
| 1.3 | Build CONCLAVE system (CONVENER + SCRIBE) | ✅ Done | Jan 17 |
| 1.4 | Fix HEPHAESTUS MCP for Claude Web visibility | ✅ Done | Jan 17 |
| 1.5 | Start CONVENER service (port 8300) | ✅ Done | Jan 17 |
| 1.6 | Start SCRIBE service (port 8301) | ✅ Done | Jan 17 |

---

## PHASE 2: NAMING & PROFILES ✅ COMPLETE

| Step | Description | Status | Date |
|------|-------------|--------|------|
| 2.1 | Rename agent directories (18 agents) | ✅ Done | Jan 17 |
| 2.2 | Update CONVENER AGENT_ENDPOINTS (40 agents) | ✅ Done | Jan 17 |
| 2.3 | Update agent-registry.yaml | ✅ Done | Jan 17 |
| 2.4 | Update council_agent_profiles in DB (19 profiles) | ✅ Done | Jan 17 |
| 2.5 | Update fleet dashboard with themed categories | ✅ Done | Jan 17 |
| 2.6 | Add auto-run + domain supervisors to CONVENER | ✅ Done | Jan 17 |
| 2.7 | Store ANTHROPIC_API_KEY in AEGIS | ✅ Done | Jan 17 |

---

## PHASE 3: DESIGN SESSION ✅ COMPLETE

| Step | Description | Status | Date |
|------|-------------|--------|------|
| 3.1 | Council design session (via Claude Web to save $) | ✅ Done | Jan 17 |
| 3.2 | Define domain visual themes | ✅ Done | Jan 17 |
| 3.3 | Define Master Control Center layout | ✅ Done | Jan 17 |
| 3.4 | Define VARYS role (intelligence, not money) | ✅ Done | Jan 17 |
| 3.5 | Create detailed build spec | ✅ Done | Jan 17 |

**Design Decisions Made:**
- VARYS = Master of Whisperers (intelligence) - overlay + portal
- LITTLEFINGER = Master of Coin (money) - in THE KEEP
- Master Control Center = Technomantic Bridge aesthetic
- 9 domain portals arranged around central hub
- V key summons VARYS overlay anywhere
- Top bar shows revenue/portfolio/countdown/status

---

## PHASE 4: BUILD MASTER CONTROL CENTER 🔄 IN PROGRESS

| Step | Description | Status | Date |
|------|-------------|--------|------|
| 4.1 | Create spec file | ✅ Done | Jan 17 |
| 4.2 | Build Next.js app (Claude Code) | 🔄 Building | Jan 17 |
| 4.3 | Test locally | ⏳ Pending | |
| 4.4 | Add Cloudflare DNS | ⏳ Pending | |
| 4.5 | Configure Caddy | ⏳ Pending | |
| 4.6 | Deploy to command.leveredgeai.com | ⏳ Pending | |

**Spec Location:** `/opt/leveredge/specs/MASTER-CONTROL-CENTER-SPEC.md`
**Build Location:** `/opt/leveredge/ui/command-center/`

---

## PHASE 5: BUILD DOMAIN DASHBOARDS ⏳ PENDING

| Step | Description | Status |
|------|-------------|--------|
| 5.1 | THE KEEP (GoT war room) - business ops | ⏳ |
| 5.2 | THE SHIRE (LOTR hobbit) - personal wellness | ⏳ |
| 5.3 | ARIA SANCTUM (ethereal) - personal AI | ⏳ |
| 5.4 | PANTHEON (Olympus) - system control | ⏳ |
| 5.5 | ALCHEMY (mystic workshop) - creative | ⏳ |
| 5.6 | SENTINELS (guardians) - security | ⏳ |
| 5.7 | CHANCERY (royal court) - legal/financial | ⏳ |
| 5.8 | GAIA (primordial) - emergency/genesis | ⏳ |
| 5.9 | VARYS full dashboard - intelligence HQ | ⏳ |

---

## PHASE 6: API INTEGRATION ⏳ PENDING

| Step | Description | Status |
|------|-------------|--------|
| 6.1 | Connect to real system health | ⏳ |
| 6.2 | Connect to portfolio data (VARYS) | ⏳ |
| 6.3 | Connect to agent activity | ⏳ |
| 6.4 | Connect to ARIA whispers | ⏳ |
| 6.5 | Real-time updates via WebSocket | ⏳ |

---

## DOMAIN THEMES (Approved)

| Domain | Theme | Supervisor | Colors |
|--------|-------|------------|--------|
| **GAIA** | Primordial Creation | GAIA | Earth brown, lava orange, gold |
| **PANTHEON** | Mount Olympus | ATLAS | Gold, white marble, sky blue |
| **SENTINELS** | Mythic Guardians | GRIFFIN | Dark red, slate, tomato |
| **THE SHIRE** | LOTR Comfort | GANDALF | Forest green, brown, gold |
| **THE KEEP** | Game of Thrones | TYRION | Slate gray, crimson, silver |
| **CHANCERY** | Royal Court | MAGISTRATE | Indigo, crimson, gold |
| **ALCHEMY** | Mystic Workshop | CATALYST | Magenta, copper, teal |
| **ARIA SANCTUM** | Ethereal Intelligence | ARIA | Cyan, purple, silver |
| **VARYS** | Whisper Network | VARYS | Deep purple, silver, red |

---

## MASTER AESTHETIC: TECHNOMANTIC BRIDGE

```
Colors:
  void:    #0a0e27    // Deep space background
  aether:  #00d4ff    // Cyan primary
  arcane:  #8b5cf6    // Purple secondary  
  relic:   #fbbf24    // Gold accents
  life:    #22c55e    // Healthy green
  ember:   #ef4444    // Alert red

Effects:
  - Starfield background with parallax
  - Energy threads connecting portals
  - Breathing glow on central hub
  - Particle trails on hover

Typography:
  - Orbitron for headings (techy)
  - Inter for body (readable)
  - JetBrains Mono for data
```

---

## KEY DECISIONS

| Decision | Outcome |
|----------|---------|
| Run design council through Claude Web | Saves API costs ($0 vs ~$0.25/meeting) |
| VARYS = intelligence, LITTLEFINGER = money | Correct GoT roles |
| VARYS overlay (V key) + portal | Best of both worlds |
| Build via Claude Code + spec | Most powerful approach |
| Can port to Bolt.diy later | Already have it on old stack |
| URLs easily changeable | Caddy + Cloudflare API |

---

## INFRASTRUCTURE

| URL | Purpose | Port |
|-----|---------|------|
| command.leveredgeai.com | Master Control Center | 3000 |
| aria.leveredgeai.com | ARIA Chat (existing) | - |
| control.n8n.leveredgeai.com | n8n Control Plane | 5679 |
| n8n.leveredgeai.com | n8n Data Plane | 5678 |

**Cloudflare:** Can automate DNS via API (add to AEGIS later)

---

## BLOCKING ISSUES

*None currently*

---

## SESSION VALUE

| Item | Value Added |
|------|-------------|
| CONVENER enhancements (auto-run, domains) | $2K-$4K |
| Design session (themes, layout, spec) | $3K-$5K |
| Master Control Center spec | $2K-$3K |
| **Session Total** | **$7K-$12K** |

**Portfolio: $65K-$129K across 31+ wins**

---

## NOTES

- Claude Web = command center, saves API costs for design work
- Claude Code = builder, does the heavy lifting
- Bolt.diy = visual iteration tool (already on old stack)
- CONVENER works but db_get has silent failures - fix later
- 43 days to March 1 launch
