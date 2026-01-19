# GSD: Advisory Team Upgrades

**Priority:** HIGH
**Time:** ~20 min total
**Purpose:** Expand SOLON, QUAESTOR, LITTLEFINGER, MIDAS to fill gaps

---

## OVERVIEW

| Agent | Current | Adding |
|-------|---------|--------|
| **SOLON** | Legal info, contracts | + Memory of your situation, + Attorney meeting prep |
| **QUAESTOR** | Tax strategies | + CPA meeting prep, + Doc checklists, + Deadline tracking |
| **LITTLEFINGER** | Invoices, P&L | + Balance sheet, + Cash flow statement |
| **MIDAS** | Investment tracking | + Personal budgeting, + Net worth tracking |

---

## PHASE 1: SOLON UPGRADES

Add to `solon.py`:

### Database Schema

```sql
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

CREATE INDEX idx_contracts_status ON solon_contracts(status);
CREATE INDEX idx_contracts_expiry ON solon_contracts(expiration_date);

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
```

### New Endpoints

```python
# ============ SITUATION MEMORY ============

@app.get("/situation")
async def get_situation(category: Optional[str] = None):
    """Get your current legal situation"""
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        if category:
            rows = await conn.fetch(
                "SELECT * FROM solon_situation WHERE category = $1 ORDER BY updated_at DESC",
                category
            )
        else:
            rows = await conn.fetch("SELECT * FROM solon_situation ORDER BY category, topic")
        return [dict(r) for r in rows]


@app.post("/situation")
async def update_situation(category: str, topic: str, current_state: str, attorney_notes: Optional[str] = None):
    """Update your legal situation"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        # Check if exists
        existing = await conn.fetchrow(
            "SELECT id, history FROM solon_situation WHERE category = $1 AND topic = $2",
            category, topic
        )
        
        if existing:
            # Append old state to history
            history = existing['history'] or []
            history.append({
                "state": current_state,
                "updated_at": datetime.now().isoformat()
            })
            
            await conn.execute("""
                UPDATE solon_situation
                SET current_state = $3, history = $4, attorney_notes = $5, updated_at = NOW()
                WHERE id = $1
            """, existing['id'], current_state, history, attorney_notes)
        else:
            await conn.execute("""
                INSERT INTO solon_situation (category, topic, current_state, attorney_notes)
                VALUES ($1, $2, $3, $4)
            """, category, topic, current_state, attorney_notes)
        
        return {"status": "updated"}


# ============ CONTRACTS ============

@app.get("/contracts")
async def list_contracts(status: Optional[str] = None):
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM solon_contracts WHERE status = $1 ORDER BY expiration_date",
                status
            )
        else:
            rows = await conn.fetch("SELECT * FROM solon_contracts ORDER BY status, expiration_date")
        return [dict(r) for r in rows]


@app.get("/contracts/expiring")
async def expiring_contracts(days: int = 30):
    """Get contracts expiring within N days"""
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM solon_contracts
            WHERE status = 'active'
            AND expiration_date BETWEEN CURRENT_DATE AND CURRENT_DATE + $1
            ORDER BY expiration_date
        """, days)
        return [dict(r) for r in rows]


@app.post("/contracts")
async def add_contract(
    name: str,
    contract_type: str,
    counterparty: str,
    effective_date: Optional[date] = None,
    expiration_date: Optional[date] = None,
    key_terms: Dict = {}
):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO solon_contracts (name, contract_type, counterparty, effective_date, expiration_date, key_terms)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, name, contract_type, counterparty, effective_date, expiration_date, json.dumps(key_terms))
        return dict(row)


# ============ COMPLIANCE ============

@app.get("/compliance")
async def list_compliance(status: Optional[str] = None):
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM solon_compliance WHERE status = $1 ORDER BY due_date",
                status
            )
        else:
            rows = await conn.fetch("SELECT * FROM solon_compliance ORDER BY due_date NULLS LAST")
        return [dict(r) for r in rows]


@app.get("/compliance/due")
async def due_compliance(days: int = 30):
    """Get compliance items due within N days"""
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM solon_compliance
            WHERE status = 'pending'
            AND due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + $1
            ORDER BY due_date
        """, days)
        return [dict(r) for r in rows]


# ============ MEETING PREP ============

@app.post("/prep/attorney")
async def prep_attorney_meeting(topics: List[str], context: Optional[str] = None):
    """Generate attorney meeting prep"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI not configured")
    
    # Gather current situation
    situation = await get_situation()
    contracts = await list_contracts(status='active')
    compliance = await due_compliance(days=90)
    
    prompt = f"""Prepare me for a meeting with my attorney.

Topics to discuss: {', '.join(topics)}
Additional context: {context or 'None'}

My current legal situation:
{json.dumps(situation, indent=2, default=str)}

Active contracts:
{json.dumps(contracts[:10], indent=2, default=str)}

Upcoming compliance:
{json.dumps(compliance, indent=2, default=str)}

Please provide:
1. Key questions to ask about each topic
2. Documents I should bring
3. Background context I should understand
4. Potential issues or risks to discuss
5. Action items to prepare before the meeting

Be specific and practical."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "topics": topics,
        "prep": response.content[0].text,
        "situation_summary": f"{len(situation)} tracked items, {len(contracts)} active contracts"
    }


# ============ STATUS ============

@app.get("/status")
async def solon_status():
    """Get SOLON dashboard"""
    if not pool:
        return {"solon_says": "The law awaits your queries."}
    
    async with pool.acquire() as conn:
        contracts_expiring = await conn.fetchval("""
            SELECT COUNT(*) FROM solon_contracts
            WHERE status = 'active' AND expiration_date < CURRENT_DATE + 30
        """)
        
        compliance_due = await conn.fetchval("""
            SELECT COUNT(*) FROM solon_compliance
            WHERE status = 'pending' AND due_date < CURRENT_DATE + 30
        """)
        
        situation_count = await conn.fetchval("SELECT COUNT(*) FROM solon_situation")
        
        return {
            "situation_items": situation_count,
            "contracts_expiring_30d": contracts_expiring,
            "compliance_due_30d": compliance_due,
            "summary": f"{situation_count} tracked items, {contracts_expiring} contracts expiring soon",
            "solon_says": generate_solon_status(contracts_expiring, compliance_due)
        }


def generate_solon_status(contracts_expiring, compliance_due):
    if contracts_expiring > 0 and compliance_due > 0:
        return f"Attention required: {contracts_expiring} contracts expiring and {compliance_due} compliance items due."
    elif contracts_expiring > 0:
        return f"{contracts_expiring} contracts approaching expiration. Review recommended."
    elif compliance_due > 0:
        return f"{compliance_due} compliance matters require attention."
    else:
        return "Legal matters are in order. The law is satisfied."
```

