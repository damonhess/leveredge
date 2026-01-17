# LeverEdge Client Portal

A Next.js 14+ application providing a client portal for LeverEdge customers to view projects, invoices, and submit support tickets.

## Tech Stack

- **Framework**: Next.js 14+ with App Router
- **Authentication**: Supabase Auth
- **Database**: Supabase (PostgreSQL)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React

## Prerequisites

- Node.js 18+
- npm or yarn
- Supabase project with the required tables

## Getting Started

### 1. Install Dependencies

```bash
cd /opt/leveredge/client-portal
npm install
```

### 2. Configure Environment Variables

Copy the example environment file and configure your Supabase credentials:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your Supabase project details:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 3. Run the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## Database Schema

The application expects the following tables in Supabase:

### clients
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| name | text | Client name |
| email | text | Client email (matches auth user) |
| company | text | Company name |
| created_at | timestamp | Creation timestamp |

### projects
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| client_id | uuid | Foreign key to clients |
| name | text | Project name |
| status | text | Status (active, in_progress, completed, on_hold, cancelled) |
| created_at | timestamp | Creation timestamp |

### invoices
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| client_id | uuid | Foreign key to clients |
| amount | numeric | Invoice amount |
| status | text | Status (pending, paid, overdue, draft) |
| due_date | date | Payment due date |

### support_tickets
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| client_id | uuid | Foreign key to clients |
| subject | text | Ticket subject |
| message | text | Ticket message |
| status | text | Status (open, in_review, resolved, closed) |
| created_at | timestamp | Creation timestamp |

## Application Structure

```
src/
├── app/
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Login page (/)
│   ├── globals.css        # Global styles
│   ├── dashboard/
│   │   ├── layout.tsx     # Dashboard layout with navigation
│   │   └── page.tsx       # Dashboard overview
│   ├── projects/
│   │   ├── layout.tsx     # Projects layout
│   │   ├── page.tsx       # Projects list
│   │   └── [id]/
│   │       └── page.tsx   # Project detail
│   ├── invoices/
│   │   ├── layout.tsx     # Invoices layout
│   │   └── page.tsx       # Invoice history
│   └── support/
│       ├── layout.tsx     # Support layout
│       └── page.tsx       # Support ticket form
├── components/
│   ├── Navigation.tsx     # Main navigation component
│   └── StatusBadge.tsx    # Status badge component
├── lib/
│   └── supabase/
│       ├── client.ts      # Browser Supabase client
│       ├── server.ts      # Server Supabase client
│       └── types.ts       # TypeScript types for database
└── middleware.ts          # Auth middleware for protected routes
```

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing/login page |
| `/dashboard` | Main client dashboard with overview |
| `/projects` | List of all client projects |
| `/projects/[id]` | Individual project details |
| `/invoices` | Invoice history and payment status |
| `/support` | Support ticket submission form |

## Features

- **Authentication**: Email/password login with Supabase Auth
- **Protected Routes**: Middleware-based route protection
- **Dashboard**: Overview of projects, invoices, and support tickets
- **Projects**: List view with status badges, detail pages
- **Invoices**: Table view with payment status and download placeholders
- **Support**: Ticket submission form with history

## Development

### Build for Production

```bash
npm run build
```

### Start Production Server

```bash
npm start
```

### Lint Code

```bash
npm run lint
```

## Customization

### Styling

The application uses Tailwind CSS with a custom primary color scheme. Modify `tailwind.config.ts` to adjust colors and other theme settings.

### Components

Common components are in `src/components/`. Add new shared components here as needed.

### API Integration

The application uses Supabase client libraries directly. For custom API routes, create them in `src/app/api/`.

## Security Notes

- All authenticated routes are protected by middleware
- Client data is filtered by `client_id` matching the authenticated user
- Row Level Security (RLS) should be enabled on all Supabase tables for production

## Support

For issues or questions, contact the LeverEdge development team.
