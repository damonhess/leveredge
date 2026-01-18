# MEGA GSD: FULL DASHBOARD BUILD + CONCLAVE V2

*Prepared: January 17, 2026*
*Purpose: Build ALL dashboards, deploy CONCLAVE V2, get everything functional*
*Approach: Function first, visual upgrades later*

---

## OVERVIEW

Build the complete LeverEdge command center with:
- Master hub dashboard
- All 8 domain dashboards
- All 40+ agent pages
- CONCLAVE V2 council meeting system
- Real metrics integration
- Ready to publish

**Tech Stack:**
- Next.js 14 (App Router)
- Tailwind CSS (functional styling, not fancy)
- React Query for data fetching
- Deployed via Caddy at command.leveredgeai.com

**CRITICAL:**
- You have n8n-control MCP for control plane
- You have n8n-troubleshooter MCP for data plane
- DEV FIRST always
- Commit after each major component

---

## PART 1: PROJECT SETUP

### 1.1 Initialize Next.js Project
```bash
cd /opt/leveredge/ui
npx create-next-app@latest command-center --typescript --tailwind --app --src-dir
cd command-center
```

### 1.2 Install Dependencies
```bash
npm install @tanstack/react-query axios lucide-react date-fns
npm install -D @types/node
```

### 1.3 Create Base Structure
```
/opt/leveredge/ui/command-center/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout
│   │   ├── page.tsx                # Hub dashboard
│   │   ├── domains/
│   │   │   ├── gaia/page.tsx
│   │   │   ├── pantheon/page.tsx
│   │   │   ├── sentinels/page.tsx
│   │   │   ├── shire/page.tsx
│   │   │   ├── keep/page.tsx
│   │   │   ├── chancery/page.tsx
│   │   │   ├── alchemy/page.tsx
│   │   │   └── aria-sanctum/page.tsx
│   │   ├── agents/
│   │   │   └── [agent]/page.tsx    # Dynamic agent pages
│   │   ├── council/
│   │   │   ├── page.tsx            # Council hub
│   │   │   ├── new/page.tsx        # Create meeting
│   │   │   └── [id]/page.tsx       # Active meeting
│   │   └── api/
│   │       └── [...proxy]/route.ts # Proxy to agents
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── DomainNav.tsx
│   │   ├── dashboard/
│   │   │   ├── MetricCard.tsx
│   │   │   ├── AgentStatus.tsx
│   │   │   ├── DomainCard.tsx
│   │   │   └── SystemHealth.tsx
│   │   ├── council/
│   │   │   ├── MeetingRoom.tsx
│   │   │   ├── Transcript.tsx
│   │   │   ├── VotePanel.tsx
│   │   │   └── ParticipantList.tsx
│   │   └── agents/
│   │       ├── AgentCard.tsx
│   │       └── AgentActions.tsx
│   ├── lib/
│   │   ├── api.ts                  # API client
│   │   ├── agents.ts               # Agent registry
│   │   └── types.ts                # TypeScript types
│   └── hooks/
│       ├── useAgentHealth.ts
│       ├── useMetrics.ts
│       └── useCouncil.ts
├── public/
└── next.config.js
```

### 1.4 Environment Config
```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8007
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=your-anon-key
```

---

## PART 2: AGENT REGISTRY

