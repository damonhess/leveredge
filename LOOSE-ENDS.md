# LEVEREDGE LOOSE ENDS & TODO

*Last Updated: January 17, 2026 (1:30 AM)*

---

## 🎯 LAUNCH TIMELINE

| Milestone | Date | Status |
|-----------|------|--------|
| Infrastructure complete | Jan 16 | ✅ DONE |
| ARIA demo-ready | Jan 22 | ⬜ IN PROGRESS |
| Outreach ready | Jan 29 | ⬜ UPCOMING |
| 10 outreach attempts | Feb 4 | ⬜ UPCOMING |
| 3 discovery calls | Feb 12 | ⬜ UPCOMING |
| **IN BUSINESS** | **March 1** | 🎯 TARGET |

---

## 🔄 IN PROGRESS

### Connect n8n to Portfolio Dynamically
**Status:** Guide exists, needs implementation
**Task:** Add HTTP Request node to fetch `aria_get_portfolio_summary()` and inject into DAMON_PROFILE
**Location:** `/home/damon/environments/dev/aria-assistant/n8n-portfolio-integration.md`
**MCP:** Use n8n-troubleshooter (61 tools)

### promote-to-prod.sh API Keys
**Status:** Script created, needs keys configured
**Task:** Get API keys from n8n UI, add to .env
**Location:** `/opt/leveredge/shared/scripts/.env`

---

## 📋 HIGH PRIORITY (By Jan 22 - ARIA Demo Ready)

### 1. ARIA Frontend Upgrade
**Task:** Rebuild/enhance ARIA web UI in Bolt.new
**Why:** Better UX, richer components, mobile optimization
**Approach:** Build in Bolt.new, manage via git, deploy to dev first
**Components needed:**
- Interactive charts (Recharts/Chart.js)
- Data tables with sorting/filtering
- Code blocks with syntax highlighting
- Better responsive layouts
- Gesture support for mobile

