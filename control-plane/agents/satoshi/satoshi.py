"""
SATOSHI - Crypto & Blockchain Master
Port: 8206

In code we trust.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
import os
import asyncpg
import httpx
import json

app = FastAPI(
    title="SATOSHI - Crypto & Blockchain Master",
    description="In code we trust.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
COINGECKO_API_KEY = os.environ.get("COINGECKO_API_KEY", "")
ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")
ALCHEMY_API_KEY = os.environ.get("ALCHEMY_API_KEY", "")
DEFILLAMA_BASE = "https://api.llama.fi"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

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
    db_status = "connected" if pool else "disconnected"
    return {
        "status": "healthy",
        "service": "SATOSHI",
        "agent": "SATOSHI",
        "port": 8206,
        "database": db_status,
        "tagline": "In code we trust."
    }


# ============ WALLETS ============

class WalletCreate(BaseModel):
    name: str
    address: str
    chain: str  # ethereum, polygon, arbitrum, solana, bitcoin
    wallet_type: str = "hot"
    notes: Optional[str] = None


@app.get("/wallets")
async def list_wallets():
    """List all tracked wallets with balances"""
    async with pool.acquire() as conn:
        wallets = await conn.fetch("""
            SELECT w.*,
                COALESCE(SUM(b.value_usd), 0) as total_balance_usd,
                COUNT(DISTINCT b.token_symbol) as token_count
            FROM satoshi_wallets w
            LEFT JOIN satoshi_balances b ON w.id = b.wallet_id
            GROUP BY w.id
            ORDER BY total_balance_usd DESC
        """)
        return [dict(w) for w in wallets]


@app.post("/wallets")
async def add_wallet(wallet: WalletCreate):
    """Add a wallet to track"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO satoshi_wallets (name, address, chain, wallet_type, notes)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (address, chain) DO UPDATE SET name = EXCLUDED.name
            RETURNING *
        """, wallet.name, wallet.address.lower(), wallet.chain, wallet.wallet_type, wallet.notes)
        return dict(row)


@app.get("/wallets/{wallet_id}")
async def get_wallet(wallet_id: str):
    """Get wallet details with balances"""
    async with pool.acquire() as conn:
        wallet = await conn.fetchrow(
            "SELECT * FROM satoshi_wallets WHERE id = $1::uuid", wallet_id
        )
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        balances = await conn.fetch("""
            SELECT * FROM satoshi_balances WHERE wallet_id = $1::uuid
            ORDER BY value_usd DESC NULLS LAST
        """, wallet_id)

        return {
            **dict(wallet),
            "balances": [dict(b) for b in balances]
        }


@app.delete("/wallets/{wallet_id}")
async def delete_wallet(wallet_id: str):
    """Remove a wallet"""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM satoshi_wallets WHERE id = $1::uuid", wallet_id)
        return {"status": "deleted", "id": wallet_id}


@app.post("/wallets/{wallet_id}/refresh")
async def refresh_wallet(wallet_id: str, background_tasks: BackgroundTasks):
    """Refresh wallet balances"""
    background_tasks.add_task(do_wallet_refresh, wallet_id)
    return {"status": "started", "message": "Wallet refresh running"}


async def do_wallet_refresh(wallet_id: str):
    """Background task to refresh wallet balances"""
    async with pool.acquire() as conn:
        wallet = await conn.fetchrow(
            "SELECT * FROM satoshi_wallets WHERE id = $1::uuid", wallet_id
        )
        if not wallet:
            return

        if wallet['chain'] == 'ethereum':
            await refresh_ethereum_wallet(conn, wallet)
        # Add other chains as needed


async def refresh_ethereum_wallet(conn, wallet: dict):
    """Refresh Ethereum wallet balances using Alchemy or Etherscan"""
    address = wallet['address']

    # Get ETH balance
    if ALCHEMY_API_KEY:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_getBalance",
                        "params": [address, "latest"],
                        "id": 1
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    balance_wei = int(data['result'], 16)
                    balance_eth = balance_wei / 1e18

                    # Get ETH price
                    eth_price = await get_token_price('ethereum')
                    value_usd = balance_eth * eth_price if eth_price else None

                    await conn.execute("""
                        INSERT INTO satoshi_balances
                        (wallet_id, token_symbol, token_name, balance, price_usd, value_usd, last_updated)
                        VALUES ($1::uuid, 'ETH', 'Ethereum', $2, $3, $4, NOW())
                        ON CONFLICT (wallet_id, token_address) DO UPDATE SET
                            balance = EXCLUDED.balance,
                            price_usd = EXCLUDED.price_usd,
                            value_usd = EXCLUDED.value_usd,
                            last_updated = NOW()
                    """, wallet['id'], balance_eth, eth_price, value_usd)
            except Exception:
                pass


# ============ MARKET DATA ============

async def get_token_price(token_id: str) -> Optional[float]:
    """Get token price from CoinGecko"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={"ids": token_id, "vs_currencies": "usd"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return data.get(token_id, {}).get('usd')
    except Exception:
        pass
    return None


