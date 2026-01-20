# GSD: Command Center - Master Dashboard

**Priority:** HIGH
**Estimated Time:** 8-10 hours
**Domain:** GAIA

---

## OVERVIEW

One dashboard to rule them all. See everything at a glance:
- System health
- Agent fleet status
- Project progress (MAGNUS)
- Portfolio value (VARYS)
- Financial status (LITTLEFINGER)
- Recent activity
- Alerts

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LEVEREDGE COMMAND CENTER                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Frontend (React)                                                    │   │
│  │  - Dashboard components                                              │   │
│  │  - Real-time updates (WebSocket)                                    │   │
│  │  - Mobile responsive                                                 │   │
│  │  - Domain-themed sections                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GAIA Aggregation Layer (Port 8000)                                 │   │
│  │  - /command-center/status                                           │   │
│  │  - /command-center/agents                                           │   │
│  │  - /command-center/metrics                                          │   │
│  │  - WebSocket /ws/command-center                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────┬──────────┬────┴────┬──────────┬──────────┐           │
│         ▼          ▼          ▼         ▼          ▼          ▼           │
│     PANOPTES   MAGNUS    VARYS   LITTLEFINGER  LCIS     All Agents       │
│     (health)   (projects) (intel)  (finance)   (lessons)  (status)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## DASHBOARD SECTIONS

### 1. Header Bar
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏔️ LEVEREDGE COMMAND CENTER                    [ARIA] 💬  [🔔 3]  [⚙️]  │
│                                                                             │
│  System Health: ████████░░ 85%    Agents: 38/40 ✅    Days to Launch: 41   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Quick Stats Row
```
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│  💰 Portfolio │  📈 MRR      │  📋 Tasks    │  🚨 Alerts   │  📊 Health   │
│  $58K-$117K  │  $0 → $30K   │  12 active   │  2 warnings  │  85%         │
│  28 wins     │  0% progress │  3 blocked   │  0 critical  │  ▲ +2%       │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

### 3. Agent Fleet Grid (by Domain)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT FLEET                                                    [View All]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🏰 THE_KEEP          │  👁️ SENTINELS        │  🏛️ CHANCERY              │
│  CHRONOS      ✅ 8010 │  PANOPTES    ✅ 8023 │  MAGNUS      ✅ 8019      │
│  HADES        ✅ 8008 │  ASCLEPIUS   ✅ 8024 │  VARYS       ✅ 8018      │
│  AEGIS        ✅ 8012 │  ARGUS       ✅ 8016 │  LITTLEFINGER ⏳ 8020     │
│  HERMES       ✅ 8014 │  ALOY        ✅ 8015 │  SCHOLAR     ✅ 8XXX      │
│  DAEDALUS     ⏳ 8026 │                      │  CHIRON      ✅ 8XXX      │
│                       │                      │                            │
│  🎭 ALCHEMY          │  ⚔️ ARIA_SANCTUM     │  🌍 GAIA                   │
│  MUSE         ✅ 8XXX │  ARIA        ✅ 8111 │  GAIA        ✅ 8000      │
│  QUILL        ✅ 8XXX │  CONVENER    ✅ 8025 │  ATLAS       ✅ n8n       │
│  STAGE        ✅ 8XXX │                      │  HEPHAESTUS  ✅ 8011      │
│  REEL         ✅ 8XXX │                      │                            │
│  CRITIC       ✅ 8XXX │                      │                            │
│                                                                             │
│  Legend: ✅ Healthy  ⚠️ Warning  ❌ Down  ⏳ Deploying                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Project Dashboard (MAGNUS)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PROJECTS                                              [MAGNUS] [View All]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LeverEdge Agency Launch                                    41 days left   │
│  ████████████████████░░░░░░░░░░ 65%                                        │
│                                                                             │
│  Tasks: 18 done │ 8 in progress │ 3 blocked │ 12 todo                      │
│  Blockers: 1 critical, 2 medium                                            │
│                                                                             │
│  Recent:                                                                    │
│  ✅ MAGNUS deployed and operational                         2 hours ago    │
│  ✅ LCIS migration complete                                 3 hours ago    │
│  🔄 Command Center build                                    in progress    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5. Intelligence Feed (VARYS)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INTELLIGENCE                                           [VARYS] [View All]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  💰 Portfolio: $58,500 - $117,000 across 28 wins                           │
│     This week: +$3,200 (2 new wins)                                        │
│                                                                             │
│  🎯 Opportunities: 0 active                                                │
│                                                                             │
│  📡 Recent Intel:                                                          │
│  • [market] AI automation demand up 40% in compliance sector               │
│  • [competitor] Agency X launched similar offering at $2K/mo               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6. Financial Overview (LITTLEFINGER)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FINANCES                                       [LITTLEFINGER] [View All]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MRR Progress                                                              │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ $0 / $30,000                              │
│                                                                             │
│  Monthly Expenses: $235                                                    │
│  • Claude Max: $200                                                        │
│  • Contabo VPS: $15                                                        │
│  • Bolt.new: $20                                                           │
│                                                                             │
│  Outstanding Invoices: $0                                                  │
│  Runway: ∞ (employed)                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7. Activity Feed
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ACTIVITY                                                        [View All] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  01:45  MAGNUS    Council integration complete                             │
│  01:35  MAGNUS    Deployed and operational                                 │
│  01:30  LCIS      187 lessons migrated, 8 rules active                    │
│  01:20  LCIS      LIBRARIAN and ORACLE deployed                           │
│  00:45  ARIA      V4 deployed to production                               │
│  00:30  CONVENER  Council UI standardization complete                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8. Alerts Panel
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ALERTS                                                    [2 Active] [✓]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ⚠️  DAEDALUS container not responding                      10 min ago     │
│      Action: Check container logs                          [Acknowledge]    │
│                                                                             │
│  ⚠️  3 tasks overdue in LeverEdge Launch                    1 hour ago     │
│      Action: Review with MAGNUS                            [Acknowledge]    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## GAIA AGGREGATION ENDPOINTS

Add to GAIA (port 8000):

```python
# ============ COMMAND CENTER ENDPOINTS ============

