# GSD: LITTLEFINGER - Master of Coin

**Priority:** HIGH
**Estimated Time:** 6-8 hours
**Port:** 8020
**Domain:** CHANCERY

---

## IDENTITY

**Name:** LITTLEFINGER
**Title:** Master of Coin
**Tagline:** "Chaos isn't a pit. Chaos is a ladder. And money? Money is the rungs."

LITTLEFINGER manages all financial operations. Invoicing, expenses, revenue tracking, MRR monitoring. He knows where every dollar comes from and where it goes.

**Personality:**
- **Calculating** - Everything is a transaction with ROI
- **Meticulous** - Tracks every penny
- **Ambitious** - Always eyes on the $30K MRR goal
- **Opportunistic** - Spots financial optimizations

**Voice:**
> "At your current trajectory, you'll hit $30K MRR by March 15th. But I see three optimizations that could accelerate that by two weeks."

> "The Anthropic invoice is overdue by 3 days. Shall I send a gentle reminder, or something more... persuasive?"

> "Your expense ratio is 12%. Industry average is 25%. You're running lean. Perhaps too lean. Some investments now could yield 10x returns."

---

## RESPONSIBILITIES

### 1. Client Management
- Client records
- Billing details
- Payment terms
- Contact information

### 2. Invoicing
- Generate invoices
- Track payment status
- Send reminders
- Record payments

### 3. Expense Tracking
- Categorize expenses
- Track subscriptions
- Monitor recurring costs
- Receipt management

### 4. Revenue Management
- Track all revenue
- Calculate MRR
- Project revenue
- Goal tracking

### 5. Financial Reporting
- P&L statements
- Cash flow
- Runway calculations
- Tax prep data

---

## DATABASE SCHEMA

