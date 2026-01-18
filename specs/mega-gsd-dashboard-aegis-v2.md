# MEGA GSD: FULL DASHBOARD BUILD + AEGIS V2

*Prepared: January 17, 2026*
*Purpose: Build ALL dashboards, upgrade AEGIS to V2, get everything functional*
*Approach: Function first, visual upgrades later*

---

## OVERVIEW

Build the complete LeverEdge command center with:
- Master hub dashboard
- All 8 domain dashboards
- All 40+ agent pages
- Council meeting UI (CONVENER V2 already built - just needs frontend)
- AEGIS V2 enterprise credential management
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
│   │   ├── credentials/
│   │   │   ├── page.tsx            # AEGIS dashboard
│   │   │   ├── [name]/page.tsx     # Individual credential
│   │   │   └── audit/page.tsx      # Audit log
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
│   │   ├── credentials/
│   │   │   ├── CredentialCard.tsx
│   │   │   ├── CredentialForm.tsx
│   │   │   ├── RotationHistory.tsx
│   │   │   └── AuditLog.tsx
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
│       ├── useCouncil.ts
│       └── useCredentials.ts
├── public/
└── next.config.js
```

### 1.4 Environment Config
```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8007
NEXT_PUBLIC_AEGIS_URL=http://localhost:8012
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
  Sparkles, Star, MessageSquare, Settings, Key 
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
          System
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
        
        <Link
          href="/credentials"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
            pathname.startsWith('/credentials') ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
          }`}
        >
          <Key size={18} />
          <span>AEGIS Vault</span>
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
import { useCredentialHealth } from '@/hooks/useCredentials';
import { Clock, DollarSign, Calendar, Activity, Key } from 'lucide-react';

export function Header() {
  const { data: metrics } = useMetrics();
  const { data: credHealth } = useCredentialHealth();
  
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
        
        <div className="flex items-center gap-2 text-sm">
          <Key size={16} className={credHealth?.expiring > 0 ? 'text-amber-400' : 'text-green-400'} />
          <span className="text-slate-400">Creds</span>
          <span className={`font-bold ${credHealth?.expiring > 0 ? 'text-amber-400' : 'text-green-400'}`}>
            {credHealth?.healthy || 0}/{credHealth?.total || 0}
          </span>
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

---

## PART 4: HUB DASHBOARD

### 4.1 Main Hub Page
```typescript
// src/app/page.tsx
'use client';
import { DOMAINS, AGENTS, COUNCIL_MEMBERS } from '@/lib/agents';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { DomainCard } from '@/components/dashboard/DomainCard';
import { CredentialSummary } from '@/components/credentials/CredentialSummary';
import { useAgentHealth } from '@/hooks/useAgentHealth';
import { useCredentialHealth } from '@/hooks/useCredentials';
import { 
  Users, Activity, DollarSign, Calendar, 
  MessageSquare, Zap, Server, Shield, Key 
} from 'lucide-react';
import Link from 'next/link';

