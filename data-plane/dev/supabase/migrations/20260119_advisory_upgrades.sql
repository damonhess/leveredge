-- ============================================
-- ADVISORY TEAM UPGRADES
-- SOLON, QUAESTOR, MIDAS expansions
-- ============================================

-- ============================================
-- SOLON UPGRADES
-- ============================================

-- Your legal situation memory
CREATE TABLE IF NOT EXISTS solon_situation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100) NOT NULL,  -- entity, contract, compliance, ip, employment
    topic VARCHAR(255) NOT NULL,
    current_state TEXT,
    history JSONB DEFAULT '[]',
    documents JSONB DEFAULT '[]',
    last_reviewed DATE,
    next_review DATE,
    attorney_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contracts tracker
CREATE TABLE IF NOT EXISTS solon_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    contract_type VARCHAR(100),  -- client, vendor, employment, nda, etc.
    counterparty VARCHAR(255),
    status VARCHAR(50) DEFAULT 'draft',  -- draft, review, active, expired, terminated
    effective_date DATE,
    expiration_date DATE,
    auto_renew BOOLEAN DEFAULT FALSE,
    renewal_notice_days INTEGER,
    key_terms JSONB DEFAULT '{}',
    file_path TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contracts_status ON solon_contracts(status);
CREATE INDEX IF NOT EXISTS idx_contracts_expiry ON solon_contracts(expiration_date);

-- Compliance tracker
CREATE TABLE IF NOT EXISTS solon_compliance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement VARCHAR(255) NOT NULL,
    jurisdiction VARCHAR(100),
    category VARCHAR(100),  -- license, registration, filing, etc.
    due_date DATE,
    recurring_interval VARCHAR(50),  -- annual, quarterly, etc.
    status VARCHAR(50) DEFAULT 'pending',
    completed_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- QUAESTOR UPGRADES
-- ============================================

-- Tax deadlines
CREATE TABLE IF NOT EXISTS quaestor_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    deadline_type VARCHAR(100),  -- filing, payment, election, etc.
    jurisdiction VARCHAR(100),  -- federal, california, nevada
    due_date DATE NOT NULL,
    recurring_interval VARCHAR(50),  -- annual, quarterly
    status VARCHAR(50) DEFAULT 'pending',
    completed_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deadlines_due ON quaestor_deadlines(due_date);

-- Document checklist
CREATE TABLE IF NOT EXISTS quaestor_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    document_type VARCHAR(100),  -- w2, 1099, receipt, statement
    tax_year INTEGER NOT NULL,
    category VARCHAR(100),  -- income, deduction, credit, entity
    status VARCHAR(50) DEFAULT 'needed',  -- needed, requested, received, filed
    source VARCHAR(255),  -- employer name, bank, etc.
    due_date DATE,
    received_date DATE,
    file_path TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_docs_year ON quaestor_documents(tax_year);
CREATE INDEX IF NOT EXISTS idx_docs_status ON quaestor_documents(status);

-- Your tax situation
CREATE TABLE IF NOT EXISTS quaestor_situation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_year INTEGER NOT NULL,
    category VARCHAR(100) NOT NULL,  -- filing_status, entity, income, deduction
    topic VARCHAR(255) NOT NULL,
    current_value TEXT,
    notes TEXT,
    cpa_notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tax_year, category, topic)
);

-- ============================================
-- MIDAS UPGRADES
-- ============================================

-- Personal budgets
CREATE TABLE IF NOT EXISTS midas_budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100) NOT NULL,
    monthly_limit DECIMAL(15,2) NOT NULL,
    year_month VARCHAR(7),  -- YYYY-MM, NULL for ongoing
    spent DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Personal transactions (for budgeting)
CREATE TABLE IF NOT EXISTS midas_personal_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_date DATE NOT NULL,
    category VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    amount DECIMAL(15,2) NOT NULL,
    is_income BOOLEAN DEFAULT FALSE,
    source VARCHAR(255),  -- account name
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_personal_tx_date ON midas_personal_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_personal_tx_cat ON midas_personal_transactions(category);

-- Net worth snapshots (without GENERATED columns for compatibility)
CREATE TABLE IF NOT EXISTS midas_net_worth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Assets
    cash DECIMAL(15,2) DEFAULT 0,
    investments DECIMAL(15,2) DEFAULT 0,
    real_estate DECIMAL(15,2) DEFAULT 0,
    vehicles DECIMAL(15,2) DEFAULT 0,
    other_assets DECIMAL(15,2) DEFAULT 0,

    -- Liabilities
    mortgage DECIMAL(15,2) DEFAULT 0,
    auto_loans DECIMAL(15,2) DEFAULT 0,
    student_loans DECIMAL(15,2) DEFAULT 0,
    credit_cards DECIMAL(15,2) DEFAULT 0,
    other_liabilities DECIMAL(15,2) DEFAULT 0,

    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(snapshot_date)
);