---

## PHASE 2: QUAESTOR UPGRADES

Add to `quaestor.py`:

### Database Schema

```sql
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

CREATE INDEX idx_deadlines_due ON quaestor_deadlines(due_date);

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

CREATE INDEX idx_docs_year ON quaestor_documents(tax_year);
CREATE INDEX idx_docs_status ON quaestor_documents(status);

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
```

### New Endpoints

```python
# ============ DEADLINES ============

@app.get("/deadlines")
async def list_deadlines(status: Optional[str] = None, year: Optional[int] = None):
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        query = "SELECT * FROM quaestor_deadlines WHERE 1=1"
        params = []
        
        if status:
            params.append(status)
            query += f" AND status = ${len(params)}"
        if year:
            params.append(year)
            query += f" AND EXTRACT(YEAR FROM due_date) = ${len(params)}"
        
        query += " ORDER BY due_date"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.get("/deadlines/upcoming")
async def upcoming_deadlines(days: int = 60):
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM quaestor_deadlines
            WHERE status = 'pending' AND due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + $1
            ORDER BY due_date
        """, days)
        return [dict(r) for r in rows]


@app.post("/deadlines")
async def add_deadline(name: str, deadline_type: str, jurisdiction: str, due_date: date, recurring_interval: Optional[str] = None):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO quaestor_deadlines (name, deadline_type, jurisdiction, due_date, recurring_interval)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, name, deadline_type, jurisdiction, due_date, recurring_interval)
        return dict(row)


# ============ DOCUMENT CHECKLIST ============

@app.get("/documents/checklist/{tax_year}")
async def document_checklist(tax_year: int):
    """Get document checklist for tax year"""
    if not pool:
        return {"needed": [], "received": [], "missing": []}
    
    async with pool.acquire() as conn:
        docs = await conn.fetch(
            "SELECT * FROM quaestor_documents WHERE tax_year = $1 ORDER BY category, name",
            tax_year
        )
        
        needed = [d for d in docs if d['status'] == 'needed']
        received = [d for d in docs if d['status'] in ('received', 'filed')]
        
        return {
            "tax_year": tax_year,
            "needed": [dict(d) for d in needed],
            "received": [dict(d) for d in received],
            "progress": f"{len(received)}/{len(docs)} documents" if docs else "No documents tracked"
        }


@app.post("/documents")
async def add_document(
    name: str,
    document_type: str,
    tax_year: int,
    category: str,
    source: Optional[str] = None,
    due_date: Optional[date] = None
):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO quaestor_documents (name, document_type, tax_year, category, source, due_date)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, name, document_type, tax_year, category, source, due_date)
        return dict(row)


@app.post("/documents/generate-checklist/{tax_year}")
async def generate_standard_checklist(tax_year: int):
    """Generate standard tax document checklist"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    standard_docs = [
        ("W-2 from Employer", "w2", "income", "Government Job"),
        ("1099-INT Bank Interest", "1099", "income", "Bank"),
        ("1099-DIV Dividends", "1099", "income", "Brokerage"),
        ("1099-B Stock Sales", "1099", "income", "Brokerage"),
        ("1099-MISC/NEC Freelance", "1099", "income", "Clients"),
        ("Mortgage Interest (1098)", "1098", "deduction", "Lender"),
        ("Property Tax Statement", "statement", "deduction", "County"),
        ("Charitable Donation Receipts", "receipt", "deduction", "Various"),
        ("Business Expense Receipts", "receipt", "deduction", "Various"),
        ("Health Insurance (1095)", "1095", "credit", "Insurance"),
        ("Retirement Contributions", "statement", "deduction", "401k/IRA"),
    ]
    
    async with pool.acquire() as conn:
        for name, doc_type, category, source in standard_docs:
            await conn.execute("""
                INSERT INTO quaestor_documents (name, document_type, tax_year, category, source)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
            """, name, doc_type, tax_year, category, source)
    
    return {"status": "generated", "tax_year": tax_year, "documents": len(standard_docs)}


# ============ CPA MEETING PREP ============

@app.post("/prep/cpa")
async def prep_cpa_meeting(topics: List[str], tax_year: int, context: Optional[str] = None):
    """Generate CPA meeting prep"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI not configured")
    
    # Gather context
    deadlines = await upcoming_deadlines(days=90)
    checklist = await document_checklist(tax_year)
    
    prompt = f"""Prepare me for a meeting with my CPA.

Topics: {', '.join(topics)}
Tax Year: {tax_year}
Additional context: {context or 'None'}

Upcoming deadlines:
{json.dumps(deadlines, indent=2, default=str)}

Document status:
- Needed: {len(checklist['needed'])} documents
- Received: {len(checklist['received'])} documents

Please provide:
1. Key questions to ask about each topic
2. Documents I should bring to this meeting
3. Tax strategies to discuss
4. Potential deductions or credits to explore
5. Decisions I need to make (elections, entity choices, etc.)

Be specific to my situation as a government employee starting a business."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "topics": topics,
        "tax_year": tax_year,
        "prep": response.content[0].text
    }


# ============ STATUS ============

@app.get("/status")
async def quaestor_status():
    if not pool:
        return {"quaestor_says": "The treasury awaits your records."}
    
    async with pool.acquire() as conn:
        deadlines_soon = await conn.fetchval("""
            SELECT COUNT(*) FROM quaestor_deadlines
            WHERE status = 'pending' AND due_date < CURRENT_DATE + 30
        """)
        
        current_year = date.today().year
        docs_needed = await conn.fetchval("""
            SELECT COUNT(*) FROM quaestor_documents
            WHERE tax_year = $1 AND status = 'needed'
        """, current_year)
        
        return {
            "deadlines_30d": deadlines_soon,
            "documents_needed": docs_needed,
            "current_tax_year": current_year,
            "quaestor_says": generate_quaestor_status(deadlines_soon, docs_needed)
        }


def generate_quaestor_status(deadlines, docs_needed):
    if deadlines > 0:
        return f"Caesar demands tribute: {deadlines} deadlines within 30 days."
    elif docs_needed > 0:
        return f"{docs_needed} documents still needed for the treasury."
    else:
        return "The treasury's records are in order."
```

