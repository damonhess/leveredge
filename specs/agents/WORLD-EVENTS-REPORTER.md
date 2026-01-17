# IRIS - AI-Powered World Events Reporter Agent

**Agent Type:** News & Information
**Named After:** Iris - The goddess of the rainbow and messenger of the gods, who traveled between realms delivering news and connecting the heavens with the mortal world
**Port:** 8209
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

IRIS is an AI-powered news aggregation and briefing agent that provides personalized, bias-aware news coverage from multiple sources. It serves as the central information hub for LeverEdge, enabling users to stay informed with balanced perspectives and reliable sources.

### Value Proposition
- 90% time savings on daily news consumption with AI-generated briefings
- Transparent bias detection for informed decision-making
- Source reliability scoring prevents misinformation
- Personalized topic tracking for relevant updates only
- Premium feature for enterprise clients ($2K-8K deployments)

---

## CORE CAPABILITIES

### 1. News Aggregation
**Purpose:** Collect and normalize news from multiple sources across topics and regions

**Features:**
- RSS/Atom feed parsing and monitoring
- API integrations with major news providers
- Real-time article ingestion and deduplication
- Multi-language support with translation
- Automatic topic extraction and categorization

**Source Categories:**
| Category | Examples | Update Frequency |
|----------|----------|------------------|
| Wire Services | AP, Reuters, AFP | Real-time |
| Major Outlets | NYT, BBC, Guardian | Hourly |
| Tech News | TechCrunch, Ars Technica | Hourly |
| Finance | Bloomberg, FT, WSJ | Real-time |
| Regional | Local news feeds | Every 2 hours |
| Specialty | Industry-specific | Daily |

### 2. Daily Briefings
**Purpose:** Generate personalized, digestible news summaries tailored to user preferences

**Features:**
- AI-synthesized executive summaries
- Multiple format options (text, bullet points, audio-ready)
- Scheduled delivery at preferred times
- Topic filtering based on subscriptions
- Priority ranking by relevance and importance
- Cross-reference related stories

**Briefing Types:**
- Morning Overview (comprehensive daily start)
- Topic Deep-Dive (focused subject analysis)
- Breaking News Alert (urgent updates)
- Weekly Recap (trend analysis)
- Custom Schedule (user-defined)

### 3. Bias Detection
**Purpose:** Analyze source and article bias to present balanced viewpoints

**Features:**
- Political spectrum analysis (left/center/right)
- Sentiment scoring per article
- Language pattern detection (loaded words, framing)
- Cross-source comparison for same events
- Bias trend tracking per source over time
- Alternative perspective suggestions

**Bias Dimensions:**
| Dimension | Scale | Detection Method |
|-----------|-------|------------------|
| Political | -5 to +5 | Language analysis, sourcing patterns |
| Corporate | 0 to 10 | Advertiser influence, ownership analysis |
| Sensationalism | 0 to 10 | Headline analysis, emotional language |
| Factual Accuracy | 0 to 100% | Claim verification, correction history |

### 4. Source Ranking
**Purpose:** Evaluate and rank news sources by reliability, bias, and quality

**Features:**
- Reliability scoring based on correction history
- Bias rating with transparency reports
- Quality metrics (original reporting vs. aggregation)
- Trust indicators for user guidance
- Community feedback integration
- Historical accuracy tracking

**Rating Factors:**
- Correction policy and frequency
- Source attribution practices
- Fact-checking partnerships
- Editorial independence
- Transparency of ownership
- Track record on major stories

### 5. Topic Tracking
**Purpose:** Monitor specific topics of interest with smart alerts and updates

**Features:**
- Keyword and entity-based tracking
- Related topic discovery
- Trend detection and alerts
- Historical context provision
- Cross-source coverage analysis
- Custom notification thresholds

**Tracking Options:**
- Companies and organizations
- Public figures and personalities
- Industries and sectors
- Geographic regions
- Ongoing events and crises
- Custom keyword combinations

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for analysis, local NLP for classification
Cache: Redis for feed caching
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/iris/
├── iris.py                  # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── sources.yaml         # News source configurations
│   ├── topics.yaml          # Topic definitions and keywords
│   └── bias_models.yaml     # Bias detection parameters
├── modules/
│   ├── aggregator.py        # News collection and parsing
│   ├── briefing_generator.py # AI briefing synthesis
│   ├── bias_analyzer.py     # Bias detection engine
│   ├── source_ranker.py     # Source reliability scoring
│   └── topic_tracker.py     # Topic monitoring system
└── tests/
    └── test_iris.py
