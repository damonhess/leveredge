# ARIA Agent Pages - UI/UX Specification

**Created:** January 18, 2026
**Purpose:** Define what each agent's dedicated page should display in ARIA frontend
**Principle:** Each page = Dashboard + Actions + Chat Interface

---

## Design Principles

### Universal Elements (Every Agent Page)
1. **Agent Header**
   - Avatar/icon with signature color
   - Name and tagline
   - Status indicator (🟢 online / 🟡 busy / 🔴 offline)
   - Version number
   - Last activity timestamp

2. **Quick Chat** (always visible)
   - Collapsible chat panel on right side
   - Pre-populated with agent-specific suggested prompts
   - Full conversation history with this agent

3. **Activity Feed**
   - Recent actions taken by this agent
   - Filterable by date, type, status

4. **Settings Gear**
   - Agent-specific preferences
   - Notification settings
   - Permissions (if applicable)

### ADHD-Friendly Design
- ONE primary metric highlighted (most important thing)
- Visual status indicators (red/yellow/green)
- Action buttons with clear labels
- Undo where possible
- Minimal text, maximum visual clarity

---

## TIER 1: INFRASTRUCTURE AGENTS

---

### AEGIS (Credential Vault) - Port 8012

**Tagline:** "Guardian of Secrets"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Credential Health Score** | Large gauge (0-100) | PRIMARY |
| Expiring Soon | Count badge (30/60/90 days) | HIGH |
| Total Credentials | Number by type | MEDIUM |
| Last Rotation | Timestamp | LOW |
| Failed Auth (24h) | Alert count | HIGH if >0 |

#### Organized Views
- **By Project:** LeverEdge, ARIA, Personal, Client-X
- **By Provider:** Google, AWS, OpenAI, Anthropic, Supabase, n8n
- **By Type:** API Keys, OAuth Tokens, Passwords, Certificates, SSH Keys
- **By Status:** Active, Expiring, Expired, Disabled

#### Credential Card Display
```
┌─────────────────────────────────────────┐
│ 🔑 OpenAI API Key (Production)          │
│ Provider: OpenAI    Project: LeverEdge  │
│ Created: Jan 1, 2026    Expires: Never  │
│ Last Used: 2 hours ago                  │
│ Used By: ARIA, SCHOLAR, CHIRON          │
│ [Test] [Rotate] [View Usage] [Delete]   │
└─────────────────────────────────────────┘
```

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Add Credential | Guided wizard | Primary |
| Sync from n8n | Pull credentials | Secondary |
| Bulk Health Check | Test all | Secondary |
| Rotate Expiring | Rotate all due | Warning |
| Export Audit Log | Compliance report | Secondary |
| Emergency Revoke | Disable all | Danger |

#### Personal Vault Section
- All personal accounts (bank, email, subscriptions)
- Password manager integration
- 2FA backup codes storage
- Emergency access contacts

#### Chat Prompts
- "Check if the Salesforce API key is still valid"
- "Rotate all AWS credentials expiring this month"
- "What credentials failed authentication today?"
- "Set up automatic rotation for database passwords"
- "Show me all credentials used by ARIA"
- "Which credentials are shared across multiple apps?"

---

### CHRONOS (Backup Manager) - Port 8010

**Tagline:** "Master of Time"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Last Backup** | Time ago + status | PRIMARY |
| Storage Used | GB with trend | HIGH |
| Backup Success Rate | % (7 days) | HIGH |
| RPO Status | Meeting targets? | MEDIUM |
| Next Scheduled | Countdown | LOW |

#### Backup Timeline (Visual)
```
Jan 18  ●────●────●────●  4 backups (all ✓)
Jan 17  ●────●────○────●  3/4 successful
Jan 16  ●────●────●────●  4 backups (all ✓)
```

#### Backup List View
| Backup | Components | Size | Duration | Actions |
|--------|------------|------|----------|---------|
| Jan 18 06:00 | All | 2.4GB | 3m 42s | [Restore] [Verify] [Download] [Delete] |

