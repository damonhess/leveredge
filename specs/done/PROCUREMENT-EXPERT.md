# PROCUREMENT EXPERT - AI-Powered Shopping Research & Purchase Intelligence Agent

**Agent Type:** Commerce & Procurement
**Named After:** Hermes - the messenger god, also god of commerce, trade, and merchants - PROCUREMENT EXPERT facilitates smart commerce decisions for users
**Port:** 8206
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

PROCUREMENT EXPERT is an AI-powered shopping research and purchase intelligence agent that helps users make informed buying decisions through product research, price comparison, deal tracking, and purchase history management. It serves as the central commerce brain for personal and household procurement optimization.

### Value Proposition
- 30% average savings through intelligent price comparison
- Never miss a deal with automated price drop alerts
- Warranty tracking prevents costly out-of-warranty repairs
- Purchase history enables smart reorder decisions
- Wishlist budget management keeps spending in check

---

## CORE CAPABILITIES

### 1. Shopping Research
**Purpose:** AI-powered product research across vendors and marketplaces

**Features:**
- Multi-vendor product search and comparison
- Specification extraction and normalization
- Review aggregation and sentiment analysis
- Alternative product recommendations
- Brand and model comparison matrices

**Research Categories:**
| Category | Data Points | Sources |
|----------|-------------|---------|
| Electronics | Specs, reviews, warranties | Amazon, Best Buy, Newegg |
| Appliances | Energy ratings, dimensions, features | Home Depot, Lowes, Amazon |
| Groceries | Price per unit, nutrition, availability | Instacart, Walmart, Costco |
| Household | Quality ratings, value scores | Target, Amazon, Costco |
| Clothing | Size guides, materials, care | Various retailers |
| Tools | Durability, warranty, accessories | Home Depot, Harbor Freight |

### 2. Price Comparison
**Purpose:** Real-time price tracking and comparison across retailers

**Features:**
- Live price fetching from multiple vendors
- Historical price charting
- Price trend analysis (rising/falling/stable)
- Best time to buy recommendations
- Total cost calculation (including shipping, tax)

**Price Tracking Metrics:**
- Current price
- 30/60/90-day average
- All-time low
- Typical price range
- Price volatility score

### 3. Purchase Recommendations
**Purpose:** AI-driven purchase decision support

**Features:**
- Value score calculation (quality/price ratio)
- Need vs. want analysis
- Budget impact assessment
- Alternative suggestions at different price points
- "Wait or buy now" recommendations

**Recommendation Factors:**
- Price history trends
- Upcoming sales events
- Product lifecycle stage
- User budget constraints
- Urgency of need

### 4. Deal Tracking
**Purpose:** Automated monitoring for deals, price drops, and coupons

**Features:**
- Wishlist price monitoring
- Automatic coupon discovery
- Flash sale alerts
- Price drop notifications
- Deal quality scoring (real deal vs. fake discount)

**Alert Triggers:**
| Event | Notification | Priority |
|-------|--------------|----------|
| Price drops > 20% | Immediate | High |
| Price drops 10-20% | Daily digest | Medium |
| Coupon found | Immediate | Medium |
| Back in stock | Immediate | High |
| Sale event starts | 24h before | Medium |

### 5. Purchase History
**Purpose:** Comprehensive purchase tracking for warranty, reorder, and analysis

**Features:**
- Receipt and invoice storage
- Warranty expiration tracking
- Reorder reminders for consumables
- Spending analytics and budgeting
- Return window tracking

**Tracked Data:**
- Purchase date and vendor
- Price paid and payment method
- Warranty period and expiration
- Receipt/invoice images
- Product satisfaction rating

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for analysis, price prediction
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/procurement-expert/
├── procurement_expert.py      # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── vendors.yaml           # Vendor configurations
│   ├── categories.yaml        # Product category mappings
│   └── alerts.yaml            # Alert thresholds
├── modules/
│   ├── product_researcher.py  # Product research engine
│   ├── price_tracker.py       # Price monitoring
│   ├── deal_hunter.py         # Deal and coupon finder
│   ├── purchase_logger.py     # Purchase history management
│   └── recommendation_engine.py # AI purchase recommendations
└── tests/
    └── test_procurement_expert.py
```

### Database Schema

```sql
-- Products catalog
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,          -- electronics, appliances, grocery, etc.
    brand TEXT,
    model TEXT,
    specs JSONB,                     -- normalized specifications
    notes TEXT,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_name ON products USING gin(to_tsvector('english', name));