@app.get("/command-center/status")
async def command_center_status():
    """Aggregate status for Command Center"""
    
    # Parallel fetch from all sources
    async with httpx.AsyncClient(timeout=5.0) as client:
        results = await asyncio.gather(
            client.get("http://localhost:8023/health"),  # PANOPTES
            client.get("http://localhost:8019/status"),  # MAGNUS
            client.get("http://localhost:8018/portfolio/summary"),  # VARYS
            client.get("http://localhost:8020/status"),  # LITTLEFINGER
            client.get("http://localhost:8052/health"),  # LCIS ORACLE
            return_exceptions=True
        )
    
    # Process results
    panoptes = results[0].json() if not isinstance(results[0], Exception) else None
    magnus = results[1].json() if not isinstance(results[1], Exception) else None
    varys = results[2].json() if not isinstance(results[2], Exception) else None
    littlefinger = results[3].json() if not isinstance(results[3], Exception) else None
    lcis = results[4].json() if not isinstance(results[4], Exception) else None
    
    return {
        "timestamp": datetime.now().isoformat(),
        "days_to_launch": (date(2026, 3, 1) - date.today()).days,
        "system_health": panoptes,
        "projects": magnus,
        "portfolio": varys,
        "finances": littlefinger,
        "lcis": lcis,
        "agents": await get_agent_fleet_status()
    }

@app.get("/command-center/agents")
async def command_center_agents():
    """Get status of all agents"""
    return await get_agent_fleet_status()

async def get_agent_fleet_status():
    """Check health of all agents"""
    agents = {
        "THE_KEEP": [
            {"name": "CHRONOS", "port": 8010},
            {"name": "HADES", "port": 8008},
            {"name": "AEGIS", "port": 8012},
            {"name": "HERMES", "port": 8014},
            {"name": "DAEDALUS", "port": 8026},
        ],
        "SENTINELS": [
            {"name": "PANOPTES", "port": 8023},
            {"name": "ASCLEPIUS", "port": 8024},
            {"name": "ARGUS", "port": 8016},
            {"name": "ALOY", "port": 8015},
        ],
        "CHANCERY": [
            {"name": "MAGNUS", "port": 8019},
            {"name": "VARYS", "port": 8018},
            {"name": "LITTLEFINGER", "port": 8020},
            {"name": "SCHOLAR", "port": 8030},
            {"name": "CHIRON", "port": 8031},
        ],
        "ARIA_SANCTUM": [
            {"name": "ARIA", "port": 8111},
            {"name": "CONVENER", "port": 8025},
        ],
        "GAIA": [
            {"name": "GAIA", "port": 8000},
            {"name": "HEPHAESTUS", "port": 8011},
            {"name": "LCIS_LIBRARIAN", "port": 8050},
            {"name": "LCIS_ORACLE", "port": 8052},
        ],
    }
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        for domain, domain_agents in agents.items():
            for agent in domain_agents:
                try:
                    response = await client.get(f"http://localhost:{agent['port']}/health")
                    agent["status"] = "healthy" if response.status_code == 200 else "unhealthy"
                except:
                    agent["status"] = "down"
    
    return agents