### 2.1 Create Agent Registry
```typescript
// src/lib/agents.ts

export interface Agent {
  id: string;
  name: string;
  port: number;
  domain: string;
  function: string;
  supervisor?: boolean;
  councilMember?: boolean;
  status?: 'online' | 'offline' | 'degraded';
}

export interface Domain {
  id: string;
  name: string;
  theme: string;
  color: string;
  supervisor: string;
  agents: string[];
}

export const DOMAINS: Record<string, Domain> = {
  gaia: {
    id: 'gaia',
    name: 'GAIA',
    theme: 'Primordial Creation',
    color: '#8B4513',
    supervisor: 'GAIA',
    agents: ['GAIA']
  },
  pantheon: {
    id: 'pantheon',
    name: 'PANTHEON',
    theme: 'Mount Olympus',
    color: '#FFD700',
    supervisor: 'ATLAS',
    agents: ['ATLAS', 'HEPHAESTUS', 'CHRONOS', 'HADES', 'AEGIS', 'ATHENA', 'HERMES', 'ARGUS', 'CHIRON', 'SCHOLAR']
  },
  sentinels: {
    id: 'sentinels',
    name: 'SENTINELS',
    theme: 'Mythic Guardians',
    color: '#8B0000',
    supervisor: 'GRIFFIN',
    agents: ['GRIFFIN', 'CERBERUS', 'SPHINX']
  },
  shire: {
    id: 'shire',
    name: 'THE SHIRE',
    theme: 'LOTR Hobbit Comfort',
    color: '#228B22',
    supervisor: 'GANDALF',
    agents: ['GANDALF', 'ARAGORN', 'BOMBADIL', 'SAMWISE', 'ARWEN']
  },
  keep: {
    id: 'keep',
    name: 'THE KEEP',
    theme: 'Game of Thrones',
    color: '#2F4F4F',
    supervisor: 'TYRION',
    agents: ['TYRION', 'SAMWELL-TARLY', 'GENDRY', 'STANNIS', 'DAVOS', 'LITTLEFINGER', 'BRONN', 'RAVEN']
  },
  chancery: {
    id: 'chancery',
    name: 'CHANCERY',
    theme: 'Royal Court',
    color: '#800020',
    supervisor: 'MAGISTRATE',
    agents: ['MAGISTRATE', 'EXCHEQUER']
  },
  alchemy: {
    id: 'alchemy',
    name: 'ALCHEMY',
    theme: 'Mystic Workshop',
    color: '#9B59B6',
    supervisor: 'CATALYST',
    agents: ['CATALYST', 'SAGA', 'PRISM', 'ELIXIR', 'RELIC']
  },
  'aria-sanctum': {
    id: 'aria-sanctum',
    name: 'ARIA SANCTUM',
    theme: 'Ethereal Intelligence',
    color: '#E8D5E8',
    supervisor: 'ARIA',
    agents: ['ARIA', 'ARIA-OMNISCIENCE', 'ARIA-REMINDERS', 'VARYS']
  }
};

export const AGENTS: Record<string, Agent> = {
  // GAIA
  'GAIA': { id: 'gaia', name: 'GAIA', port: 8000, domain: 'gaia', function: 'Emergency bootstrap', supervisor: true },
  
  // PANTHEON
  'ATLAS': { id: 'atlas', name: 'ATLAS', port: 8007, domain: 'pantheon', function: 'Master Orchestrator', supervisor: true, councilMember: true },
  'HEPHAESTUS': { id: 'hephaestus', name: 'HEPHAESTUS', port: 8011, domain: 'pantheon', function: 'Builder/Deployer', councilMember: true },
  'CHRONOS': { id: 'chronos', name: 'CHRONOS', port: 8010, domain: 'pantheon', function: 'Backup Manager' },
  'HADES': { id: 'hades', name: 'HADES', port: 8008, domain: 'pantheon', function: 'Rollback/Recovery' },
  'AEGIS': { id: 'aegis', name: 'AEGIS', port: 8012, domain: 'pantheon', function: 'Credential Vault' },
  'ATHENA': { id: 'athena', name: 'ATHENA', port: 8013, domain: 'pantheon', function: 'Planner/Documenter', councilMember: true },
  'HERMES': { id: 'hermes', name: 'HERMES', port: 8014, domain: 'pantheon', function: 'Messenger/Notifications' },
  'ARGUS': { id: 'argus', name: 'ARGUS', port: 8016, domain: 'pantheon', function: 'Monitor' },
  'CHIRON': { id: 'chiron', name: 'CHIRON', port: 8017, domain: 'pantheon', function: 'Elite Business Mentor', councilMember: true },
  'SCHOLAR': { id: 'scholar', name: 'SCHOLAR', port: 8018, domain: 'pantheon', function: 'Market Research', councilMember: true },
  
  // SENTINELS
  'GRIFFIN': { id: 'griffin', name: 'GRIFFIN', port: 8019, domain: 'sentinels', function: 'Perimeter Watch', supervisor: true },
  'CERBERUS': { id: 'cerberus', name: 'CERBERUS', port: 8020, domain: 'sentinels', function: 'Defense/Auth' },
  'SPHINX': { id: 'sphinx', name: 'SPHINX', port: 8021, domain: 'sentinels', function: 'Access Control' },
  
  // THE SHIRE
  'GANDALF': { id: 'gandalf', name: 'GANDALF', port: 8103, domain: 'shire', function: 'Learning/Wisdom', supervisor: true, councilMember: true },
  'ARAGORN': { id: 'aragorn', name: 'ARAGORN', port: 8110, domain: 'shire', function: 'Fitness' },
  'BOMBADIL': { id: 'bombadil', name: 'BOMBADIL', port: 8101, domain: 'shire', function: 'Nutrition' },
  'SAMWISE': { id: 'samwise', name: 'SAMWISE', port: 8102, domain: 'shire', function: 'Meal Planning' },
  'ARWEN': { id: 'arwen', name: 'ARWEN', port: 8104, domain: 'shire', function: 'Relationships' },
  
  // THE KEEP
  'TYRION': { id: 'tyrion', name: 'TYRION', port: 8200, domain: 'keep', function: 'Project Leadership', supervisor: true, councilMember: true },
  'SAMWELL-TARLY': { id: 'samwell-tarly', name: 'SAMWELL-TARLY', port: 8201, domain: 'keep', function: 'Knowledge Keeper' },
  'GENDRY': { id: 'gendry', name: 'GENDRY', port: 8202, domain: 'keep', function: 'Workflow Builder', councilMember: true },
  'STANNIS': { id: 'stannis', name: 'STANNIS', port: 8203, domain: 'keep', function: 'QA/Compliance' },
  'DAVOS': { id: 'davos', name: 'DAVOS', port: 8204, domain: 'keep', function: 'Business Advisor', councilMember: true },
  'LITTLEFINGER': { id: 'littlefinger', name: 'LITTLEFINGER', port: 8205, domain: 'keep', function: 'Finance', councilMember: true },
  'BRONN': { id: 'bronn', name: 'BRONN', port: 8206, domain: 'keep', function: 'Procurement' },
  'RAVEN': { id: 'raven', name: 'RAVEN', port: 8209, domain: 'keep', function: 'News/Intel' },
  
  // CHANCERY
  'MAGISTRATE': { id: 'magistrate', name: 'MAGISTRATE', port: 8210, domain: 'chancery', function: 'Legal Counsel', supervisor: true, councilMember: true },
  'EXCHEQUER': { id: 'exchequer', name: 'EXCHEQUER', port: 8211, domain: 'chancery', function: 'Tax & Wealth' },
  
  // ALCHEMY
  'CATALYST': { id: 'catalyst', name: 'CATALYST', port: 8030, domain: 'alchemy', function: 'Creative Director', supervisor: true, councilMember: true },
  'SAGA': { id: 'saga', name: 'SAGA', port: 8031, domain: 'alchemy', function: 'Writer', councilMember: true },
  'PRISM': { id: 'prism', name: 'PRISM', port: 8032, domain: 'alchemy', function: 'Visual Designer', councilMember: true },
  'ELIXIR': { id: 'elixir', name: 'ELIXIR', port: 8033, domain: 'alchemy', function: 'Media Producer', councilMember: true },
  'RELIC': { id: 'relic', name: 'RELIC', port: 8034, domain: 'alchemy', function: 'Reviewer' },
  
  // ARIA SANCTUM
  'ARIA': { id: 'aria', name: 'ARIA', port: 0, domain: 'aria-sanctum', function: 'Personal AI', supervisor: true },
  'ARIA-OMNISCIENCE': { id: 'aria-omniscience', name: 'ARIA-OMNISCIENCE', port: 8112, domain: 'aria-sanctum', function: 'System Awareness' },
  'ARIA-REMINDERS': { id: 'aria-reminders', name: 'ARIA-REMINDERS', port: 8111, domain: 'aria-sanctum', function: 'Proactive Notifications' },
  'VARYS': { id: 'varys', name: 'VARYS', port: 8113, domain: 'aria-sanctum', function: 'Intelligence/Portfolio', councilMember: true },
  
  // CONCLAVE
  'CONVENER': { id: 'convener', name: 'CONVENER', port: 8300, domain: 'conclave', function: 'Council Facilitator' },
  'SCRIBE': { id: 'scribe', name: 'SCRIBE', port: 8301, domain: 'conclave', function: 'Council Secretary' }
};

export const COUNCIL_MEMBERS = Object.values(AGENTS).filter(a => a.councilMember);
export const SUPERVISORS = Object.values(AGENTS).filter(a => a.supervisor);
```

