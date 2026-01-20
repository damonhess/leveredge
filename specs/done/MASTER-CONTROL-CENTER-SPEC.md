# MASTER CONTROL CENTER - Build Specification
*Created: January 17, 2026*
*Status: APPROVED FOR BUILD*

## Overview

| Attribute | Value |
|-----------|-------|
| **Name** | LeverEdge Master Control Center |
| **Purpose** | Central hub to access all domain dashboards, view system health, key business metrics |
| **Theme** | Technomantic Bridge - sci-fi command bridge meets wizard's tower |
| **URL** | command.leveredgeai.com |
| **Tech Stack** | Next.js 14 + TypeScript + Tailwind + Framer Motion + Three.js (optional for 3D) |

---

## Design Philosophy

The Master Control Center is where Damon stands at the nexus of his entire system. It should feel:

1. **Powerful** - You are in command of a sophisticated AI agent fleet
2. **Mystical** - Technology that feels like magic
3. **Clear** - Despite the aesthetic, information is instantly readable
4. **Alive** - Subtle animations show the system is breathing, working

---

## Color Palette

```typescript
const colors = {
  // Backgrounds
  void: '#0a0e27',        // Deep space - main background
  voidLight: '#111936',   // Slightly lighter for cards
  
  // Primary energy
  aether: '#00d4ff',      // Cyan - primary accent, energy lines
  aetherGlow: '#00d4ff33', // Cyan with transparency for glows
  
  // Secondary mystical  
  arcane: '#8b5cf6',      // Purple - secondary accent
  arcaneGlow: '#8b5cf633', // Purple glow
  
  // Highlights
  relic: '#fbbf24',       // Gold - important highlights, money
  relicGlow: '#fbbf2433', // Gold glow
  
  // Status
  life: '#22c55e',        // Green - healthy
  ember: '#ef4444',       // Red - alert/error
  caution: '#f59e0b',     // Amber - warning
  
  // Text
  textPrimary: '#f8fafc',   // White
  textSecondary: '#94a3b8', // Muted
  textAccent: '#00d4ff',    // Cyan for emphasis
}
```

---

## Typography

```typescript
const typography = {
  fontFamily: {
    display: '"Orbitron", sans-serif',     // Headings - techy
    body: '"Inter", sans-serif',            // Body - readable
    mono: '"JetBrains Mono", monospace',    // Data/numbers
  },
  sizes: {
    hero: '2.5rem',      // Main title
    h1: '1.875rem',      // Section headers
    h2: '1.5rem',        // Card titles
    body: '1rem',        // Regular text
    small: '0.875rem',   // Secondary info
    tiny: '0.75rem',     // Labels
  }
}
```

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ TOP METRICS BAR (fixed, 60px height)                                 │
│ Revenue Progress | Portfolio Value | Days to Launch | System Status │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  MAIN CONTENT AREA (centered, max-width 1400px)                     │
│                                                                      │
│     ┌─────────┐        ┌─────────┐        ┌─────────┐              │
│     │  GAIA   │        │PANTHEON │        │SENTINELS│              │
│     │   🌋    │        │    ⚡    │        │   🦅    │              │
│     └─────────┘        └─────────┘        └─────────┘              │
│                                                                      │
│  ┌─────────┐    ┌───────────────────────┐    ┌─────────┐           │
│  │  SHIRE  │    │                       │    │  KEEP   │           │
│  │   🏡    │    │     CENTRAL HUB       │    │   ⚔️    │           │
│  └─────────┘    │                       │    └─────────┘           │
│                 │   ● System Heartbeat   │                          │
│  ┌─────────┐    │   📡 Agent Activity    │    ┌─────────┐           │
│  │ ALCHEMY │    │   ✨ ARIA Whisper      │    │CHANCERY │           │
│  │   ⚗️    │    │                       │    │   📜    │           │
│  └─────────┘    └───────────────────────┘    └─────────┘           │
│                                                                      │
│           ┌─────────┐              ┌─────────┐                      │
│           │  ARIA   │              │  VARYS  │                      │
│           │   ✨    │              │   🕷️    │                      │
│           └─────────┘              └─────────┘                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