```sql
-- ============================================================
-- LITTLEFINGER: Master of Coin
-- Database Schema
-- ============================================================

-- Clients
CREATE TABLE IF NOT EXISTS littlefinger_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL,
    company TEXT,
    email TEXT,
    phone TEXT,
    
    billing_address TEXT,
    billing_email TEXT,
    
    payment_terms INTEGER DEFAULT 30,  -- Net 30, Net 15, etc.
    default_hourly_rate DECIMAL(10,2),
    default_project_rate DECIMAL(10,2),
    
    tax_id TEXT,
    notes TEXT,
    
    status TEXT DEFAULT 'active' CHECK (status IN ('prospect', 'active', 'inactive', 'churned')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices
CREATE TABLE IF NOT EXISTS littlefinger_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    invoice_number TEXT NOT NULL UNIQUE,
    client_id UUID REFERENCES littlefinger_clients(id),
    project_id UUID,  -- Reference to magnus_projects
    
    status TEXT DEFAULT 'draft' CHECK (status IN (
        'draft', 'sent', 'viewed', 'partial', 'paid', 'overdue', 'cancelled', 'refunded'
    )),
    
    -- Dates
    issue_date DATE DEFAULT CURRENT_DATE,
    due_date DATE,
    sent_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    
    -- Amounts
    subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(12,2) DEFAULT 0,
    discount_reason TEXT,
    tax_rate DECIMAL(5,2) DEFAULT 0,
    tax_amount DECIMAL(12,2) DEFAULT 0,
    total DECIMAL(12,2) NOT NULL DEFAULT 0,
    
    amount_paid DECIMAL(12,2) DEFAULT 0,
    amount_due DECIMAL(12,2) GENERATED ALWAYS AS (total - amount_paid) STORED,
    
    -- Details
    line_items JSONB DEFAULT '[]',
    notes TEXT,
    terms TEXT,
    
    -- Payment info
    payment_method TEXT,
    payment_reference TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoice line items (for detailed tracking)
CREATE TABLE IF NOT EXISTS littlefinger_invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES littlefinger_invoices(id) ON DELETE CASCADE,
    
    description TEXT NOT NULL,
    quantity DECIMAL(10,2) DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    amount DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    
    task_id UUID,  -- Reference to magnus_tasks if billing for specific work
    
    sort_order INTEGER DEFAULT 0
);

-- Expenses
CREATE TABLE IF NOT EXISTS littlefinger_expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    category TEXT NOT NULL CHECK (category IN (
        'software', 'hosting', 'tools', 'marketing', 'advertising',
        'contractor', 'education', 'equipment', 'travel', 
        'office', 'legal', 'insurance', 'taxes', 'other'
    )),
    
    vendor TEXT NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    
    expense_date DATE DEFAULT CURRENT_DATE,
    
    -- Recurring
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_interval TEXT CHECK (recurring_interval IN ('weekly', 'monthly', 'quarterly', 'yearly')),
    next_occurrence DATE,
    
    -- Tracking
    receipt_url TEXT,
    tax_deductible BOOLEAN DEFAULT TRUE,
    reimbursable BOOLEAN DEFAULT FALSE,
    reimbursed BOOLEAN DEFAULT FALSE,
    
    -- Allocation
    client_id UUID REFERENCES littlefinger_clients(id),
    project_id UUID,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Revenue entries
CREATE TABLE IF NOT EXISTS littlefinger_revenue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    source_type TEXT NOT NULL CHECK (source_type IN (
        'project', 'retainer', 'hourly', 'consulting', 'product', 'other'
    )),
    
    client_id UUID REFERENCES littlefinger_clients(id),
    invoice_id UUID REFERENCES littlefinger_invoices(id),
    project_id UUID,
    
    description TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    revenue_date DATE DEFAULT CURRENT_DATE,
    
    -- Recurring revenue
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_interval TEXT CHECK (recurring_interval IN ('weekly', 'monthly', 'quarterly', 'yearly')),
    mrr_amount DECIMAL(12,2),  -- Monthly equivalent
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Monthly financial summary
CREATE TABLE IF NOT EXISTS littlefinger_monthly_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    month_year TEXT NOT NULL UNIQUE,  -- '2026-01', '2026-02', etc.
    
    -- Revenue
    total_revenue DECIMAL(12,2) DEFAULT 0,
    recurring_revenue DECIMAL(12,2) DEFAULT 0,
    project_revenue DECIMAL(12,2) DEFAULT 0,
    other_revenue DECIMAL(12,2) DEFAULT 0,
    
    -- Expenses
    total_expenses DECIMAL(12,2) DEFAULT 0,
    fixed_expenses DECIMAL(12,2) DEFAULT 0,
    variable_expenses DECIMAL(12,2) DEFAULT 0,
    
    -- Calculated
    gross_profit DECIMAL(12,2) GENERATED ALWAYS AS (total_revenue - total_expenses) STORED,
    profit_margin DECIMAL(5,2),
    
    -- Invoicing
    invoices_sent INTEGER DEFAULT 0,
    invoices_paid INTEGER DEFAULT 0,
    invoices_overdue INTEGER DEFAULT 0,
    outstanding_amount DECIMAL(12,2) DEFAULT 0,
    
    -- MRR tracking
    mrr_start DECIMAL(12,2) DEFAULT 0,
    mrr_end DECIMAL(12,2) DEFAULT 0,
    mrr_growth DECIMAL(12,2) DEFAULT 0,
    
    -- Clients
    new_clients INTEGER DEFAULT 0,
    churned_clients INTEGER DEFAULT 0,
    total_clients INTEGER DEFAULT 0,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Financial goals
CREATE TABLE IF NOT EXISTS littlefinger_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    goal_type TEXT NOT NULL CHECK (goal_type IN (
        'mrr', 'revenue', 'clients', 'profit', 'savings'
    )),
    
    name TEXT NOT NULL,
    target_value DECIMAL(12,2) NOT NULL,
    current_value DECIMAL(12,2) DEFAULT 0,
    
    target_date DATE,
    
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'achieved', 'missed', 'abandoned')),
    achieved_at TIMESTAMPTZ,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions tracking
CREATE TABLE IF NOT EXISTS littlefinger_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL,
    vendor TEXT NOT NULL,
    
    amount DECIMAL(10,2) NOT NULL,
    billing_interval TEXT CHECK (billing_interval IN ('monthly', 'yearly')),
    monthly_equivalent DECIMAL(10,2),
    
    category TEXT,
    
    start_date DATE,
    next_billing_date DATE,
    
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'paused')),
    cancellation_date DATE,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_littlefinger_invoices_client ON littlefinger_invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_littlefinger_invoices_status ON littlefinger_invoices(status);
CREATE INDEX IF NOT EXISTS idx_littlefinger_expenses_category ON littlefinger_expenses(category);
CREATE INDEX IF NOT EXISTS idx_littlefinger_expenses_date ON littlefinger_expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_littlefinger_revenue_date ON littlefinger_revenue(revenue_date);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Calculate current MRR
CREATE OR REPLACE FUNCTION littlefinger_current_mrr()
RETURNS DECIMAL AS $$
    SELECT COALESCE(SUM(
        CASE 
            WHEN recurring_interval = 'yearly' THEN amount / 12
            WHEN recurring_interval = 'quarterly' THEN amount / 3
            WHEN recurring_interval = 'monthly' THEN amount
            WHEN recurring_interval = 'weekly' THEN amount * 4.33
            ELSE 0
        END
    ), 0)
    FROM littlefinger_revenue
    WHERE is_recurring = TRUE;
$$ LANGUAGE SQL;

-- Get financial snapshot
CREATE OR REPLACE FUNCTION littlefinger_snapshot()
RETURNS TABLE (
    mrr DECIMAL,
    revenue_mtd DECIMAL,
    expenses_mtd DECIMAL,
    outstanding DECIMAL,
    active_clients BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        littlefinger_current_mrr(),
        COALESCE((SELECT SUM(amount) FROM littlefinger_revenue WHERE revenue_date >= DATE_TRUNC('month', CURRENT_DATE)), 0),
        COALESCE((SELECT SUM(amount) FROM littlefinger_expenses WHERE expense_date >= DATE_TRUNC('month', CURRENT_DATE)), 0),
        COALESCE((SELECT SUM(amount_due) FROM littlefinger_invoices WHERE status IN ('sent', 'viewed', 'partial', 'overdue')), 0),
        (SELECT COUNT(*) FROM littlefinger_clients WHERE status = 'active');
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- SEED DATA
-- ============================================================

-- Current subscriptions
INSERT INTO littlefinger_subscriptions (name, vendor, amount, billing_interval, monthly_equivalent, category, status) VALUES
('Claude Max', 'Anthropic', 200.00, 'monthly', 200.00, 'software', 'active'),
('Contabo VPS', 'Contabo', 15.00, 'monthly', 15.00, 'hosting', 'active'),
('Bolt.new', 'StackBlitz', 20.00, 'monthly', 20.00, 'tools', 'active'),
('Cloudflare', 'Cloudflare', 0.00, 'monthly', 0.00, 'hosting', 'active')
ON CONFLICT DO NOTHING;

-- Primary goal
INSERT INTO littlefinger_goals (goal_type, name, target_value, target_date, current_value) VALUES
('mrr', '$30K MRR by March', 30000.00, '2026-03-01', 0.00)
ON CONFLICT DO NOTHING;
```