@app.websocket("/ws/command-center")
async def command_center_websocket(websocket: WebSocket):
    """Real-time updates for Command Center"""
    await websocket.accept()
    
    try:
        while True:
            # Send status update every 30 seconds
            status = await command_center_status()
            await websocket.send_json(status)
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
```

---

## FRONTEND (React)

### Tech Stack
- React 18
- Tailwind CSS
- Recharts (charts)
- Lucide React (icons)
- WebSocket for real-time

### Component Structure
```
src/
├── components/
│   ├── Header.jsx
│   ├── QuickStats.jsx
│   ├── AgentFleet.jsx
│   ├── ProjectDashboard.jsx
│   ├── IntelligenceFeed.jsx
│   ├── FinancialOverview.jsx
│   ├── ActivityFeed.jsx
│   └── AlertsPanel.jsx
├── hooks/
│   ├── useCommandCenter.js
│   └── useWebSocket.js
├── App.jsx
└── index.jsx
```

### Main App Component
```jsx
import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import QuickStats from './components/QuickStats';
import AgentFleet from './components/AgentFleet';
import ProjectDashboard from './components/ProjectDashboard';
import IntelligenceFeed from './components/IntelligenceFeed';
import FinancialOverview from './components/FinancialOverview';
import ActivityFeed from './components/ActivityFeed';
import AlertsPanel from './components/AlertsPanel';
import useCommandCenter from './hooks/useCommandCenter';

export default function CommandCenter() {
  const { data, loading, error } = useCommandCenter();
  
  if (loading) return <LoadingScreen />;
  if (error) return <ErrorScreen error={error} />;
  
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header data={data} />
      
      <main className="container mx-auto p-4 space-y-4">
        <QuickStats data={data} />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AgentFleet agents={data.agents} />
          <ProjectDashboard projects={data.projects} />
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <IntelligenceFeed intel={data.portfolio} />
          <FinancialOverview finances={data.finances} />
          <AlertsPanel alerts={data.alerts} />
        </div>
        
        <ActivityFeed activities={data.activities} />
      </main>
    </div>
  );
}
```

### useCommandCenter Hook
```jsx
import { useState, useEffect, useCallback } from 'react';

const API_BASE = 'https://gaia.leveredgeai.com';
const WS_URL = 'wss://gaia.leveredgeai.com/ws/command-center';

export default function useCommandCenter() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Initial fetch
  useEffect(() => {
    fetch(`${API_BASE}/command-center/status`)
      .then(res => res.json())
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, []);
  
  // WebSocket for real-time updates
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    
    ws.onmessage = (event) => {
      const newData = JSON.parse(event.data);
      setData(newData);
    };
    
    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
    
    return () => ws.close();
  }, []);
  
  const refresh = useCallback(() => {
    fetch(`${API_BASE}/command-center/status`)
      .then(res => res.json())
      .then(setData);
  }, []);
  
  return { data, loading, error, refresh };
}
```

---

## DEPLOYMENT

### Option 1: Bolt.new
Build in Bolt.new, export, deploy to Cloudflare Pages.

### Option 2: Build locally
```bash
# Create React app
cd /opt/leveredge/frontends
npx create-react-app command-center
cd command-center

# Install deps
npm install recharts lucide-react

# Build
npm run build

# Deploy to static hosting
```

### Caddy Route
```
command.leveredgeai.com {
    root * /opt/leveredge/frontends/command-center/build
    file_server
    try_files {path} /index.html
}
```

---

## BUILD PHASES

| Phase | Task | Time |
|-------|------|------|
| 1 | GAIA aggregation endpoints | 2 hrs |
| 2 | React app scaffold | 1 hr |
| 3 | Header + QuickStats | 1 hr |
| 4 | AgentFleet component | 1.5 hrs |
| 5 | ProjectDashboard (MAGNUS) | 1.5 hrs |
| 6 | IntelligenceFeed (VARYS) | 1 hr |
| 7 | FinancialOverview (LITTLEFINGER) | 1 hr |
| 8 | ActivityFeed + Alerts | 1 hr |
| 9 | WebSocket integration | 1 hr |
| 10 | Deploy + DNS | 1 hr |
| **Total** | | **12 hrs** |

---

## GIT COMMIT

```bash
git add .
git commit -m "Command Center: Master Dashboard

- GAIA aggregation endpoints
- React frontend with Tailwind
- Real-time WebSocket updates
- Agent fleet status grid
- MAGNUS project dashboard
- VARYS intelligence feed
- LITTLEFINGER financial overview
- Activity feed and alerts

One dashboard to rule them all."
```

---

*"All roads lead to the Command Center."*
