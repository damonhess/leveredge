-- ============================================
-- SATOSHI - Crypto & Blockchain Master
-- Date: 2026-01-19
-- ============================================

-- ============================================
-- WALLETS
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,  -- "Main ETH", "Cold Storage", "DeFi Wallet"
    address VARCHAR(255) NOT NULL,
    chain VARCHAR(50) NOT NULL,  -- ethereum, polygon, arbitrum, optimism, base, solana, bitcoin
    wallet_type VARCHAR(50) DEFAULT 'hot',  -- hot, cold, hardware, multisig
    is_tracked BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(address, chain)
);

-- ============================================
-- TOKEN BALANCES
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES satoshi_wallets(id) ON DELETE CASCADE,
    token_address VARCHAR(255),  -- NULL for native token
    token_symbol VARCHAR(50) NOT NULL,
    token_name VARCHAR(255),
    token_decimals INTEGER DEFAULT 18,
    balance_raw VARCHAR(100),  -- Raw balance (can be huge)
    balance DECIMAL(38,18) NOT NULL,
    price_usd DECIMAL(18,8),
    value_usd DECIMAL(18,2),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(wallet_id, token_address)
);

CREATE INDEX IF NOT EXISTS idx_satoshi_balances_wallet ON satoshi_balances(wallet_id);
CREATE INDEX IF NOT EXISTS idx_satoshi_balances_symbol ON satoshi_balances(token_symbol);

-- ============================================
-- DEFI POSITIONS
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_defi_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES satoshi_wallets(id) ON DELETE CASCADE,
    protocol VARCHAR(100) NOT NULL,  -- aave, compound, uniswap, curve, lido
    chain VARCHAR(50) NOT NULL,
    position_type VARCHAR(50) NOT NULL,  -- lending, borrowing, liquidity, staking, farming
    pool_name VARCHAR(255),
    pool_address VARCHAR(255),

    -- For lending/staking
    deposited_amount DECIMAL(38,18),
    deposited_token VARCHAR(50),
    deposited_value_usd DECIMAL(18,2),

    -- For borrowing
    borrowed_amount DECIMAL(38,18),
    borrowed_token VARCHAR(50),
    borrowed_value_usd DECIMAL(18,2),

    -- For LP positions
    lp_token_balance DECIMAL(38,18),
    token0_symbol VARCHAR(50),
    token0_amount DECIMAL(38,18),
    token1_symbol VARCHAR(50),
    token1_amount DECIMAL(38,18),

    -- Yields
    apy DECIMAL(10,4),
    rewards_pending DECIMAL(38,18),
    rewards_token VARCHAR(50),
    rewards_value_usd DECIMAL(18,2),

    -- Health
    health_factor DECIMAL(10,4),  -- For lending protocols
    liquidation_price DECIMAL(18,8),

    total_value_usd DECIMAL(18,2),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_satoshi_defi_wallet ON satoshi_defi_positions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_satoshi_defi_protocol ON satoshi_defi_positions(protocol);

-- ============================================
-- NFT HOLDINGS
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_nfts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES satoshi_wallets(id) ON DELETE CASCADE,
    chain VARCHAR(50) NOT NULL,
    contract_address VARCHAR(255) NOT NULL,
    token_id VARCHAR(100) NOT NULL,
    collection_name VARCHAR(255),
    collection_slug VARCHAR(255),
    name VARCHAR(255),
    image_url TEXT,
    floor_price_eth DECIMAL(18,8),
    floor_price_usd DECIMAL(18,2),
    last_sale_price_eth DECIMAL(18,8),
    rarity_rank INTEGER,
    traits JSONB,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(wallet_id, contract_address, token_id)
);

CREATE INDEX IF NOT EXISTS idx_satoshi_nfts_wallet ON satoshi_nfts(wallet_id);
CREATE INDEX IF NOT EXISTS idx_satoshi_nfts_collection ON satoshi_nfts(collection_slug);

-- ============================================
-- TRANSACTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES satoshi_wallets(id) ON DELETE CASCADE,
    chain VARCHAR(50) NOT NULL,
    tx_hash VARCHAR(255) NOT NULL,
    block_number BIGINT,
    timestamp TIMESTAMPTZ NOT NULL,
    from_address VARCHAR(255),
    to_address VARCHAR(255),
    tx_type VARCHAR(50),  -- transfer, swap, mint, stake, claim, approve, contract_interaction

    -- Token details
    token_symbol VARCHAR(50),
    token_address VARCHAR(255),
    amount DECIMAL(38,18),
    amount_usd DECIMAL(18,2),

    -- Gas
    gas_used BIGINT,
    gas_price_gwei DECIMAL(18,4),
    gas_cost_eth DECIMAL(18,8),
    gas_cost_usd DECIMAL(18,2),

    -- Classification
    is_incoming BOOLEAN,
    counterparty VARCHAR(255),  -- Protocol name or address
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chain, tx_hash, wallet_id)
);

CREATE INDEX IF NOT EXISTS idx_satoshi_tx_wallet ON satoshi_transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_satoshi_tx_timestamp ON satoshi_transactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_satoshi_tx_type ON satoshi_transactions(tx_type);

-- ============================================
-- PRICE CACHE
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id VARCHAR(255) NOT NULL,  -- CoinGecko ID
    symbol VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    current_price DECIMAL(18,8),
    price_change_24h DECIMAL(10,4),
    price_change_7d DECIMAL(10,4),
    market_cap DECIMAL(24,2),
    volume_24h DECIMAL(24,2),
    circulating_supply DECIMAL(24,2),
    total_supply DECIMAL(24,2),
    ath DECIMAL(18,8),
    ath_date TIMESTAMPTZ,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_id)
);

CREATE INDEX IF NOT EXISTS idx_satoshi_prices_symbol ON satoshi_prices(symbol);

-- ============================================
-- WATCHLIST
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id VARCHAR(255) NOT NULL,  -- CoinGecko ID
    symbol VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    target_buy_price DECIMAL(18,8),
    target_sell_price DECIMAL(18,8),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(token_id)
);

-- ============================================
-- ALERTS
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type VARCHAR(50) NOT NULL,  -- price, whale, gas, health_factor, liquidation
    token_id VARCHAR(255),
    wallet_id UUID REFERENCES satoshi_wallets(id),
    condition VARCHAR(50) NOT NULL,  -- above, below, change_pct
    threshold DECIMAL(18,8) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- GAS TRACKER
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_gas_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain VARCHAR(50) NOT NULL DEFAULT 'ethereum',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    slow_gwei DECIMAL(10,2),
    standard_gwei DECIMAL(10,2),
    fast_gwei DECIMAL(10,2),
    instant_gwei DECIMAL(10,2),
    base_fee_gwei DECIMAL(10,2)
);

CREATE INDEX IF NOT EXISTS idx_satoshi_gas_timestamp ON satoshi_gas_history(timestamp DESC);

-- ============================================
-- PORTFOLIO SNAPSHOTS
-- ============================================
CREATE TABLE IF NOT EXISTS satoshi_portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_value_usd DECIMAL(18,2),
    wallet_balances_usd DECIMAL(18,2),
    defi_value_usd DECIMAL(18,2),
    nft_floor_value_usd DECIMAL(18,2),
    by_chain JSONB,
    by_protocol JSONB,
    top_holdings JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

-- Done!
SELECT 'SATOSHI Crypto schema migration complete!' as status;