#### Components Tracked
- Supabase (DEV + PROD)
- n8n workflows (DEV + PROD)
- Agent configs
- ARIA data
- Credentials (encrypted)
- Docker volumes

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Backup Now | Manual full backup | Primary |
| Backup Component | Select specific | Secondary |
| Test Restore | Dry run restore | Secondary |
| Verify Integrity | Check all backups | Secondary |
| Clean Old | Free space | Warning |
| Download | Local copy | Secondary |

#### Schedule View
- Daily: 6:00 AM (full)
- Hourly: On the hour (incremental)
- Before deployments (automatic)

#### Chat Prompts
- "Backup the CRM database right now"
- "When was the last successful backup of n8n?"
- "Test restoring yesterday's Supabase backup"
- "How much storage am I using for backups?"
- "Show me all failed backups from this week"
- "Set up a backup before I deploy"

---

### HADES (Rollback & Recovery) - Port 8008

**Tagline:** "Lord of the Underworld"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Rollback Ready** | Yes/No per system | PRIMARY |
| Active Deployments | Count | HIGH if >0 |
| Last Rollback | When + what | MEDIUM |
| Safe Window | Time remaining | MEDIUM |
| Recovery Points | Count available | LOW |

#### Deployment Timeline
```
v2.4.1 ──┬── Current (2h ago)
         │   [Rollback to v2.4.0]
v2.4.0 ──┼── Previous (yesterday)
         │   [Rollback to v2.3.9]
v2.3.9 ──┴── 3 days ago
```

#### System Status Cards
```
┌─────────────────────────────────┐
│ 🟢 ARIA Frontend               │
│ Version: 3.2.1                  │
│ Deployed: 2 hours ago           │
│ Rollback: Available (v3.2.0)    │
│ [Emergency Rollback] [History]  │
└─────────────────────────────────┘
```

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Emergency Rollback | BIG RED BUTTON | Danger |
| Planned Rollback | Scheduled | Warning |
| Create Checkpoint | Manual save point | Primary |
| Test Rollback | Dry run | Secondary |
| View Diff | Compare versions | Secondary |

#### Rollback History
| Date | Component | From | To | Reason | Duration |
|------|-----------|------|----|---------|---------| 
| Jan 17 | ARIA | 3.1.0 | 3.0.9 | Bug in chat | 45s |

#### Chat Prompts
- "Roll back ARIA to yesterday's version"
- "Can I safely rollback the API right now?"
- "What changed between current and previous?"
- "Create a checkpoint before I make changes"
- "Show me all rollbacks from this month"
- "What's the recovery time if something breaks?"

---

### PANOPTES (Integrity Guardian) - Port 8023

**Tagline:** "The All-Seeing Eye"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Health Score** | Large gauge (0-100) | PRIMARY |
| Critical Issues | Red badge | CRITICAL |
| High Issues | Orange badge | HIGH |
| Medium Issues | Yellow badge | MEDIUM |
| Last Scan | Timestamp | LOW |

#### Issue Breakdown (Visual)
```
Integrity ████████░░ 85%
Agents    ██████████ 100%
Ports     █████████░ 95%
Registry  ██████████ 100%
Services  ███████░░░ 78%
```

#### Issues List
| Severity | Category | Description | Affected | Actions |
|----------|----------|-------------|----------|---------|
| 🔴 CRITICAL | Port Conflict | 8020 claimed by 2 agents | VARYS, CERBERUS | [Fix Now] |
| 🟠 HIGH | Agent Offline | magistrate not responding | magistrate | [Restart] |
| 🟡 MEDIUM | No systemd | chronos running manually | chronos | [Create Service] |

#### Scan Types
- Full Scan (all checks)
- Quick Scan (critical only)
- Port Scan (conflicts)
- Agent Verify (identity)
- Registry Validate (YAML)

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Full Scan | Comprehensive check | Primary |
| Quick Scan | Critical only | Secondary |
| Fix All Critical | Auto-heal criticals | Danger |
| Generate Report | Export findings | Secondary |
| Set Baseline | After fixes | Secondary |

