"""
LITTLEFINGER - Master of Coin
Port: 8020
Domain: THE KEEP

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
import json

app = FastAPI(
    title="LITTLEFINGER - Master of Coin",
    description="Chaos isn't a pit. Chaos is a ladder. And money? Money is the rungs.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
EVENT_BUS_URL = os.environ.get("EVENT_BUS_URL", "http://event-bus:8099")
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


class SubscriptionCreate(BaseModel):
    name: str
    vendor: str
    amount: float
    billing_interval: str = "monthly"
    category: Optional[str] = None


# ============ HEALTH ============

@app.get("/health")
async def health():
    db_status = "connected" if pool else "no connection"
    return {
        "status": "healthy",
        "service": "LITTLEFINGER - Master of Coin",
        "port": 8020,
        "database": db_status,
        "tagline": "Chaos isn't a pit. Chaos is a ladder. And money? Money is the rungs."
    }


# ============ DASHBOARD ============

@app.get("/status")
async def financial_status():
    """Get complete financial status"""
    if not pool:
        return {
            "mrr": 0,
            "revenue_mtd": 0,
            "expenses_mtd": 0,
            "profit_mtd": 0,
            "outstanding": 0,
            "active_clients": 0,
            "monthly_subscriptions": 0,
            "goal": None,
            "goal_progress_pct": 0,
            "pending_invoices": [],
            "littlefinger_says": "The coffers are empty. Time to change that."
        }

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
            goal_progress = (float(snapshot['mrr']) / float(goal['target_value'])) * 100

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
    elif goal and mrr >= float(goal['target_value']):
        return f"We've reached ${mrr:,.0f} MRR. The goal is achieved. But why stop here?"
    elif goal:
        remaining = float(goal['target_value']) - mrr
        days_left = (goal['target_date'] - date.today()).days
        return f"${remaining:,.0f} to go in {days_left} days. The ladder awaits."
    else:
        return f"Current MRR: ${mrr:,.0f}. Every coin counts."


# ============ CLIENTS ============

@app.get("/clients")
async def list_clients(status: str = None):
    """List all clients"""
    if not pool:
        return []

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
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO littlefinger_clients (name, company, email, payment_terms, default_hourly_rate)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, client.name, client.company, client.email,
            client.payment_terms, client.default_hourly_rate)

        await publish_event("client.created", {"name": client.name})
        return dict(row)


@app.get("/clients/{client_id}")
async def get_client(client_id: str):
    """Get client details"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM littlefinger_clients WHERE id = $1",
            client_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Client not found")
        return dict(row)


# ============ INVOICES ============

@app.get("/invoices")
async def list_invoices(status: str = None, client_id: str = None):
    """List invoices"""
    if not pool:
        return []

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
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

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
        """, invoice_number, invoice.client_id, json.dumps(invoice.line_items),
            subtotal, due_date, invoice.notes)

        await publish_event("invoice.created", {
            "invoice_number": invoice_number,
            "total": subtotal
        })
        return dict(row)


@app.post("/invoices/{invoice_id}/send")
async def send_invoice(invoice_id: str):
    """Mark invoice as sent"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

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
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        invoice = await conn.fetchrow("SELECT * FROM littlefinger_invoices WHERE id = $1", invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        paid_amount = amount or float(invoice['total'])
        new_status = 'paid' if paid_amount >= float(invoice['total']) else 'partial'

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

        await publish_event("invoice.paid", {
            "invoice_number": invoice['invoice_number'],
            "amount": paid_amount
        })

        return {"status": new_status, "amount_paid": paid_amount}


# ============ EXPENSES ============

@app.get("/expenses")
async def list_expenses(category: str = None, month: str = None):
    """List expenses"""
    if not pool:
        return []

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
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO littlefinger_expenses
            (category, vendor, description, amount, expense_date, is_recurring, recurring_interval, tax_deductible)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """, expense.category, expense.vendor, expense.description,
            expense.amount, expense.expense_date or date.today(),
            expense.is_recurring, expense.recurring_interval, expense.tax_deductible)

        await publish_event("expense.added", {
            "vendor": expense.vendor,
            "amount": expense.amount,
            "category": expense.category
        })
        return dict(row)


# ============ REVENUE ============

@app.get("/revenue")
async def list_revenue(month: str = None, source_type: str = None):
    """List revenue"""
    if not pool:
        return []

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
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

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

        await publish_event("revenue.added", {
            "amount": revenue.amount,
            "is_recurring": revenue.is_recurring
        })

        return dict(row)


# ============ MRR ============

@app.get("/mrr")
async def get_mrr():
    """Get MRR breakdown"""
    if not pool:
        return {
            "total_mrr": 0,
            "breakdown": [],
            "target": 30000,
            "progress_pct": 0,
            "littlefinger_says": "No revenue yet. Time to climb the ladder."
        }

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

        goal = await conn.fetchrow("""
            SELECT target_value, target_date
            FROM littlefinger_goals
            WHERE goal_type = 'mrr' AND status = 'active'
            LIMIT 1
        """)

        target = float(goal['target_value']) if goal else 30000
        progress = round((float(total_mrr or 0) / target) * 100, 1)

        return {
            "total_mrr": float(total_mrr or 0),
            "breakdown": [dict(b) for b in breakdown],
            "target": target,
            "target_date": str(goal['target_date']) if goal else "2026-03-01",
            "progress_pct": progress,
            "littlefinger_says": f"${float(total_mrr or 0):,.0f} of ${target:,.0f} target. {100 - progress:.1f}% to go."
        }


# ============ SUBSCRIPTIONS ============

@app.get("/subscriptions")
async def list_subscriptions():
    """List active subscriptions"""
    if not pool:
        return {"subscriptions": [], "total_monthly": 0}

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM littlefinger_subscriptions
            WHERE status = 'active'
            ORDER BY monthly_equivalent DESC
        """)

        total = sum(float(row['monthly_equivalent'] or 0) for row in rows)

        return {
            "subscriptions": [dict(row) for row in rows],
            "total_monthly": total,
            "littlefinger_says": f"${total:,.0f}/month in subscriptions. Every coin that leaves must earn its way back."
        }


@app.post("/subscriptions")
async def add_subscription(sub: SubscriptionCreate):
    """Add subscription"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    monthly_equivalent = sub.amount if sub.billing_interval == 'monthly' else sub.amount / 12

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO littlefinger_subscriptions
            (name, vendor, amount, billing_interval, monthly_equivalent, category, status)
            VALUES ($1, $2, $3, $4, $5, $6, 'active')
            RETURNING *
        """, sub.name, sub.vendor, sub.amount, sub.billing_interval,
            monthly_equivalent, sub.category)

        return dict(row)


# ============ GOALS ============

@app.get("/goals")
async def list_goals():
    """List financial goals"""
    if not pool:
        return []

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
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

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
    if not pool:
        return {"error": "Database not connected"}

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

        profit = float(revenue['total']) - float(expenses['total'])
        margin = round((profit / float(revenue['total'] or 1)) * 100, 1)

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
            "profit": profit,
            "margin_pct": margin,
            "littlefinger_says": f"Profit margin: {margin}%. {'The ladder is strong.' if margin > 20 else 'Room for improvement.'}"
        }


# ============ HELPERS ============

async def publish_event(event_type: str, data: dict):
    """Publish event to Event Bus"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": f"littlefinger.{event_type}",
                    "source": "LITTLEFINGER",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                },
                timeout=5.0
            )
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