@app.get("/market/prices")
async def get_prices(tokens: str = "bitcoin,ethereum,solana"):
    """Get current prices for tokens (comma-separated CoinGecko IDs)"""
    token_list = [t.strip() for t in tokens.split(",")]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": ",".join(token_list),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true"
                },
                timeout=10.0
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch prices")

            return response.json()
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to connect to price API")


@app.get("/market/trending")
async def get_trending():
    """Get trending tokens"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{COINGECKO_BASE}/search/trending",
                timeout=10.0
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch trending")

            data = response.json()
            coins = data.get('coins', [])

            return {
                "trending": [
                    {
                        "name": c['item']['name'],
                        "symbol": c['item']['symbol'],
                        "market_cap_rank": c['item'].get('market_cap_rank'),
                        "price_btc": c['item'].get('price_btc')
                    }
                    for c in coins[:10]
                ],
                "satoshi_says": "These are the tokens the market is watching."
            }
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to connect to trending API")


@app.get("/market/gas")
async def get_gas_prices():
    """Get current gas prices"""
    if not ETHERSCAN_API_KEY:
        return {
            "error": "Etherscan API key not configured",
            "satoshi_says": "Configure ETHERSCAN_API_KEY for gas tracking"
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.etherscan.io/api",
                params={
                    "module": "gastracker",
                    "action": "gasoracle",
                    "apikey": ETHERSCAN_API_KEY
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {})

                gas_price = float(result.get('ProposeGasPrice', 100))

                return {
                    "slow": float(result.get('SafeGasPrice', 0)),
                    "standard": float(result.get('ProposeGasPrice', 0)),
                    "fast": float(result.get('FastGasPrice', 0)),
                    "base_fee": float(result.get('suggestBaseFee', 0)),
                    "timestamp": datetime.now().isoformat(),
                    "satoshi_says": f"Gas is {gas_price} gwei. {'Good time to transact.' if gas_price < 30 else 'Consider waiting for lower gas.'}"
                }
    except Exception:
        pass

    return {"error": "Failed to fetch gas prices"}


# ============ DEFI ============

@app.get("/defi/protocols")
async def list_defi_protocols():
    """Get top DeFi protocols from DefiLlama"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DEFILLAMA_BASE}/protocols",
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch protocols")

            protocols = response.json()[:50]  # Top 50

            return [
                {
                    "name": p['name'],
                    "symbol": p.get('symbol'),
                    "tvl": p.get('tvl'),
                    "chain": p.get('chain'),
                    "category": p.get('category'),
                    "change_1d": p.get('change_1d'),
                    "change_7d": p.get('change_7d')
                }
                for p in protocols
            ]
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to connect to DeFi API")


