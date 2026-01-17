# PLUTUS - AI-Powered Financial Analysis Agent

**Agent Type:** Financial Analysis & Portfolio Intelligence
**Named After:** Plutus - Greek god of wealth, who distributes riches and prosperity
**Port:** 8205
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

PLUTUS is an AI-powered financial analysis agent providing comprehensive market data analysis, portfolio tracking, technical analysis, and risk assessment. It serves as the financial intelligence brain for LeverEdge users requiring investment insights and portfolio management.

### CRITICAL SAFETY NOTICE

**THIS AGENT PROVIDES ANALYSIS ONLY - NO TRADE EXECUTION CAPABILITY**

PLUTUS is strictly a READ-ONLY analysis tool. It:
- CANNOT execute trades or place orders
- CANNOT move funds or modify positions
- CANNOT access brokerage execution APIs
- CANNOT perform any financial transactions

All trading decisions and executions must be performed manually by the user through their own brokerage platforms.

### Value Proposition
- Real-time market data analysis across stocks, crypto, and forex
- AI-powered technical and fundamental analysis
- Portfolio performance tracking with P&L reporting
- Risk assessment and position sizing recommendations
- Automated price alerts and watchlist management
- Premium pricing tier ($5K-15K deployments)

---

## CORE CAPABILITIES

### 1. Trading Analysis
**Purpose:** AI-powered technical and fundamental analysis for trading opportunities

**Features:**
- Technical indicator analysis (RSI, MACD, Bollinger Bands, Moving Averages)
- Chart pattern recognition (head & shoulders, double tops, triangles)
- Support and resistance level identification
- Volume analysis and trend confirmation
- Multi-timeframe analysis (1m, 5m, 1h, 4h, 1D, 1W)

**Analysis Output:**
| Analysis Type | Components | Confidence Score |
|--------------|------------|------------------|
| Technical | Indicators, patterns, levels | 0-100% |
| Fundamental | Financials, ratios, news sentiment | 0-100% |
| Sentiment | Social media, news, analyst ratings | 0-100% |
| Combined | Weighted aggregate | 0-100% |

**SAFETY:** Analysis results are informational only. No trade recommendations or financial advice provided.

### 2. Market Data
**Purpose:** Real-time and historical market data aggregation and analysis

**Features:**
- Stock market data (NYSE, NASDAQ, global exchanges)
- Cryptocurrency data (major exchanges, DeFi protocols)
- Forex pairs (major, minor, exotic)
- Commodity prices (metals, energy, agriculture)
- Economic indicators and calendar events

**Data Sources:**
- Public market data APIs
- News and sentiment feeds
- Economic calendars
- Earnings reports

### 3. Portfolio Tracking
**Purpose:** Comprehensive portfolio performance monitoring

**Features:**
- Multi-portfolio support (stocks, crypto, forex, mixed)
- Real-time position valuation
- Historical performance tracking
- Asset allocation visualization
- Dividend and income tracking
- Tax lot tracking for cost basis

**Metrics Tracked:**
- Total portfolio value
- Daily/weekly/monthly/yearly returns
- Unrealized and realized P&L
- Portfolio beta and volatility
- Sharpe ratio and risk-adjusted returns

### 4. Risk Assessment
**Purpose:** Quantitative risk analysis and position sizing

**Features:**
- Value at Risk (VaR) calculations
- Maximum drawdown analysis
- Correlation analysis between holdings
- Position sizing recommendations (Kelly criterion, fixed %)
- Portfolio stress testing
- Concentration risk alerts

**Risk Metrics:**
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| VaR 95% | 95% confidence loss limit | > 5% portfolio |
| Max Drawdown | Largest peak-to-trough decline | > 20% |
| Correlation | Asset correlation matrix | > 0.8 concentration |
| Beta | Market sensitivity | > 1.5 high risk |

**SAFETY:** Risk metrics are for informational purposes. Users must make their own risk decisions.

### 5. Reporting
**Purpose:** Comprehensive financial reporting and documentation

**Report Types:**
- Daily portfolio summary
- Weekly performance report
- Monthly P&L statement
- Quarterly tax report preparation
- Annual performance review
- Custom date range reports