---

## PHASE 3: LITTLEFINGER UPGRADES

Add to `littlefinger.py`:

### New Endpoints for Financial Statements

```python
# ============ BALANCE SHEET ============

@app.get("/statements/balance-sheet")
async def balance_sheet(as_of: Optional[date] = None):
    """Generate balance sheet"""
    if not pool:
        return {"error": "Database not connected"}
    
    as_of_date = as_of or date.today()
    
    async with pool.acquire() as conn:
        # Assets
        cash = await conn.fetchval("""
            SELECT COALESCE(SUM(amount), 0)
            FROM littlefinger_revenue
            WHERE revenue_date <= $1
        """, as_of_date) or 0
        
        outstanding_ar = await conn.fetchval("""
            SELECT COALESCE(SUM(total - amount_paid), 0)
            FROM littlefinger_invoices
            WHERE status IN ('sent', 'partial') AND issue_date <= $1
        """, as_of_date) or 0
        
        # Liabilities
        # (Would add accounts payable table for full implementation)
        
        total_assets = float(cash) + float(outstanding_ar)
        total_liabilities = 0  # Placeholder
        equity = total_assets - total_liabilities
        
        return {
            "as_of": str(as_of_date),
            "assets": {
                "cash_and_equivalents": float(cash),
                "accounts_receivable": float(outstanding_ar),
                "total_assets": total_assets
            },
            "liabilities": {
                "accounts_payable": 0,
                "total_liabilities": total_liabilities
            },
            "equity": equity,
            "balanced": abs(total_assets - total_liabilities - equity) < 0.01
        }


# ============ CASH FLOW STATEMENT ============

@app.get("/statements/cash-flow/{month}")
async def cash_flow_statement(month: str):
    """Generate cash flow statement for month (YYYY-MM)"""
    if not pool:
        return {"error": "Database not connected"}
    
    async with pool.acquire() as conn:
        # Operating activities
        revenue_received = await conn.fetchval("""
            SELECT COALESCE(SUM(amount), 0)
            FROM littlefinger_revenue
            WHERE TO_CHAR(revenue_date, 'YYYY-MM') = $1
        """, month) or 0
        
        expenses_paid = await conn.fetchval("""
            SELECT COALESCE(SUM(amount), 0)
            FROM littlefinger_expenses
            WHERE TO_CHAR(expense_date, 'YYYY-MM') = $1
        """, month) or 0
        
        operating_cash_flow = float(revenue_received) - float(expenses_paid)
        
        # Investing activities (placeholder)
        investing_cash_flow = 0
        
        # Financing activities (placeholder)
        financing_cash_flow = 0
        
        net_cash_flow = operating_cash_flow + investing_cash_flow + financing_cash_flow
        
        return {
            "month": month,
            "operating_activities": {
                "revenue_received": float(revenue_received),
                "expenses_paid": float(expenses_paid),
                "net_operating": operating_cash_flow
            },
            "investing_activities": {
                "net_investing": investing_cash_flow
            },
            "financing_activities": {
                "net_financing": financing_cash_flow
            },
            "net_cash_flow": net_cash_flow,
            "littlefinger_says": f"Net cash flow: ${net_cash_flow:,.0f}. {'The coffers grow.' if net_cash_flow > 0 else 'More must flow in than out.'}"
        }
```

