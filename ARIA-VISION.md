# ARIA VISION & ENHANCEMENTS

*Captured: January 17, 2026 (2:45 AM)*

---

## ARIA AS CENTRAL NERVOUS SYSTEM

### Passive Awareness (No Query Needed)
ARIA should have a **live feed dashboard** of all agent activity:
- Every CHRONOS backup
- Every HADES rollback
- Every HERMES notification
- Every HEPHAESTUS build
- Every ARGUS alert
- Every ALOY anomaly
- Every project status change
- Every client interaction

**Implementation:**
- All agents already log to Event Bus (8099)
- Create ARIA Event Feed node that subscribes to Event Bus
- Surface in ARIA's context window automatically
- "What's happening?" shows real-time activity
- "What did I miss?" shows recent history

### Active Query (When Needed)
ARIA should also be able to:
- Query specific agent status
- Ask for detailed logs
- Request reports from any agent
- Drill down into specifics

---

## UI CHANGES

### 1. Bubble Expand: Click Not Hover
**Current:** Hover expands message bubble
**Target:** Click to expand
**Why:** Accidental expansions on mobile/touch, annoying

### 2. Token/Cost Info Per Message
**Display:**
- Input tokens
- Output tokens
- Model used
- Cost (USD)
- Latency

**Drill Down:**
- Click to see full breakdown
- Cumulative session cost
- Daily/weekly/monthly trends
- Cost by conversation

**Implementation:**
- Add to `aria_messages` table: `input_tokens`, `output_tokens`, `model`, `cost_usd`, `latency_ms`
- Display in message footer (subtle, expandable)
- Link to `llm_usage` table for drill-down

---

## FUTURE ARIA CAPABILITIES

### Email Integration
- ARIA gets her own email address (aria@leveredgeai.com?)
- Can receive and respond to emails
- Email → ARIA → Response → Email
- Filters, prioritization, drafting

### Phone Number
- Twilio or similar
- SMS interface to ARIA
- Quick queries on the go
- Notification delivery

### Voice Interface
- Speech-to-text input
- Text-to-speech output
- Real-time conversation
- Wake word? "Hey ARIA"

### Video Interface
- Video chat with ARIA
- Screen sharing for demos
- Avatar/face for ARIA?
- Loom-style recording

---

## BUSINESS INFRASTRUCTURE

### Website with Chatbot
- leveredgeai.com landing page
- Embedded chatbot (lead capture)
- Chat → CRM integration
- Qualification questions
- Book discovery call

### CRM System
- Lead tracking
- Pipeline management
- Client communication history
- Project status
- Invoice tracking
- Integration with MERCHANT agent

**Options:**
- Build custom in Supabase
- Use existing (HubSpot, Pipedrive, Close)
- Hybrid: Simple CRM + integrations

---

## AGENT NAMING THEMES (TO DECIDE)

| Tier | Theme Options |
|------|---------------|
| 0 | Cosmic (GAIA - keep) |
| 1 | Star Trek / Mass Effect / Halo |
| 2 | Game of Thrones (ARIA, VARYS - keep) |
| 3 | Titans of Industry / Mad Men |
| 4 | Avatar TLA / Ghibli / Cozy Games |
| 5 | NASA Missions / Sci-Fi Ships |

---

## PRIORITY ORDER

1. **Event Feed for ARIA** - See all agent activity
2. **Click not hover** - Quick UI fix
3. **Token/cost per message** - Visibility into spend
4. **Website + chatbot** - Lead capture
5. **CRM** - Client management
6. **Email** - aria@leveredgeai.com
7. **Phone/SMS** - Mobile access
8. **Voice** - Hands-free
9. **Video** - Future vision