```

### Database Schema

```sql
-- News sources table
CREATE TABLE news_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    rss_feed TEXT,
    category TEXT NOT NULL,          -- wire, major, tech, finance, regional, specialty
    bias_rating FLOAT DEFAULT 0,     -- -5 (left) to +5 (right)
    reliability_score FLOAT DEFAULT 50, -- 0-100
    active BOOLEAN DEFAULT TRUE,
    last_fetched TIMESTAMPTZ,
    fetch_frequency_minutes INT DEFAULT 60,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sources_category ON news_sources(category);
CREATE INDEX idx_sources_active ON news_sources(active);
CREATE INDEX idx_sources_reliability ON news_sources(reliability_score DESC);

-- Articles table
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES news_sources(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    summary TEXT,
    full_content TEXT,
    author TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    topics TEXT[] DEFAULT '{}',
    entities JSONB,                   -- extracted people, orgs, locations
    sentiment FLOAT DEFAULT 0,        -- -1 (negative) to +1 (positive)
    bias_score FLOAT DEFAULT 0,       -- -5 to +5
    importance_score FLOAT DEFAULT 50, -- 0-100
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    metadata JSONB
);

CREATE INDEX idx_articles_source ON articles(source_id);
CREATE INDEX idx_articles_published ON articles(published_at DESC);
CREATE INDEX idx_articles_topics ON articles USING GIN(topics);
CREATE INDEX idx_articles_importance ON articles(importance_score DESC);

-- Topics table
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    related_topics TEXT[] DEFAULT '{}',
    importance FLOAT DEFAULT 50,      -- 0-100 global importance
    user_subscribed BOOLEAN DEFAULT FALSE,
    article_count INT DEFAULT 0,
    trending_score FLOAT DEFAULT 0,
    last_article_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_topics_name ON topics(name);
CREATE INDEX idx_topics_trending ON topics(trending_score DESC);
CREATE INDEX idx_topics_subscribed ON topics(user_subscribed);

-- Briefings table
CREATE TABLE briefings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    format TEXT DEFAULT 'summary',    -- summary, bullets, detailed, audio
    briefing_type TEXT DEFAULT 'morning', -- morning, topic, breaking, weekly
    topics TEXT[] DEFAULT '{}',
    articles_included UUID[] DEFAULT '{}',
    content TEXT NOT NULL,
    ai_model TEXT,
    token_count INT,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    feedback JSONB,
    metadata JSONB
);

CREATE INDEX idx_briefings_user ON briefings(user_id);
CREATE INDEX idx_briefings_date ON briefings(date DESC);
CREATE INDEX idx_briefings_type ON briefings(briefing_type);

-- Source ratings table
CREATE TABLE source_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES news_sources(id) ON DELETE CASCADE,
    rating_type TEXT NOT NULL,        -- bias, reliability, quality, factual
    score FLOAT NOT NULL,
    evidence TEXT,
    methodology TEXT,
    confidence FLOAT DEFAULT 0.5,     -- 0-1
    rated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    rated_by TEXT                     -- system, user, third_party
);

CREATE INDEX idx_ratings_source ON source_ratings(source_id);
CREATE INDEX idx_ratings_type ON source_ratings(rating_type);
CREATE INDEX idx_ratings_date ON source_ratings(rated_at DESC);

-- User preferences table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT UNIQUE NOT NULL,
    topics TEXT[] DEFAULT '{}',
    excluded_topics TEXT[] DEFAULT '{}',
    sources TEXT[] DEFAULT '{}',
    excluded_sources TEXT[] DEFAULT '{}',
    briefing_time TIME DEFAULT '07:00',
    briefing_timezone TEXT DEFAULT 'UTC',
    briefing_format TEXT DEFAULT 'summary',
    notification_settings JSONB,
    bias_preference TEXT DEFAULT 'balanced', -- balanced, left_lean, right_lean, all
    language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_prefs_user ON user_preferences(user_id);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + aggregation status
GET /status              # Real-time news pipeline status
GET /metrics             # Prometheus-compatible metrics
```

### News Aggregation
```
GET /news                # Get latest news (filtered, paginated)
GET /news/{id}           # Get specific article details
GET /news/search         # Search articles by keyword/topic
POST /news/fetch         # Force fetch from sources
GET /news/trending       # Get trending stories
```

### Briefings
```
POST /briefings/generate # Generate new briefing
GET /briefings           # List user's briefings
GET /briefings/{id}      # Get specific briefing
GET /briefings/today     # Get today's briefing
POST /briefings/schedule # Schedule recurring briefings
DELETE /briefings/{id}   # Delete briefing
```

### Bias Analysis
```
GET /bias/article/{id}   # Get article bias analysis
GET /bias/source/{id}    # Get source bias profile
POST /bias/analyze       # Analyze custom text for bias
GET /bias/compare        # Compare coverage across sources
GET /bias/spectrum       # Get bias spectrum for topic
```

### Source Management
```
GET /sources             # List all sources
GET /sources/{id}        # Get source details
POST /sources            # Add new source
PUT /sources/{id}        # Update source
DELETE /sources/{id}     # Remove source
GET /sources/rankings    # Get ranked source list
POST /sources/evaluate   # Trigger source evaluation
```

### Topic Tracking
```
GET /topics              # List all topics
GET /topics/{id}         # Get topic with recent articles
POST /topics             # Create/track new topic
PUT /topics/{id}         # Update topic settings
DELETE /topics/{id}      # Stop tracking topic
GET /topics/trending     # Get trending topics
POST /topics/subscribe   # Subscribe to topic alerts
```

### User Preferences
```
GET /preferences         # Get user preferences
PUT /preferences         # Update preferences
POST /preferences/topics # Add tracked topics
DELETE /preferences/topics/{id} # Remove topic
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store news insights
await aria_store_memory(
    memory_type="fact",
    content=f"Trending topic: {topic} with {article_count} articles",
    category="news",
    source_type="agent_result",
    tags=["iris", "trending", topic]
)