VARYS OVERLAY (slides from right when V pressed)
┌──────────────────────────────────────┐
│  🕷️ VARYS - Master of Whisperers     │
│                                      │
│  Portfolio Intelligence              │
│  ├─ Total Value: $58.5K - $117K     │
│  ├─ Wins: 28                         │
│  ├─ Pipeline: 3 prospects            │
│  └─ Confidence: High                 │
│                                      │
│  Recent Intel                        │
│  "Compliance sector showing          │
│   increased demand for AI agents..." │
│                                      │
│  [View Full Intelligence →]          │
└──────────────────────────────────────┘
```

---

## Component Specifications

### 1. TopMetricsBar

**Purpose:** Always-visible key business metrics

**Props:**
```typescript
interface TopMetricsBarProps {
  revenue: { current: number; goal: number };
  portfolio: { low: number; high: number; wins: number };
  daysToLaunch: number;
  systemStatus: 'healthy' | 'warning' | 'error';
}
```

**Visual:**
- Fixed at top, 60px height
- Semi-transparent void background with subtle border
- Four sections with dividers
- Revenue shows progress bar with gold glow
- Portfolio shows range + win count
- Countdown with pulsing urgency as it decreases
- System status as colored dot with tooltip

---

### 2. DomainPortal

**Purpose:** Clickable card that leads to domain dashboard

**Props:**
```typescript
interface DomainPortalProps {
  domain: {
    id: string;
    name: string;
    icon: string;
    theme: string;
    colors: { primary: string; secondary: string; accent: string };
    supervisor: string;
    status: 'online' | 'offline' | 'busy';
    quickStat?: string; // e.g., "3 agents active"
  };
  onClick: () => void;
}
```

**Visual:**
- Hexagonal shape (or rounded hex)
- Size: 140px x 160px
- Background: domain's primary color at 20% opacity
- Border: domain's accent color, subtle glow
- Icon centered, 48px
- Name below icon
- Status indicator dot (top-right)
- Quick stat at bottom (small text)

**Hover:**
- Scale to 1.05
- Glow intensifies
- Background opacity increases to 40%
- Show preview tooltip with more metrics

**Active/Click:**
- Ripple effect in domain color
- Scale briefly to 0.95 then zoom transition

---

### 3. CentralHub

**Purpose:** Show system health, agent activity, ARIA whisper

**Visual:**
- Circular, 280px diameter
- Concentric rings:
  - Outer ring: Agent activity (particles flowing)
  - Middle ring: System status (color-coded)
  - Inner circle: ARIA whisper text
- Slow rotation animation (20s per revolution)
- Breathing glow effect (3.5s cycle)

**Content:**
- Agent activity: Dots representing active agents, flowing clockwise
- System heartbeat: Pulsing ring, color = status
- ARIA whisper: Latest insight or greeting from ARIA, updates periodically

---

### 4. EnergyThreads

**Purpose:** Visual connections between portals and hub

**Visual:**
- SVG paths connecting each portal to central hub
- Stroke: aether color at 30% opacity
- Animated dash pattern flowing toward hub
- Brighten to 60% when that domain has activity

---

### 5. VarysOverlay

**Purpose:** Summon-able intelligence panel

**Trigger:** Press 'V' key anywhere, or click VARYS portal

**Visual:**
- Slides in from right, 400px width
- Dark purple background (#1a1033) with 95% opacity
- Spider web pattern as subtle background texture
- Silver/white text
- Red accent for VARYS icon

**Content:**
```
🕷️ VARYS - Master of Whisperers

PORTFOLIO INTELLIGENCE
├─ Total Value: $58.5K - $117K
├─ Wins: 28
├─ By Tier:
│   ├─ Tier 1: 12 ($6K-$30K)
│   ├─ Tier 2: 10 ($25K-$75K)
│   └─ Tier 3: 6 ($45K-$150K)
└─ Win Rate: 73%