#### Scan Schedule
- Daily: 6:00 AM (full)
- Every 6 hours (quick)
- On-demand (manual)

#### Chat Prompts
- "Scan the system for integrity issues"
- "What's causing the low health score?"
- "Are there any port conflicts?"
- "Which agents aren't responding?"
- "Generate a compliance report"
- "Set up alerts if health drops below 80%"

---

### ASCLEPIUS (Healing Agent) - Port 8024

**Tagline:** "The Divine Physician"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Systems Healthy** | X/Y count | PRIMARY |
| Auto-Heals Today | Count | HIGH |
| Success Rate | % (7 days) | HIGH |
| Manual Required | Alert count | CRITICAL if >0 |
| Last Heal | Timestamp | LOW |

#### Healing Timeline
```
10:42 ✅ Restarted chronos (auto)
09:15 ✅ Cleared disk space (auto)
08:30 ✅ Fixed port 8020 conflict (auto)
06:45 ⚠️ magistrate restart failed (manual needed)
```

#### Current Healing Plans
```
┌─────────────────────────────────────────┐
│ 📋 Plan #42 - Pending Approval          │
│ Actions: 3 service restarts, 1 cleanup  │
│ Risk: LOW                               │
│ Created: 5 minutes ago                  │
│ [Approve & Execute] [Review] [Reject]   │
└─────────────────────────────────────────┘
```

#### Healing Strategies
| Strategy | Success Rate | Avg Time | Last Used |
|----------|--------------|----------|-----------|
| Service Restart | 95% | 12s | 2h ago |
| Port Reassign | 100% | 3s | 6h ago |
| Disk Cleanup | 98% | 45s | 1d ago |
| Config Fix | 87% | 8s | 3d ago |

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Auto-Heal Now | Heal all issues | Primary |
| Generate Plan | Create without executing | Secondary |
| Manual Heal | Select specific fix | Secondary |
| Emergency Full | Nuclear option | Danger |
| Disable Auto | Maintenance mode | Warning |

#### Chat Prompts
- "Heal all current issues automatically"
- "What problems couldn't you fix today?"
- "Restart all unresponsive services"
- "Clear disk space on the server"
- "Show me the healing plan before executing"
- "Why did the magistrate restart fail?"

---

### HERMES (Notifications) - Port 8014

**Tagline:** "Messenger of the Gods"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Messages Sent Today** | Count by channel | PRIMARY |
| Delivery Rate | % success | HIGH |
| Failed Deliveries | Alert count | HIGH if >0 |
| Channels Active | Status indicators | MEDIUM |

#### Channel Status
```
📱 Telegram    🟢 Connected (Damon)
📧 Email       🟡 Limited (no SMTP)
🔔 Event Bus   🟢 Active
🌐 Webhooks    🟢 3 configured
```

#### Recent Messages
| Time | Channel | Message | Status |
|------|---------|---------|--------|
| 10:42 | Telegram | Backup complete | ✅ Delivered |
| 09:15 | Email | Weekly report | ❌ Failed (no SMTP) |

#### Notification Rules
```
┌─────────────────────────────────────────┐
│ 🔔 Critical Issues                      │
│ When: PANOPTES finds critical issue     │
│ Channels: Telegram + Email              │
│ Priority: CRITICAL                      │
│ [Edit] [Disable] [Test]                 │
└─────────────────────────────────────────┘
```

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Send Test | Test all channels | Primary |
| Create Rule | New notification rule | Secondary |
| View Queue | Pending messages | Secondary |
| Retry Failed | Resend failures | Warning |

#### Chat Prompts
- "Send a test message to Telegram"
- "Why did the email fail to send?"
- "Set up alerts for backup failures"
- "Show me all notifications from today"
- "Notify me when health drops below 80%"

---

### ARGUS (Monitoring) - Port 8016

**Tagline:** "The Watchful Guardian"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **System Status** | Overall health | PRIMARY |
| CPU Usage | Gauge + trend | HIGH |
| Memory Usage | Gauge + trend | HIGH |
| Disk Usage | Gauge + trend | HIGH |
| Cost Today | $ amount | MEDIUM |