export default function HubPage() {
  const { data: health } = useAgentHealth();
  const { data: credHealth } = useCredentialHealth();
  
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
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
        <MetricCard
          title="Credentials"
          value={`${credHealth?.healthy || 0}/${credHealth?.total || 0}`}
          subtitle={credHealth?.expiring > 0 ? `${credHealth.expiring} expiring` : 'All healthy'}
          icon={<Key size={20} />}
          color={credHealth?.expiring > 0 ? '#FBBF24' : '#34D399'}
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
        <Link
          href="/credentials"
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
        >
          <Key size={18} />
          <span>AEGIS Vault</span>
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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
            <Key size={18} />
            Credential Health
          </h3>
          <CredentialSummary />
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
              event="AEGIS rotated API key" 
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

---

## PART 5: AEGIS V2 - ENTERPRISE CREDENTIAL MANAGEMENT

### 5.1 Database Schema Migration

Run this in DEV first, then PROD:

```sql
-- Core credential registry (enhanced)
CREATE TABLE IF NOT EXISTS aegis_credentials_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    credential_type TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'n8n', -- n8n, supabase, api, env, caddy
    description TEXT,
    
    -- Encrypted storage (for non-n8n creds)
    encrypted_value TEXT,
    encryption_key_id TEXT,
    
    -- Provider reference
    provider_credential_id TEXT, -- n8n credential ID, etc.
    
    -- Lifecycle
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expiring', 'expired', 'rotating', 'failed', 'retired')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_rotated_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_health_check TIMESTAMPTZ,
    
    -- Rotation config
    rotation_enabled BOOLEAN DEFAULT FALSE,
    rotation_interval_hours INT DEFAULT 720, -- 30 days default
    rotation_strategy TEXT DEFAULT 'manual', -- manual, scheduled, on_expiry
    next_rotation_at TIMESTAMPTZ,
    
    -- Alert config
    alert_threshold_hours INT DEFAULT 168, -- 7 days before expiry
    alert_sent BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Credential versions (for rollback)
CREATE TABLE IF NOT EXISTS aegis_credential_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    version INT NOT NULL,
    encrypted_value TEXT,
    provider_credential_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    reason TEXT, -- 'initial', 'rotation', 'manual_update', 'emergency'
    is_current BOOLEAN DEFAULT TRUE,
    
    UNIQUE(credential_id, version)
);

-- Comprehensive audit log
CREATE TABLE IF NOT EXISTS aegis_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    credential_id UUID REFERENCES aegis_credentials_v2(id),
    credential_name TEXT NOT NULL,
    action TEXT NOT NULL, -- 'created', 'read', 'applied', 'rotated', 'expired', 'failed', 'retired'
    actor TEXT NOT NULL, -- 'HEPHAESTUS', 'ARIA', 'scheduler', 'manual'
    target TEXT, -- workflow_id, node_name, etc.
    details JSONB DEFAULT '{}',
    ip_address TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Rotation history
CREATE TABLE IF NOT EXISTS aegis_rotation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    rotated_at TIMESTAMPTZ DEFAULT NOW(),
    previous_version INT,
    new_version INT,
    trigger TEXT NOT NULL, -- 'scheduled', 'manual', 'emergency', 'expiry'
    duration_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    rolled_back BOOLEAN DEFAULT FALSE,
    rollback_at TIMESTAMPTZ
);

-- Health check results
CREATE TABLE IF NOT EXISTS aegis_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL, -- 'healthy', 'unhealthy', 'unknown'
    response_time_ms INT,
    details JSONB DEFAULT '{}',
    error_message TEXT
);

-- Provider registry
CREATE TABLE IF NOT EXISTS aegis_providers (
    id SERIAL PRIMARY KEY,
    provider_name TEXT UNIQUE NOT NULL,
    provider_type TEXT NOT NULL, -- 'api_key', 'oauth2', 'service_account', 'basic_auth'
    base_url TEXT,
    auth_endpoint TEXT,
    token_endpoint TEXT,
    docs_url TEXT,
    required_scopes TEXT[],
    credential_fields JSONB,
    validation_endpoint TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_credentials_status ON aegis_credentials_v2(status);
CREATE INDEX IF NOT EXISTS idx_credentials_expires ON aegis_credentials_v2(expires_at);
CREATE INDEX IF NOT EXISTS idx_credentials_next_rotation ON aegis_credentials_v2(next_rotation_at);
CREATE INDEX IF NOT EXISTS idx_audit_credential ON aegis_audit_log(credential_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON aegis_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON aegis_audit_log(action);
```

### 5.2 Populate Provider Registry
```sql
INSERT INTO aegis_providers (provider_name, provider_type, base_url, validation_endpoint, credential_fields) VALUES

-- AI Providers
('openai', 'api_key', 'https://api.openai.com/v1', '/models', 
 '{"api_key": {"type": "secret", "required": true}}'),

('anthropic', 'api_key', 'https://api.anthropic.com/v1', '/messages',
 '{"api_key": {"type": "secret", "required": true}}'),

('google_ai', 'api_key', 'https://generativelanguage.googleapis.com/v1', '/models',
 '{"api_key": {"type": "secret", "required": true}}'),

('replicate', 'api_key', 'https://api.replicate.com/v1', '/models',
 '{"api_token": {"type": "secret", "required": true}}'),

('fal_ai', 'api_key', 'https://fal.run', '/health',
 '{"api_key": {"type": "secret", "required": true}}'),

('elevenlabs', 'api_key', 'https://api.elevenlabs.io/v1', '/voices',
 '{"api_key": {"type": "secret", "required": true}}'),

-- Google Services (OAuth2)
('google_oauth', 'oauth2', 'https://oauth2.googleapis.com', '/tokeninfo',
 '{"client_id": {"type": "string", "required": true}, "client_secret": {"type": "secret", "required": true}, "refresh_token": {"type": "secret", "required": true}}'),

('google_drive', 'oauth2', 'https://www.googleapis.com/drive/v3', '/about',
 '{"client_id": {"type": "string", "required": true}, "client_secret": {"type": "secret", "required": true}, "refresh_token": {"type": "secret", "required": true}}'),

('google_sheets', 'oauth2', 'https://sheets.googleapis.com/v4', '/spreadsheets',
 '{"client_id": {"type": "string", "required": true}, "client_secret": {"type": "secret", "required": true}, "refresh_token": {"type": "secret", "required": true}}'),

('gmail', 'oauth2', 'https://gmail.googleapis.com/gmail/v1', '/users/me/profile',
 '{"client_id": {"type": "string", "required": true}, "client_secret": {"type": "secret", "required": true}, "refresh_token": {"type": "secret", "required": true}}'),

-- GitHub
('github', 'api_key', 'https://api.github.com', '/user',
 '{"personal_access_token": {"type": "secret", "required": true}}'),

-- Communication
('telegram', 'api_key', 'https://api.telegram.org', '/getMe',
 '{"bot_token": {"type": "secret", "required": true}}'),

('sendgrid', 'api_key', 'https://api.sendgrid.com/v3', '/user/profile',
 '{"api_key": {"type": "secret", "required": true}}'),

-- Infrastructure
('cloudflare', 'api_key', 'https://api.cloudflare.com/client/v4', '/user/tokens/verify',
 '{"api_token": {"type": "secret", "required": true}}'),

('supabase', 'api_key', NULL, NULL,
 '{"project_url": {"type": "string", "required": true}, "anon_key": {"type": "string", "required": true}, "service_role_key": {"type": "secret", "required": true}}'),

-- Caddy (basic auth)
('caddy_basic_auth', 'basic_auth', NULL, NULL,
 '{"username": {"type": "string", "required": true}, "password_hash": {"type": "secret", "required": true}, "config_path": {"type": "string", "required": true}}'),

-- Payment
('stripe', 'api_key', 'https://api.stripe.com/v1', '/balance',
 '{"secret_key": {"type": "secret", "required": true}, "publishable_key": {"type": "string", "required": true}}'),

-- Media
('midjourney', 'api_key', NULL, NULL,
 '{"discord_token": {"type": "secret", "required": true}, "server_id": {"type": "string", "required": true}}')

ON CONFLICT (provider_name) DO NOTHING;
```

### 5.3 AEGIS V2 FastAPI App
```python
# /opt/leveredge/control-plane/agents/aegis/aegis_v2.py

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import httpx
import asyncpg
from uuid import uuid4

app = FastAPI(title="AEGIS V2", description="Enterprise Credential Management")

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54321")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
MASTER_KEY_PATH = "/opt/leveredge/secrets/aegis_master.key"
HERMES_URL = "http://localhost:8014"

# Encryption
class CredentialEncryption:
    def __init__(self):
        self.fernet = None
        self._init_encryption()
    
    def _init_encryption(self):
        if os.path.exists(MASTER_KEY_PATH):
            with open(MASTER_KEY_PATH, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(MASTER_KEY_PATH), exist_ok=True)
            with open(MASTER_KEY_PATH, 'wb') as f:
                f.write(key)
        self.fernet = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        return self.fernet.decrypt(encrypted_value.encode()).decode()

encryption = CredentialEncryption()

# Models
class CredentialCreate(BaseModel):
    name: str
    credential_type: str
    provider: str = "api"
    description: Optional[str] = None
    value: Optional[str] = None  # Will be encrypted
    provider_credential_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    rotation_enabled: bool = False
    rotation_interval_hours: int = 720
    rotation_strategy: str = "manual"
    alert_threshold_hours: int = 168
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

class CredentialUpdate(BaseModel):
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    rotation_enabled: Optional[bool] = None
    rotation_interval_hours: Optional[int] = None
    rotation_strategy: Optional[str] = None
    alert_threshold_hours: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class RotateRequest(BaseModel):
    trigger: str = "manual"
    reason: Optional[str] = None
    new_value: Optional[str] = None

# Database
async def get_db():
    return await asyncpg.connect(
        f"{SUPABASE_URL.replace('http://', 'postgresql://postgres:postgres@').replace(':54321', ':54322')}/postgres"
    )

# Audit logging
async def audit_log(
    credential_id: Optional[str],
    credential_name: str,
    action: str,
    actor: str,
    target: Optional[str] = None,
    details: Dict = {},
    success: bool = True,
    error_message: Optional[str] = None
):
    db = await get_db()
    await db.execute("""
        INSERT INTO aegis_audit_log 
        (credential_id, credential_name, action, actor, target, details, success, error_message)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """, credential_id, credential_name, action, actor, target, details, success, error_message)
    await db.close()

# Alert via HERMES
async def send_alert(message: str, priority: str = "normal"):
    async with httpx.AsyncClient() as client:
        await client.post(f"{HERMES_URL}/notify", json={
            "channel": "telegram",
            "message": message,
            "priority": priority
        })

# Endpoints
@app.get("/health")
async def health():
    db = await get_db()
    counts = await db.fetchrow("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as healthy,
            COUNT(*) FILTER (WHERE status = 'expiring') as expiring,
            COUNT(*) FILTER (WHERE status = 'expired') as expired,
            COUNT(*) FILTER (WHERE status = 'failed') as failed
        FROM aegis_credentials_v2
    """)
    await db.close()
    
    return {
        "status": "healthy",
        "agent": "AEGIS",
        "version": "2.0",
        "credentials": dict(counts)
    }

@app.get("/credentials")
async def list_credentials(
    status: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0
):
    db = await get_db()
    
    query = "SELECT * FROM aegis_credentials_v2 WHERE 1=1"
    params = []
    
    if status:
        params.append(status)
        query += f" AND status = ${len(params)}"
    if provider:
        params.append(provider)
        query += f" AND provider = ${len(params)}"
    
    query += f" ORDER BY name LIMIT {limit} OFFSET {offset}"
    
    rows = await db.fetch(query, *params)
    await db.close()
    
    # Don't expose encrypted values
    credentials = []
    for row in rows:
        cred = dict(row)
        cred.pop('encrypted_value', None)
        credentials.append(cred)
    
    return {"credentials": credentials, "total": len(credentials)}

@app.get("/credentials/{name}")
async def get_credential(name: str):
    db = await get_db()
    row = await db.fetchrow(
        "SELECT * FROM aegis_credentials_v2 WHERE name = $1", name
    )
    await db.close()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")
    
    cred = dict(row)
    cred.pop('encrypted_value', None)
    
    await audit_log(str(cred['id']), name, 'read', 'API')
    
    return cred

@app.post("/credentials")
async def create_credential(cred: CredentialCreate):
    db = await get_db()
    
    # Check if exists
    existing = await db.fetchrow(
        "SELECT id FROM aegis_credentials_v2 WHERE name = $1", cred.name
    )
    if existing:
        await db.close()
        raise HTTPException(status_code=400, detail=f"Credential '{cred.name}' already exists")
    
    # Encrypt value if provided
    encrypted_value = None
    if cred.value:
        encrypted_value = encryption.encrypt(cred.value)
    
    # Calculate next rotation
    next_rotation = None
    if cred.rotation_enabled and cred.rotation_strategy == 'scheduled':
        next_rotation = datetime.utcnow() + timedelta(hours=cred.rotation_interval_hours)
    
    cred_id = str(uuid4())
    
    await db.execute("""
        INSERT INTO aegis_credentials_v2 
        (id, name, credential_type, provider, description, encrypted_value, 
         provider_credential_id, expires_at, rotation_enabled, rotation_interval_hours,
         rotation_strategy, next_rotation_at, alert_threshold_hours, tags, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
    """, cred_id, cred.name, cred.credential_type, cred.provider, cred.description,
        encrypted_value, cred.provider_credential_id, cred.expires_at, cred.rotation_enabled,
        cred.rotation_interval_hours, cred.rotation_strategy, next_rotation,
        cred.alert_threshold_hours, cred.tags, cred.metadata)
    
    # Create initial version
    await db.execute("""
        INSERT INTO aegis_credential_versions (credential_id, version, encrypted_value, created_by, reason)
        VALUES ($1, 1, $2, 'system', 'initial')
    """, cred_id, encrypted_value)
    
    await db.close()
    
    await audit_log(cred_id, cred.name, 'created', 'API', details={"provider": cred.provider})
    
    return {"id": cred_id, "name": cred.name, "status": "created"}

@app.patch("/credentials/{name}")
async def update_credential(name: str, updates: CredentialUpdate):
    db = await get_db()
    
    row = await db.fetchrow("SELECT id FROM aegis_credentials_v2 WHERE name = $1", name)
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")
    
    # Build update query
    update_fields = []
    params = []
    param_idx = 1
    
    for field, value in updates.dict(exclude_none=True).items():
        update_fields.append(f"{field} = ${param_idx}")
        params.append(value)
        param_idx += 1
    
    if update_fields:
        update_fields.append(f"updated_at = ${param_idx}")
        params.append(datetime.utcnow())
        params.append(name)
        
        query = f"UPDATE aegis_credentials_v2 SET {', '.join(update_fields)} WHERE name = ${param_idx + 1}"
        await db.execute(query, *params)
    
    await db.close()
    
    await audit_log(str(row['id']), name, 'updated', 'API', details=updates.dict(exclude_none=True))
    
    return {"name": name, "status": "updated"}

@app.post("/credentials/{name}/rotate")
async def rotate_credential(name: str, req: RotateRequest):
    db = await get_db()
    
    row = await db.fetchrow(
        "SELECT * FROM aegis_credentials_v2 WHERE name = $1", name
    )
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")
    
    cred_id = str(row['id'])
    
    # Get current version
    current_version = await db.fetchval(
        "SELECT MAX(version) FROM aegis_credential_versions WHERE credential_id = $1",
        row['id']
    ) or 0
    
    new_version = current_version + 1
    
    # Encrypt new value
    encrypted_value = None
    if req.new_value:
        encrypted_value = encryption.encrypt(req.new_value)
    
    start_time = datetime.utcnow()
    
    try:
        # Mark old version as not current
        await db.execute("""
            UPDATE aegis_credential_versions SET is_current = FALSE
            WHERE credential_id = $1 AND is_current = TRUE
        """, row['id'])
        
        # Create new version
        await db.execute("""
            INSERT INTO aegis_credential_versions 
            (credential_id, version, encrypted_value, created_by, reason, is_current)
            VALUES ($1, $2, $3, $4, $5, TRUE)
        """, row['id'], new_version, encrypted_value, 'rotation', req.trigger)
        
        # Update credential
        next_rotation = None
        if row['rotation_enabled'] and row['rotation_strategy'] == 'scheduled':
            next_rotation = datetime.utcnow() + timedelta(hours=row['rotation_interval_hours'])
        
        await db.execute("""
            UPDATE aegis_credentials_v2 
            SET encrypted_value = $1, last_rotated_at = $2, next_rotation_at = $3, 
                status = 'active', updated_at = $2
            WHERE id = $4
        """, encrypted_value, datetime.utcnow(), next_rotation, row['id'])
        
        # Log rotation history
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        await db.execute("""
            INSERT INTO aegis_rotation_history 
            (credential_id, previous_version, new_version, trigger, duration_ms, success)
            VALUES ($1, $2, $3, $4, $5, TRUE)
        """, row['id'], current_version, new_version, req.trigger, duration_ms)
        
        await db.close()
        
        await audit_log(cred_id, name, 'rotated', 'API', 
                       details={"trigger": req.trigger, "new_version": new_version})
        
        return {
            "status": "rotated",
            "previous_version": current_version,
            "new_version": new_version,
            "duration_ms": duration_ms
        }
        
    except Exception as e:
        await db.execute("""
            INSERT INTO aegis_rotation_history 
            (credential_id, previous_version, new_version, trigger, success, error_message)
            VALUES ($1, $2, $3, $4, FALSE, $5)
        """, row['id'], current_version, new_version, req.trigger, str(e))
        
        await db.close()
        
        await send_alert(f"❌ Rotation failed for '{name}': {str(e)}", "critical")
        raise HTTPException(status_code=500, detail=f"Rotation failed: {str(e)}")

@app.post("/credentials/{name}/rollback")
async def rollback_credential(name: str, version: Optional[int] = None):
    db = await get_db()
    
    row = await db.fetchrow(
        "SELECT * FROM aegis_credentials_v2 WHERE name = $1", name
    )
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")
    
    # Get version to rollback to
    if version:
        target = await db.fetchrow("""
            SELECT * FROM aegis_credential_versions 
            WHERE credential_id = $1 AND version = $2
        """, row['id'], version)
    else:
        # Get previous version
        target = await db.fetchrow("""
            SELECT * FROM aegis_credential_versions 
            WHERE credential_id = $1 AND is_current = FALSE
            ORDER BY version DESC LIMIT 1
        """, row['id'])
    
    if not target:
        await db.close()
        raise HTTPException(status_code=404, detail="No version available to rollback to")
    
    # Update current version markers
    await db.execute("""
        UPDATE aegis_credential_versions SET is_current = FALSE
        WHERE credential_id = $1
    """, row['id'])
    
    await db.execute("""
        UPDATE aegis_credential_versions SET is_current = TRUE
        WHERE credential_id = $1 AND version = $2
    """, row['id'], target['version'])
    
    # Update credential
    await db.execute("""
        UPDATE aegis_credentials_v2 
        SET encrypted_value = $1, updated_at = $2, status = 'active'
        WHERE id = $3
    """, target['encrypted_value'], datetime.utcnow(), row['id'])
    
    await db.close()
    
    await audit_log(str(row['id']), name, 'rolled_back', 'API', 
                   details={"to_version": target['version']})
    
    return {"status": "rolled_back", "to_version": target['version']}

@app.get("/credentials/{name}/value")
async def get_credential_value(name: str, actor: str = "API"):
    """Get decrypted credential value (restricted access)"""
    db = await get_db()
    
    row = await db.fetchrow(
        "SELECT * FROM aegis_credentials_v2 WHERE name = $1", name
    )
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")
    
    # Update last_used
    await db.execute("""
        UPDATE aegis_credentials_v2 SET last_used_at = $1 WHERE name = $2
    """, datetime.utcnow(), name)
    
    await db.close()
    
    if not row['encrypted_value']:
        raise HTTPException(status_code=400, detail="No value stored for this credential")
    
    await audit_log(str(row['id']), name, 'value_accessed', actor)
    
    return {
        "name": name,
        "value": encryption.decrypt(row['encrypted_value'])
    }

@app.post("/credentials/{name}/test")
async def test_credential(name: str):
    """Test if credential is valid"""
    db = await get_db()
    
    row = await db.fetchrow(
        "SELECT * FROM aegis_credentials_v2 WHERE name = $1", name
    )
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail=f"Credential '{name}' not found")
    
    # Get provider info
    provider = await db.fetchrow(
        "SELECT * FROM aegis_providers WHERE provider_name = $1", row['provider']
    )
    
    start_time = datetime.utcnow()
    status = "unknown"
    error_message = None
    
    if provider and provider['validation_endpoint'] and row['encrypted_value']:
        try:
            value = encryption.decrypt(row['encrypted_value'])
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Provider-specific validation
                if row['provider'] == 'openai':
                    resp = await client.get(
                        f"{provider['base_url']}{provider['validation_endpoint']}",
                        headers={"Authorization": f"Bearer {value}"}
                    )
                elif row['provider'] == 'anthropic':
                    resp = await client.post(
                        f"{provider['base_url']}{provider['validation_endpoint']}",
                        headers={
                            "x-api-key": value,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={"model": "claude-3-haiku-20240307", "max_tokens": 1, 
                              "messages": [{"role": "user", "content": "hi"}]}
                    )
                elif row['provider'] == 'github':
                    resp = await client.get(
                        f"{provider['base_url']}{provider['validation_endpoint']}",
                        headers={"Authorization": f"Bearer {value}"}
                    )
                elif row['provider'] == 'cloudflare':
                    resp = await client.get(
                        f"{provider['base_url']}{provider['validation_endpoint']}",
                        headers={"Authorization": f"Bearer {value}"}
                    )
                elif row['provider'] == 'telegram':
                    resp = await client.get(
                        f"{provider['base_url']}/bot{value}{provider['validation_endpoint']}"
                    )
                else:
                    status = "unknown"
                    resp = None
                
                if resp:
                    status = "healthy" if resp.status_code in [200, 400] else "unhealthy"
                    if status == "unhealthy":
                        error_message = f"HTTP {resp.status_code}"
                        
        except Exception as e:
            status = "unhealthy"
            error_message = str(e)
    
    response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    # Log health check
    await db.execute("""
        INSERT INTO aegis_health_checks (credential_id, status, response_time_ms, error_message)
        VALUES ($1, $2, $3, $4)
    """, row['id'], status, response_time_ms, error_message)
    
    # Update credential status if unhealthy
    if status == "unhealthy":
        await db.execute("""
            UPDATE aegis_credentials_v2 SET status = 'failed', last_health_check = $1
            WHERE id = $2
        """, datetime.utcnow(), row['id'])
    else:
        await db.execute("""
            UPDATE aegis_credentials_v2 SET last_health_check = $1
            WHERE id = $2
        """, datetime.utcnow(), row['id'])
    
    await db.close()
    
    return {
        "name": name,
        "status": status,
        "response_time_ms": response_time_ms,
        "error": error_message
    }

@app.get("/health/dashboard")
async def health_dashboard():
    """Dashboard view of all credentials"""
    db = await get_db()
    
    summary = await db.fetchrow("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as healthy,
            COUNT(*) FILTER (WHERE status = 'expiring') as expiring,
            COUNT(*) FILTER (WHERE status = 'expired') as expired,
            COUNT(*) FILTER (WHERE status = 'failed') as failed
        FROM aegis_credentials_v2
    """)
    
    credentials = await db.fetch("""
        SELECT name, status, provider, credential_type, 
               expires_at, last_used_at, last_health_check,
               EXTRACT(EPOCH FROM (expires_at - NOW()))/3600 as expires_in_hours
        FROM aegis_credentials_v2
        ORDER BY 
            CASE status 
                WHEN 'failed' THEN 1 
                WHEN 'expired' THEN 2 
                WHEN 'expiring' THEN 3 
                ELSE 4 
            END,
            name
    """)
    
    alerts = await db.fetch("""
        SELECT c.name as credential, 
               CASE 
                   WHEN c.status = 'failed' THEN 'Health check failed'
                   WHEN c.status = 'expired' THEN 'Credential expired'
                   WHEN c.status = 'expiring' THEN 'Expiring soon'
               END as alert_type,
               c.updated_at as created_at
        FROM aegis_credentials_v2 c
        WHERE c.status IN ('failed', 'expired', 'expiring')
        ORDER BY c.updated_at DESC
        LIMIT 10
    """)
    
    await db.close()
    
    return {
        "summary": dict(summary),
        "credentials": [dict(c) for c in credentials],
        "alerts": [dict(a) for a in alerts]
    }

@app.get("/health/expiring")
async def get_expiring(threshold_hours: int = 168):
    """Get credentials expiring within threshold"""
    db = await get_db()
    
    credentials = await db.fetch("""
        SELECT * FROM aegis_credentials_v2
        WHERE expires_at IS NOT NULL
          AND expires_at < NOW() + INTERVAL '%s hours'
          AND status != 'retired'
        ORDER BY expires_at
    """, threshold_hours)
    
    await db.close()
    
    return {"credentials": [dict(c) for c in credentials], "count": len(credentials)}

@app.post("/health/check-all")
async def check_all_credentials():
    """Run health checks on all credentials"""
    db = await get_db()
    
    credentials = await db.fetch(
        "SELECT name FROM aegis_credentials_v2 WHERE status != 'retired'"
    )
    await db.close()
    
    results = {"checked": 0, "healthy": 0, "unhealthy": 0, "details": []}
    
    for cred in credentials:
        try:
            result = await test_credential(cred['name'])
            results["checked"] += 1
            if result["status"] == "healthy":
                results["healthy"] += 1
            else:
                results["unhealthy"] += 1
            results["details"].append(result)
        except Exception as e:
            results["details"].append({
                "name": cred['name'],
                "status": "error",
                "error": str(e)
            })
    
    return results

@app.get("/rotation/schedule")
async def get_rotation_schedule():
    """Get upcoming and overdue rotations"""
    db = await get_db()
    
    upcoming = await db.fetch("""
        SELECT name, next_rotation_at, rotation_interval_hours
        FROM aegis_credentials_v2
        WHERE rotation_enabled = TRUE
          AND next_rotation_at IS NOT NULL
          AND next_rotation_at > NOW()
        ORDER BY next_rotation_at
        LIMIT 20
    """)
    
    overdue = await db.fetch("""
        SELECT name, next_rotation_at, rotation_interval_hours
        FROM aegis_credentials_v2
        WHERE rotation_enabled = TRUE
          AND next_rotation_at IS NOT NULL
          AND next_rotation_at <= NOW()
        ORDER BY next_rotation_at
    """)
    
    await db.close()
    
    return {
        "upcoming_rotations": [dict(r) for r in upcoming],
        "overdue_rotations": [dict(r) for r in overdue]
    }

@app.post("/rotation/run-scheduled")
async def run_scheduled_rotations():
    """Execute all scheduled rotations that are due"""
    db = await get_db()
    
    due = await db.fetch("""
        SELECT name FROM aegis_credentials_v2
        WHERE rotation_enabled = TRUE
          AND rotation_strategy = 'scheduled'
          AND next_rotation_at IS NOT NULL
          AND next_rotation_at <= NOW()
    """)
    
    await db.close()
    
    results = {"rotated": 0, "failed": 0, "details": []}
    
    for cred in due:
        try:
            result = await rotate_credential(cred['name'], RotateRequest(trigger="scheduled"))
            results["rotated"] += 1
            results["details"].append({"name": cred['name'], "status": "success"})
        except Exception as e:
            results["failed"] += 1
            results["details"].append({"name": cred['name'], "status": "failed", "error": str(e)})
    
    return results

@app.get("/rotation/history")
async def get_rotation_history(
    credential_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get rotation history"""
    db = await get_db()
    
    if credential_name:
        history = await db.fetch("""
            SELECT h.*, c.name as credential_name
            FROM aegis_rotation_history h
            JOIN aegis_credentials_v2 c ON h.credential_id = c.id
            WHERE c.name = $1
            ORDER BY h.rotated_at DESC
            LIMIT $2 OFFSET $3
        """, credential_name, limit, offset)
    else:
        history = await db.fetch("""
            SELECT h.*, c.name as credential_name
            FROM aegis_rotation_history h
            JOIN aegis_credentials_v2 c ON h.credential_id = c.id
            ORDER BY h.rotated_at DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
    
    await db.close()
    
    return {"history": [dict(h) for h in history], "total": len(history)}

@app.get("/audit/log")
async def get_audit_log(
    credential_name: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
):
    """Get audit log"""
    db = await get_db()
    
    query = "SELECT * FROM aegis_audit_log WHERE 1=1"
    params = []
    
    if credential_name:
        params.append(credential_name)
        query += f" AND credential_name = ${len(params)}"
    if action:
        params.append(action)
        query += f" AND action = ${len(params)}"
    if actor:
        params.append(actor)
        query += f" AND actor = ${len(params)}"
    if start_date:
        params.append(start_date)
        query += f" AND timestamp >= ${len(params)}"
    if end_date:
        params.append(end_date)
        query += f" AND timestamp <= ${len(params)}"
    
    query += f" ORDER BY timestamp DESC LIMIT {limit}"
    
    logs = await db.fetch(query, *params)
    await db.close()
    
    return {"log": [dict(l) for l in logs], "total": len(logs)}

@app.get("/providers")
async def list_providers():
    """List all registered providers"""
    db = await get_db()
    providers = await db.fetch("SELECT * FROM aegis_providers ORDER BY provider_name")
    await db.close()
    return {"providers": [dict(p) for p in providers]}

@app.post("/sync/n8n")
async def sync_from_n8n():
    """Sync credentials from n8n"""
    # This would call the n8n API to get all credentials
    # and register any new ones in AEGIS
    return {"status": "not_implemented", "message": "n8n sync coming soon"}

# Startup - update expiring status
@app.on_event("startup")
async def update_expiring_status():
    try:
        db = await get_db()
        await db.execute("""
            UPDATE aegis_credentials_v2 
            SET status = 'expiring'
            WHERE expires_at IS NOT NULL
              AND expires_at > NOW()
              AND expires_at <= NOW() + (alert_threshold_hours || ' hours')::INTERVAL
              AND status = 'active'
        """)
        await db.execute("""
            UPDATE aegis_credentials_v2 
            SET status = 'expired'
            WHERE expires_at IS NOT NULL
              AND expires_at <= NOW()
              AND status NOT IN ('expired', 'retired')
        """)
        await db.close()
    except:
        pass  # Ignore startup errors if DB not ready

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
```

---

## PART 6: AEGIS UI PAGES

### 6.1 Credentials Dashboard
```typescript
// src/app/credentials/page.tsx
'use client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { CredentialCard } from '@/components/credentials/CredentialCard';
import { 
  Key, Shield, AlertTriangle, Clock, 
  RefreshCw, Plus, Search 
} from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export default function CredentialsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['aegis-dashboard'],
    queryFn: () => api.get('http://localhost:8012/health/dashboard').then(r => r.data),
    refetchInterval: 30000
  });
  
  const checkAllMutation = useMutation({
    mutationFn: () => api.post('http://localhost:8012/health/check-all'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['aegis-dashboard'] });
    }
  });
  
  const filteredCredentials = dashboard?.credentials?.filter((cred: any) => {
    const matchesSearch = cred.name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || cred.status === statusFilter;
    return matchesSearch && matchesStatus;
  }) || [];
  
  if (isLoading) {
    return <div>Loading...</div>;
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield size={28} />
            AEGIS Vault
          </h1>
          <p className="text-slate-400">Enterprise Credential Management</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => checkAllMutation.mutate()}
            disabled={checkAllMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
          >
            <RefreshCw size={18} className={checkAllMutation.isPending ? 'animate-spin' : ''} />
            <span>Check All</span>
          </button>
          <Link
            href="/credentials/new"
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
          >
            <Plus size={18} />
            <span>Add Credential</span>
          </Link>
        </div>
      </div>
      
      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <MetricCard
          title="Total"
          value={dashboard?.summary?.total || 0}
          icon={<Key size={20} />}
          color="#60A5FA"
        />
        <MetricCard
          title="Healthy"
          value={dashboard?.summary?.healthy || 0}
          icon={<Shield size={20} />}
          color="#34D399"
        />
        <MetricCard
          title="Expiring"
          value={dashboard?.summary?.expiring || 0}
          icon={<Clock size={20} />}
          color="#FBBF24"
        />
        <MetricCard
          title="Expired"
          value={dashboard?.summary?.expired || 0}
          icon={<AlertTriangle size={20} />}
          color="#F87171"
        />
        <MetricCard
          title="Failed"
          value={dashboard?.summary?.failed || 0}
          icon={<AlertTriangle size={20} />}
          color="#EF4444"
        />
      </div>
      
      {/* Alerts */}
      {dashboard?.alerts?.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
          <h3 className="font-semibold text-red-400 mb-2 flex items-center gap-2">
            <AlertTriangle size={18} />
            Attention Required
          </h3>
          <div className="space-y-2">
            {dashboard.alerts.map((alert: any, i: number) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-slate-300">{alert.credential}</span>
                <span className="text-red-400">{alert.alert_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search credentials..."
            className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-indigo-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Status</option>
          <option value="active">Healthy</option>
          <option value="expiring">Expiring</option>
          <option value="expired">Expired</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      
      {/* Credentials List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredCredentials.map((cred: any) => (
          <CredentialCard key={cred.name} credential={cred} />
        ))}
      </div>
      
      {filteredCredentials.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          No credentials found
        </div>
      )}
    </div>
  );
}
```

### 6.2 Credential Card Component
```typescript
// src/components/credentials/CredentialCard.tsx
import Link from 'next/link';
import { Key, Clock, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface CredentialCardProps {
  credential: {
    name: string;
    status: string;
    provider: string;
    credential_type: string;
    expires_at?: string;
    last_used_at?: string;
    last_health_check?: string;
    expires_in_hours?: number;
  };
}

const statusConfig: Record<string, { color: string; icon: any; bg: string }> = {
  active: { color: 'text-green-400', icon: CheckCircle, bg: 'bg-green-500/20' },
  expiring: { color: 'text-amber-400', icon: Clock, bg: 'bg-amber-500/20' },
  expired: { color: 'text-red-400', icon: AlertTriangle, bg: 'bg-red-500/20' },
  failed: { color: 'text-red-400', icon: XCircle, bg: 'bg-red-500/20' },
  rotating: { color: 'text-blue-400', icon: RefreshCw, bg: 'bg-blue-500/20' },
};

export function CredentialCard({ credential }: CredentialCardProps) {
  const config = statusConfig[credential.status] || statusConfig.active;
  const Icon = config.icon;
  
  return (
    <Link
      href={`/credentials/${credential.name}`}
      className="block bg-slate-800 rounded-xl p-4 border border-slate-700 hover:border-slate-600 transition"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Key size={18} className="text-slate-400" />
          <h3 className="font-medium">{credential.name}</h3>
        </div>
        <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${config.bg} ${config.color}`}>
          <Icon size={12} />
          {credential.status}
        </span>
      </div>
      
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Provider</span>
          <span className="text-slate-300">{credential.provider}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Type</span>
          <span className="text-slate-300">{credential.credential_type}</span>
        </div>
        {credential.expires_at && (
          <div className="flex justify-between">
            <span className="text-slate-500">Expires</span>
            <span className={credential.status === 'expiring' ? 'text-amber-400' : 'text-slate-300'}>
              {credential.expires_in_hours 
                ? `${Math.round(credential.expires_in_hours)}h`
                : formatDistanceToNow(new Date(credential.expires_at), { addSuffix: true })
              }
            </span>
          </div>
        )}
        {credential.last_used_at && (
          <div className="flex justify-between">
            <span className="text-slate-500">Last Used</span>
            <span className="text-slate-400">
              {formatDistanceToNow(new Date(credential.last_used_at), { addSuffix: true })}
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}
```

### 6.3 Individual Credential Page
```typescript
// src/app/credentials/[name]/page.tsx
'use client';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { 
  Key, Shield, Clock, RefreshCw, RotateCcw, 
  Activity, History, Eye, EyeOff, Trash2 
} from 'lucide-react';
import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';

export default function CredentialPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const name = params.name as string;
  
  const [showValue, setShowValue] = useState(false);
  const [credValue, setCredValue] = useState<string | null>(null);
  
  const { data: credential, isLoading } = useQuery({
    queryKey: ['credential', name],
    queryFn: () => api.get(`http://localhost:8012/credentials/${name}`).then(r => r.data)
  });
  
  const { data: history } = useQuery({
    queryKey: ['credential-history', name],
    queryFn: () => api.get(`http://localhost:8012/rotation/history?credential_name=${name}`).then(r => r.data)
  });
  
  const testMutation = useMutation({
    mutationFn: () => api.post(`http://localhost:8012/credentials/${name}/test`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credential', name] });
    }
  });
  
  const rotateMutation = useMutation({
    mutationFn: () => api.post(`http://localhost:8012/credentials/${name}/rotate`, {
      trigger: 'manual',
      reason: 'Manual rotation from dashboard'
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credential', name] });
      queryClient.invalidateQueries({ queryKey: ['credential-history', name] });
    }
  });
  
  const rollbackMutation = useMutation({
    mutationFn: () => api.post(`http://localhost:8012/credentials/${name}/rollback`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credential', name] });
    }
  });
  
  const fetchValue = async () => {
    if (showValue) {
      setShowValue(false);
      setCredValue(null);
    } else {
      const resp = await api.get(`http://localhost:8012/credentials/${name}/value`);
      setCredValue(resp.data.value);
      setShowValue(true);
    }
  };
  
  if (isLoading) {
    return <div>Loading...</div>;
  }
  
  if (!credential) {
    return <div>Credential not found</div>;
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Key size={28} className="text-slate-400" />
            <h1 className="text-2xl font-bold">{credential.name}</h1>
            <span className={`px-3 py-1 rounded-full text-sm ${
              credential.status === 'active' ? 'bg-green-500/20 text-green-400' :
              credential.status === 'expiring' ? 'bg-amber-500/20 text-amber-400' :
              credential.status === 'failed' ? 'bg-red-500/20 text-red-400' :
              'bg-slate-500/20 text-slate-400'
            }`}>
              {credential.status}
            </span>
          </div>
          <p className="text-slate-400 mt-1">{credential.description || 'No description'}</p>
        </div>
      </div>
      
      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Provider"
          value={credential.provider}
          icon={<Shield size={20} />}
        />
        <MetricCard
          title="Type"
          value={credential.credential_type}
          icon={<Key size={20} />}
        />
        <MetricCard
          title="Last Used"
          value={credential.last_used_at 
            ? formatDistanceToNow(new Date(credential.last_used_at), { addSuffix: true })
            : 'Never'}
          icon={<Clock size={20} />}
        />
        <MetricCard
          title="Last Health Check"
          value={credential.last_health_check 
            ? formatDistanceToNow(new Date(credential.last_health_check), { addSuffix: true })
            : 'Never'}
          icon={<Activity size={20} />}
        />
      </div>
      
      {/* Actions */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4">Actions</h2>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm"
          >
            <Activity size={16} className={testMutation.isPending ? 'animate-pulse' : ''} />
            Test Credential
          </button>
          
          <button
            onClick={() => rotateMutation.mutate()}
            disabled={rotateMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition text-sm"
          >
            <RefreshCw size={16} className={rotateMutation.isPending ? 'animate-spin' : ''} />
            Rotate
          </button>
          
          <button
            onClick={() => rollbackMutation.mutate()}
            disabled={rollbackMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg transition text-sm"
          >
            <RotateCcw size={16} />
            Rollback
          </button>
          
          <button
            onClick={fetchValue}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm"
          >
            {showValue ? <EyeOff size={16} /> : <Eye size={16} />}
            {showValue ? 'Hide Value' : 'Show Value'}
          </button>
        </div>
        
        {showValue && credValue && (
          <div className="mt-4 p-3 bg-slate-900 rounded-lg font-mono text-sm break-all">
            {credValue}
          </div>
        )}
      </div>
      
      {/* Configuration */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4">Configuration</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-500">Rotation Enabled</span>
            <p className="text-slate-300">{credential.rotation_enabled ? 'Yes' : 'No'}</p>
          </div>
          <div>
            <span className="text-slate-500">Rotation Strategy</span>
            <p className="text-slate-300">{credential.rotation_strategy}</p>
          </div>
          <div>
            <span className="text-slate-500">Rotation Interval</span>
            <p className="text-slate-300">{credential.rotation_interval_hours} hours</p>
          </div>
          <div>
            <span className="text-slate-500">Alert Threshold</span>
            <p className="text-slate-300">{credential.alert_threshold_hours} hours before expiry</p>
          </div>
          {credential.expires_at && (
            <div>
              <span className="text-slate-500">Expires At</span>
              <p className="text-slate-300">{new Date(credential.expires_at).toLocaleString()}</p>
            </div>
          )}
          {credential.next_rotation_at && (
            <div>
              <span className="text-slate-500">Next Rotation</span>
              <p className="text-slate-300">{new Date(credential.next_rotation_at).toLocaleString()}</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Rotation History */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <History size={18} />
          Rotation History
        </h2>
        {history?.history?.length > 0 ? (
          <div className="space-y-2">
            {history.history.map((entry: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-slate-700 last:border-0 text-sm">
                <div>
                  <span className="text-slate-300">
                    v{entry.previous_version} → v{entry.new_version}
                  </span>
                  <span className="text-slate-500 ml-2">({entry.trigger})</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className={entry.success ? 'text-green-400' : 'text-red-400'}>
                    {entry.success ? 'Success' : 'Failed'}
                  </span>
                  <span className="text-slate-500">
                    {formatDistanceToNow(new Date(entry.rotated_at), { addSuffix: true })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-500 text-sm">No rotation history</p>
        )}
      </div>
    </div>
  );
}
```

### 6.4 Audit Log Page
```typescript
// src/app/credentials/audit/page.tsx
'use client';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { History, Filter } from 'lucide-react';
import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';

export default function AuditLogPage() {
  const [filters, setFilters] = useState({
    credential_name: '',
    action: '',
    actor: ''
  });
  
  const { data: logs, isLoading } = useQuery({
    queryKey: ['audit-log', filters],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters.credential_name) params.set('credential_name', filters.credential_name);
      if (filters.action) params.set('action', filters.action);
      if (filters.actor) params.set('actor', filters.actor);
      return api.get(`http://localhost:8012/audit/log?${params}`).then(r => r.data);
    }
  });
  
  const actionColors: Record<string, string> = {
    created: 'text-green-400 bg-green-500/20',
    read: 'text-blue-400 bg-blue-500/20',
    applied: 'text-cyan-400 bg-cyan-500/20',
    rotated: 'text-indigo-400 bg-indigo-500/20',
    value_accessed: 'text-amber-400 bg-amber-500/20',
    rolled_back: 'text-orange-400 bg-orange-500/20',
    updated: 'text-purple-400 bg-purple-500/20',
    failed: 'text-red-400 bg-red-500/20',
  };
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <History size={28} />
          Audit Log
        </h1>
        <p className="text-slate-400">Complete history of credential operations</p>
      </div>
      
      {/* Filters */}
      <div className="flex gap-4 items-center">
        <Filter size={18} className="text-slate-400" />
        <input
          type="text"
          placeholder="Credential name..."
          value={filters.credential_name}
          onChange={e => setFilters(f => ({ ...f, credential_name: e.target.value }))}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-indigo-500"
        />
        <select
          value={filters.action}
          onChange={e => setFilters(f => ({ ...f, action: e.target.value }))}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Actions</option>
          <option value="created">Created</option>
          <option value="read">Read</option>
          <option value="applied">Applied</option>
          <option value="rotated">Rotated</option>
          <option value="value_accessed">Value Accessed</option>
          <option value="rolled_back">Rolled Back</option>
        </select>
        <input
          type="text"
          placeholder="Actor..."
          value={filters.actor}
          onChange={e => setFilters(f => ({ ...f, actor: e.target.value }))}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-indigo-500"
        />
      </div>
      
      {/* Log Table */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left p-4 text-slate-400 font-medium">Time</th>
              <th className="text-left p-4 text-slate-400 font-medium">Credential</th>
              <th className="text-left p-4 text-slate-400 font-medium">Action</th>
              <th className="text-left p-4 text-slate-400 font-medium">Actor</th>
              <th className="text-left p-4 text-slate-400 font-medium">Target</th>
              <th className="text-left p-4 text-slate-400 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {logs?.log?.map((entry: any, i: number) => (
              <tr key={i} className="border-b border-slate-700 last:border-0 hover:bg-slate-700/50">
                <td className="p-4 text-sm text-slate-400">
                  {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                </td>
                <td className="p-4 text-sm font-medium">{entry.credential_name}</td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded text-xs ${actionColors[entry.action] || 'text-slate-400 bg-slate-500/20'}`}>
                    {entry.action}
                  </span>
                </td>
                <td className="p-4 text-sm text-slate-300">{entry.actor}</td>
                <td className="p-4 text-sm text-slate-400">{entry.target || '-'}</td>
                <td className="p-4">
                  {entry.success ? (
                    <span className="text-green-400 text-sm">✓</span>
                  ) : (
                    <span className="text-red-400 text-sm" title={entry.error_message}>✗</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {logs?.log?.length === 0 && (
          <div className="p-8 text-center text-slate-500">
            No audit entries found
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## PART 7: COUNCIL UI (Frontend Only - Backend Already Built)

Use the council UI components from the previous spec - CONVENER V2 is already deployed at port 8300.

The frontend pages remain the same:
- `/council` - Council hub
- `/council/new` - Create meeting  
- `/council/[id]` - Active meeting room

---

## PART 8: DEPLOYMENT

### 8.1 Build
```bash
cd /opt/leveredge/ui/command-center
npm run build
```

### 8.2 Caddy Configuration
```caddyfile
command.leveredgeai.com {
    reverse_proxy localhost:3000
    encode gzip
}
```

### 8.3 Systemd Services

**Command Center:**
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

**AEGIS V2:**
```bash
# /etc/systemd/system/leveredge-aegis-v2.service
[Unit]
Description=LeverEdge AEGIS V2 Credential Manager
After=network.target

[Service]
Type=simple
User=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/aegis
ExecStart=/usr/bin/python3 -m uvicorn aegis_v2:app --host 0.0.0.0 --port 8012
Restart=always
Environment=PYTHONPATH=/opt/leveredge/shared/lib

[Install]
WantedBy=multi-user.target
```

### 8.4 Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable leveredge-command-center leveredge-aegis-v2
sudo systemctl start leveredge-command-center leveredge-aegis-v2
```

---

## PART 9: N8N WORKFLOWS FOR AEGIS

### 9.1 AEGIS Health Monitor (Hourly)
Create in n8n-control:
- Trigger: Cron `0 * * * *`
- HTTP Request: GET http://localhost:8012/health/check-all
- IF: Any unhealthy → HERMES notify
- IF: Any expiring → HERMES notify

### 9.2 AEGIS Rotation Scheduler (Hourly)
Create in n8n-control:
- Trigger: Cron `30 * * * *`
- HTTP Request: POST http://localhost:8012/rotation/run-scheduled
- IF: Any failures → HERMES notify (critical)

### 9.3 AEGIS Daily Report
Create in n8n-control:
- Trigger: Cron `0 8 * * *`
- HTTP Request: GET http://localhost:8012/health/dashboard
- Format summary
- HERMES: Send daily status

---

## PART 10: UPGRADE PLAN

After everything is deployed and functional, upgrade in this order:

### Phase 1: Core Infrastructure (Week 1)
1. [ ] AEGIS V2 - Database migration
2. [ ] AEGIS V2 - FastAPI deployment
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

### Phase 4: AEGIS Full Integration (Week 4)
1. [ ] Import all existing n8n credentials
2. [ ] Add non-n8n credentials (Caddy, env vars)
3. [ ] Set up rotation schedules
4. [ ] Configure expiry alerts
5. [ ] Test health checks for all providers

### Phase 5: Council UI + Polish
1. [ ] Council meeting frontend connected to CONVENER
2. [ ] Test full meeting flow
3. [ ] End-to-end verification

### Phase 6: Visual Upgrades (Post-Functional)
*See PINNED-VISUAL-UPGRADES.md*

---

## COMPLETION CHECKLIST

After each major part, commit progress:

```bash
cd /opt/leveredge
git add .
git commit -m "GSD: [Part N] - description"
```

At the end:
1. Run full health check
2. Notify HERMES with summary
3. Update LOOSE-ENDS.md
4. Log to aria_knowledge

---

## NOTIFICATION ON COMPLETION

```bash
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "message": "🏛️ MEGA BUILD COMPLETE!\n\n✅ Command Center UI\n✅ 8 domain dashboards\n✅ 40+ agent pages\n✅ AEGIS V2 credential vault\n✅ Council meeting UI\n\nAll systems operational.",
    "priority": "high"
  }'
```

---

*End of MEGA GSD*
*Function first. Beauty later. Ship it.*