PIPELINE
├─ Active Prospects: 3
├─ Weighted Value: $12K
└─ Next Action: Follow up with [prospect]

LITTLE BIRDS REPORT
"Compliance automation demand up 40% this quarter.
 Your water rights expertise differentiates strongly."

[View Full Dashboard →]
```

---

### 6. StarfieldBackground

**Purpose:** Subtle animated background

**Visual:**
- Canvas or CSS-based star particles
- 50-100 small white dots at varying opacity
- Very slow drift animation
- Parallax effect on mouse move (subtle)
- Performance: Should not impact UI responsiveness

---

## Domain Data

```typescript
const domains = [
  {
    id: 'gaia',
    name: 'GAIA',
    icon: '🌋',
    theme: 'Primordial Creation',
    description: 'Emergency bootstrap, system genesis',
    supervisor: 'GAIA',
    colors: { primary: '#8B4513', secondary: '#FF4500', accent: '#FFD700' },
    position: 'top-left',
  },
  {
    id: 'pantheon',
    name: 'PANTHEON',
    icon: '⚡',
    theme: 'Mount Olympus',
    description: 'Core infrastructure, divine orchestration',
    supervisor: 'ATLAS',
    colors: { primary: '#FFD700', secondary: '#FFFFFF', accent: '#87CEEB' },
    position: 'top-center',
  },
  {
    id: 'sentinels',
    name: 'SENTINELS',
    icon: '🦅',
    theme: 'Mythic Guardians',
    description: 'Security, perimeter defense',
    supervisor: 'GRIFFIN',
    colors: { primary: '#8B0000', secondary: '#2F4F4F', accent: '#FF6347' },
    position: 'top-right',
  },
  {
    id: 'shire',
    name: 'THE SHIRE',
    icon: '🏡',
    theme: 'LOTR Comfort',
    description: 'Personal wellness, cozy growth',
    supervisor: 'GANDALF',
    colors: { primary: '#228B22', secondary: '#8B4513', accent: '#FFD700' },
    position: 'middle-left',
  },
  {
    id: 'keep',
    name: 'THE KEEP',
    icon: '⚔️',
    theme: 'Game of Thrones',
    description: 'Business operations, strategy',
    supervisor: 'TYRION',
    colors: { primary: '#2F4F4F', secondary: '#8B0000', accent: '#C0C0C0' },
    position: 'middle-right',
  },
  {
    id: 'alchemy',
    name: 'ALCHEMY',
    icon: '⚗️',
    theme: 'Mystic Workshop',
    description: 'Creative transformation',
    supervisor: 'CATALYST',
    colors: { primary: '#8B008B', secondary: '#B87333', accent: '#00CED1' },
    position: 'lower-left',
  },
  {
    id: 'chancery',
    name: 'CHANCERY',
    icon: '📜',
    theme: 'Royal Court',
    description: 'Legal, financial advisory',
    supervisor: 'MAGISTRATE',
    colors: { primary: '#4B0082', secondary: '#8B0000', accent: '#FFD700' },
    position: 'lower-right',
  },
  {
    id: 'aria',
    name: 'ARIA SANCTUM',
    icon: '✨',
    theme: 'Ethereal Intelligence',
    description: 'Personal AI, the voice',
    supervisor: 'ARIA',
    colors: { primary: '#00CED1', secondary: '#8B5CF6', accent: '#C0C0C0' },
    position: 'bottom-left',
  },
  {
    id: 'varys',
    name: 'VARYS',
    icon: '🕷️',
    theme: 'Whisper Network',
    description: 'Portfolio intelligence, little birds',
    supervisor: 'VARYS',
    colors: { primary: '#2D1B4E', secondary: '#C0C0C0', accent: '#DC2626' },
    position: 'bottom-right',
  },
];
```

---

## Animations

### Framer Motion Variants

```typescript
const portalVariants = {
  initial: { scale: 1, opacity: 0.8 },
  hover: { 
    scale: 1.05, 
    opacity: 1,
    boxShadow: '0 0 30px var(--domain-accent)',
    transition: { duration: 0.2 }
  },
  tap: { scale: 0.95 },
  enter: {
    scale: [1, 1.1, 0],
    opacity: [1, 1, 0],
    transition: { duration: 0.5 }
  }
};