**Export Formats:**
- PDF reports
- CSV data export
- JSON API responses
- Integration with accounting tools

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for analysis, local technical indicators
Container: Docker
Market Data: Public APIs (rate-limited)
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/plutus/
├── plutus.py                # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── indicators.yaml      # Technical indicator configs
│   ├── data_sources.yaml    # Market data API configs
│   └── alert_rules.yaml     # Price alert configurations
├── modules/
│   ├── market_data.py       # Market data fetching
│   ├── technical_analysis.py # Technical indicators
│   ├── portfolio_tracker.py # Portfolio management
│   ├── risk_analyzer.py     # Risk calculations
│   └── report_generator.py  # Report creation
└── tests/
    └── test_plutus.py
```

### Database Schema

```sql
-- Portfolios table
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,              -- stocks, crypto, forex, mixed
    broker TEXT,                      -- broker name for reference only
    description TEXT,
    base_currency TEXT DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_portfolios_user ON portfolios(user_id);
CREATE INDEX idx_portfolios_type ON portfolios(type);

-- Positions table (current holdings)
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    asset_type TEXT NOT NULL,         -- stock, crypto, forex, etf, option
    quantity DECIMAL(20, 8) NOT NULL,
    avg_cost DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    market_value DECIMAL(20, 2),
    unrealized_pnl DECIMAL(20, 2),
    unrealized_pnl_pct DECIMAL(10, 4),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(portfolio_id, symbol)
);

CREATE INDEX idx_positions_portfolio ON positions(portfolio_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);

-- Transactions table (trade history - manually entered)
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    type TEXT NOT NULL,               -- buy, sell, dividend, split, transfer
    symbol TEXT NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    fees DECIMAL(20, 4) DEFAULT 0,
    total_amount DECIMAL(20, 2),
    date TIMESTAMPTZ NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_portfolio ON transactions(portfolio_id);
CREATE INDEX idx_transactions_symbol ON transactions(symbol);
CREATE INDEX idx_transactions_date ON transactions(date DESC);

-- Watchlists table
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    symbols TEXT[] NOT NULL DEFAULT '{}',
    alerts JSONB DEFAULT '[]',        -- price alerts config
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_watchlists_user ON watchlists(user_id);

-- Market analysis results
CREATE TABLE market_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    analysis_type TEXT NOT NULL,      -- technical, fundamental, sentiment, combined
    timeframe TEXT,                   -- 1m, 5m, 1h, 4h, 1D, 1W
    result JSONB NOT NULL,            -- analysis results
    confidence DECIMAL(5, 2),         -- 0-100 confidence score
    ai_summary TEXT,                  -- LLM-generated summary
    data_timestamp TIMESTAMPTZ,       -- when market data was captured
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ            -- cache expiration
);

CREATE INDEX idx_analysis_symbol ON market_analysis(symbol);
CREATE INDEX idx_analysis_type ON market_analysis(analysis_type);
CREATE INDEX idx_analysis_created ON market_analysis(created_at DESC);

-- Price alerts
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    symbol TEXT NOT NULL,
    condition TEXT NOT NULL,          -- above, below, crosses_above, crosses_below, pct_change
    target_value DECIMAL(20, 8) NOT NULL,
    current_value DECIMAL(20, 8),
    triggered BOOLEAN DEFAULT FALSE,
    triggered_at TIMESTAMPTZ,
    notification_sent BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_user ON alerts(user_id);