#### Agent Fleet Status
```
┌──────────┬────────┬──────┬─────────┐
│ Agent    │ Status │ Port │ Latency │
├──────────┼────────┼──────┼─────────┤
│ ATLAS    │ 🟢     │ 8007 │ 12ms    │
│ AEGIS    │ 🟢     │ 8012 │ 8ms     │
│ CHRONOS  │ 🟢     │ 8010 │ 15ms    │
│ PANOPTES │ 🟢     │ 8023 │ 22ms    │
│ ...      │        │      │         │
└──────────┴────────┴──────┴─────────┘
```

#### Cost Tracking
```
Today:     $1.42 ████░░░░░░ (14% of budget)
This Week: $8.50 ████████░░ (85% of budget)
This Month: $32.40

By Agent:
SCHOLAR    $12.50 ██████████
CHIRON     $8.20  ██████░░░░
ARIA       $6.40  █████░░░░░
```

#### Resource Graphs
- CPU over time (24h)
- Memory over time (24h)
- Network I/O
- Disk I/O

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Full Health Check | Test all agents | Primary |
| View Metrics | Grafana dashboard | Secondary |
| Cost Report | Export costs | Secondary |
| Set Alert | Custom threshold | Secondary |

#### Chat Prompts
- "What's the current system status?"
- "How much have I spent on API calls today?"
- "Which agent is using the most resources?"
- "Show me CPU usage over the last week"
- "Alert me if costs exceed $5/day"

---

### ALOY (Audit & Anomaly) - Port 8015

**Tagline:** "The Anomaly Hunter"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Anomalies Detected** | Count (24h) | PRIMARY |
| Audit Events | Count (24h) | MEDIUM |
| Compliance Score | Gauge | MEDIUM |
| Suspicious Activity | Alert count | CRITICAL if >0 |

#### Anomaly Feed
```
🔴 10:42 - Unusual API call pattern from SCHOLAR
   Expected: 10-20 calls/hour
   Actual: 150 calls in 5 minutes
   [Investigate] [Dismiss] [Block]

🟡 09:15 - Login from new location
   User: damon
   Location: Coffee Shop WiFi
   [Verify] [Block]
```

#### Audit Log
| Time | Agent | Action | User | Details |
|------|-------|--------|------|---------|
| 10:42 | AEGIS | credential.read | SCHOLAR | openai-key |
| 10:40 | HADES | rollback.create | system | aria-frontend |

#### Compliance Dashboard
- Access controls: ✅
- Credential rotation: ⚠️ 3 overdue
- Backup verification: ✅
- Security patches: ✅

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| View Logs | Full audit trail | Primary |
| Export Compliance | Generate report | Secondary |
| Investigate | Drill into anomaly | Secondary |
| Set Baseline | Update normal behavior | Secondary |

#### Chat Prompts
- "Show me unusual activity from today"
- "Who accessed credentials this week?"
- "Generate a compliance report"
- "What triggered the anomaly alert?"
- "Set up monitoring for failed logins"

---

### ATLAS (Orchestrator) - Port 8007

**Tagline:** "Bearer of the World"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Active Chains** | Count running | PRIMARY |
| Completed Today | Success count | HIGH |
| Failed Today | Error count | HIGH if >0 |
| Avg Execution Time | Duration | MEDIUM |
| Total Cost Today | $ amount | MEDIUM |

#### Active Executions
```
┌─────────────────────────────────────────┐
│ 🔄 research-and-plan (Running)         │
│ Started: 2 minutes ago                  │
│ Step: 2/3 (CHIRON planning)            │
│ Progress: ████████░░ 75%               │
│ [View Details] [Cancel]                 │
└─────────────────────────────────────────┘
```

#### Available Chains
| Chain | Description | Est. Cost | Est. Time |
|-------|-------------|-----------|-----------|
| research-and-plan | Research then plan | $0.25 | 3 min |
| validate-and-decide | Test assumption | $0.25 | 2.5 min |
| comprehensive-market-analysis | Full market research | $0.75 | 5 min |
| weekly-planning | Review and plan week | $0.40 | 3 min |
| fear-to-action | Overcome fear | $0.30 | 2 min |