-- Price history tracking
CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    vendor TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    url TEXT,
    in_stock BOOLEAN DEFAULT TRUE,
    shipping_cost DECIMAL(10,2),
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_price_product ON price_history(product_id);
CREATE INDEX idx_price_vendor ON price_history(vendor);
CREATE INDEX idx_price_scraped ON price_history(scraped_at DESC);

-- User purchases
CREATE TABLE purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    product_id UUID REFERENCES products(id),
    vendor TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    quantity INTEGER DEFAULT 1,
    purchase_date DATE NOT NULL,
    warranty_months INTEGER,
    warranty_expires DATE,
    receipt_url TEXT,
    return_window_expires DATE,
    satisfaction_rating INTEGER CHECK (satisfaction_rating BETWEEN 1 AND 5),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_purchases_user ON purchases(user_id);
CREATE INDEX idx_purchases_product ON purchases(product_id);
CREATE INDEX idx_purchases_date ON purchases(purchase_date DESC);
CREATE INDEX idx_purchases_warranty ON purchases(warranty_expires);

-- User wishlists
CREATE TABLE wishlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    items JSONB NOT NULL DEFAULT '[]',   -- [{product_id, target_price, priority, added_at}]
    budget DECIMAL(10,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wishlists_user ON wishlists(user_id);
CREATE INDEX idx_wishlists_active ON wishlists(is_active) WHERE is_active = TRUE;

-- Active deals and coupons
CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    vendor TEXT NOT NULL,
    original_price DECIMAL(10,2) NOT NULL,
    deal_price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) GENERATED ALWAYS AS
        (ROUND((original_price - deal_price) / original_price * 100, 2)) STORED,
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    coupon_code TEXT,
    deal_url TEXT,
    verified BOOLEAN DEFAULT FALSE,
    deal_quality_score INTEGER CHECK (deal_quality_score BETWEEN 1 AND 10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_deals_product ON deals(product_id);
CREATE INDEX idx_deals_vendor ON deals(vendor);
CREATE INDEX idx_deals_valid ON deals(valid_until) WHERE valid_until > NOW();

-- Vendor registry
CREATE TABLE vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    url TEXT,
    rating DECIMAL(3,2) CHECK (rating BETWEEN 0 AND 5),
    notes TEXT,
    categories TEXT[],                -- which product categories they carry
    price_match_policy BOOLEAN DEFAULT FALSE,
    free_shipping_threshold DECIMAL(10,2),
    return_policy_days INTEGER,
    api_supported BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vendors_name ON vendors(name);
CREATE INDEX idx_vendors_categories ON vendors USING gin(categories);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health check
GET /status              # Service status with stats
GET /metrics             # Prometheus-compatible metrics
```

### Product Research
```
POST /research           # Research a product (AI-powered)
GET /products            # List tracked products
GET /products/{id}       # Product detail with price history
POST /products           # Add product to tracking
PUT /products/{id}       # Update product info
DELETE /products/{id}    # Remove product
GET /products/search     # Search products by name/category
```

### Price Comparison
```
POST /compare            # Compare prices across vendors
GET /prices/{product_id} # Price history for product
GET /prices/lowest       # Current lowest prices
GET /prices/trends       # Price trend analysis
POST /prices/check       # Force price check for product
```

### Deal Tracking
```
GET /deals               # List active deals
GET /deals/{id}          # Deal detail
POST /deals/track        # Track a deal
GET /deals/expiring      # Deals expiring soon
POST /deals/verify       # Verify deal is still active
GET /coupons             # Available coupons
POST /coupons/search     # Search for coupons
```

### Purchase History
```
POST /purchases          # Log a purchase
GET /purchases           # List user purchases
GET /purchases/{id}      # Purchase detail
PUT /purchases/{id}      # Update purchase info
GET /purchases/warranty  # Check warranty status
GET /purchases/expiring  # Warranties expiring soon
GET /purchases/stats     # Purchase statistics
POST /purchases/receipt  # Upload receipt
```

### Wishlists
```
GET /wishlists           # List user wishlists
POST /wishlists          # Create wishlist
GET /wishlists/{id}      # Wishlist detail
PUT /wishlists/{id}      # Update wishlist
DELETE /wishlists/{id}   # Delete wishlist
POST /wishlists/{id}/items    # Add item to wishlist
DELETE /wishlists/{id}/items/{item_id}  # Remove item
```

### Vendors
```
GET /vendors             # List vendors
GET /vendors/{id}        # Vendor detail
POST /vendors            # Add vendor
PUT /vendors/{id}        # Update vendor
GET /vendors/best        # Best vendors by category
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store shopping insights
await aria_store_memory(
    memory_type="fact",
    content=f"Best price for {product_name}: ${price} at {vendor}",
    category="shopping",
    source_type="agent_result",
    tags=["procurement-expert", "price"]
)

# Store purchase decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Purchased {product_name} from {vendor} for ${price}",
    category="shopping",
    source_type="user_action"
)

