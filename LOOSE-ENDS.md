# LEVEREDGE LOOSE ENDS & TODO

*Last Updated: January 17, 2026 (2:30 AM)*
*Mode: JUGGERNAUT until May/June 2026*

---

## 🗓️ WEEKEND BATTLE PLAN

### FRIDAY Jan 17 - LOOSE ENDS BLITZ
**Target:** Items 1-10, then 13-20 (skip 11-12 niche/TRW for now)

| # | Item | Est Time |
|---|------|----------|
| 1 | promote-to-prod.sh API keys | 15 min |
| 2 | ARIA V3.2 - portfolio injection | 2 hrs |
| 3 | ARIA V3.2 - time calibration | 1 hr |
| 4 | ARIA frontend polish (Bolt.new) | 3 hrs |
| 5 | Test full ARIA demo | 1 hr |
| 6 | Shield/Sword nodes | 2 hrs |
| 7 | Cost tracking (llm_usage) | 2 hrs |
| 8 | Dev credential separation | 1 hr |
| 9 | Cloudflare Access control plane | 2 hrs |
| 10 | GitHub remote push | 30 min |
| **SKIP** | 11. Niche research | - |
| **SKIP** | 12. TRW Outreach Module | - |
| 13 | AEGIS credential manager enhance | 1 hr |
| 14 | SMTP configuration | 1 hr |
| 15 | ARIA/PA tool routing separation | 1 hr |
| 16 | GitHub repo audit | 30 min |
| 17 | File upload system | 3 hrs |
| 18 | Telegram interface for ARIA | 2 hrs |
| 19 | Unified memory consolidation | 2 hrs |
| 20 | Two-way Google Tasks sync | 1 hr |

### SATURDAY Jan 18 - TECHNICAL DEBT + AGENTS
**Morning:** Technical debt cleanup
**Afternoon/Evening:** Start building new agents

| Item | Est Time |
|------|----------|
| Convert all agents to native n8n nodes | 4-6 hrs |
| Storage bucket cleanup | 1 hr |
| n8n chat memory cleanup | 1 hr |
| n8n-troubleshooter rename | 30 min |
| Old volume locations cleanup | 30 min |
| **Then start:** CHIRON (business mentor) | 3-4 hrs |

### SUNDAY Jan 19+ - AGENT BUILDING BEGINS
- Continue CHIRON
- Start SCHOLAR (market research)
- Start LIBRARIAN (RAG)
- Start content agents (SAPPHO, SCRIBE, DAEDALUS, CICERO, THOTH)

---

## 🎯 MASTER TIMELINE

| Phase | Dates | Focus |
|-------|-------|-------|
| **Infrastructure** | Jan 11-16 | ✅ COMPLETE |
| **Loose Ends + Agents** | Jan 17-31 | 🔥 NOW |
| **Outreach** | Feb 1-28 | Niche, TRW, 10 attempts, 3 calls |
| **Launch** | March 1 | IN BUSINESS |
| **Scale** | March-June | Clients + more agents |

---

## 📋 DETAILED LOOSE ENDS

### 🔴 HIGH PRIORITY (By Jan 22 - ARIA Demo Ready)

#### 1. promote-to-prod.sh API Keys ⬜
**Status:** Script created, needs keys
**Task:** Get API keys from n8n UI, add to .env
**Location:** `/opt/leveredge/shared/scripts/.env`

#### 2. ARIA V3.2 - Dynamic Portfolio Injection ⬜
**Status:** Guide exists, needs implementation
**Task:** HTTP Request node to fetch `aria_get_portfolio_summary()`
**Location:** `/home/damon/environments/dev/aria-assistant/n8n-portfolio-integration.md`

#### 3. ARIA V3.2 - Time Calibration ⬜
**Task:** Make time responses less verbose
**Why:** Current responses too wordy when asked what time it is

#### 4. ARIA Frontend Upgrade ⬜
**Task:** Rebuild/enhance in Bolt.new
**Components:** Charts, data tables, code blocks, responsive

#### 5. Demo Walkthrough Test ⬜
**Task:** Full test of all 7 modes, portfolio, time, mobile

#### 6. Shield/Sword Nodes ⬜
**Task:** Separate dark psychology into distinct nodes
- Shield = Pre-processing (detect manipulation)
- Sword = Post-processing (frame response)

### 🟡 MEDIUM PRIORITY (By Feb 1)

#### 7. Cost Tracking System ⬜
```sql
llm_usage (id, timestamp, model, input_tokens, output_tokens, cost_usd, context, agent_source)
llm_usage_daily (date, total_cost, total_tokens, by_model, by_agent)
llm_budget_alerts (threshold_daily, threshold_monthly, notification_channel)
```

#### 8. Dev Credential Separation ⬜
| Credential | PROD refs | Needs DEV |
|------------|-----------|-----------|
| Google Sheets | 9 | Yes |
| Telegram | 14 | Yes |
| Google Drive | 4 | Yes |
| Pinecone | misc | Yes |
| Fal AI | misc | Yes |