---

## PART 3: CORE COMPONENTS

### 3.1 Root Layout
```typescript
// src/app/layout.tsx
import './globals.css';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { QueryProvider } from '@/components/providers/QueryProvider';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-900 text-white">
        <QueryProvider>
          <div className="flex h-screen">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
              <Header />
              <main className="flex-1 overflow-auto p-6">
                {children}
              </main>
            </div>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
```

### 3.2 Sidebar Component
```typescript
// src/components/layout/Sidebar.tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { DOMAINS } from '@/lib/agents';
import { 
  Home, Users, Shield, Leaf, Sword, Scale, 
  Sparkles, Star, MessageSquare, Settings 
} from 'lucide-react';

const domainIcons: Record<string, any> = {
  gaia: Sparkles,
  pantheon: Star,
  sentinels: Shield,
  shire: Leaf,
  keep: Sword,
  chancery: Scale,
  alchemy: Sparkles,
  'aria-sanctum': Star,
};

export function Sidebar() {
  const pathname = usePathname();
  
  return (
    <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-xl font-bold">LeverEdge</h1>
        <p className="text-xs text-slate-400">Command Center</p>
      </div>
      
      <nav className="flex-1 p-4 space-y-2">
        <Link 
          href="/"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
            pathname === '/' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
          }`}
        >
          <Home size={18} />
          <span>Hub</span>
        </Link>
        
        <div className="pt-4 pb-2 px-3 text-xs text-slate-500 uppercase tracking-wider">
          Domains
        </div>
        
        {Object.values(DOMAINS).map(domain => {
          const Icon = domainIcons[domain.id] || Star;
          const isActive = pathname.startsWith(`/domains/${domain.id}`);
          
          return (
            <Link
              key={domain.id}
              href={`/domains/${domain.id}`}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
                isActive ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              <Icon size={18} style={{ color: domain.color }} />
              <span>{domain.name}</span>
            </Link>
          );
        })}
        
        <div className="pt-4 pb-2 px-3 text-xs text-slate-500 uppercase tracking-wider">
          Council
        </div>
        
        <Link
          href="/council"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
            pathname.startsWith('/council') ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
          }`}
        >
          <MessageSquare size={18} />
          <span>The Conclave</span>
        </Link>
      </nav>
      
      <div className="p-4 border-t border-slate-700">
        <Link
          href="/settings"
          className="flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white rounded-lg transition hover:bg-slate-700/50"
        >
          <Settings size={18} />
          <span>Settings</span>
        </Link>
      </div>
    </aside>
  );
}
```

### 3.3 Header Component
```typescript
// src/components/layout/Header.tsx
'use client';
import { useMetrics } from '@/hooks/useMetrics';
import { Clock, DollarSign, Calendar, Activity } from 'lucide-react';

export function Header() {
  const { data: metrics } = useMetrics();
  
  const daysToLaunch = Math.ceil(
    (new Date('2026-03-01').getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );
  
  return (
    <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-6">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-sm">
          <Calendar size={16} className="text-amber-400" />
          <span className="text-slate-400">Launch in</span>
          <span className="font-bold text-amber-400">{daysToLaunch} days</span>
        </div>
        
        <div className="flex items-center gap-2 text-sm">
          <DollarSign size={16} className="text-green-400" />
          <span className="text-slate-400">Portfolio</span>
          <span className="font-bold text-green-400">$58K - $117K</span>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <Activity size={16} className="text-cyan-400" />
          <span className="text-slate-400">Agents</span>
          <span className="font-bold text-cyan-400">{metrics?.agentsOnline || 0}/40</span>
        </div>
        
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Clock size={16} />
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </header>
  );
}
```

### 3.4 Metric Card Component
```typescript
// src/components/dashboard/MetricCard.tsx
interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export function MetricCard({ title, value, subtitle, icon, color = '#60A5FA' }: MetricCardProps) {
  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <p className="text-2xl font-bold mt-1" style={{ color }}>{value}</p>
          {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
        </div>
        <div className="p-2 rounded-lg bg-slate-700/50" style={{ color }}>
          {icon}
        </div>
      </div>
    </div>
  );
}
```

### 3.5 Agent Status Component
```typescript
// src/components/dashboard/AgentStatus.tsx
import { Agent } from '@/lib/agents';
import { Circle } from 'lucide-react';

interface AgentStatusProps {
  agent: Agent;
  onClick?: () => void;
}

export function AgentStatus({ agent, onClick }: AgentStatusProps) {
  const statusColors = {
    online: 'text-green-400',
    offline: 'text-red-400',
    degraded: 'text-amber-400'
  };
  
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition w-full text-left"
    >
      <Circle 
        size={8} 
        className={`fill-current ${statusColors[agent.status || 'offline']}`} 
      />
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{agent.name}</p>
        <p className="text-xs text-slate-400 truncate">{agent.function}</p>
      </div>
      <span className="text-xs text-slate-500">:{agent.port}</span>
    </button>
  );
}
```

---

## PART 4: HUB DASHBOARD

