# GSD: MIDAS - Traditional Finance Master

**Priority:** MEDIUM (Post-launch nice-to-have)
**Port:** 8205
**Estimated Time:** 3-4 hours
**Purpose:** Personal finance and investment portfolio management

---

## THE VISION

MIDAS manages your **traditional financial life**:
- Investment portfolios (stocks, ETFs, bonds, mutual funds)
- Retirement accounts (401k, IRA tracking)
- Market analysis and alerts
- Risk assessment
- Performance reporting
- Tax-loss harvesting suggestions

**Named after:** King Midas, whose touch turned things to gold. Building wealth through smart investing.

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    MIDAS - Finance Master                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  PORTFOLIO  │  │   MARKET    │  │    RISK     │             │
│  │   TRACKER   │  │  ANALYSIS   │  │  ASSESSOR   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │               │                │                      │
│  ┌──────┴───────────────┴────────────────┴──────┐              │
│  │              DATA LAYER                       │              │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐            │              │
│  │  │Yahoo│ │Alpha│ │Finn │ │Manual│            │              │
│  │  │Fin  │ │Vntge│ │hub  │ │Entry │            │              │
│  └──┴─────┴─┴─────┴─┴─────┴─┴─────┴────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: DATABASE SCHEMA

```sql
-- ============================================
-- ACCOUNTS (Brokerage, Retirement, etc.)
-- ============================================
CREATE TABLE midas_accounts (
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
CREATE TABLE midas_positions (
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

CREATE INDEX idx_positions_account ON midas_positions(account_id);
CREATE INDEX idx_positions_symbol ON midas_positions(symbol);

-- ============================================
-- TRANSACTIONS
-- ============================================
CREATE TABLE midas_transactions (
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

CREATE INDEX idx_transactions_account ON midas_transactions(account_id);
CREATE INDEX idx_transactions_symbol ON midas_transactions(symbol);
CREATE INDEX idx_transactions_date ON midas_transactions(transaction_date DESC);

-- ============================================
-- WATCHLIST
-- ============================================
CREATE TABLE midas_watchlist (
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
CREATE TABLE midas_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,  -- price_above, price_below, pct_change, volume_spike
    threshold DECIMAL(18,4) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered TIMESTAMPTZ,
    notification_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_symbol ON midas_alerts(symbol);
CREATE INDEX idx_alerts_active ON midas_alerts(is_active);

-- ============================================
-- PRICE HISTORY (for charts)
-- ============================================
CREATE TABLE midas_price_history (
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

CREATE INDEX idx_price_history_symbol ON midas_price_history(symbol, date DESC);

-- ============================================
-- PORTFOLIO SNAPSHOTS (daily value tracking)
-- ============================================
CREATE TABLE midas_portfolio_snapshots (
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

CREATE INDEX idx_snapshots_date ON midas_portfolio_snapshots(snapshot_date DESC);

-- ============================================
-- DIVIDENDS
-- ============================================
CREATE TABLE midas_dividends (
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

CREATE INDEX idx_dividends_symbol ON midas_dividends(symbol);
CREATE INDEX idx_dividends_date ON midas_dividends(pay_date DESC);
```

---

## PHASE 2: CORE ENDPOINTS

Create `/opt/leveredge/control-plane/agents/midas/midas.py`:

```python
"""
MIDAS - Traditional Finance Master
Port: 8205

Everything I touch turns to gold.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
import os
import asyncpg
import httpx

app = FastAPI(
    title="MIDAS - Traditional Finance Master",
    description="Everything I touch turns to gold.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")

pool: asyncpg.Pool = None


@app.on_event("startup")
async def startup():
    global pool
    if DATABASE_URL:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


# ============ HEALTH ============

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "MIDAS - Traditional Finance Master",
        "port": 8205,
        "tagline": "Everything I touch turns to gold."
    }


# ============ ACCOUNTS ============

class AccountCreate(BaseModel):
    name: str
    account_type: str  # brokerage, 401k, ira, roth_ira, hsa
    institution: Optional[str] = None
    is_tax_advantaged: bool = False
    notes: Optional[str] = None


@app.get("/accounts")
async def list_accounts():
    """List all accounts with current values"""
    async with pool.acquire() as conn:
        accounts = await conn.fetch("""
            SELECT a.*,
                COALESCE(SUM(p.current_value), 0) as total_value,
                COALESCE(SUM(p.cost_basis), 0) as total_cost_basis,
                COALESCE(SUM(p.unrealized_gain_loss), 0) as unrealized_gain_loss,
                COUNT(p.id) as position_count
            FROM midas_accounts a
            LEFT JOIN midas_positions p ON a.id = p.account_id
            GROUP BY a.id
            ORDER BY a.name
        """)
        return [dict(a) for a in accounts]


@app.post("/accounts")
async def create_account(account: AccountCreate):
    """Create a new account"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO midas_accounts (name, account_type, institution, is_tax_advantaged, notes)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, account.name, account.account_type, account.institution,
            account.is_tax_advantaged, account.notes)
        return dict(row)


# ============ POSITIONS ============

class PositionCreate(BaseModel):
    account_id: str
    symbol: str
    quantity: float
    cost_basis: Optional[float] = None
    asset_type: str = "stock"


@app.get("/positions")
async def list_positions(account_id: Optional[str] = None):
    """List all positions"""
    async with pool.acquire() as conn:
        if account_id:
            rows = await conn.fetch("""
                SELECT p.*, a.name as account_name
                FROM midas_positions p
                JOIN midas_accounts a ON p.account_id = a.id
                WHERE p.account_id = $1::uuid
                ORDER BY p.current_value DESC NULLS LAST
            """, account_id)
        else:
            rows = await conn.fetch("""
                SELECT p.*, a.name as account_name
                FROM midas_positions p
                JOIN midas_accounts a ON p.account_id = a.id
                ORDER BY p.current_value DESC NULLS LAST
            """)
        return [dict(r) for r in rows]


@app.post("/positions")
async def create_position(position: PositionCreate):
    """Add a position"""
    # Get current price
    price = await get_current_price(position.symbol)
    current_value = position.quantity * price if price else None
    cost_basis_per_share = position.cost_basis / position.quantity if position.cost_basis and position.quantity else None
    gain_loss = (current_value - position.cost_basis) if current_value and position.cost_basis else None
    gain_loss_pct = (gain_loss / position.cost_basis * 100) if gain_loss and position.cost_basis else None
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO midas_positions 
            (account_id, symbol, quantity, cost_basis, cost_basis_per_share, 
             current_price, current_value, unrealized_gain_loss, unrealized_gain_loss_pct,
             asset_type, last_price_update)
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
            ON CONFLICT (account_id, symbol) DO UPDATE SET
                quantity = EXCLUDED.quantity,
                cost_basis = EXCLUDED.cost_basis,
                updated_at = NOW()
            RETURNING *
        """, position.account_id, position.symbol.upper(), position.quantity,
            position.cost_basis, cost_basis_per_share, price, current_value,
            gain_loss, gain_loss_pct, position.asset_type)
        return dict(row)


# ============ TRANSACTIONS ============

class TransactionCreate(BaseModel):
    account_id: str
    symbol: Optional[str] = None
    transaction_type: str  # buy, sell, dividend, deposit, withdrawal
    quantity: Optional[float] = None
    price_per_share: Optional[float] = None
    total_amount: float
    fees: float = 0
    transaction_date: date
    notes: Optional[str] = None


@app.get("/transactions")
async def list_transactions(
    account_id: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100
):
    """List transactions"""
    async with pool.acquire() as conn:
        query = """
            SELECT t.*, a.name as account_name
            FROM midas_transactions t
            JOIN midas_accounts a ON t.account_id = a.id
            WHERE 1=1
        """
        params = []
        
        if account_id:
            params.append(account_id)
            query += f" AND t.account_id = ${len(params)}::uuid"
        if symbol:
            params.append(symbol.upper())
            query += f" AND t.symbol = ${len(params)}"
        
        query += f" ORDER BY t.transaction_date DESC LIMIT {limit}"
        
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/transactions")
async def create_transaction(txn: TransactionCreate):
    """Record a transaction and update positions"""
    async with pool.acquire() as conn:
        # Create transaction
        row = await conn.fetchrow("""
            INSERT INTO midas_transactions 
            (account_id, symbol, transaction_type, quantity, price_per_share,
             total_amount, fees, transaction_date, notes)
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """, txn.account_id, txn.symbol.upper() if txn.symbol else None,
            txn.transaction_type, txn.quantity, txn.price_per_share,
            txn.total_amount, txn.fees, txn.transaction_date, txn.notes)
        
        # Update position if buy/sell
        if txn.symbol and txn.transaction_type in ['buy', 'sell']:
            await update_position_from_transaction(conn, txn)
        
        return dict(row)


async def update_position_from_transaction(conn, txn: TransactionCreate):
    """Update position based on transaction"""
    position = await conn.fetchrow("""
        SELECT * FROM midas_positions 
        WHERE account_id = $1::uuid AND symbol = $2
    """, txn.account_id, txn.symbol.upper())
    
    if txn.transaction_type == 'buy':
        if position:
            # Update existing position
            new_qty = float(position['quantity']) + txn.quantity
            new_cost = float(position['cost_basis'] or 0) + txn.total_amount
            await conn.execute("""
                UPDATE midas_positions 
                SET quantity = $3, cost_basis = $4, 
                    cost_basis_per_share = $4 / $3,
                    updated_at = NOW()
                WHERE account_id = $1::uuid AND symbol = $2
            """, txn.account_id, txn.symbol.upper(), new_qty, new_cost)
        else:
            # Create new position
            await conn.execute("""
                INSERT INTO midas_positions 
                (account_id, symbol, quantity, cost_basis, cost_basis_per_share, asset_type)
                VALUES ($1::uuid, $2, $3, $4, $4/$3, 'stock')
            """, txn.account_id, txn.symbol.upper(), txn.quantity, txn.total_amount)
    
    elif txn.transaction_type == 'sell' and position:
        new_qty = float(position['quantity']) - txn.quantity
        if new_qty <= 0:
            await conn.execute("""
                DELETE FROM midas_positions 
                WHERE account_id = $1::uuid AND symbol = $2
            """, txn.account_id, txn.symbol.upper())
        else:
            # Reduce position (FIFO cost basis approximation)
            cost_per_share = float(position['cost_basis'] or 0) / float(position['quantity'])
            new_cost = new_qty * cost_per_share
            await conn.execute("""
                UPDATE midas_positions 
                SET quantity = $3, cost_basis = $4, updated_at = NOW()
                WHERE account_id = $1::uuid AND symbol = $2
            """, txn.account_id, txn.symbol.upper(), new_qty, new_cost)


# ============ MARKET DATA ============

async def get_current_price(symbol: str) -> Optional[float]:
    """Get current price for a symbol"""
    # Try Yahoo Finance (free, no key needed)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"interval": "1d", "range": "1d"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                price = data['chart']['result'][0]['meta']['regularMarketPrice']
                return float(price)
    except Exception:
        pass
    
    # Fallback to Alpha Vantage if key exists
    if ALPHA_VANTAGE_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.alphavantage.co/query",
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": symbol,
                        "apikey": ALPHA_VANTAGE_KEY
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return float(data['Global Quote']['05. price'])
        except Exception:
            pass
    
    return None


@app.get("/market/quote/{symbol}")
async def get_quote(symbol: str):
    """Get current quote for a symbol"""
    price = await get_current_price(symbol.upper())
    if price is None:
        raise HTTPException(status_code=404, detail=f"Could not get price for {symbol}")
    
    return {
        "symbol": symbol.upper(),
        "price": price,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/positions/refresh-prices")
async def refresh_all_prices(background_tasks: BackgroundTasks):
    """Refresh prices for all positions (background)"""
    background_tasks.add_task(do_price_refresh)
    return {"status": "started", "message": "Price refresh running in background"}


async def do_price_refresh():
    """Background task to refresh all prices"""
    async with pool.acquire() as conn:
        positions = await conn.fetch("SELECT DISTINCT symbol FROM midas_positions")
        
        for pos in positions:
            symbol = pos['symbol']
            price = await get_current_price(symbol)
            
            if price:
                await conn.execute("""
                    UPDATE midas_positions 
                    SET current_price = $2,
                        current_value = quantity * $2,
                        unrealized_gain_loss = (quantity * $2) - cost_basis,
                        unrealized_gain_loss_pct = ((quantity * $2) - cost_basis) / NULLIF(cost_basis, 0) * 100,
                        last_price_update = NOW()
                    WHERE symbol = $1
                """, symbol, price)


# ============ WATCHLIST ============

@app.get("/watchlist")
async def get_watchlist():
    """Get watchlist with current prices"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM midas_watchlist ORDER BY symbol
        """)
        return [dict(r) for r in rows]


@app.post("/watchlist/{symbol}")
async def add_to_watchlist(
    symbol: str,
    target_buy_price: Optional[float] = None,
    target_sell_price: Optional[float] = None,
    notes: Optional[str] = None
):
    """Add symbol to watchlist"""
    price = await get_current_price(symbol.upper())
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO midas_watchlist (symbol, target_buy_price, target_sell_price, notes, current_price, last_price_update)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (symbol) DO UPDATE SET
                target_buy_price = EXCLUDED.target_buy_price,
                target_sell_price = EXCLUDED.target_sell_price,
                notes = EXCLUDED.notes
            RETURNING *
        """, symbol.upper(), target_buy_price, target_sell_price, notes, price)
        return dict(row)


# ============ ALERTS ============

@app.get("/alerts")
async def get_alerts(active_only: bool = True):
    """Get price alerts"""
    async with pool.acquire() as conn:
        if active_only:
            rows = await conn.fetch(
                "SELECT * FROM midas_alerts WHERE is_active = TRUE ORDER BY symbol"
            )
        else:
            rows = await conn.fetch("SELECT * FROM midas_alerts ORDER BY symbol")
        return [dict(r) for r in rows]


@app.post("/alerts")
async def create_alert(
    symbol: str,
    alert_type: str,  # price_above, price_below, pct_change
    threshold: float
):
    """Create a price alert"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO midas_alerts (symbol, alert_type, threshold)
            VALUES ($1, $2, $3)
            RETURNING *
        """, symbol.upper(), alert_type, threshold)
        return dict(row)


# ============ PORTFOLIO SUMMARY ============

@app.get("/portfolio/summary")
async def portfolio_summary():
    """Get complete portfolio summary"""
    async with pool.acquire() as conn:
        # Total values
        totals = await conn.fetchrow("""
            SELECT 
                COALESCE(SUM(current_value), 0) as total_value,
                COALESCE(SUM(cost_basis), 0) as total_cost_basis,
                COALESCE(SUM(unrealized_gain_loss), 0) as total_gain_loss
            FROM midas_positions
        """)
        
        # By account
        by_account = await conn.fetch("""
            SELECT a.name, a.account_type,
                COALESCE(SUM(p.current_value), 0) as value
            FROM midas_accounts a
            LEFT JOIN midas_positions p ON a.id = p.account_id
            GROUP BY a.id
            ORDER BY value DESC
        """)
        
        # By asset type
        by_asset = await conn.fetch("""
            SELECT asset_type, 
                COALESCE(SUM(current_value), 0) as value,
                COUNT(*) as position_count
            FROM midas_positions
            GROUP BY asset_type
            ORDER BY value DESC
        """)
        
        # Top holdings
        top_holdings = await conn.fetch("""
            SELECT symbol, name, current_value, unrealized_gain_loss_pct
            FROM midas_positions
            ORDER BY current_value DESC NULLS LAST
            LIMIT 10
        """)
        
        total_value = float(totals['total_value']) if totals['total_value'] else 0
        total_cost = float(totals['total_cost_basis']) if totals['total_cost_basis'] else 0
        total_gain = float(totals['total_gain_loss']) if totals['total_gain_loss'] else 0
        gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0
        
        return {
            "total_value": total_value,
            "total_cost_basis": total_cost,
            "total_gain_loss": total_gain,
            "total_gain_loss_pct": gain_pct,
            "by_account": [dict(a) for a in by_account],
            "by_asset_type": [dict(a) for a in by_asset],
            "top_holdings": [dict(h) for h in top_holdings],
            "last_updated": datetime.now().isoformat(),
            "midas_says": f"Your portfolio is worth ${total_value:,.2f} with {'+' if gain_pct >= 0 else ''}{gain_pct:.1f}% returns."
        }


@app.post("/portfolio/snapshot")
async def take_snapshot():
    """Take a daily snapshot of portfolio value"""
    async with pool.acquire() as conn:
        # Get current totals
        totals = await conn.fetchrow("""
            SELECT 
                COALESCE(SUM(current_value), 0) as total_value,
                COALESCE(SUM(cost_basis), 0) as total_cost_basis,
                COALESCE(SUM(unrealized_gain_loss), 0) as total_gain_loss
            FROM midas_positions
        """)
        
        total_value = float(totals['total_value'])
        total_cost = float(totals['total_cost_basis'])
        gain_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
        
        # Get breakdowns
        by_account = await conn.fetch("""
            SELECT a.name, COALESCE(SUM(p.current_value), 0) as value
            FROM midas_accounts a
            LEFT JOIN midas_positions p ON a.id = p.account_id
            GROUP BY a.id
        """)
        
        by_asset = await conn.fetch("""
            SELECT asset_type, COALESCE(SUM(current_value), 0) as value
            FROM midas_positions GROUP BY asset_type
        """)
        
        import json
        row = await conn.fetchrow("""
            INSERT INTO midas_portfolio_snapshots 
            (total_value, total_cost_basis, total_gain_loss, total_gain_loss_pct, by_account, by_asset_type)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (snapshot_date) DO UPDATE SET
                total_value = EXCLUDED.total_value,
                total_cost_basis = EXCLUDED.total_cost_basis,
                total_gain_loss = EXCLUDED.total_gain_loss
            RETURNING *
        """, total_value, total_cost, total_value - total_cost, gain_pct,
            json.dumps({a['name']: float(a['value']) for a in by_account}),
            json.dumps({a['asset_type']: float(a['value']) for a in by_asset}))
        
        return dict(row)


@app.get("/portfolio/history")
async def portfolio_history(days: int = 30):
    """Get portfolio value history"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM midas_portfolio_snapshots
            WHERE snapshot_date >= CURRENT_DATE - $1
            ORDER BY snapshot_date
        """, days)
        return [dict(r) for r in rows]


# ============ DIVIDENDS ============

@app.get("/dividends")
async def list_dividends(year: Optional[int] = None):
    """List dividend income"""
    async with pool.acquire() as conn:
        if year:
            rows = await conn.fetch("""
                SELECT d.*, a.name as account_name
                FROM midas_dividends d
                JOIN midas_accounts a ON d.account_id = a.id
                WHERE EXTRACT(YEAR FROM d.pay_date) = $1
                ORDER BY d.pay_date DESC
            """, year)
        else:
            rows = await conn.fetch("""
                SELECT d.*, a.name as account_name
                FROM midas_dividends d
                JOIN midas_accounts a ON d.account_id = a.id
                ORDER BY d.pay_date DESC
                LIMIT 100
            """)
        return [dict(r) for r in rows]


@app.get("/dividends/summary")
async def dividend_summary(year: Optional[int] = None):
    """Get dividend summary"""
    target_year = year or date.today().year
    
    async with pool.acquire() as conn:
        total = await conn.fetchrow("""
            SELECT 
                COALESCE(SUM(total_amount), 0) as total_dividends,
                COUNT(*) as dividend_count
            FROM midas_dividends
            WHERE EXTRACT(YEAR FROM pay_date) = $1
        """, target_year)
        
        by_symbol = await conn.fetch("""
            SELECT symbol, SUM(total_amount) as total
            FROM midas_dividends
            WHERE EXTRACT(YEAR FROM pay_date) = $1
            GROUP BY symbol
            ORDER BY total DESC
        """, target_year)
        
        return {
            "year": target_year,
            "total_dividends": float(total['total_dividends']),
            "dividend_count": total['dividend_count'],
            "by_symbol": [dict(s) for s in by_symbol],
            "midas_says": f"You earned ${float(total['total_dividends']):,.2f} in dividends in {target_year}."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8205)
```