# Store preferences
await aria_store_memory(
    memory_type="preference",
    content=f"User prefers {vendor} for {category} purchases",
    category="shopping",
    source_type="inferred"
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "What's the best price for [product]?"
- Request "Track this deal for me"
- Query "When does my [product] warranty expire?"
- Get alerted on price drops and expiring warranties

**Routing Triggers (ARIA Tools):**
```python
# shop.research - Research a product
{
    "tool": "shop.research",
    "description": "Research a product across vendors",
    "parameters": {
        "query": "product search query",
        "category": "optional category filter",
        "budget": "optional max price"
    }
}

# shop.compare - Compare prices
{
    "tool": "shop.compare",
    "description": "Compare prices for a product across retailers",
    "parameters": {
        "product_id": "product to compare",
        "include_shipping": "include shipping in comparison"
    }
}

# shop.track_deal - Track a deal
{
    "tool": "shop.track_deal",
    "description": "Track a deal or set price alert",
    "parameters": {
        "product_id": "product to track",
        "target_price": "alert when price drops below",
        "vendor": "optional specific vendor"
    }
}

# shop.log_purchase - Log a purchase
{
    "tool": "shop.log_purchase",
    "description": "Log a purchase for tracking",
    "parameters": {
        "product_name": "what was purchased",
        "vendor": "where purchased",
        "price": "purchase price",
        "warranty_months": "warranty period"
    }
}

# shop.warranty - Check warranty status
{
    "tool": "shop.warranty",
    "description": "Check warranty status for purchases",
    "parameters": {
        "product_id": "optional specific product",
        "expiring_days": "show warranties expiring within N days"
    }
}
```

**Routing Patterns:**
```javascript
const procurementExpertPatterns = [
  /price (check|compare|comparison|track)/i,
  /best (price|deal|value)/i,
  /buy|purchase|shop|shopping/i,
  /warranty|receipt/i,
  /deal|coupon|discount|sale/i,
  /wishlist|want to buy/i,
  /how much (does|is|for)/i
];
```

### Event Bus Integration
```python
# Published events
"shop.deal.found"          # New deal discovered
"shop.price.dropped"       # Price dropped on tracked item
"shop.warranty.expiring"   # Warranty expiring soon
"shop.purchase.logged"     # New purchase recorded
"shop.wishlist.updated"    # Wishlist changed
"shop.stock.available"     # Out of stock item available

# Subscribed events
"user.query.shopping"      # Shopping-related query from ARIA
"calendar.reminder.set"    # For warranty expiration reminders
"finance.budget.updated"   # Budget constraints changed
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("PROCUREMENT_EXPERT")

# Log AI research costs
await cost_tracker.log_usage(
    endpoint="/research",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"product_category": category}
)

# Log price comparison costs
await cost_tracker.log_usage(
    endpoint="/compare",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"vendors_compared": vendor_count}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(shopping_context: dict) -> str:
    return f"""You are PROCUREMENT EXPERT - Smart Shopping Agent for LeverEdge AI.

Named after Hermes, the messenger god and deity of commerce and trade, you help users make intelligent purchasing decisions through research, price comparison, and deal tracking.

## TIME AWARENESS
- Current: {shopping_context['current_time']}
- Upcoming Sales: {shopping_context['upcoming_sales']}

## YOUR IDENTITY
You are the commerce intelligence brain of LeverEdge. You research products, track prices, find deals, and ensure users never overpay or miss a good deal.

## CURRENT CONTEXT
- Active Wishlists: {shopping_context['active_wishlists']}
- Tracked Products: {shopping_context['tracked_products']}
- Pending Deals: {shopping_context['active_deals']}
- Expiring Warranties: {shopping_context['expiring_warranties']}

## YOUR CAPABILITIES

### Shopping Research
- Search and compare products across vendors
- Extract and normalize specifications
- Aggregate reviews and ratings
- Recommend alternatives at various price points
- Analyze product quality and value

### Price Comparison
- Track prices across multiple retailers
- Analyze historical price trends
- Calculate true total cost (shipping, tax)
- Identify best time to buy
- Detect fake discounts vs. real deals

### Deal Tracking
- Monitor wishlists for price drops
- Find applicable coupon codes
- Alert on flash sales
- Score deal quality
- Track limited-time offers

### Purchase History
- Log all purchases with receipts
- Track warranty expirations
- Calculate spending by category
- Suggest reorders for consumables
- Monitor return windows

### Warranty Management
- Track warranty periods
- Alert before expiration
- Store warranty documents
- Recommend extended warranties

## TEAM COORDINATION
- Store purchase insights -> Unified Memory
- Calendar reminders for warranties -> CHRONOS
- Send deal alerts -> HERMES
- Budget tracking -> FORTUNA (Finance Agent)
- Publish events -> Event Bus

## RESPONSE FORMAT
For product research:
1. Product overview and specs
2. Price comparison table
3. Pros and cons analysis
4. Value recommendation
5. Best purchase timing

For deal alerts:
1. Deal summary
2. Discount analysis (real vs. fake)
3. Historical price context
4. Time sensitivity
5. Action recommendation

## YOUR MISSION
Help users spend smarter, not more.
Find the best value, not just the lowest price.
Track everything so nothing expires forgotten.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with product tracking and manual price logging

- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Database schema deployment
- [ ] Basic product CRUD operations
- [ ] Manual price entry functionality
- [ ] Deploy and test

**Done When:** Can manually add products and log prices

### Phase 2: Price Comparison (Sprint 3-4)
**Goal:** Automated price tracking and comparison

- [ ] Vendor registry implementation
- [ ] Price fetching module (API-based)
- [ ] Price history storage and retrieval
- [ ] Price comparison across vendors
- [ ] Historical price charting
- [ ] Price trend analysis

**Done When:** Can compare prices across multiple vendors with history

### Phase 3: Deal Tracking (Sprint 5-6)
**Goal:** Automated deal discovery and alerts

- [ ] Deal detection logic
- [ ] Coupon code discovery
- [ ] Wishlist price monitoring
- [ ] Price drop notifications
- [ ] Deal quality scoring
- [ ] Event Bus integration for alerts

**Done When:** Automatic alerts when wishlist items drop in price

### Phase 4: Purchase Intelligence (Sprint 7-8)
**Goal:** Full purchase tracking and AI recommendations

- [ ] Purchase logging with receipt storage
- [ ] Warranty tracking and alerts
- [ ] AI-powered purchase recommendations
- [ ] Spending analytics
- [ ] ARIA tool integration
- [ ] Unified Memory integration

**Done When:** Full purchase lifecycle tracking with AI insights

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 10 | 1-2 |
| Price Comparison | 6 | 14 | 3-4 |
| Deal Tracking | 6 | 12 | 5-6 |
| Purchase Intelligence | 6 | 14 | 7-8 |
| **Total** | **24** | **50** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Product research returns results within 5 seconds
- [ ] Price comparison across 5+ vendors simultaneously
- [ ] Deal alerts within 1 hour of price drop
- [ ] Warranty expiration alerts 30/14/7 days before

### Quality
- [ ] 95%+ uptime
- [ ] < 5% false positive rate on deal quality
- [ ] Price accuracy within 2% of actual
- [ ] All purchases tracked with receipts

### Integration
- [ ] ARIA can query prices and log purchases
- [ ] Events publish to Event Bus
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per request

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Vendor API rate limits | Incomplete price data | Implement caching, multiple API keys |
| Price scraping blocked | Stale price data | Use official APIs where available |
| False deal detection | User trust erosion | Historical price verification |
| Receipt storage limits | Lost purchase records | Cloud storage integration |
| Vendor coverage gaps | Incomplete comparisons | Prioritize major retailers first |

---

## GIT COMMIT

```
Add PROCUREMENT EXPERT - AI-powered shopping research agent spec

- Product research across vendors
- Price comparison and tracking
- Deal and coupon discovery
- Purchase history with warranty tracking
- Wishlist management with budget tracking
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/PROCUREMENT-EXPERT.md

Context: Build PROCUREMENT EXPERT shopping research agent. Start with Phase 1 foundation.
```