#### 9. Cloudflare Access for Control Plane ⬜
**Current:** Basic auth
**Target:** Cloudflare Access with email

#### 10. Push to GitHub Remote ⬜
**Task:** Create repo, add remote, push /opt/leveredge

#### 11. Niche Research & Selection ⬜ (SKIP FOR NOW)
**Task:** Pick ONE niche by Jan 24
**Candidates:** Water utilities, environmental, municipal, law firms, real estate

#### 12. TRW Outreach Module ⬜ (SKIP FOR NOW)
**Task:** Complete outreach training
**Time:** 8+ hours

### 🟢 LOWER PRIORITY

#### 13. AEGIS Credential Manager Enhancement ⬜
**Task:** Expiration alerts, rotation reminders

#### 14. SMTP Configuration ⬜
**Options:** Gmail, SendGrid, AWS SES

#### 15. ARIA/PA Tool Routing Separation ⬜
**Task:** Create ARIA-specific tool versions

#### 16. GitHub Repo Audit ⬜
**Task:** Ensure all repos have remotes, SSH keys

#### 17. File Upload System ⬜
- PDF processing with citations
- Image processing with vision
- Audio transcription (Whisper)
- Video processing

#### 18. Telegram Interface for ARIA ⬜
- Bot creation and token
- Webhook setup
- Cross-interface continuity

#### 19. Unified Memory Consolidation ⬜
- Extract facts from conversations
- Semantic search across all

#### 20. Two-Way Google Tasks Sync ⬜
- Currently one-way
- Need bidirectional

---

## 🔧 TECHNICAL DEBT

| Item | Priority | Est Time |
|------|----------|----------|
| **Convert all agents to native n8n nodes** | 🔴 HIGH | 4-6 hrs |
| Storage bucket cleanup | 🟡 Medium | 1 hr |
| n8n chat memory cleanup | 🟡 Medium | 1 hr |
| n8n-troubleshooter rename | 🟢 Low | 30 min |
| Old volume locations | 🟢 Low | 30 min |

---

## 🤖 AGENTS TO BUILD (31 Total)

### ✅ BUILT (11)
GAIA, ATLAS, HEPHAESTUS, AEGIS, CHRONOS, HADES, HERMES, ARGUS, ALOY, ATHENA, ARIA

### 🔥 NEXT WAVE - Business (10)
| Agent | Domain | Priority |
|-------|--------|----------|
| CHIRON | Business mentor | 🔴 HIGH |
| SCHOLAR | Market research | 🔴 HIGH |
| LIBRARIAN | RAG/knowledge | 🔴 HIGH |
| SAPPHO | Copywriting | 🟡 |
| SCRIBE | Long-form content | 🟡 |
| DAEDALUS | Graphics | 🟡 |
| CICERO | Presentations | 🟡 |
| THOTH | Reports | 🟡 |
| VARYS | Project management | 🟡 |
| MERCHANT | Sales/CRM | 🟡 |
| ORACLE | Forecasting | 🟢 |

### 🌴 LIFE WAVE (9)
NIKE, DEMETER, COCO, PHILEAS, APOLLO, MENTOR, EROS, MIDAS, NICHOLAS

### 🌐 PRODUCT (1)
Geopolitical Intelligence System

---

## 🚫 DECISIONS MADE

| Decision | Rationale |
|----------|-----------|
| No LinkedIn until after first clients | Protecting reputation |
| Direct outreach via TRW methodology | More targeted than social |
| ARIA is personal assistant, not a product | Sell outcomes, not tools |
| Native n8n nodes over Code nodes | Visibility and maintainability |
| JUGGERNAUT MODE until May/June | Momentum is everything |

---

## 📍 KEY FILE LOCATIONS

| File | Purpose |
|------|---------|
| `/opt/leveredge/README.md` | Quick reference |
| `/opt/leveredge/ARCHITECTURE.md` | System design |
| `/opt/leveredge/MASTER-LAUNCH-CALENDAR.md` | Timeline |
| `/opt/leveredge/LOOSE-ENDS.md` | This file |
| `/opt/leveredge/FUTURE-VISION.md` | Agent roadmap |
| `/opt/leveredge/LESSONS-LEARNED.md` | Knowledge base |
| `/home/damon/.claude/EXECUTION_RULES.md` | Claude Code rules |

---

## 🎯 SUCCESS BY DATE

### Jan 22 - ARIA Demo Ready
- [ ] Portfolio injection working
- [ ] Time calibration fixed
- [ ] Frontend polished
- [ ] All 7 modes tested
- [ ] Mobile experience smooth

### Jan 31 - Loose Ends Complete
- [ ] Items 1-10 done
- [ ] Items 13-20 done
- [ ] Technical debt cleared
- [ ] First wave agents started

### Feb 28 - Outreach Complete
- [ ] Niche selected
- [ ] TRW module done
- [ ] 10 outreach attempts
- [ ] 3 discovery calls

### March 1 - IN BUSINESS
- [ ] Ready for paying clients

### May/June - Scale
- [ ] All 31 agents operational
- [ ] $30K+ MRR
- [ ] Quit government job