#### Execution History
| Chain | Status | Duration | Cost | Started |
|-------|--------|----------|------|---------|
| research-and-plan | ✅ | 3m 42s | $0.28 | 10:00 |
| weekly-planning | ✅ | 2m 15s | $0.35 | 09:00 |
| validate-and-decide | ❌ | 1m 30s | $0.12 | 08:30 |

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Execute Chain | Run selected chain | Primary |
| View Running | Monitor active | Secondary |
| Cancel All | Stop everything | Danger |
| View Costs | Cost breakdown | Secondary |

#### Chat Prompts
- "Run research-and-plan for compliance automation"
- "What chains are currently running?"
- "Cancel the current research task"
- "Show me execution history from today"
- "How much did chains cost this week?"

---

## TIER 2: BUSINESS AGENTS

---

### SCHOLAR (Research) - Port 8018

**Tagline:** "Seeker of Truth"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Research Projects** | Active count | PRIMARY |
| Completed Today | Count | HIGH |
| Sources Analyzed | Count | MEDIUM |
| Cost This Week | $ amount | MEDIUM |

#### Recent Research
```
┌─────────────────────────────────────────┐
│ 📚 Compliance Automation Market (Done)  │
│ Completed: 2 hours ago                  │
│ Sources: 12    Confidence: HIGH         │
│ [View Report] [Export] [Continue]       │
└─────────────────────────────────────────┘
```

#### Research Types
| Type | Description | Cost Tier |
|------|-------------|-----------|
| Deep Research | Comprehensive multi-source | High |
| Competitors | Competitive analysis | High |
| Market Size | TAM/SAM/SOM | High |
| Pain Discovery | Customer pain points | High |
| Validate Assumption | Evidence-based testing | High |
| ICP | Ideal Customer Profile | Medium |
| Niche Analysis | Viability scoring | Medium |
| Lead Research | Company intelligence | Medium |

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| New Research | Start research | Primary |
| Continue Project | Resume existing | Secondary |
| Compare Niches | Side-by-side | Secondary |
| Export Reports | Download all | Secondary |

#### Chat Prompts
- "Research the compliance automation market"
- "Who are the top competitors for AI chatbots?"
- "What's the market size for legal tech?"
- "Validate that SMBs need automation help"
- "Create an ICP for compliance officers"
- "Research this company as a potential lead"

---

### CHIRON (Business Coach) - Port 8017

**Tagline:** "Wisdom of the Centaur"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Days to Launch** | Countdown | PRIMARY |
| Commitments Active | Count | HIGH |
| Weekly Wins | Count | MEDIUM |
| Current Focus | Text | HIGH |

#### Accountability Tracker
```
┌─────────────────────────────────────────┐
│ 📋 Current Commitments                  │
│                                         │
│ ☑️ Deploy ARIA V3 (Due: Today)          │
│ ☐ 10 outreach attempts (Due: Feb 28)   │
│ ☐ 3 discovery calls (Due: Feb 28)      │
│ ☐ First paying client (Due: March 1)   │
│                                         │
│ [Add Commitment] [Weekly Review]        │
└─────────────────────────────────────────┘
```

#### Frameworks Available
| Framework | Use Case |
|-----------|----------|
| Decision | Making hard choices |
| Fear | Overcoming avoidance |
| ADHD | Managing energy/focus |
| Pricing | Value-based pricing |
| Sales | Closing deals |
| MVP | Shipping fast |
| Launch | Go-to-market |

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Sprint Plan | Plan my week | Primary |
| Fear Check | Face my fears | Secondary |
| Weekly Review | Reflect on week | Secondary |
| Pricing Help | Calculate value | Secondary |
| Challenge | Test assumption | Secondary |
| Hype Me | Motivation boost | Fun |

#### Chat Prompts
- "Help me plan this week"
- "I'm afraid of reaching out to prospects"
- "How should I price this service?"
- "Break down this large task for me"
- "Give me a motivation boost"
- "Challenge my assumption that I need more features"