### 4.1 Main Hub Page
```typescript
// src/app/page.tsx
'use client';
import { DOMAINS, AGENTS, COUNCIL_MEMBERS } from '@/lib/agents';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { DomainCard } from '@/components/dashboard/DomainCard';
import { useAgentHealth } from '@/hooks/useAgentHealth';
import { 
  Users, Activity, DollarSign, Calendar, 
  MessageSquare, Zap, Server, Shield 
} from 'lucide-react';
import Link from 'next/link';

export default function HubPage() {
  const { data: health } = useAgentHealth();
  
  const daysToLaunch = Math.ceil(
    (new Date('2026-03-01').getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Command Center</h1>
        <p className="text-slate-400">LeverEdge AI Operations Hub</p>
      </div>
      
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Days to Launch"
          value={daysToLaunch}
          subtitle="March 1, 2026"
          icon={<Calendar size={20} />}
          color="#FBBF24"
        />
        <MetricCard
          title="Portfolio Value"
          value="$58K-$117K"
          subtitle="28 wins"
          icon={<DollarSign size={20} />}
          color="#34D399"
        />
        <MetricCard
          title="Agents Online"
          value={`${health?.online || 0}/${Object.keys(AGENTS).length}`}
          subtitle="Across 8 domains"
          icon={<Users size={20} />}
          color="#60A5FA"
        />
        <MetricCard
          title="Council Members"
          value={COUNCIL_MEMBERS.length}
          subtitle="Available for meetings"
          icon={<MessageSquare size={20} />}
          color="#A78BFA"
        />
      </div>
      
      {/* Quick Actions */}
      <div className="flex gap-4">
        <Link
          href="/council/new"
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
        >
          <MessageSquare size={18} />
          <span>New Council Meeting</span>
        </Link>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
          <Zap size={18} />
          <span>Quick Command</span>
        </button>
      </div>
      
      {/* Domains Grid */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Domains</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.values(DOMAINS).map(domain => (
            <DomainCard key={domain.id} domain={domain} />
          ))}
        </div>
      </div>
      
      {/* System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Server size={18} />
            System Health
          </h3>
          <div className="space-y-2">
            <HealthRow label="Database" status="healthy" />
            <HealthRow label="Event Bus" status="healthy" />
            <HealthRow label="n8n Control" status="healthy" />
            <HealthRow label="n8n Prod" status="healthy" />
            <HealthRow label="Backups" status="healthy" />
          </div>
        </div>
        
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Activity size={18} />
            Recent Activity
          </h3>
          <div className="space-y-2 text-sm">
            <ActivityRow 
              time="2m ago" 
              event="CHIRON completed sprint plan" 
            />
            <ActivityRow 
              time="15m ago" 
              event="CHRONOS backup successful" 
            />
            <ActivityRow 
              time="1h ago" 
              event="SCHOLAR research completed" 
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function HealthRow({ label, status }: { label: string; status: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-700 last:border-0">
      <span className="text-slate-400">{label}</span>
      <span className={`text-sm ${status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
        {status}
      </span>
    </div>
  );
}

function ActivityRow({ time, event }: { time: string; event: string }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-700 last:border-0">
      <span className="text-xs text-slate-500 w-16">{time}</span>
      <span className="text-slate-300">{event}</span>
    </div>
  );
}
```

### 4.2 Domain Card Component
```typescript
// src/components/dashboard/DomainCard.tsx
import Link from 'next/link';
import { Domain, AGENTS } from '@/lib/agents';
import { ChevronRight } from 'lucide-react';

interface DomainCardProps {
  domain: Domain;
}

export function DomainCard({ domain }: DomainCardProps) {
  const agentCount = domain.agents.length;
  const onlineCount = domain.agents.filter(
    name => AGENTS[name]?.status === 'online'
  ).length;
  
  return (
    <Link
      href={`/domains/${domain.id}`}
      className="block bg-slate-800 rounded-xl p-4 border border-slate-700 hover:border-slate-600 transition group"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold" style={{ color: domain.color }}>
            {domain.name}
          </h3>
          <p className="text-sm text-slate-400 mt-1">{domain.theme}</p>
        </div>
        <ChevronRight 
          size={20} 
          className="text-slate-600 group-hover:text-slate-400 transition" 
        />
      </div>
      
      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-slate-400">
          {agentCount} agents
        </span>
        <span className="text-slate-500">
          Supervisor: {domain.supervisor}
        </span>
      </div>
      
      <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className="h-full rounded-full transition-all"
          style={{ 
            width: `${(onlineCount / agentCount) * 100}%`,
            backgroundColor: domain.color 
          }}
        />
      </div>
    </Link>
  );
}
```

---

## PART 5: DOMAIN PAGES

### 5.1 Domain Page Template
```typescript
// src/app/domains/[domain]/page.tsx
'use client';
import { useParams } from 'next/navigation';
import { DOMAINS, AGENTS } from '@/lib/agents';
import { AgentStatus } from '@/components/dashboard/AgentStatus';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { useAgentHealth } from '@/hooks/useAgentHealth';
import { Users, Activity, Zap, Crown } from 'lucide-react';
import Link from 'next/link';