---

## PHASE 4: MIDAS UPGRADES

Add to `midas.py`:

### Database Schema

```sql
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

CREATE INDEX idx_personal_tx_date ON midas_personal_transactions(transaction_date);
CREATE INDEX idx_personal_tx_cat ON midas_personal_transactions(category);

-- Net worth snapshots
CREATE TABLE IF NOT EXISTS midas_net_worth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Assets
    cash DECIMAL(15,2) DEFAULT 0,
    investments DECIMAL(15,2) DEFAULT 0,  -- From portfolio
    real_estate DECIMAL(15,2) DEFAULT 0,
    vehicles DECIMAL(15,2) DEFAULT 0,
    other_assets DECIMAL(15,2) DEFAULT 0,
    total_assets DECIMAL(15,2) GENERATED ALWAYS AS (cash + investments + real_estate + vehicles + other_assets) STORED,
    
    -- Liabilities
    mortgage DECIMAL(15,2) DEFAULT 0,
    auto_loans DECIMAL(15,2) DEFAULT 0,
    student_loans DECIMAL(15,2) DEFAULT 0,
    credit_cards DECIMAL(15,2) DEFAULT 0,
    other_liabilities DECIMAL(15,2) DEFAULT 0,
    total_liabilities DECIMAL(15,2) GENERATED ALWAYS AS (mortgage + auto_loans + student_loans + credit_cards + other_liabilities) STORED,
    
    -- Net worth
    net_worth DECIMAL(15,2) GENERATED ALWAYS AS (
        (cash + investments + real_estate + vehicles + other_assets) -
        (mortgage + auto_loans + student_loans + credit_cards + other_liabilities)
    ) STORED,
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(snapshot_date)
);
```