---

## LITTLEFINGER SERVICE

Create `/opt/leveredge/control-plane/agents/littlefinger/littlefinger.py`:

```python
"""
LITTLEFINGER - Master of Coin
Port: 8020
Domain: CHANCERY

Chaos isn't a pit. Chaos is a ladder. And money? Money is the rungs.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
import os
import asyncpg
import httpx

app = FastAPI(
    title="LITTLEFINGER - Master of Coin",
    description="Chaos isn't a pit. Chaos is a ladder. And money? Money is the rungs.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()

# ============ MODELS ============

class ClientCreate(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    payment_terms: int = 30
    default_hourly_rate: Optional[float] = None

class InvoiceCreate(BaseModel):
    client_id: str
    line_items: List[Dict[str, Any]]
    notes: Optional[str] = None
    due_days: int = 30

class ExpenseCreate(BaseModel):
    category: str
    vendor: str
    description: str
    amount: float
    expense_date: Optional[date] = None
    is_recurring: bool = False
    recurring_interval: Optional[str] = None
    tax_deductible: bool = True

class RevenueCreate(BaseModel):
    source_type: str
    description: str
    amount: float
    client_id: Optional[str] = None
    is_recurring: bool = False
    recurring_interval: Optional[str] = None

# ============ HEALTH ============

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "LITTLEFINGER - Master of Coin",
        "port": 8020,
        "tagline": "Chaos isn't a pit. Chaos is a ladder. And money? Money is the rungs."
    }

# ============ DASHBOARD ============

@app.get("/status")
async def financial_status():
    """Get complete financial status"""
    async with pool.acquire() as conn:
        snapshot = await conn.fetchrow("SELECT * FROM littlefinger_snapshot()")
        
        # Get goal progress
        goal = await conn.fetchrow("""
            SELECT name, target_value, current_value, target_date
            FROM littlefinger_goals
            WHERE status = 'active' AND goal_type = 'mrr'
            ORDER BY target_date
            LIMIT 1
        """)
        
        # Recent invoices
        invoices = await conn.fetch("""
            SELECT i.invoice_number, c.name as client, i.total, i.status, i.due_date
            FROM littlefinger_invoices i
            LEFT JOIN littlefinger_clients c ON i.client_id = c.id
            WHERE i.status NOT IN ('paid', 'cancelled')
            ORDER BY i.due_date
            LIMIT 5
        """)
        
        # Monthly expenses
        subscriptions = await conn.fetchrow("""
            SELECT SUM(monthly_equivalent) as total
            FROM littlefinger_subscriptions
            WHERE status = 'active'
        """)
        
        goal_progress = 0
        if goal and goal['target_value'] > 0:
            goal_progress = (snapshot['mrr'] / goal['target_value']) * 100
        
        return {
            "mrr": float(snapshot['mrr']),
            "revenue_mtd": float(snapshot['revenue_mtd']),
            "expenses_mtd": float(snapshot['expenses_mtd']),
            "profit_mtd": float(snapshot['revenue_mtd'] - snapshot['expenses_mtd']),
            "outstanding": float(snapshot['outstanding']),
            "active_clients": snapshot['active_clients'],
            "monthly_subscriptions": float(subscriptions['total'] or 0),
            "goal": dict(goal) if goal else None,
            "goal_progress_pct": round(goal_progress, 1),
            "pending_invoices": [dict(i) for i in invoices],
            "littlefinger_says": generate_status_quote(snapshot, goal)
        }

def generate_status_quote(snapshot, goal):
    """Generate LITTLEFINGER's status quote"""
    mrr = float(snapshot['mrr'])
    
    if mrr == 0:
        return "The coffers are empty. Time to change that. Every great fortune starts with the first coin."
    elif goal and mrr >= goal['target_value']:
        return f"We've reached ${mrr:,.0f} MRR. The goal is achieved. But why stop here?"
    elif goal:
        remaining = goal['target_value'] - mrr
        return f"${remaining:,.0f} to go before we hit our target. The ladder awaits."
    else:
        return f"Current MRR: ${mrr:,.0f}. Every coin counts."

# ============ CLIENTS ============

@app.get("/clients")
async def list_clients(status: str = None):
    """List all clients"""
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM littlefinger_clients WHERE status = $1 ORDER BY name",
                status
            )
        else:
            rows = await conn.fetch("SELECT * FROM littlefinger_clients ORDER BY name")
        return [dict(row) for row in rows]

@app.post("/clients")
async def create_client(client: ClientCreate):
    """Create new client"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO littlefinger_clients (name, company, email, payment_terms, default_hourly_rate)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, client.name, client.company, client.email, 
            client.payment_terms, client.default_hourly_rate)
        return dict(row)

# ============ INVOICES ============

@app.get("/invoices")
async def list_invoices(status: str = None, client_id: str = None):
    """List invoices"""
    async with pool.acquire() as conn:
        query = """
            SELECT i.*, c.name as client_name
            FROM littlefinger_invoices i
            LEFT JOIN littlefinger_clients c ON i.client_id = c.id
            WHERE 1=1
        """
        params = []
        
        if status:
            params.append(status)
            query += f" AND i.status = ${len(params)}"
        if client_id:
            params.append(client_id)
            query += f" AND i.client_id = ${len(params)}"
        
        query += " ORDER BY i.issue_date DESC"
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.post("/invoices")
async def create_invoice(invoice: InvoiceCreate):
    """Create new invoice"""
    async with pool.acquire() as conn:
        # Generate invoice number
        count = await conn.fetchval("SELECT COUNT(*) FROM littlefinger_invoices")
        invoice_number = f"INV-{date.today().year}-{count + 1:04d}"
        
        # Calculate totals
        subtotal = sum(item.get('quantity', 1) * item.get('unit_price', 0) for item in invoice.line_items)
        
        due_date = date.today() + timedelta(days=invoice.due_days)
        
        row = await conn.fetchrow("""
            INSERT INTO littlefinger_invoices 
            (invoice_number, client_id, line_items, subtotal, total, due_date, notes)
            VALUES ($1, $2, $3, $4, $4, $5, $6)
            RETURNING *
        """, invoice_number, invoice.client_id, invoice.line_items,
            subtotal, due_date, invoice.notes)
        
        return dict(row)

@app.post("/invoices/{invoice_id}/send")
async def send_invoice(invoice_id: str):
    """Mark invoice as sent"""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE littlefinger_invoices 
            SET status = 'sent', sent_at = NOW()
            WHERE id = $1
        """, invoice_id)
        return {"status": "sent"}

@app.post("/invoices/{invoice_id}/paid")
async def mark_invoice_paid(invoice_id: str, amount: float = None, payment_method: str = None):
    """Mark invoice as paid"""
    async with pool.acquire() as conn:
        invoice = await conn.fetchrow("SELECT * FROM littlefinger_invoices WHERE id = $1", invoice_id)
        
        paid_amount = amount or invoice['total']
        new_status = 'paid' if paid_amount >= invoice['total'] else 'partial'
        
        await conn.execute("""
            UPDATE littlefinger_invoices 
            SET status = $2, amount_paid = amount_paid + $3, paid_at = NOW(), payment_method = $4
            WHERE id = $1
        """, invoice_id, new_status, paid_amount, payment_method)
        
        # Record revenue
        await conn.execute("""
            INSERT INTO littlefinger_revenue (source_type, description, amount, client_id, invoice_id)
            VALUES ('project', $2, $3, $4, $1)
        """, invoice_id, f"Invoice {invoice['invoice_number']}", paid_amount, invoice['client_id'])
        
        # Update MRR goal tracking
        await update_mrr_goal(conn)
        
        return {"status": new_status, "amount_paid": paid_amount}

# ============ EXPENSES ============

@app.get("/expenses")
async def list_expenses(category: str = None, month: str = None):
    """List expenses"""
    async with pool.acquire() as conn:
        query = "SELECT * FROM littlefinger_expenses WHERE 1=1"
        params = []
        
        if category:
            params.append(category)
            query += f" AND category = ${len(params)}"
        if month:  # Format: '2026-01'
            params.append(month)
            query += f" AND TO_CHAR(expense_date, 'YYYY-MM') = ${len(params)}"
        
        query += " ORDER BY expense_date DESC"
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.post("/expenses")
async def add_expense(expense: ExpenseCreate):
    """Add expense"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO littlefinger_expenses 
            (category, vendor, description, amount, expense_date, is_recurring, recurring_interval, tax_deductible)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """, expense.category, expense.vendor, expense.description,
            expense.amount, expense.expense_date or date.today(),
            expense.is_recurring, expense.recurring_interval, expense.tax_deductible)
        return dict(row)

# ============ REVENUE ============

@app.get("/revenue")
async def list_revenue(month: str = None, source_type: str = None):
    """List revenue"""
    async with pool.acquire() as conn:
        query = """
            SELECT r.*, c.name as client_name
            FROM littlefinger_revenue r
            LEFT JOIN littlefinger_clients c ON r.client_id = c.id
            WHERE 1=1
        """
        params = []
        
        if month:
            params.append(month)
            query += f" AND TO_CHAR(r.revenue_date, 'YYYY-MM') = ${len(params)}"
        if source_type:
            params.append(source_type)
            query += f" AND r.source_type = ${len(params)}"
        
        query += " ORDER BY r.revenue_date DESC"
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.post("/revenue")
async def add_revenue(revenue: RevenueCreate):
    """Add revenue entry"""
    async with pool.acquire() as conn:
        # Calculate MRR if recurring
        mrr_amount = None
        if revenue.is_recurring:
            if revenue.recurring_interval == 'monthly':
                mrr_amount = revenue.amount
            elif revenue.recurring_interval == 'yearly':
                mrr_amount = revenue.amount / 12
            elif revenue.recurring_interval == 'quarterly':
                mrr_amount = revenue.amount / 3
        
        row = await conn.fetchrow("""
            INSERT INTO littlefinger_revenue 
            (source_type, description, amount, client_id, is_recurring, recurring_interval, mrr_amount)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, revenue.source_type, revenue.description, revenue.amount,
            revenue.client_id, revenue.is_recurring, revenue.recurring_interval, mrr_amount)
        
        await update_mrr_goal(conn)
        
        return dict(row)

# ============ MRR ============

@app.get("/mrr")
async def get_mrr():
    """Get MRR breakdown"""
    async with pool.acquire() as conn:
        total_mrr = await conn.fetchval("SELECT littlefinger_current_mrr()")
        
        breakdown = await conn.fetch("""
            SELECT source_type, 
                   SUM(CASE 
                       WHEN recurring_interval = 'yearly' THEN amount / 12
                       WHEN recurring_interval = 'quarterly' THEN amount / 3
                       WHEN recurring_interval = 'monthly' THEN amount
                       ELSE 0
                   END) as mrr
            FROM littlefinger_revenue
            WHERE is_recurring = TRUE
            GROUP BY source_type
        """)
        
        return {
            "total_mrr": float(total_mrr or 0),
            "breakdown": [dict(b) for b in breakdown],
            "target": 30000,
            "progress_pct": round((float(total_mrr or 0) / 30000) * 100, 1)
        }

# ============ SUBSCRIPTIONS ============

@app.get("/subscriptions")
async def list_subscriptions():
    """List active subscriptions"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM littlefinger_subscriptions
            WHERE status = 'active'
            ORDER BY monthly_equivalent DESC
        """)
        
        total = sum(row['monthly_equivalent'] or 0 for row in rows)
        
        return {
            "subscriptions": [dict(row) for row in rows],
            "total_monthly": float(total)
        }

# ============ GOALS ============

@app.get("/goals")
async def list_goals():
    """List financial goals"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM littlefinger_goals
            WHERE status = 'active'
            ORDER BY target_date
        """)
        return [dict(row) for row in rows]

@app.post("/goals")
async def create_goal(goal_type: str, name: str, target_value: float, target_date: date):
    """Create financial goal"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO littlefinger_goals (goal_type, name, target_value, target_date)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """, goal_type, name, target_value, target_date)
        return dict(row)

async def update_mrr_goal(conn):
    """Update MRR goal progress"""
    current_mrr = await conn.fetchval("SELECT littlefinger_current_mrr()")
    await conn.execute("""
        UPDATE littlefinger_goals 
        SET current_value = $1
        WHERE goal_type = 'mrr' AND status = 'active'
    """, current_mrr)

# ============ REPORTS ============

@app.get("/report/monthly/{month}")
async def monthly_report(month: str):
    """Get monthly P&L report"""
    async with pool.acquire() as conn:
        revenue = await conn.fetchrow("""
            SELECT 
                COALESCE(SUM(amount), 0) as total,
                COALESCE(SUM(amount) FILTER (WHERE is_recurring), 0) as recurring,
                COALESCE(SUM(amount) FILTER (WHERE NOT is_recurring), 0) as one_time
            FROM littlefinger_revenue
            WHERE TO_CHAR(revenue_date, 'YYYY-MM') = $1
        """, month)
        
        expenses = await conn.fetchrow("""
            SELECT 
                COALESCE(SUM(amount), 0) as total,
                COALESCE(SUM(amount) FILTER (WHERE is_recurring), 0) as recurring,
                COALESCE(SUM(amount) FILTER (WHERE NOT is_recurring), 0) as one_time
            FROM littlefinger_expenses
            WHERE TO_CHAR(expense_date, 'YYYY-MM') = $1
        """, month)
        
        expense_breakdown = await conn.fetch("""
            SELECT category, SUM(amount) as amount
            FROM littlefinger_expenses
            WHERE TO_CHAR(expense_date, 'YYYY-MM') = $1
            GROUP BY category
            ORDER BY amount DESC
        """, month)
        
        return {
            "month": month,
            "revenue": {
                "total": float(revenue['total']),
                "recurring": float(revenue['recurring']),
                "one_time": float(revenue['one_time'])
            },
            "expenses": {
                "total": float(expenses['total']),
                "recurring": float(expenses['recurring']),
                "one_time": float(expenses['one_time']),
                "by_category": [dict(e) for e in expense_breakdown]
            },
            "profit": float(revenue['total'] - expenses['total']),
            "margin_pct": round((float(revenue['total'] - expenses['total']) / float(revenue['total'] or 1)) * 100, 1)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
```