---

### VARYS (Mission Guardian) - Port 8020

**Tagline:** "The Spider"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Days to Launch** | Large countdown | PRIMARY |
| Mission Alignment | Score (0-100) | HIGH |
| Drift Flags | Alert count | HIGH if >0 |
| Today's Focus | From calendar | HIGH |

#### Mission Documents
- MISSION STATEMENT
- LAUNCH DATE (March 1, 2026)
- REVENUE GOAL ($30K MRR)
- BOUNDARIES (what NOT to do)
- PORTFOLIO TARGET

#### Drift Detection
```
🚨 DRIFT ALERT (Yesterday)
─────────────────────────────
Commit: "Add credential rotation UI"
Flag: New feature not in launch scope
Risk: Scope creep

Recommendation: Defer to post-launch
[Accept] [Dismiss] [Discuss]
```

#### Daily Brief
```
┌─────────────────────────────────────────┐
│ 📅 Sunday, January 18, 2026            │
│ 42 DAYS TO LAUNCH                       │
│                                         │
│ Today's Focus: Infrastructure cleanup   │
│                                         │
│ ✅ PANOPTES deployed                    │
│ ✅ ASCLEPIUS deployed                   │
│ ☐ ARIA frontend connection             │
│ ☐ Git commit everything                │
│                                         │
│ [Get Full Brief] [Edit Focus]          │
└─────────────────────────────────────────┘
```

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Daily Brief | Get today's brief | Primary |
| Weekly Review | Full week review | Secondary |
| Scan Drift | Check recent commits | Secondary |
| Validate Decision | Check alignment | Secondary |

#### Chat Prompts
- "What should I focus on today?"
- "How many days until launch?"
- "Check if this task aligns with launch goals"
- "Generate my daily accountability brief"
- "Scan for scope creep in recent work"

---

## TIER 3: CREATIVE AGENTS

---

### MUSE (Creative Director) - Port 8030

**Tagline:** "Conductor of Creativity"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Active Projects** | Count | PRIMARY |
| In Review | Count | HIGH |
| Completed This Week | Count | MEDIUM |

#### Project Board (Kanban)
```
Ideation → In Progress → Review → Complete

[New Video]   [Case Study]   [LinkedIn]   [Slides]
             [Proposal]                   [Report]
```

#### Project Types
| Type | Agents Involved |
|------|-----------------|
| Presentation | CALLIOPE → THALIA → CLIO |
| Video | CALLIOPE → ERATO → CLIO |
| Document | CALLIOPE → THALIA → CLIO |
| Social Post | CALLIOPE → ERATO |

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| New Project | Start creative project | Primary |
| View Pipeline | See all projects | Secondary |
| Storyboard | Plan video | Secondary |

#### Chat Prompts
- "Create a case study about my PANOPTES build"
- "Make a LinkedIn post about AI automation"
- "Design a presentation for a sales call"
- "Start a video about compliance automation"

---

### THALIA (Designer) - Port 8032

**Tagline:** "Artist of the Digital Realm"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Designs This Week** | Count | PRIMARY |
| Templates Available | Count | MEDIUM |
| Brand Profiles | Count | MEDIUM |

#### Design Types
- Presentations
- Charts & Graphs
- Thumbnails
- Landing Pages
- UI Components
- Wireframes
- Website Templates

#### Brand Profiles
```
┌─────────────────────────────────────────┐
│ 🎨 LeverEdge AI Brand                  │
│ Primary: #3B82F6                        │
│ Accent: #8B5CF6                         │
│ Font: Inter                             │
│ [Edit] [Use] [Export]                   │
└─────────────────────────────────────────┘
```

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Design Presentation | Create slides | Primary |
| Create Chart | Data visualization | Secondary |
| Landing Page | Generate page | Secondary |
| UI Component | Create component | Secondary |

#### Chat Prompts
- "Design a presentation for my sales pitch"
- "Create a chart showing market growth"
- "Make a thumbnail for my video"
- "Design a landing page for LeverEdge"