const hubBreathing = {
  animate: {
    boxShadow: [
      '0 0 20px #00d4ff33',
      '0 0 40px #00d4ff66',
      '0 0 20px #00d4ff33',
    ],
    transition: {
      duration: 3.5,
      repeat: Infinity,
      ease: 'easeInOut'
    }
  }
};

const varysSlide = {
  hidden: { x: '100%', opacity: 0 },
  visible: { 
    x: 0, 
    opacity: 1,
    transition: { type: 'spring', damping: 25 }
  },
  exit: { 
    x: '100%', 
    opacity: 0,
    transition: { duration: 0.2 }
  }
};
```

---

## API Endpoints Needed

The dashboard should fetch real data from:

```typescript
// System health
GET /api/system/health
Response: { status: 'healthy' | 'warning' | 'error', agents: AgentStatus[] }

// Portfolio data (for VARYS)
GET /api/portfolio/summary
Response: { low: number, high: number, wins: number, byTier: TierBreakdown[] }

// Agent activity
GET /api/agents/activity
Response: { active: string[], recent: ActivityLog[] }

// ARIA's latest whisper
GET /api/aria/whisper
Response: { message: string, timestamp: string }

// Metrics
GET /api/metrics/launch
Response: { daysToLaunch: number, revenue: number, goal: number }
```

For MVP, these can return mock data. Real integration later.

---

## File Structure

```
leveredge-command/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                 # Master Control Center
│   ├── globals.css
│   └── [domain]/
│       └── page.tsx             # Domain detail pages (future)
├── components/
│   ├── TopMetricsBar.tsx
│   ├── DomainPortal.tsx
│   ├── CentralHub.tsx
│   ├── EnergyThreads.tsx
│   ├── VarysOverlay.tsx
│   ├── StarfieldBackground.tsx
│   └── ui/                      # Shared UI primitives
│       ├── GlowCard.tsx
│       ├── PulsingDot.tsx
│       └── ProgressBar.tsx
├── lib/
│   ├── domains.ts               # Domain configuration
│   ├── colors.ts                # Color palette
│   ├── api.ts                   # API client
│   └── hooks/
│       ├── useKeyPress.ts       # For V key
│       └── useSystemHealth.ts
├── public/
│   └── fonts/
├── tailwind.config.ts
├── next.config.js
└── package.json
```

---

## Implementation Priority

### Phase 1: Static Layout
1. TopMetricsBar with hardcoded data
2. Domain portals grid (static)
3. Central hub (static)
4. Basic styling and colors

### Phase 2: Interactivity
1. Portal hover effects
2. V key for VARYS overlay
3. Portal click (just logs for now)
4. Breathing animations

### Phase 3: Data Integration
1. Mock API endpoints
2. Real-time system health
3. Portfolio data from Supabase
4. ARIA whisper integration

### Phase 4: Polish
1. Starfield background
2. Energy threads
3. Transition animations
4. Mobile responsiveness

---

## Success Criteria

- [ ] All 9 domain portals visible and styled
- [ ] Top metrics bar shows key data
- [ ] Central hub pulses with system heartbeat
- [ ] V key summons VARYS overlay
- [ ] Hover effects on all interactive elements
- [ ] Looks like a technomantic command center, not a boring dashboard
- [ ] Loads fast, animations smooth (60fps)
- [ ] Works on desktop (mobile later)

---

## Notes

- ARIA should feel present even on this hub - her whisper in the center is key
- VARYS overlay should feel like summoning a shadow advisor
- Energy threads are optional but add significant atmosphere
- Performance matters - don't sacrifice responsiveness for effects
- This is YOUR command center - it should feel powerful

---

*Spec approved by Council design session, January 17, 2026*