CREATE INDEX idx_alerts_symbol ON alerts(symbol);
CREATE INDEX idx_alerts_active ON alerts(active) WHERE active = TRUE;
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + market data status
GET /status              # Current operational status
GET /metrics             # Prometheus-compatible metrics
```

### Portfolio Management
```
GET /portfolios                    # List user portfolios
POST /portfolios                   # Create new portfolio
GET /portfolios/{id}               # Get portfolio details
PUT /portfolios/{id}               # Update portfolio
DELETE /portfolios/{id}            # Delete portfolio
GET /portfolios/{id}/summary       # Portfolio summary with P&L
GET /portfolios/{id}/performance   # Historical performance
GET /portfolios/{id}/allocation    # Asset allocation breakdown
```

### Position Tracking
```
GET /portfolios/{id}/positions     # List positions
POST /portfolios/{id}/positions    # Add/update position (manual entry)
DELETE /portfolios/{id}/positions/{symbol}  # Remove position
POST /portfolios/{id}/refresh      # Refresh current prices
```

### Transaction History
```
GET /portfolios/{id}/transactions           # List transactions
POST /portfolios/{id}/transactions          # Record transaction (manual)
PUT /portfolios/{id}/transactions/{tx_id}   # Update transaction
DELETE /portfolios/{id}/transactions/{tx_id} # Delete transaction
GET /portfolios/{id}/transactions/export    # Export to CSV
```

### Market Analysis
```
GET /analyze/{symbol}              # Get analysis for symbol
POST /analyze                      # Request new analysis
GET /analyze/{symbol}/technical    # Technical analysis only
GET /analyze/{symbol}/sentiment    # Sentiment analysis only
GET /market/overview               # Market overview (indices, sectors)
GET /market/movers                 # Top gainers/losers
GET /market/calendar               # Economic calendar
```

### Watchlists
```
GET /watchlists                    # List user watchlists
POST /watchlists                   # Create watchlist
GET /watchlists/{id}               # Get watchlist with current prices
PUT /watchlists/{id}               # Update watchlist
DELETE /watchlists/{id}            # Delete watchlist
POST /watchlists/{id}/symbols      # Add symbols
DELETE /watchlists/{id}/symbols/{symbol}  # Remove symbol
```

### Alerts
```
GET /alerts                        # List user alerts
POST /alerts                       # Create price alert
PUT /alerts/{id}                   # Update alert
DELETE /alerts/{id}                # Delete alert
GET /alerts/triggered              # Get triggered alerts
POST /alerts/{id}/acknowledge      # Acknowledge triggered alert
```

### Reporting
```
GET /reports/pnl                   # P&L report
GET /reports/daily                 # Daily summary
GET /reports/performance           # Performance report
GET /reports/tax                   # Tax report preparation
POST /reports/custom               # Custom date range report
GET /reports/{id}/download         # Download report as PDF
```

### Risk Analysis
```
GET /risk/{portfolio_id}           # Portfolio risk metrics
GET /risk/{portfolio_id}/var       # Value at Risk calculation
GET /risk/{portfolio_id}/stress    # Stress test results
GET /risk/{portfolio_id}/correlation  # Correlation matrix
POST /risk/position-size           # Position sizing calculator
```

---

## INTEGRATION REQUIREMENTS

### ARIA Tool Definitions

```python
# ARIA tools for financial analysis
ARIA_TOOLS = {
    "finance.portfolio": {
        "description": "Get portfolio summary and performance",
        "parameters": {
            "portfolio_id": "UUID of the portfolio (optional, returns all if omitted)",
            "include_positions": "Include position details (default: true)"
        },
        "returns": "Portfolio summary with current value, P&L, and positions"
    },
    "finance.analyze": {
        "description": "Analyze a stock, crypto, or forex symbol",
        "parameters": {
            "symbol": "Ticker symbol (e.g., AAPL, BTC-USD, EUR/USD)",
            "analysis_type": "technical, fundamental, sentiment, or combined",
            "timeframe": "Analysis timeframe (1h, 4h, 1D, 1W)"
        },
        "returns": "Analysis results with confidence score and AI summary"
    },
    "finance.watchlist": {
        "description": "Manage watchlist - view, add, or remove symbols",
        "parameters": {
            "action": "get, add, remove",
            "watchlist_id": "UUID of watchlist (optional for get)",
            "symbols": "Symbols to add/remove (array)"
        },
        "returns": "Watchlist with current prices and changes"
    },
    "finance.pnl": {
        "description": "Get profit and loss report",
        "parameters": {
            "portfolio_id": "UUID of portfolio",
            "period": "today, week, month, quarter, year, ytd, all",
            "include_transactions": "Include transaction details"
        },
        "returns": "P&L report with realized/unrealized gains"
    },
    "finance.alert": {
        "description": "Set or manage price alerts",
        "parameters": {
            "action": "create, list, delete, acknowledge",
            "symbol": "Ticker symbol for new alert",
            "condition": "above, below, pct_change",
            "target": "Target price or percentage"
        },
        "returns": "Alert confirmation or list of alerts"
    }
}
```

### Unified Memory Integration
```python
# Store financial insights
await aria_store_memory(
    memory_type="fact",
    content=f"Portfolio {portfolio_name} performance: {return_pct}% YTD",
    category="finance",
    source_type="agent_result",
    tags=["plutus", "portfolio", "performance"]
)

# Store analysis results
await aria_store_memory(
    memory_type="fact",
    content=f"Technical analysis for {symbol}: {signal} signal with {confidence}% confidence",
    category="finance",
    source_type="analysis"
)