@app.get("/defi/yields")
async def get_defi_yields(chain: str = "Ethereum", min_tvl: float = 1000000):
    """Get DeFi yield opportunities"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DEFILLAMA_BASE}/pools",
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch yields")

            pools = response.json().get('data', [])

            # Filter and sort
            filtered = [
                p for p in pools
                if p.get('chain') == chain
                and p.get('tvlUsd', 0) >= min_tvl
                and p.get('apy', 0) > 0
            ]

            sorted_pools = sorted(filtered, key=lambda x: x.get('apy', 0), reverse=True)[:20]

            return [
                {
                    "pool": p.get('pool'),
                    "project": p.get('project'),
                    "symbol": p.get('symbol'),
                    "tvl_usd": p.get('tvlUsd'),
                    "apy": p.get('apy'),
                    "apy_base": p.get('apyBase'),
                    "apy_reward": p.get('apyReward'),
                    "reward_tokens": p.get('rewardTokens'),
                    "il_risk": p.get('ilRisk')
                }
                for p in sorted_pools
            ]
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to connect to yields API")


@app.get("/defi/positions")
async def get_defi_positions(wallet_id: Optional[str] = None):
    """Get tracked DeFi positions"""
    async with pool.acquire() as conn:
        if wallet_id:
            rows = await conn.fetch("""
                SELECT d.*, w.name as wallet_name, w.address
                FROM satoshi_defi_positions d
                JOIN satoshi_wallets w ON d.wallet_id = w.id
                WHERE d.wallet_id = $1::uuid
                ORDER BY d.total_value_usd DESC
            """, wallet_id)
        else:
            rows = await conn.fetch("""
                SELECT d.*, w.name as wallet_name, w.address
                FROM satoshi_defi_positions d
                JOIN satoshi_wallets w ON d.wallet_id = w.id
                ORDER BY d.total_value_usd DESC
            """)
        return [dict(r) for r in rows]


# ============ NFTs ============

@app.get("/nfts")
async def get_nfts(wallet_id: Optional[str] = None):
    """Get NFT holdings"""
    async with pool.acquire() as conn:
        if wallet_id:
            rows = await conn.fetch("""
                SELECT n.*, w.name as wallet_name
                FROM satoshi_nfts n
                JOIN satoshi_wallets w ON n.wallet_id = w.id
                WHERE n.wallet_id = $1::uuid
                ORDER BY n.floor_price_usd DESC NULLS LAST
            """, wallet_id)
        else:
            rows = await conn.fetch("""
                SELECT n.*, w.name as wallet_name
                FROM satoshi_nfts n
                JOIN satoshi_wallets w ON n.wallet_id = w.id
                ORDER BY n.floor_price_usd DESC NULLS LAST
            """)
        return [dict(r) for r in rows]


@app.get("/nfts/collections")
async def get_nft_collections():
    """Get top NFT collections from OpenSea (placeholder)"""
    # OpenSea API requires key - this is a placeholder
    return {
        "message": "OpenSea API integration pending",
        "satoshi_says": "NFT data requires OpenSea API key configuration"
    }


# ============ PORTFOLIO ============

@app.get("/portfolio/summary")
async def portfolio_summary():
    """Get complete crypto portfolio summary"""
    async with pool.acquire() as conn:
        # Wallet balances
        wallet_totals = await conn.fetchrow("""
            SELECT COALESCE(SUM(value_usd), 0) as total_wallet_value
            FROM satoshi_balances
        """)

        # DeFi positions
        defi_totals = await conn.fetchrow("""
            SELECT COALESCE(SUM(total_value_usd), 0) as total_defi_value
            FROM satoshi_defi_positions
        """)

        # NFT floor values
        nft_totals = await conn.fetchrow("""
            SELECT COALESCE(SUM(floor_price_usd), 0) as total_nft_value
            FROM satoshi_nfts
        """)

        # By chain
        by_chain = await conn.fetch("""
            SELECT w.chain, COALESCE(SUM(b.value_usd), 0) as value
            FROM satoshi_wallets w
            LEFT JOIN satoshi_balances b ON w.id = b.wallet_id
            GROUP BY w.chain
            ORDER BY value DESC
        """)

        # Top holdings
        top_holdings = await conn.fetch("""
            SELECT token_symbol, SUM(balance) as total_balance,
                   SUM(value_usd) as total_value
            FROM satoshi_balances
            GROUP BY token_symbol
            ORDER BY total_value DESC NULLS LAST
            LIMIT 10
        """)

        wallet_value = float(wallet_totals['total_wallet_value']) if wallet_totals else 0
        defi_value = float(defi_totals['total_defi_value']) if defi_totals else 0
        nft_value = float(nft_totals['total_nft_value']) if nft_totals else 0
        total_value = wallet_value + defi_value + nft_value

        return {
            "total_value_usd": total_value,
            "breakdown": {
                "wallets": wallet_value,
                "defi": defi_value,
                "nfts": nft_value
            },
            "by_chain": {r['chain']: float(r['value']) for r in by_chain},
            "top_holdings": [dict(h) for h in top_holdings],
            "last_updated": datetime.now().isoformat(),
            "satoshi_says": f"Your crypto portfolio is worth ${total_value:,.2f}. WAGMI."
        }


@app.post("/portfolio/snapshot")
async def take_snapshot():
    """Take a daily snapshot"""
    summary = await portfolio_summary()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO satoshi_portfolio_snapshots
            (total_value_usd, wallet_balances_usd, defi_value_usd, nft_floor_value_usd,
             by_chain, top_holdings)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (snapshot_date) DO UPDATE SET
                total_value_usd = EXCLUDED.total_value_usd
            RETURNING *
        """, summary['total_value_usd'], summary['breakdown']['wallets'],
            summary['breakdown']['defi'], summary['breakdown']['nfts'],
            json.dumps(summary['by_chain']), json.dumps(summary['top_holdings']))

        return dict(row)