# Store bias findings
await aria_store_memory(
    memory_type="observation",
    content=f"Source {source_name} showing {bias_direction} bias trend",
    category="news_analysis",
    source_type="agent_analysis"
)

# Store briefing delivery
await aria_store_memory(
    memory_type="event",
    content=f"Daily briefing generated with {article_count} articles on {topics}",
    category="news",
    source_type="automated"
)
```

### ARIA Tools Integration
ARIA should expose these tools for natural language interaction:

```python
# Tool definitions for ARIA
tools = [
    {
        "name": "news.briefing",
        "description": "Get today's news briefing or generate a new one",
        "parameters": {
            "format": "summary|bullets|detailed",
            "topics": ["optional", "topic", "filters"]
        }
    },
    {
        "name": "news.topic",
        "description": "Get news on a specific topic",
        "parameters": {
            "topic": "topic name or keyword",
            "limit": "number of articles",
            "timeframe": "1h|24h|7d"
        }
    },
    {
        "name": "news.sources",
        "description": "Manage news sources - list, add, remove",
        "parameters": {
            "action": "list|add|remove|evaluate",
            "source": "source name or URL"
        }
    },
    {
        "name": "news.bias",
        "description": "Check source or article bias rating",
        "parameters": {
            "target": "source name or article URL",
            "compare": "optional comparison source"
        }
    },
    {
        "name": "news.track",
        "description": "Track a topic for updates",
        "parameters": {
            "topic": "topic to track",
            "keywords": ["additional", "keywords"],
            "alert_threshold": "breaking|high|all"
        }
    }
]
```

**Routing Triggers:**
```javascript
const irisPatterns = [
  /news|briefing|headlines/i,
  /what('s| is) happening|current events/i,
  /bias|balanced|perspective/i,
  /source (rating|reliability|trust)/i,
  /track(ing)? (topic|story|news)/i,
  /breaking news|trending/i
];
```

### Event Bus Integration
```python
# Published events
"news.briefing.ready"        # Daily briefing generated
"news.breaking"              # Breaking news detected
"news.topic.trending"        # Topic trending above threshold
"news.source.added"          # New source added
"news.source.unreliable"     # Source reliability dropped
"news.bias.shift"            # Source bias shift detected

# Subscribed events
"user.preference.updated"    # Update user news preferences
"system.schedule.trigger"    # Scheduled briefing trigger
"agent.request.news"         # Other agents requesting news context
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("IRIS")

# Log briefing generation costs
await cost_tracker.log_usage(
    endpoint="/briefings/generate",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={
        "briefing_type": briefing_type,
        "article_count": len(articles),
        "topics": topics
    }
)

# Log bias analysis costs
await cost_tracker.log_usage(
    endpoint="/bias/analyze",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"analysis_type": "article_bias"}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(news_context: dict) -> str:
    return f"""You are IRIS - World Events Reporter Agent for LeverEdge AI.

Named after the goddess of the rainbow and messenger of the gods, you bridge the gap between world events and informed decision-making.

## TIME AWARENESS
- Current: {news_context['current_time']}
- Timezone: {news_context['timezone']}
- Days to Launch: {news_context['days_to_launch']}

## YOUR IDENTITY
You are the information hub of LeverEdge. You aggregate news, detect bias, rank sources, and deliver personalized briefings that keep users informed without overwhelming them.

## CURRENT NEWS STATE
- Active Sources: {news_context['active_sources']}
- Articles Today: {news_context['articles_today']}
- Trending Topics: {', '.join(news_context['trending_topics'])}
- Last Briefing: {news_context['last_briefing']}

## YOUR CAPABILITIES

### News Aggregation
- Collect from {news_context['active_sources']} active sources
- Parse RSS feeds and news APIs
- Deduplicate and categorize articles
- Extract entities and topics automatically

### Briefing Generation
- Create personalized daily briefings
- Multiple formats: summary, bullets, detailed
- Filter by user's tracked topics
- Rank by relevance and importance

### Bias Detection
- Analyze political spectrum (-5 to +5)
- Detect sensationalism and loaded language
- Compare coverage across sources
- Suggest alternative perspectives

### Source Ranking
- Score reliability (0-100)
- Track correction history
- Evaluate editorial independence
- Monitor bias trends over time

### Topic Tracking
- Monitor keywords and entities
- Detect trending stories
- Provide historical context
- Alert on significant developments

## TEAM COORDINATION
- Request user context -> MNEMOS (user memory)
- Send notifications -> HERMES
- Store insights -> ARIA via Unified Memory
- Publish events -> Event Bus
- Cross-reference data -> other agents

## RESPONSE PRINCIPLES
1. **Objectivity First**: Present facts before analysis
2. **Bias Transparency**: Always disclose source bias ratings
3. **Multiple Perspectives**: Offer alternative viewpoints
4. **Source Attribution**: Always cite sources
5. **Recency Priority**: Prefer latest information

## BRIEFING FORMAT
When generating briefings:
1. Lead with most important/impactful stories
2. Group by topic or region as appropriate
3. Include bias indicators for each source
4. Provide "Read More" links
5. End with emerging/developing stories

## YOUR MISSION
Keep LeverEdge users informed with accurate, balanced, and relevant news.
Combat information overload with intelligent curation.
Expose bias while respecting all perspectives.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with health endpoints and source management

- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Database schema migration
- [ ] Basic source CRUD operations
- [ ] RSS feed parser module
- [ ] Deploy and test connectivity

**Done When:** IRIS runs, can add sources, and fetch RSS feeds

### Phase 2: News Aggregation (Sprint 3-4)
**Goal:** Automated news collection and storage

- [ ] Implement feed fetching scheduler
- [ ] Article deduplication logic
- [ ] Content extraction and cleaning
- [ ] Topic extraction with NLP
- [ ] Entity recognition (people, orgs, places)
- [ ] Importance scoring algorithm

**Done When:** IRIS continuously collects and stores articles from configured sources

### Phase 3: Briefing Generation (Sprint 5-6)
**Goal:** AI-powered personalized briefings

- [ ] User preferences management
- [ ] Article selection algorithm
- [ ] Claude integration for synthesis
- [ ] Multiple format templates
- [ ] Scheduled briefing generation
- [ ] Delivery via HERMES integration

**Done When:** Users receive daily personalized briefings

### Phase 4: Bias & Source Analysis (Sprint 7-8)
**Goal:** Comprehensive bias detection and source ranking

- [ ] Bias detection model integration
- [ ] Source reliability scoring
- [ ] Cross-source comparison
- [ ] Alternative perspective suggestions
- [ ] Bias trend tracking
- [ ] Trust indicators in UI

**Done When:** Every article and source has transparent bias ratings

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 10 | 1-2 |
| News Aggregation | 6 | 14 | 3-4 |
| Briefing Generation | 6 | 16 | 5-6 |
| Bias & Source Analysis | 6 | 14 | 7-8 |
| **Total** | **24** | **54** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Aggregate from 50+ sources with < 5 minute latency
- [ ] Generate briefings in < 30 seconds
- [ ] Bias scoring on all articles with 85%+ accuracy
- [ ] Topic tracking with real-time alerts
- [ ] Zero missed scheduled briefings

### Quality
- [ ] 99% uptime for news collection
- [ ] < 3% duplicate articles
- [ ] User satisfaction > 4.0/5.0 on briefings
- [ ] Source reliability scores validated against third-party ratings

### Integration
- [ ] ARIA can query news via natural language
- [ ] Events publish to Event Bus reliably
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per briefing and analysis
- [ ] HERMES delivers notifications correctly

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits from sources | Incomplete coverage | Implement caching, respect rate limits, diversify sources |
| Bias model inaccuracy | User distrust | Use multiple indicators, allow user feedback, transparent methodology |
| Information overload | User disengagement | Smart filtering, importance scoring, customizable volume |
| Source availability | Missing news | Monitor source health, automatic fallbacks, redundant sources |
| AI hallucination in summaries | Misinformation | Fact-grounding, source attribution, confidence indicators |

---

## GIT COMMIT

```
Add IRIS - AI-powered world events reporter agent spec

- News aggregation from multiple sources
- Personalized AI-generated briefings
- Bias detection and transparency
- Source reliability ranking
- Topic tracking with alerts
- 4-phase implementation plan
- Full database schema
- Integration with ARIA tools, Unified Memory, Event Bus
- Cost tracking for all AI operations
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/WORLD-EVENTS-REPORTER.md

Context: Build IRIS world events reporter agent. Start with Phase 1 foundation.
```