# Store user preferences
await aria_store_memory(
    memory_type="preference",
    content=f"User prefers {risk_tolerance} risk tolerance for position sizing",
    category="finance",
    source_type="user_input"
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "How is my portfolio doing?"
- Request "Analyze AAPL for me"
- Query "What's on my watchlist?"
- Get "Show me my P&L for this month"
- Set "Alert me when BTC goes above 50000"

**Routing Triggers:**
```javascript
const plutusPatterns = [
  /portfolio|holdings|positions/i,
  /stock|crypto|forex|trading/i,
  /analyze|analysis|technical/i,
  /watchlist|watch list/i,
  /p&l|pnl|profit|loss|returns/i,
  /price alert|notify.*price/i,
  /market (data|overview|news)/i,
  /risk (assessment|analysis|metrics)/i
];
```

### Event Bus Integration
```python
# Published events
"finance.alert.triggered"          # Price alert triggered
"finance.analysis.completed"       # Analysis completed
"finance.portfolio.updated"        # Portfolio value updated
"finance.position.changed"         # Position added/removed/modified
"finance.report.generated"         # Report ready for download

# Subscribed events
"user.created"                     # Create default portfolio
"scheduler.daily"                  # Daily portfolio refresh
"scheduler.hourly"                 # Hourly alert checks
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("PLUTUS")

# Log AI analysis costs
await cost_tracker.log_usage(
    endpoint="/analyze",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={
        "symbol": symbol,
        "analysis_type": analysis_type
    }
)

# Log market data API costs (if applicable)
await cost_tracker.log_external_api(
    service="market_data_provider",
    endpoint="/quote",
    cost=api_cost,
    metadata={"symbols_count": len(symbols)}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(financial_context: dict) -> str:
    return f"""You are PLUTUS - Financial Analysis Agent for LeverEdge AI.

Named after the Greek god of wealth, you provide intelligent financial analysis and portfolio insights.

## CRITICAL SAFETY NOTICE

**YOU ARE AN ANALYSIS-ONLY AGENT. YOU CANNOT AND WILL NOT:**
- Execute trades or place orders
- Move funds between accounts
- Access brokerage execution APIs
- Make buy/sell recommendations as financial advice
- Guarantee any investment returns

All analysis is for INFORMATIONAL PURPOSES ONLY. Users must make their own investment decisions and execute trades through their own brokerage platforms.

## TIME AWARENESS
- Current: {financial_context['current_time']}
- Market Status: {financial_context['market_status']}
- Days to Launch: {financial_context['days_to_launch']}

## YOUR IDENTITY
You are the financial intelligence brain of LeverEdge. You analyze markets, track portfolios, assess risk, and provide data-driven insights.

## CURRENT FINANCIAL CONTEXT
- Portfolios Tracked: {financial_context['portfolio_count']}
- Total Portfolio Value: {financial_context['total_value']}
- Today's P&L: {financial_context['daily_pnl']}
- Active Alerts: {financial_context['active_alerts']}
- Pending Analysis: {financial_context['pending_analysis']}

## YOUR CAPABILITIES

### Market Analysis
- Fetch real-time market data (stocks, crypto, forex)
- Perform technical analysis (RSI, MACD, patterns)
- Analyze market sentiment and news
- Identify support/resistance levels
- Multi-timeframe analysis

### Portfolio Tracking
- Track multiple portfolios
- Calculate real-time P&L
- Monitor asset allocation
- Track performance over time
- Generate performance reports

### Risk Assessment
- Calculate Value at Risk (VaR)
- Analyze portfolio correlation
- Recommend position sizes (informational only)
- Identify concentration risks
- Perform stress tests

### Alerts & Reporting
- Set and monitor price alerts
- Generate P&L reports
- Create performance summaries
- Export data for tax purposes

## DISCLAIMERS TO INCLUDE
When providing analysis, always include appropriate disclaimers:
- "This is not financial advice"
- "Past performance does not guarantee future results"
- "Please consult a licensed financial advisor"
- "All trading involves risk of loss"

## TEAM COORDINATION
- Route notifications -> HERMES
- Log insights -> ARIA via Unified Memory
- Publish events -> Event Bus
- Request data processing -> HEPHAESTUS (if needed)

## RESPONSE FORMAT
For market analysis:
1. Current price and key metrics
2. Technical indicator summary
3. Support/resistance levels
4. Sentiment overview
5. Confidence score
6. Disclaimer

For portfolio updates:
1. Total value and daily change
2. Top performers/laggards
3. Allocation breakdown
4. Risk metrics
5. Suggested review items (not advice)

## YOUR MISSION
Provide accurate, timely, and insightful financial analysis.
Empower users with data to make informed decisions.
Never provide financial advice or execute transactions.
Always prioritize user education and transparency.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with health endpoints and database setup

- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Set up PostgreSQL schema
- [ ] Basic portfolio CRUD operations
- [ ] Position tracking (manual entry)
- [ ] Deploy and test

**Done When:** PLUTUS runs and can store/retrieve portfolios and positions

### Phase 2: Market Data Integration (Sprint 3-4)
**Goal:** Real-time market data fetching and display

- [ ] Integrate public market data APIs
- [ ] Stock quote fetching (delayed/real-time)
- [ ] Crypto price feeds
- [ ] Forex rate feeds
- [ ] Automatic position price updates
- [ ] Market overview endpoint

**Done When:** Portfolio positions show current market prices

### Phase 3: Technical Analysis (Sprint 5-6)
**Goal:** AI-powered technical analysis

- [ ] Technical indicator calculations
- [ ] Chart pattern recognition
- [ ] Support/resistance detection
- [ ] AI analysis summary generation
- [ ] Multi-timeframe support
- [ ] Analysis caching

**Done When:** Users can get comprehensive technical analysis for any symbol

### Phase 4: Alerts & Reporting (Sprint 7-8)
**Goal:** Price alerts and comprehensive reporting

- [ ] Price alert creation and monitoring
- [ ] Alert notification via HERMES
- [ ] P&L report generation
- [ ] Performance reports
- [ ] Tax report preparation
- [ ] PDF export functionality

**Done When:** Automated alerts trigger and reports generate on demand

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 10 | 1-2 |
| Market Data | 5 | 12 | 3-4 |
| Technical Analysis | 6 | 16 | 5-6 |
| Alerts & Reporting | 6 | 12 | 7-8 |
| **Total** | **23** | **50** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Portfolio tracking with < 5 second price refresh
- [ ] Technical analysis completion in < 10 seconds
- [ ] Price alerts trigger within 60 seconds of condition met
- [ ] Reports generate in < 30 seconds

### Quality
- [ ] 99%+ uptime for analysis endpoints
- [ ] < 1% error rate on market data fetches
- [ ] All financial calculations accurate to 2 decimal places
- [ ] Zero trade execution capability (by design)

### Integration
- [ ] ARIA can query portfolio status via tools
- [ ] Events publish to Event Bus correctly
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per analysis request

### Safety
- [ ] No trade execution endpoints exist
- [ ] All responses include appropriate disclaimers
- [ ] Read-only database access for market data
- [ ] Clear "analysis only" messaging in all outputs

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Market data API rate limits | Delayed data | Multiple data sources, intelligent caching |
| Users misinterpret analysis as advice | Legal liability | Clear disclaimers, no recommendation language |
| Stale price data | Incorrect valuations | Timestamp display, refresh indicators |
| API cost overruns | Budget exceeded | Rate limiting, cost tracking, alerts |
| Data accuracy issues | Wrong P&L calculations | Validation, audit trails, manual override |

---

## SECURITY CONSIDERATIONS

### Data Protection
- User portfolio data encrypted at rest
- No storage of actual brokerage credentials
- Transaction history is user-entered, not connected to brokers
- API keys for market data stored securely in secrets manager

### Access Control
- User isolation (users only see their own portfolios)
- Rate limiting on all endpoints
- Audit logging for all data access
- No admin override for user data

### Compliance Notes
- Not a registered investment advisor
- Not providing personalized financial advice
- For informational and educational purposes only
- Users responsible for their own trading decisions

---

## GIT COMMIT

```
Add PLUTUS - AI-powered financial analysis agent spec

- Trading analysis with technical indicators (READ-ONLY)
- Market data integration (stocks, crypto, forex)
- Portfolio tracking and performance monitoring
- Risk assessment and position sizing calculations
- Price alerts and reporting
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
- SAFETY: Analysis only - no trade execution capability
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/FINANCIAL-ANALYST.md

Context: Build PLUTUS financial analysis agent. Start with Phase 1 foundation.
Note: This is a READ-ONLY analysis agent. No trade execution capability.
```