---

## DOCKERFILE

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY littlefinger.py .

EXPOSE 8020

CMD ["uvicorn", "littlefinger:app", "--host", "0.0.0.0", "--port", "8020"]
```

---

## MCP TOOLS

```python
@mcp_tool(name="littlefinger_status")
async def littlefinger_status() -> dict:
    """Get financial status from LITTLEFINGER"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8020/status")
        return response.json()

@mcp_tool(name="littlefinger_mrr")
async def littlefinger_mrr() -> dict:
    """Get MRR breakdown"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8020/mrr")
        return response.json()

@mcp_tool(name="littlefinger_add_expense")
async def littlefinger_add_expense(category: str, vendor: str, description: str, amount: float) -> dict:
    """Add expense"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8020/expenses",
            json={"category": category, "vendor": vendor, "description": description, "amount": amount}
        )
        return response.json()

@mcp_tool(name="littlefinger_subscriptions")
async def littlefinger_subscriptions() -> dict:
    """Get active subscriptions"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8020/subscriptions")
        return response.json()

@mcp_tool(name="littlefinger_create_invoice")
async def littlefinger_create_invoice(client_id: str, line_items: list, due_days: int = 30) -> dict:
    """Create invoice"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8020/invoices",
            json={"client_id": client_id, "line_items": line_items, "due_days": due_days}
        )
        return response.json()
```

---

## CADDY

```
littlefinger.leveredgeai.com {
    reverse_proxy localhost:8020
}
```

---

## BUILD & RUN

```bash
# Create migration
psql $DEV_DATABASE_URL -f /opt/leveredge/database/migrations/20260119_littlefinger_schema.sql

# Build
cd /opt/leveredge/control-plane/agents/littlefinger
docker build -t littlefinger:dev .

# Run
docker run -d --name littlefinger \
  --network leveredge-network \
  -p 8020:8020 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  littlefinger:dev

# Verify
curl http://localhost:8020/health
curl http://localhost:8020/status
curl http://localhost:8020/mrr
curl http://localhost:8020/subscriptions
```

---

## GIT COMMIT

```bash
git add .
git commit -m "LITTLEFINGER: Master of Coin

- Client management
- Invoice generation and tracking
- Expense tracking with categories
- Revenue and MRR tracking
- Subscription management
- Monthly P&L reports
- Goal tracking ($30K MRR target)
- MCP tools for HEPHAESTUS

Chaos is a ladder. Money is the rungs."
```

---

*"The coffers await their first coins. Let's fill them."*