---

## PHASE 3: DOCKER SETUP

Create `/opt/leveredge/control-plane/agents/midas/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8205

CMD ["uvicorn", "midas:app", "--host", "0.0.0.0", "--port", "8205"]
```

Create `requirements.txt`:
```
fastapi==0.109.0
uvicorn==0.27.0
asyncpg==0.29.0
httpx==0.26.0
pydantic==2.5.3
```

Add to docker-compose:
```yaml
midas:
  build: ./agents/midas
  container_name: midas
  ports:
    - "8205:8205"
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - ALPHA_VANTAGE_KEY=${ALPHA_VANTAGE_KEY}
  networks:
    - leveredge-net
  restart: unless-stopped
```

---

## PHASE 4: FUTURE ENHANCEMENTS (Post-Launch)

- Tax-loss harvesting suggestions
- Rebalancing recommendations
- Sector/geographic allocation analysis
- Integration with brokerage APIs (Schwab, Fidelity)
- Retirement projections
- Monte Carlo simulations

---

## DELIVERABLES

- [ ] Database schema
- [ ] MIDAS FastAPI service
- [ ] Docker configuration
- [ ] Basic market data integration
- [ ] Portfolio tracking
- [ ] Transaction recording
- [ ] Watchlist and alerts
- [ ] Dividend tracking

---

## COMMIT MESSAGE

```
MIDAS: Traditional Finance Master

- Portfolio tracking across multiple accounts
- Transaction recording (buy/sell/dividend)
- Real-time price updates via Yahoo Finance
- Watchlist with target prices
- Price alerts
- Dividend tracking
- Daily portfolio snapshots
- Performance reporting

Everything I touch turns to gold.
```

---

*"I don't gamble. I calculate. Every position, every allocation, every move - measured for maximum return."*