---

## TIER 4: PERSONAL AGENTS

---

### ARAGORN (Gym Coach) - Port 8110

**Tagline:** "Forge Your Strength"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Workouts This Week** | Count vs goal | PRIMARY |
| Current Streak | Days | HIGH |
| Last Workout | Timestamp | MEDIUM |
| Goals Progress | % complete | MEDIUM |

#### Workout Log
```
Today ────────────────────────
☐ Upper Body (Scheduled)

Yesterday ─────────────────────
✅ Lower Body - 45 min
   Squats: 3x12 @ 185lb
   Deadlift: 3x8 @ 225lb
   Leg Press: 3x15 @ 360lb
```

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Plan Workout | Create today's plan | Primary |
| Log Workout | Record completed | Secondary |
| View Progress | Charts over time | Secondary |
| Set Goals | Update fitness goals | Secondary |

#### Chat Prompts
- "Plan my workout for today"
- "Log my workout: squats 3x12, bench 3x10"
- "What should I focus on this week?"
- "Show my strength progress over 3 months"

---

### SAMWISE (Meal Planner) - Port 8102

**Tagline:** "Fuel for the Journey"

#### Dashboard
| Metric | Display | Priority |
|--------|---------|----------|
| **Today's Meals** | List | PRIMARY |
| Calories Today | vs target | HIGH |
| Meal Prep Status | Ready/Not | MEDIUM |
| Grocery List | Items count | MEDIUM |

#### Weekly Meal Plan
```
Monday    Tuesday   Wednesday
─────────────────────────────
B: Oats   B: Eggs   B: Smoothie
L: Salad  L: Soup   L: Wrap
D: Salmon D: Stir-fry D: Tacos
```

#### Actions Panel
| Action | Description | Button Style |
|--------|-------------|--------------|
| Plan Week | Generate meal plan | Primary |
| Generate List | Grocery list | Secondary |
| Log Meal | Record what you ate | Secondary |
| Suggest Recipe | Based on ingredients | Secondary |

#### Chat Prompts
- "Plan my meals for this week"
- "What should I eat for dinner tonight?"
- "Generate a grocery list"
- "I have chicken and rice, what can I make?"

---

## Navigation Structure

### ARIA Sidebar
```
─── PERSONAL ───
💬 Chat (Unified Thread)
⏰ Reminders
📅 Calendar
✅ Tasks
👥 Council
📚 Library

─── AGENTS ───
⚙️ Infrastructure
   ├── AEGIS (Credentials)
   ├── CHRONOS (Backups)
   ├── HADES (Rollback)
   ├── PANOPTES (Integrity)
   ├── ASCLEPIUS (Healing)
   ├── HERMES (Notifications)
   ├── ARGUS (Monitoring)
   ├── ALOY (Audit)
   └── ATLAS (Orchestration)

💼 Business
   ├── SCHOLAR (Research)
   ├── CHIRON (Coach)
   ├── VARYS (Mission)
   └── [More...]

🎨 Creative
   ├── MUSE (Director)
   ├── THALIA (Design)
   └── [More...]

🏃 Personal
   ├── ARAGORN (Fitness)
   ├── SAMWISE (Meals)
   └── [More...]

─── SYSTEM ───
⚙️ Settings
```

---

## Implementation Priority

### Phase 1 (This Week)
1. AEGIS - Credentials are critical
2. CHRONOS - Backups are essential
3. PANOPTES - Already built, add UI
4. ARGUS - Cost tracking needed

### Phase 2 (Next Week)
5. CHIRON - Daily use for planning
6. SCHOLAR - Research before outreach
7. ASCLEPIUS - Healing interface
8. VARYS - Accountability

### Phase 3 (Post-Launch)
- Creative agents
- Personal agents
- Remaining infrastructure

---

## Next Steps

1. Review this document with Damon
2. Prioritize which agent pages to build first
3. Create Bolt.new prompts for each page
4. Wire up API endpoints in frontend
5. Test each page with real agent connections

---

*This document should be updated as agents evolve and new features are added.*