@app.get("/portfolio/history")
async def portfolio_history(days: int = 30):
    """Get portfolio value history"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM satoshi_portfolio_snapshots
            WHERE snapshot_date >= CURRENT_DATE - $1
            ORDER BY snapshot_date
        """, days)
        return [dict(r) for r in rows]


# ============ WATCHLIST & ALERTS ============

@app.get("/watchlist")
async def get_watchlist():
    """Get crypto watchlist"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM satoshi_watchlist ORDER BY symbol")

        # Enrich with current prices
        if rows:
            token_ids = [r['token_id'] for r in rows]
            prices = {}

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{COINGECKO_BASE}/simple/price",
                        params={"ids": ",".join(token_ids), "vs_currencies": "usd"},
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        prices = response.json()
            except Exception:
                pass

            return [
                {
                    **dict(r),
                    "current_price": prices.get(r['token_id'], {}).get('usd')
                }
                for r in rows
            ]

        return []


@app.post("/watchlist/{token_id}")
async def add_to_watchlist(
    token_id: str,
    symbol: str,
    name: Optional[str] = None,
    target_buy: Optional[float] = None,
    target_sell: Optional[float] = None
):
    """Add token to watchlist"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO satoshi_watchlist (token_id, symbol, name, target_buy_price, target_sell_price)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (token_id) DO UPDATE SET
                target_buy_price = EXCLUDED.target_buy_price,
                target_sell_price = EXCLUDED.target_sell_price
            RETURNING *
        """, token_id, symbol.upper(), name, target_buy, target_sell)
        return dict(row)


@app.delete("/watchlist/{token_id}")
async def remove_from_watchlist(token_id: str):
    """Remove token from watchlist"""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM satoshi_watchlist WHERE token_id = $1", token_id)
        return {"status": "removed", "token_id": token_id}


# ============ ALERTS ============

@app.get("/alerts")
async def get_alerts(active_only: bool = True):
    """Get price alerts"""
    async with pool.acquire() as conn:
        if active_only:
            rows = await conn.fetch(
                "SELECT * FROM satoshi_alerts WHERE is_active = TRUE ORDER BY created_at DESC"
            )
        else:
            rows = await conn.fetch("SELECT * FROM satoshi_alerts ORDER BY created_at DESC")
        return [dict(r) for r in rows]


@app.post("/alerts")
async def create_alert(
    alert_type: str,  # price, whale, gas, health_factor
    condition: str,   # above, below, change_pct
    threshold: float,
    token_id: Optional[str] = None,
    wallet_id: Optional[str] = None
):
    """Create an alert"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO satoshi_alerts (alert_type, token_id, wallet_id, condition, threshold)
            VALUES ($1, $2, $3::uuid, $4, $5)
            RETURNING *
        """, alert_type, token_id, wallet_id, condition, threshold)
        return dict(row)


@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert"""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM satoshi_alerts WHERE id = $1::uuid", alert_id)
        return {"status": "deleted", "id": alert_id}