### 2. Shield/Sword Nodes
**Task:** Separate dark psychology into distinct processing nodes
**Why:** Cleaner architecture, easier to tune
- **Shield** = Pre-processing (detect manipulation in user's situation)
- **Sword** = Post-processing (frame ARIA's response for maximum impact)

### 3. ARIA V3.2 Features
- Dynamic portfolio injection (fetches from `aria_portfolio_summary`)
- Improved time response calibration (less verbose)
- Better mode transitions

### 4. Test Full Demo Walkthrough
- All 7 modes working
- Portfolio data displaying
- Time awareness accurate
- Mobile experience smooth

---

## 📋 MEDIUM PRIORITY (By Feb 1 - Outreach Ready)

### 5. Cost Tracking System
**Task:** Create `llm_usage` table and reporting
**Why:** Must track API costs before scaling autonomous features
**Tables needed:**
```sql
llm_usage (
  id, timestamp, model, input_tokens, output_tokens,
  cost_usd, context, agent_source
)

llm_usage_daily (
  date, total_cost, total_tokens, by_model JSONB, by_agent JSONB
)

llm_budget_alerts (
  threshold_daily, threshold_monthly, notification_channel
)
```

### 6. Complete Dev Credential Separation
**Remaining:**
| Credential | PROD refs | Needs DEV version |
|------------|-----------|-------------------|
| Google Sheets | 9 workflows | Yes |
| Telegram | 14 workflows | Yes |
| Google Drive | 4 workflows | Yes |
| Pinecone | misc | Yes |
| Fal AI | misc | Yes |
| WhatsApp | misc | Yes |

### 7. Cloudflare Access for Control Plane
**Current:** Basic auth
**Target:** Cloudflare Access with email verification
**Why:** Proper security for production

### 8. Push to GitHub Remote
**Task:** Create repo, add remote, push
**Why:** Backup + future collaboration

### 9. GAIA Telegram Emergency Bot
**Task:** Set up bot for remote recovery
**Why:** Can't always SSH in emergencies

### 10. Niche Research & Selection
**Task:** Research top 5 niches, pick ONE by Jan 24
**Candidates:**
- Water utilities compliance
- Environmental permits
- Municipal government
- Small law firms
- Real estate compliance

### 11. TRW Outreach Module
**Task:** Complete The Real World outreach training
**Time:** 8+ hours
**Deliverables:** Scripts, templates, methodology

---

## 📋 LOW PRIORITY (Post-Launch)

### 12. Credential Manager Agent (AEGIS Enhancement)
**Problem:** API keys, OAuth tokens scattered everywhere
**Need:** Central tracking with expiration alerts, rotation reminders

### 13. Email Configuration (SMTP)
**Issue:** Supabase Auth pointing to non-existent mail server
**Current:** Using autoconfirm workaround
**Options:** Gmail, SendGrid, or AWS SES
**Impact:** Production auth requires real emails eventually

### 14. ARIA/PA Tool Routing Separation
**Issue:** Both ARIA and Personal Assistant share same tool workflows
**Better:** Create ARIA-specific versions for different schemas

### 15. GitHub Repo Management
**Need:** Audit all repos, ensure GitHub remotes, proper SSH keys

### 16. File Upload System
- PDF processing with page-level citations
- Image processing with vision API
- Audio transcription (Whisper)
- Video processing (extract audio + frames)

### 17. Telegram Interface for ARIA
- Bot creation and token
- Webhook setup
- Cross-interface continuity

### 18. Unified Memory Consolidation
- Extract facts/preferences from conversations
- Semantic search across all conversations

### 19. Two-Way Google Tasks Sync
- Currently one-way (n8n → Google Tasks)
- Need bidirectional sync

---

## 🔧 TECHNICAL DEBT

| Item | Issue | Solution | Priority |
|------|-------|----------|----------|
| Storage bucket cleanup | Deleted conversations leave orphaned files | Scheduled cleanup or edge function | Low |
| n8n chat memory cleanup | `n8n_chat_histories` not cleaned when archived | Scheduled cleanup workflow | Low |
| n8n-troubleshooter rename | Confusing name | Rename to n8n-prod | Low |
| Old volume data | Volumes in /home/damon/supabase/volumes | Move to /opt/leveredge eventually | Low |

---

## 🚫 DECISIONS MADE

| Decision | Rationale |
|----------|-----------|
| No LinkedIn until after first clients | Protecting reputation |
| Direct outreach via TRW methodology | More targeted than social |
| ARIA is personal assistant, not a product | Don't sell the tool, sell the outcomes |
| Credential manager waits until Feb | Outreach takes priority |
| Autonomous ATLAS deferred | Wait for revenue before API-heavy autonomy |
| Dev-first deployment | Never deploy directly to prod |
| Option A (dumb executors) for now | Zero API cost, human in loop |

---

## 🛠️ KEY TOOLS & COMMANDS

### Portfolio
```bash
add-win.sh "Title" "category" "description" low high "anchoring"
add-win.sh --summary
add-win.sh --list
```

### Development
```bash
# n8n workflow changes - use MCP, not UI
# n8n-control: Control plane (port 5679)
# n8n-troubleshooter: Prod (port 5678)
# n8n-troubleshooter-dev: Dev (port 5680)
```

### Deployment
```bash
cd /opt/leveredge/shared/scripts
./promote-to-prod.sh <workflow_id>
```

### Monitoring
```bash
docker ps | grep -E "supabase|n8n|control"
curl http://localhost:8016/status  # ARGUS fleet status
curl http://localhost:8014/health  # HERMES
```

---

## 📍 KEY FILE LOCATIONS

| File | Purpose |
|------|---------|
| `/opt/leveredge/README.md` | Quick reference |
| `/opt/leveredge/ARCHITECTURE.md` | System design |
| `/opt/leveredge/MASTER-LAUNCH-CALENDAR.md` | Timeline |
| `/opt/leveredge/LESSONS-LEARNED.md` | Knowledge base |
| `/opt/leveredge/LOOSE-ENDS.md` | This file |
| `/opt/leveredge/FUTURE-VISION.md` | Business roadmap |
| `/home/damon/.claude/EXECUTION_RULES.md` | Claude Code rules |
| `/home/damon/environments/dev/aria-assistant/prompts/` | ARIA prompts |

---

## 🎯 SUCCESS METRICS

### By End of January (Jan 31)
- [ ] ARIA V3.2 functional and polished
- [ ] Portfolio tracker connected dynamically
- [ ] Frontend upgraded via Bolt.new
- [ ] Full demo walkthrough successful

### By End of February (Feb 28)
- [ ] 10 outreach attempts completed
- [ ] 3 discovery calls scheduled
- [ ] TRW Outreach Module complete
- [ ] First potential clients identified
- [ ] Cost tracking implemented

### March 1, 2026
- [ ] **IN BUSINESS** - Ready to take paying clients

---

## 🔮 FUTURE VISION (Post-Launch)

### Option B: Autonomous Agents
- Add LLM reasoning to agents
- ATLAS routes intelligently
- HEPHAESTUS interprets vague requests
- **Trigger:** Revenue > $10K/month

### ARIA V4.0
- Multi-modal file processing
- Proactive reminders
- Telegram interface
- Voice interface

### Business Scaling
- Multi-tenant capability
- Client portal
- White-label options
- SOC 2 preparation

### Geopolitical Intelligence System
- Multi-agent news analysis
- Bias detection
- Separate product
- Timeline: 6-12 months post-launch