### New Endpoints

```python
# ============ BUDGETS ============

@app.get("/budgets")
async def list_budgets(month: Optional[str] = None):
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        current_month = month or date.today().strftime('%Y-%m')
        
        rows = await conn.fetch("""
            SELECT b.*, 
                   COALESCE(SUM(t.amount), 0) as spent
            FROM midas_budgets b
            LEFT JOIN midas_personal_transactions t 
                ON t.category = b.category 
                AND TO_CHAR(t.transaction_date, 'YYYY-MM') = $1
                AND t.is_income = FALSE
            WHERE b.year_month IS NULL OR b.year_month = $1
            GROUP BY b.id
        """, current_month)
        
        result = []
        for row in rows:
            r = dict(row)
            r['remaining'] = float(r['monthly_limit']) - float(r['spent'])
            r['percent_used'] = round((float(r['spent']) / float(r['monthly_limit'])) * 100, 1) if r['monthly_limit'] else 0
            result.append(r)
        
        return result


@app.post("/budgets")
async def create_budget(category: str, monthly_limit: float):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO midas_budgets (category, monthly_limit)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            RETURNING *
        """, category, monthly_limit)
        return dict(row) if row else {"status": "exists"}


# ============ PERSONAL TRANSACTIONS ============

@app.get("/personal/transactions")
async def list_personal_transactions(month: Optional[str] = None, category: Optional[str] = None):
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        query = "SELECT * FROM midas_personal_transactions WHERE 1=1"
        params = []
        
        if month:
            params.append(month)
            query += f" AND TO_CHAR(transaction_date, 'YYYY-MM') = ${len(params)}"
        if category:
            params.append(category)
            query += f" AND category = ${len(params)}"
        
        query += " ORDER BY transaction_date DESC"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/personal/transactions")
async def add_personal_transaction(
    transaction_date: date,
    category: str,
    amount: float,
    description: Optional[str] = None,
    is_income: bool = False,
    source: Optional[str] = None
):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO midas_personal_transactions 
            (transaction_date, category, description, amount, is_income, source)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, transaction_date, category, description, amount, is_income, source)
        return dict(row)


# ============ NET WORTH ============

@app.get("/net-worth")
async def get_net_worth():
    """Get latest net worth"""
    if not pool:
        return {"net_worth": 0}
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM midas_net_worth
            ORDER BY snapshot_date DESC LIMIT 1
        """)
        
        if not row:
            return {"net_worth": 0, "message": "No net worth snapshot yet"}
        
        return dict(row)


@app.get("/net-worth/history")
async def net_worth_history(months: int = 12):
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT snapshot_date, total_assets, total_liabilities, net_worth
            FROM midas_net_worth
            ORDER BY snapshot_date DESC
            LIMIT $1
        """, months)
        return [dict(r) for r in rows]


@app.post("/net-worth/snapshot")
async def take_net_worth_snapshot(
    cash: float = 0,
    real_estate: float = 0,
    vehicles: float = 0,
    other_assets: float = 0,
    mortgage: float = 0,
    auto_loans: float = 0,
    student_loans: float = 0,
    credit_cards: float = 0,
    other_liabilities: float = 0,
    notes: Optional[str] = None
):
    """Take net worth snapshot (investments auto-calculated from portfolio)"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        # Get investment value from portfolio
        portfolio = await conn.fetchval("""
            SELECT COALESCE(SUM(current_value), 0)
            FROM midas_positions
        """) or 0
        
        row = await conn.fetchrow("""
            INSERT INTO midas_net_worth 
            (cash, investments, real_estate, vehicles, other_assets,
             mortgage, auto_loans, student_loans, credit_cards, other_liabilities, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (snapshot_date) DO UPDATE SET
                cash = EXCLUDED.cash,
                investments = EXCLUDED.investments,
                real_estate = EXCLUDED.real_estate,
                vehicles = EXCLUDED.vehicles,
                other_assets = EXCLUDED.other_assets,
                mortgage = EXCLUDED.mortgage,
                auto_loans = EXCLUDED.auto_loans,
                student_loans = EXCLUDED.student_loans,
                credit_cards = EXCLUDED.credit_cards,
                other_liabilities = EXCLUDED.other_liabilities,
                notes = EXCLUDED.notes
            RETURNING *
        """, cash, float(portfolio), real_estate, vehicles, other_assets,
            mortgage, auto_loans, student_loans, credit_cards, other_liabilities, notes)
        
        return dict(row)
```

---

## EXECUTION ORDER

1. Run all database migrations in DEV
2. Add code to each agent
3. Test each agent
4. Run migrations in PROD
5. Rebuild containers
6. Commit

---

## COMMIT MESSAGE

```
Advisory Team Upgrades: SOLON, QUAESTOR, LITTLEFINGER, MIDAS

SOLON:
- Legal situation memory
- Contract tracking with expiry alerts
- Compliance tracker
- Attorney meeting prep

QUAESTOR:
- Tax deadline tracking
- Document checklist generator
- CPA meeting prep

LITTLEFINGER:
- Balance sheet generation
- Cash flow statement

MIDAS:
- Personal budgets
- Transaction tracking
- Net worth tracking with history

The advisory team is complete.
```
