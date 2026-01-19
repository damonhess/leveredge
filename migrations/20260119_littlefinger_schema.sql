-- ============================================================
-- LITTLEFINGER: Master of Coin
-- Database Schema
-- Created: 2026-01-19
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

-- ============================================================
-- Complete
-- ============================================================