export default function DomainPage() {
  const params = useParams();
  const domainId = params.domain as string;
  const domain = DOMAINS[domainId];
  
  if (!domain) {
    return <div>Domain not found</div>;
  }
  
  const agents = domain.agents.map(name => AGENTS[name]).filter(Boolean);
  const supervisor = agents.find(a => a.supervisor);
  const councilMembers = agents.filter(a => a.councilMember);
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: domain.color }}>
            {domain.name}
          </h1>
          <p className="text-slate-400">{domain.theme}</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full border border-slate-700">
          <Crown size={14} style={{ color: domain.color }} />
          <span className="text-sm">Supervisor: {domain.supervisor}</span>
        </div>
      </div>
      
      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="Total Agents"
          value={agents.length}
          icon={<Users size={20} />}
          color={domain.color}
        />
        <MetricCard
          title="Council Members"
          value={councilMembers.length}
          subtitle="Can join meetings"
          icon={<Activity size={20} />}
          color={domain.color}
        />
        <MetricCard
          title="Status"
          value="Operational"
          icon={<Zap size={20} />}
          color="#34D399"
        />
      </div>
      
      {/* Agents List */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4">Agents</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {agents.map(agent => (
            <Link key={agent.id} href={`/agents/${agent.id}`}>
              <AgentStatus agent={agent} />
            </Link>
          ))}
        </div>
      </div>
      
      {/* Domain Actions */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-2">
          <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm">
            Health Check All
          </button>
          <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm">
            View Logs
          </button>
          <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm">
            Restart Domain
          </button>
          {councilMembers.length > 0 && (
            <Link
              href={`/council/new?participants=${councilMembers.map(a => a.name).join(',')}`}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition text-sm"
            >
              Council with {domain.name}
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## PART 6: AGENT PAGES

### 6.1 Individual Agent Page
```typescript
// src/app/agents/[agent]/page.tsx
'use client';
import { useParams } from 'next/navigation';
import { AGENTS, DOMAINS } from '@/lib/agents';
import { useAgentHealth } from '@/hooks/useAgentHealth';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { 
  Activity, Clock, Server, Terminal, 
  MessageSquare, RefreshCw, Power 
} from 'lucide-react';
import Link from 'next/link';

export default function AgentPage() {
  const params = useParams();
  const agentId = params.agent as string;
  const agent = Object.values(AGENTS).find(a => a.id === agentId);
  
  if (!agent) {
    return <div>Agent not found</div>;
  }
  
  const domain = DOMAINS[agent.domain];
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{agent.name}</h1>
            <span className={`px-2 py-1 rounded text-xs ${
              agent.status === 'online' 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {agent.status || 'unknown'}
            </span>
          </div>
          <p className="text-slate-400 mt-1">{agent.function}</p>
          <Link 
            href={`/domains/${agent.domain}`}
            className="text-sm mt-2 inline-block"
            style={{ color: domain?.color }}
          >
            {domain?.name} Domain
          </Link>
        </div>
        
        <div className="flex gap-2">
          {agent.councilMember && (
            <span className="px-3 py-1 bg-indigo-500/20 text-indigo-400 rounded-full text-sm">
              Council Member
            </span>
          )}
          {agent.supervisor && (
            <span className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded-full text-sm">
              Supervisor
            </span>
          )}
        </div>
      </div>
      
      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Port"
          value={agent.port || 'N/A'}
          icon={<Server size={20} />}
        />
        <MetricCard
          title="Uptime"
          value="99.9%"
          subtitle="Last 30 days"
          icon={<Clock size={20} />}
          color="#34D399"
        />
        <MetricCard
          title="Requests Today"
          value="142"
          icon={<Activity size={20} />}
          color="#60A5FA"
        />
        <MetricCard
          title="Avg Response"
          value="245ms"
          icon={<Activity size={20} />}
          color="#A78BFA"
        />
      </div>
      
      {/* Actions */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4">Actions</h2>
        <div className="flex flex-wrap gap-2">
          <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm">
            <Terminal size={16} />
            View Logs
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm">
            <RefreshCw size={16} />
            Restart
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm">
            <Activity size={16} />
            Health Check
          </button>
          {agent.councilMember && (
            <Link
              href={`/council/new?participants=${agent.name}`}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition text-sm"
            >
              <MessageSquare size={16} />
              Start Council With
            </Link>
          )}
        </div>
      </div>
      
      {/* Endpoints */}
      {agent.port > 0 && (
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h2 className="font-semibold mb-4">API Endpoints</h2>
          <div className="space-y-2 font-mono text-sm">
            <EndpointRow method="GET" path={`http://localhost:${agent.port}/health`} />
            <EndpointRow method="GET" path={`http://localhost:${agent.port}/`} />
            <EndpointRow method="POST" path={`http://localhost:${agent.port}/...`} />
          </div>
        </div>
      )}
      
      {/* Recent Activity */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4">Recent Activity</h2>
        <div className="space-y-2 text-sm">
          <ActivityRow time="2m ago" event="Health check passed" />
          <ActivityRow time="15m ago" event="Processed request from ATLAS" />
          <ActivityRow time="1h ago" event="Configuration reloaded" />
        </div>
      </div>
    </div>
  );
}

function EndpointRow({ method, path }: { method: string; path: string }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-slate-700 last:border-0">
      <span className={`px-2 py-0.5 rounded text-xs ${
        method === 'GET' ? 'bg-green-500/20 text-green-400' :
        method === 'POST' ? 'bg-blue-500/20 text-blue-400' :
        'bg-slate-500/20 text-slate-400'
      }`}>
        {method}
      </span>
      <code className="text-slate-400">{path}</code>
    </div>
  );
}

function ActivityRow({ time, event }: { time: string; event: string }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-700 last:border-0">
      <span className="text-xs text-slate-500 w-16">{time}</span>
      <span className="text-slate-300">{event}</span>
    </div>
  );
}
```

---

## PART 7: CONCLAVE V2 - COUNCIL SYSTEM

### 7.1 Build CONVENER Agent
Reference: `/opt/leveredge/specs/conclave-v2-smart-councils.md`

Build the full CONVENER FastAPI app with:
- Smart facilitation (LLM-powered)
- Mid-meeting summoning
- Consultation support
- Advisory votes
- Natural meeting flow

### 7.2 Build SCRIBE Agent
Build the SCRIBE FastAPI app with:
- Transcript recording
- Summary generation
- Action item extraction
- ATHENA integration

### 7.3 Council Hub Page
```typescript
// src/app/council/page.tsx
'use client';
import { useQuery } from '@tanstack/react-query';
import { COUNCIL_MEMBERS } from '@/lib/agents';
import { api } from '@/lib/api';
import { MessageSquare, Plus, Clock, CheckCircle } from 'lucide-react';
import Link from 'next/link';

export default function CouncilPage() {
  const { data: meetings } = useQuery({
    queryKey: ['meetings'],
    queryFn: () => api.get('/council/meetings').then(r => r.data)
  });
  
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">The Conclave</h1>
          <p className="text-slate-400">Multi-agent council meetings</p>
        </div>
        <Link
          href="/council/new"
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
        >
          <Plus size={18} />
          <span>New Meeting</span>
        </Link>
      </div>
      
      {/* Council Members */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4">Council Members ({COUNCIL_MEMBERS.length})</h2>
        <div className="flex flex-wrap gap-2">
          {COUNCIL_MEMBERS.map(agent => (
            <Link
              key={agent.id}
              href={`/agents/${agent.id}`}
              className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded-full text-sm transition"
            >
              {agent.name}
            </Link>
          ))}
        </div>
      </div>
      
      {/* Active Meetings */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Clock size={18} className="text-amber-400" />
          Active Meetings
        </h2>
        {meetings?.active?.length > 0 ? (
          <div className="space-y-2">
            {meetings.active.map((meeting: any) => (
              <MeetingRow key={meeting.id} meeting={meeting} status="active" />
            ))}
          </div>
        ) : (
          <p className="text-slate-500 text-sm">No active meetings</p>
        )}
      </div>
      
      {/* Recent Meetings */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <CheckCircle size={18} className="text-green-400" />
          Recent Meetings
        </h2>
        {meetings?.recent?.length > 0 ? (
          <div className="space-y-2">
            {meetings.recent.map((meeting: any) => (
              <MeetingRow key={meeting.id} meeting={meeting} status="completed" />
            ))}
          </div>
        ) : (
          <p className="text-slate-500 text-sm">No recent meetings</p>
        )}
      </div>
    </div>
  );
}

function MeetingRow({ meeting, status }: { meeting: any; status: string }) {
  return (
    <Link
      href={`/council/${meeting.id}`}
      className="flex items-center justify-between p-3 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition"
    >
      <div>
        <p className="font-medium">{meeting.title}</p>
        <p className="text-sm text-slate-400">{meeting.participants?.join(', ')}</p>
      </div>
      <span className={`text-xs px-2 py-1 rounded ${
        status === 'active' ? 'bg-amber-500/20 text-amber-400' : 'bg-green-500/20 text-green-400'
      }`}>
        {status}
      </span>
    </Link>
  );
}
```

### 7.4 New Meeting Page
```typescript
// src/app/council/new/page.tsx
'use client';
import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { COUNCIL_MEMBERS } from '@/lib/agents';
import { api } from '@/lib/api';
import { Plus, X } from 'lucide-react';

export default function NewMeetingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselected = searchParams.get('participants')?.split(',') || [];
  
  const [title, setTitle] = useState('');
  const [topic, setTopic] = useState('');
  const [agenda, setAgenda] = useState<string[]>(['']);
  const [participants, setParticipants] = useState<string[]>(preselected);
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await api.post('/council/convene', {
        title,
        topic,
        agenda: agenda.filter(a => a.trim()),
        participants
      });
      
      router.push(`/council/${response.data.meeting_id}`);
    } catch (error) {
      console.error('Failed to create meeting:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const toggleParticipant = (name: string) => {
    setParticipants(prev => 
      prev.includes(name) 
        ? prev.filter(p => p !== name)
        : [...prev, name]
    );
  };
  
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Convene Council</h1>
        <p className="text-slate-400">Create a new multi-agent meeting</p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title */}
        <div>
          <label className="block text-sm font-medium mb-2">Meeting Title</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g., Q1 Strategy Planning"
            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-indigo-500"
            required
          />
        </div>
        
        {/* Topic */}
        <div>
          <label className="block text-sm font-medium mb-2">Topic</label>
          <textarea
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="What is this meeting about?"
            rows={3}
            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-indigo-500"
            required
          />
        </div>
        
        {/* Agenda */}
        <div>
          <label className="block text-sm font-medium mb-2">Agenda Items</label>
          <div className="space-y-2">
            {agenda.map((item, i) => (
              <div key={i} className="flex gap-2">
                <input
                  type="text"
                  value={item}
                  onChange={e => {
                    const newAgenda = [...agenda];
                    newAgenda[i] = e.target.value;
                    setAgenda(newAgenda);
                  }}
                  placeholder={`Agenda item ${i + 1}`}
                  className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-indigo-500"
                />
                {agenda.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setAgenda(agenda.filter((_, j) => j !== i))}
                    className="p-2 text-slate-400 hover:text-red-400"
                  >
                    <X size={20} />
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={() => setAgenda([...agenda, ''])}
              className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300"
            >
              <Plus size={16} />
              Add agenda item
            </button>
          </div>
        </div>
        
        {/* Participants */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Participants ({participants.length} selected)
          </label>
          <div className="flex flex-wrap gap-2">
            {COUNCIL_MEMBERS.map(agent => (
              <button
                key={agent.id}
                type="button"
                onClick={() => toggleParticipant(agent.name)}
                className={`px-3 py-1 rounded-full text-sm transition ${
                  participants.includes(agent.name)
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {agent.name}
              </button>
            ))}
          </div>
        </div>
        
        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !title || !topic || participants.length === 0}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg transition font-medium"
        >
          {loading ? 'Creating...' : 'Convene Council'}
        </button>
      </form>
    </div>
  );
}
```

### 7.5 Active Meeting Page
```typescript
// src/app/council/[id]/page.tsx
'use client';
import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { COUNCIL_MEMBERS, AGENTS } from '@/lib/agents';
import { 
  Send, UserPlus, Vote, CheckCircle, 
  XCircle, MessageSquare, Users 
} from 'lucide-react';

export default function MeetingPage() {
  const params = useParams();
  const meetingId = params.id as string;
  const queryClient = useQueryClient();
  const transcriptRef = useRef<HTMLDivElement>(null);
  
  const [input, setInput] = useState('');
  const [showSummon, setShowSummon] = useState(false);
  const [showVote, setShowVote] = useState(false);
  
  // Fetch meeting data
  const { data: meeting, isLoading } = useQuery({
    queryKey: ['meeting', meetingId],
    queryFn: () => api.get(`/council/${meetingId}/status`).then(r => r.data),
    refetchInterval: 2000 // Poll for updates
  });
  
  // Chair speak mutation
  const speakMutation = useMutation({
    mutationFn: (statement: string) => 
      api.post(`/council/${meetingId}/speak`, { statement }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] });
      setInput('');
    }
  });
  
  // Next turn mutation
  const nextMutation = useMutation({
    mutationFn: () => api.post(`/council/${meetingId}/next`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] });
    }
  });
  
  // Summon mutation
  const summonMutation = useMutation({
    mutationFn: (data: { agent: string; reason: string; question: string }) =>
      api.post(`/council/${meetingId}/summon`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] });
      setShowSummon(false);
    }
  });
  
  // Vote mutation
  const voteMutation = useMutation({
    mutationFn: (data: { question: string; options: string[] }) =>
      api.post(`/council/${meetingId}/vote`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] });
      setShowVote(false);
    }
  });
  
  // Adjourn mutation
  const adjournMutation = useMutation({
    mutationFn: () => api.post(`/council/${meetingId}/adjourn`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] });
    }
  });
  
  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [meeting?.transcript]);
  
  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }
  
  const isActive = meeting?.status === 'IN_SESSION';
  const isAdjourned = meeting?.status === 'ADJOURNED';
  
  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold">{meeting?.title}</h1>
          <p className="text-sm text-slate-400">{meeting?.topic}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm ${
            isActive ? 'bg-green-500/20 text-green-400' :
            isAdjourned ? 'bg-slate-500/20 text-slate-400' :
            'bg-amber-500/20 text-amber-400'
          }`}>
            {meeting?.status}
          </span>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Transcript */}
        <div className="flex-1 flex flex-col bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <div className="p-3 border-b border-slate-700 flex items-center justify-between">
            <span className="font-medium">Transcript</span>
            <span className="text-sm text-slate-400">
              {meeting?.turns_elapsed || 0} turns
            </span>
          </div>
          
          <div 
            ref={transcriptRef}
            className="flex-1 overflow-y-auto p-4 space-y-4"
          >
            {meeting?.transcript?.map((entry: any, i: number) => (
              <TranscriptEntry key={i} entry={entry} />
            ))}
          </div>
          
          {/* Chair Input */}
          {isActive && (
            <div className="p-3 border-t border-slate-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && input.trim()) {
                      speakMutation.mutate(input);
                    }
                  }}
                  placeholder="Speak as Chair..."
                  className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:border-indigo-500"
                />
                <button
                  onClick={() => speakMutation.mutate(input)}
                  disabled={!input.trim() || speakMutation.isPending}
                  className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 rounded-lg transition"
                >
                  <Send size={20} />
                </button>
              </div>
            </div>
          )}
        </div>
        
        {/* Sidebar */}
        <div className="w-72 space-y-4">
          {/* Participants */}
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-4">
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <Users size={16} />
              Participants
            </h3>
            <div className="space-y-2">
              {meeting?.participants?.map((name: string) => {
                const agent = AGENTS[name];
                return (
                  <div 
                    key={name}
                    className={`flex items-center gap-2 text-sm ${
                      meeting?.current_speaker === name ? 'text-indigo-400' : 'text-slate-400'
                    }`}
                  >
                    <div className={`w-2 h-2 rounded-full ${
                      meeting?.current_speaker === name ? 'bg-indigo-400' : 'bg-slate-600'
                    }`} />
                    <span>{name}</span>
                    {meeting?.current_speaker === name && (
                      <span className="text-xs">(speaking)</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
          
          {/* Actions */}
          {isActive && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 space-y-2">
              <h3 className="font-medium mb-3">Chair Actions</h3>
              
              <button
                onClick={() => nextMutation.mutate()}
                disabled={nextMutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm"
              >
                <MessageSquare size={16} />
                Next Speaker
              </button>
              
              <button
                onClick={() => setShowSummon(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm"
              >
                <UserPlus size={16} />
                Summon Agent
              </button>
              
              <button
                onClick={() => setShowVote(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm"
              >
                <Vote size={16} />
                Call Vote
              </button>
              
              <button
                onClick={() => adjournMutation.mutate()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition text-sm"
              >
                <XCircle size={16} />
                Adjourn
              </button>
            </div>
          )}
          
          {/* Decisions */}
          {meeting?.decisions?.length > 0 && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-4">
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <CheckCircle size={16} className="text-green-400" />
                Decisions
              </h3>
              <div className="space-y-2 text-sm">
                {meeting.decisions.map((d: any, i: number) => (
                  <div key={i} className="p-2 bg-slate-700/50 rounded">
                    {d.decision}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Summon Modal */}
      {showSummon && (
        <SummonModal
          meeting={meeting}
          onClose={() => setShowSummon(false)}
          onSummon={(data) => summonMutation.mutate(data)}
        />
      )}
      
      {/* Vote Modal */}
      {showVote && (
        <VoteModal
          onClose={() => setShowVote(false)}
          onVote={(data) => voteMutation.mutate(data)}
        />
      )}
    </div>
  );
}

function TranscriptEntry({ entry }: { entry: any }) {
  const isConvener = entry.speaker === 'CONVENER';
  const isChair = entry.speaker === 'CHAIR';
  
  return (
    <div className={`flex gap-3 ${isConvener ? 'opacity-70' : ''}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
        isChair ? 'bg-amber-500/20 text-amber-400' :
        isConvener ? 'bg-slate-600 text-slate-400' :
        'bg-indigo-500/20 text-indigo-400'
      }`}>
        {entry.speaker.slice(0, 2)}
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className={`font-medium text-sm ${
            isChair ? 'text-amber-400' :
            isConvener ? 'text-slate-400' :
            'text-indigo-400'
          }`}>
            {entry.speaker}
          </span>
          <span className="text-xs text-slate-500">
            {new Date(entry.timestamp).toLocaleTimeString()}
          </span>
        </div>
        <p className="text-sm text-slate-300 mt-1">{entry.statement}</p>
      </div>
    </div>
  );
}

function SummonModal({ meeting, onClose, onSummon }: any) {
  const [agent, setAgent] = useState('');
  const [reason, setReason] = useState('');
  const [question, setQuestion] = useState('');
  
  const available = COUNCIL_MEMBERS.filter(
    a => !meeting?.participants?.includes(a.name)
  );
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md border border-slate-700">
        <h2 className="text-lg font-bold mb-4">Summon Agent</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-2">Select Agent</label>
            <select
              value={agent}
              onChange={e => setAgent(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            >
              <option value="">Choose...</option>
              {available.map(a => (
                <option key={a.id} value={a.name}>{a.name} - {a.function}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm mb-2">Reason</label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="Why do you need this agent?"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
          </div>
          
          <div>
            <label className="block text-sm mb-2">Question for them</label>
            <textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="What do you want to ask?"
              rows={3}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
          </div>
        </div>
        
        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={() => onSummon({ agent, reason, specific_question: question })}
            disabled={!agent || !question}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 rounded-lg transition"
          >
            Summon
          </button>
        </div>
      </div>
    </div>
  );
}

function VoteModal({ onClose, onVote }: any) {
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState(['', '']);
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md border border-slate-700">
        <h2 className="text-lg font-bold mb-4">Call Advisory Vote</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-2">Question</label>
            <input
              type="text"
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="What should we decide?"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
          </div>
          
          <div>
            <label className="block text-sm mb-2">Options</label>
            <div className="space-y-2">
              {options.map((opt, i) => (
                <input
                  key={i}
                  type="text"
                  value={opt}
                  onChange={e => {
                    const newOpts = [...options];
                    newOpts[i] = e.target.value;
                    setOptions(newOpts);
                  }}
                  placeholder={`Option ${i + 1}`}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
                />
              ))}
              <button
                type="button"
                onClick={() => setOptions([...options, ''])}
                className="text-sm text-indigo-400 hover:text-indigo-300"
              >
                + Add option
              </button>
            </div>
          </div>
        </div>
        
        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={() => onVote({ question, options: options.filter(o => o.trim()) })}
            disabled={!question || options.filter(o => o.trim()).length < 2}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 rounded-lg transition"
          >
            Call Vote
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## PART 8: API & HOOKS

### 8.1 API Client
```typescript
// src/lib/api.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8007',
  timeout: 30000
});

// Add interceptors for error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);
```

### 8.2 Hooks
```typescript
// src/hooks/useAgentHealth.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AGENTS } from '@/lib/agents';

export function useAgentHealth() {
  return useQuery({
    queryKey: ['agent-health'],
    queryFn: async () => {
      const results: Record<string, string> = {};
      let online = 0;
      
      for (const agent of Object.values(AGENTS)) {
        if (agent.port > 0) {
          try {
            await api.get(`http://localhost:${agent.port}/health`, { timeout: 2000 });
            results[agent.id] = 'online';
            online++;
          } catch {
            results[agent.id] = 'offline';
          }
        }
      }
      
      return { agents: results, online, total: Object.keys(AGENTS).length };
    },
    refetchInterval: 30000
  });
}

// src/hooks/useMetrics.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useMetrics() {
  return useQuery({
    queryKey: ['metrics'],
    queryFn: () => api.get('/metrics').then(r => r.data),
    refetchInterval: 60000
  });
}

// src/hooks/useCouncil.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useCouncil(meetingId?: string) {
  const queryClient = useQueryClient();
  
  const meeting = useQuery({
    queryKey: ['meeting', meetingId],
    queryFn: () => api.get(`/council/${meetingId}/status`).then(r => r.data),
    enabled: !!meetingId,
    refetchInterval: 2000
  });
  
  const speak = useMutation({
    mutationFn: (statement: string) => 
      api.post(`/council/${meetingId}/speak`, { statement }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] })
  });
  
  const next = useMutation({
    mutationFn: () => api.post(`/council/${meetingId}/next`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] })
  });
  
  return { meeting, speak, next };
}
```

---

## PART 9: DEPLOYMENT

### 9.1 Build
```bash
cd /opt/leveredge/ui/command-center
npm run build
```

### 9.2 Caddy Configuration
```caddyfile
command.leveredgeai.com {
    reverse_proxy localhost:3000
    encode gzip
}
```

### 9.3 Systemd Service
```bash
# /etc/systemd/system/leveredge-command-center.service
[Unit]
Description=LeverEdge Command Center
After=network.target

[Service]
Type=simple
User=damon
WorkingDirectory=/opt/leveredge/ui/command-center
ExecStart=/usr/bin/npm start
Restart=always
Environment=NODE_ENV=production
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
```

### 9.4 Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable leveredge-command-center
sudo systemctl start leveredge-command-center
```

---

## PART 10: UPGRADE PLAN

After everything is deployed and functional, upgrade in this order:

### Phase 1: Core Infrastructure (Week 1)
1. [ ] CONVENER - Verify smart facilitation works
2. [ ] SCRIBE - Verify transcripts and summaries
3. [ ] Hub Dashboard - Real metrics flowing
4. [ ] Agent health checks - All 40 agents responding

### Phase 2: Domain Dashboards (Week 2)
1. [ ] PANTHEON - Core system agents
2. [ ] THE KEEP - Business operations
3. [ ] ALCHEMY - Creative tools
4. [ ] ARIA SANCTUM - Personal AI

### Phase 3: Remaining Domains (Week 3)
1. [ ] SENTINELS - Security
2. [ ] THE SHIRE - Personal wellness
3. [ ] CHANCERY - Legal/financial
4. [ ] GAIA - Emergency (verify only)

### Phase 4: Council System (Week 4)
1. [ ] Run first real council meeting
2. [ ] Test summoning
3. [ ] Test voting
4. [ ] Test consultation
5. [ ] Verify SCRIBE summaries

### Phase 5: Visual Upgrades (Post-Functional)
*See PINNED-VISUAL-UPGRADES.md*
1. [ ] Generate Midjourney backgrounds
2. [ ] Implement garden atrium theme
3. [ ] Add portal transitions
4. [ ] Animate domain pages

---

## COMPLETION CHECKLIST

```bash
# After each major part, commit:
cd /opt/leveredge
git add .
git commit -m "GSD: [Part N] - description"

# At the end, notify:
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "message": "🏛️ COMMAND CENTER BUILD COMPLETE!\n\n✅ Hub dashboard\n✅ 8 domain pages\n✅ 40+ agent pages\n✅ CONCLAVE V2 council system\n✅ Meeting UI\n\nReady to test!",
    "priority": "high"
  }'
```

---

*End of MEGA GSD*
*Function first. Beauty later. Ship it.*
