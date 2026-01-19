-- ============================================
-- LITTLEFINGER - Master of Coin
-- Port: 8020
-- ============================================

-- Clients
CREATE TABLE IF NOT EXISTS littlefinger_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    email VARCHAR(255),
    payment_terms INTEGER DEFAULT 30,
    default_hourly_rate DECIMAL(15,2),
    notes TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices
CREATE TABLE IF NOT EXISTS littlefinger_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) UNIQUE,
    client_id UUID REFERENCES littlefinger_clients(id),
    issue_date DATE DEFAULT CURRENT_DATE,
    due_date DATE,
    status VARCHAR(50) DEFAULT 'draft',  -- draft, sent, partial, paid, overdue
    subtotal DECIMAL(15,2) DEFAULT 0,
    tax_rate DECIMAL(5,4) DEFAULT 0,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    total DECIMAL(15,2) DEFAULT 0,
    amount_paid DECIMAL(15,2) DEFAULT 0,
    paid_date DATE,
    notes TEXT,
    line_items JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inv_client ON littlefinger_invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_inv_status ON littlefinger_invoices(status);

-- Expenses
CREATE TABLE IF NOT EXISTS littlefinger_expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100) NOT NULL,
    vendor VARCHAR(255),
    description TEXT,
    amount DECIMAL(15,2) NOT NULL,
    expense_date DATE DEFAULT CURRENT_DATE,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_interval VARCHAR(50),
    tax_deductible BOOLEAN DEFAULT TRUE,
    receipt_path TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exp_cat ON littlefinger_expenses(category);
CREATE INDEX IF NOT EXISTS idx_exp_date ON littlefinger_expenses(expense_date);

-- Revenue
CREATE TABLE IF NOT EXISTS littlefinger_revenue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(100) NOT NULL,  -- invoice, subscription, other
    description TEXT,
    amount DECIMAL(15,2) NOT NULL,
    revenue_date DATE DEFAULT CURRENT_DATE,
    client_id UUID REFERENCES littlefinger_clients(id),
    invoice_id UUID REFERENCES littlefinger_invoices(id),
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_interval VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rev_date ON littlefinger_revenue(revenue_date);
CREATE INDEX IF NOT EXISTS idx_rev_type ON littlefinger_revenue(source_type);

-- Subscriptions (recurring expenses)
CREATE TABLE IF NOT EXISTS littlefinger_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    vendor VARCHAR(255),
    amount DECIMAL(15,2) NOT NULL,
    billing_interval VARCHAR(50) DEFAULT 'monthly',
    category VARCHAR(100),
    next_billing_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
