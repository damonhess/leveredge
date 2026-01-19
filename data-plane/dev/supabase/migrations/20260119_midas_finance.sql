-- ============================================
-- MIDAS - Traditional Finance Master
-- Date: 2026-01-19
-- ============================================

-- ============================================
-- ACCOUNTS (Brokerage, Retirement, etc.)
-- ============================================
CREATE TABLE IF NOT EXISTS midas_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,  -- "Fidelity 401k", "Schwab Brokerage"
    account_type VARCHAR(50) NOT NULL,  -- brokerage, 401k, ira, roth_ira, hsa
    institution VARCHAR(255),
    account_number_masked VARCHAR(50),  -- Last 4 digits only
    currency VARCHAR(10) DEFAULT 'USD',
    is_tax_advantaged BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- POSITIONS (Current Holdings)
-- ============================================
CREATE TABLE IF NOT EXISTS midas_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES midas_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    asset_type VARCHAR(50) NOT NULL,  -- stock, etf, mutual_fund, bond, cash, option
    quantity DECIMAL(18,8) NOT NULL,
    cost_basis DECIMAL(18,2),
    cost_basis_per_share DECIMAL(18,4),
    current_price DECIMAL(18,4),
    current_value DECIMAL(18,2),
    unrealized_gain_loss DECIMAL(18,2),
    unrealized_gain_loss_pct DECIMAL(10,4),
    last_price_update TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_midas_positions_account ON midas_positions(account_id);
CREATE INDEX IF NOT EXISTS idx_midas_positions_symbol ON midas_positions(symbol);

-- ============================================
-- TRANSACTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS midas_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES midas_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20),
    transaction_type VARCHAR(50) NOT NULL,  -- buy, sell, dividend, interest, deposit, withdrawal, split
    quantity DECIMAL(18,8),
    price_per_share DECIMAL(18,4),
    total_amount DECIMAL(18,2) NOT NULL,
    fees DECIMAL(18,2) DEFAULT 0,
    transaction_date DATE NOT NULL,
    settlement_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_midas_transactions_account ON midas_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_midas_transactions_symbol ON midas_transactions(symbol);
CREATE INDEX IF NOT EXISTS idx_midas_transactions_date ON midas_transactions(transaction_date DESC);

-- ============================================
-- WATCHLIST
-- ============================================
CREATE TABLE IF NOT EXISTS midas_watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    asset_type VARCHAR(50),
    target_buy_price DECIMAL(18,4),
    target_sell_price DECIMAL(18,4),
    notes TEXT,
    current_price DECIMAL(18,4),
    last_price_update TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- PRICE ALERTS
-- ============================================
CREATE TABLE IF NOT EXISTS midas_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,  -- price_above, price_below, pct_change, volume_spike
    threshold DECIMAL(18,4) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered TIMESTAMPTZ,
    notification_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_midas_alerts_symbol ON midas_alerts(symbol);
CREATE INDEX IF NOT EXISTS idx_midas_alerts_active ON midas_alerts(is_active);

-- ============================================
-- PRICE HISTORY (for charts)
-- ============================================
CREATE TABLE IF NOT EXISTS midas_price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(18,4),
    high_price DECIMAL(18,4),
    low_price DECIMAL(18,4),
    close_price DECIMAL(18,4),
    volume BIGINT,
    UNIQUE(symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_midas_price_history_symbol ON midas_price_history(symbol, date DESC);

-- ============================================
-- PORTFOLIO SNAPSHOTS (daily value tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS midas_portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_value DECIMAL(18,2) NOT NULL,
    total_cost_basis DECIMAL(18,2),
    total_gain_loss DECIMAL(18,2),
    total_gain_loss_pct DECIMAL(10,4),
    cash_balance DECIMAL(18,2),
    by_account JSONB,  -- Breakdown by account
    by_asset_type JSONB,  -- Breakdown by asset type
    by_sector JSONB,  -- Breakdown by sector
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_midas_snapshots_date ON midas_portfolio_snapshots(snapshot_date DESC);

-- ============================================
-- DIVIDENDS
-- ============================================
CREATE TABLE IF NOT EXISTS midas_dividends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES midas_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    ex_date DATE,
    pay_date DATE,
    amount_per_share DECIMAL(18,6),
    total_amount DECIMAL(18,2),
    shares_held DECIMAL(18,8),
    reinvested BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_midas_dividends_symbol ON midas_dividends(symbol);
CREATE INDEX IF NOT EXISTS idx_midas_dividends_date ON midas_dividends(pay_date DESC);

-- Done!
SELECT 'MIDAS Finance schema migration complete!' as status;