# ============ DEV TOOLS ============

@app.get("/dev/chains")
async def get_supported_chains():
    """Get supported chains and their details"""
    return {
        "chains": [
            {"id": "ethereum", "name": "Ethereum", "chain_id": 1, "native": "ETH", "explorer": "https://etherscan.io"},
            {"id": "polygon", "name": "Polygon", "chain_id": 137, "native": "MATIC", "explorer": "https://polygonscan.com"},
            {"id": "arbitrum", "name": "Arbitrum One", "chain_id": 42161, "native": "ETH", "explorer": "https://arbiscan.io"},
            {"id": "optimism", "name": "Optimism", "chain_id": 10, "native": "ETH", "explorer": "https://optimistic.etherscan.io"},
            {"id": "base", "name": "Base", "chain_id": 8453, "native": "ETH", "explorer": "https://basescan.org"},
            {"id": "solana", "name": "Solana", "chain_id": None, "native": "SOL", "explorer": "https://solscan.io"},
            {"id": "bitcoin", "name": "Bitcoin", "chain_id": None, "native": "BTC", "explorer": "https://blockchain.com"}
        ],
        "satoshi_says": "Multi-chain is the future. One wallet, every chain."
    }


@app.get("/dev/contract/{chain}/{address}")
async def get_contract_info(chain: str, address: str):
    """Get contract information (Etherscan integration)"""
    if chain != "ethereum" or not ETHERSCAN_API_KEY:
        return {"error": "Only Ethereum supported with API key configured"}

    try:
        async with httpx.AsyncClient() as client:
            # Get contract ABI
            response = await client.get(
                "https://api.etherscan.io/api",
                params={
                    "module": "contract",
                    "action": "getsourcecode",
                    "address": address,
                    "apikey": ETHERSCAN_API_KEY
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                result = data.get('result', [{}])[0]

                return {
                    "address": address,
                    "name": result.get('ContractName'),
                    "compiler": result.get('CompilerVersion'),
                    "is_verified": result.get('ABI') != 'Contract source code not verified',
                    "license": result.get('LicenseType'),
                    "proxy": result.get('Proxy') == '1',
                    "implementation": result.get('Implementation')
                }
    except Exception:
        pass

    return {"error": "Failed to fetch contract info"}


@app.post("/dev/decode-tx")
async def decode_transaction(tx_data: str, abi: Optional[str] = None):
    """Decode transaction data (placeholder)"""
    return {
        "message": "Transaction decoding requires ABI",
        "satoshi_says": "Provide the contract ABI to decode this transaction"
    }


# ============ TRANSACTIONS ============

@app.get("/transactions")
async def list_transactions(wallet_id: Optional[str] = None, limit: int = 100):
    """List transactions"""
    async with pool.acquire() as conn:
        if wallet_id:
            rows = await conn.fetch("""
                SELECT t.*, w.name as wallet_name
                FROM satoshi_transactions t
                JOIN satoshi_wallets w ON t.wallet_id = w.id
                WHERE t.wallet_id = $1::uuid
                ORDER BY t.timestamp DESC
                LIMIT $2
            """, wallet_id, limit)
        else:
            rows = await conn.fetch("""
                SELECT t.*, w.name as wallet_name
                FROM satoshi_transactions t
                JOIN satoshi_wallets w ON t.wallet_id = w.id
                ORDER BY t.timestamp DESC
                LIMIT $1
            """, limit)
        return [dict(r) for r in rows]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8206)
