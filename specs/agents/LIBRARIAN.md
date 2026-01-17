# LIBRARIAN - AI-Powered Knowledge Management Agent

**Agent Type:** Knowledge & Documentation
**Named After:** Clio - Greek muse of history, keeper of records - LIBRARIAN preserves and organizes all organizational knowledge
**Port:** 8201
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

LIBRARIAN is an AI-powered knowledge management agent providing enterprise-grade SOP management, prompt library curation, document versioning, and semantic search capabilities. It serves as the central knowledge brain for LeverEdge, ensuring that operational procedures, prompts, and institutional knowledge are organized, versioned, and instantly accessible.

### Value Proposition
- 85% reduction in time spent searching for SOPs and documentation
- Version-controlled knowledge prevents conflicting procedures
- Semantic search finds relevant content even with imprecise queries
- Reusable prompt templates accelerate AI workflows
- Knowledge linking reveals hidden connections between documents

---

## CORE CAPABILITIES

### 1. SOPs Management
**Purpose:** Store, version, and retrieve Standard Operating Procedures with full lifecycle management

**Features:**
- Create and store SOPs with rich metadata
- Version control with full history tracking
- Status workflow (draft, review, approved, deprecated)
- Category and tag-based organization
- Approval workflows with change notes
- Template-based SOP creation

**SOP Categories:**
| Category | Description | Examples |
|----------|-------------|----------|
| Development | Code and build procedures | Git workflow, deployment, testing |
| Operations | Day-to-day operations | Incident response, monitoring |
| Security | Security procedures | Access control, audit, compliance |
| Business | Business processes | Client onboarding, billing |
| Integration | System integration | API usage, data sync |
| Emergency | Critical procedures | Disaster recovery, rollback |

### 2. Prompt Library
**Purpose:** Manage reusable prompts with templates, variables, and usage tracking

**Features:**
- Store prompts with template variables
- Category-based organization
- Usage tracking and analytics
- Rating and feedback system
- Variable substitution engine
- Prompt versioning and A/B testing support

**Prompt Structure:**
```yaml
name: "Code Review Prompt"
category: "development"
template: |
  Review the following {{language}} code for:
  - Security vulnerabilities
  - Performance issues
  - Best practice violations

  Code:
  {{code}}

  Focus areas: {{focus_areas}}
variables:
  - language: string
  - code: string
  - focus_areas: string[]
description: "Comprehensive code review prompt"
tags: ["code", "review", "security"]
```

### 3. Knowledge Organization
**Purpose:** Tag, categorize, and link knowledge for maximum discoverability

**Features:**
- Hierarchical category taxonomy
- Multi-tag support with tag suggestions
- Bi-directional document linking
- Link type classification (related, supersedes, references, implements)
- Automatic relationship discovery
- Knowledge graph visualization

**Link Types:**
| Type | Description | Example |
|------|-------------|---------|
| related | General relationship | Two SOPs about similar topics |
| supersedes | Replaces older document | New version replaces old |
| references | Cites or uses | SOP references a template |
| implements | Realizes a concept | Procedure implements policy |
| contradicts | Conflicts with | Flags inconsistencies |

### 4. Versioning
**Purpose:** Track document versions and changes with full audit trail

**Features:**
- Automatic version increment on save
- Full version history with diffs
- Change notes requirement
- Rollback capability
- Branching for draft versions
- Merge conflict detection

**Version Workflow:**
```
Draft (v0.1) -> Review (v0.2) -> Approved (v1.0)
                                      |
                                   Update
                                      v
                              Review (v1.1) -> Approved (v2.0)
```

### 5. Semantic Search
**Purpose:** AI-powered search across all knowledge with understanding of intent

**Features:**
- Vector embedding-based semantic search
- Natural language query understanding
- Multi-field search (title, content, tags)
- Fuzzy matching for typos
- Search result ranking by relevance
- Search analytics and suggestions
- Faceted filtering (category, type, date, author)

**Search Capabilities:**
- "How do we deploy to production?" - finds deployment SOP
- "prompt for reviewing code" - finds code review prompt
- "incident response" - finds related SOPs even without exact match

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Vector Store: pgvector extension
Message Queue: Event Bus (Port 8099)
AI: Claude API for search, summarization, suggestions
Container: Docker
Embeddings: text-embedding-3-small (OpenAI) or Claude embeddings
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/librarian/
├── librarian.py              # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── categories.yaml       # Category taxonomy
│   ├── templates.yaml        # Document templates
│   └── search_config.yaml    # Search tuning parameters
├── modules/
│   ├── sop_manager.py        # SOP CRUD and versioning
│   ├── prompt_library.py     # Prompt template management
│   ├── knowledge_linker.py   # Document linking engine
│   ├── version_control.py    # Version history management
│   ├── semantic_search.py    # Vector search engine
│   └── embedding_service.py  # Text embedding generation
└── tests/
    └── test_librarian.py
```

### Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table (SOPs, guides, policies)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,              -- sop, guide, policy, reference, template
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'draft',     -- draft, review, approved, deprecated
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_documents_type ON documents(type);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX idx_documents_created ON documents(created_at DESC);
CREATE INDEX idx_documents_title_search ON documents USING GIN(to_tsvector('english', title));

-- Document versions history
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    change_notes TEXT,
    UNIQUE(document_id, version)
);

CREATE INDEX idx_versions_document ON document_versions(document_id);
CREATE INDEX idx_versions_changed_at ON document_versions(changed_at DESC);

-- Prompt templates library
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    template TEXT NOT NULL,
    variables TEXT[] DEFAULT '{}',
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_prompts_category ON prompts(category);
CREATE INDEX idx_prompts_usage ON prompts(usage_count DESC);
CREATE INDEX idx_prompts_rating ON prompts(rating DESC);
CREATE INDEX idx_prompts_name_search ON prompts USING GIN(to_tsvector('english', name || ' ' || COALESCE(description, '')));

-- Knowledge links between documents
CREATE TABLE knowledge_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL,         -- related, supersedes, references, implements, contradicts
    context TEXT,                    -- why these are linked
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_doc_id, target_doc_id, link_type)
);

CREATE INDEX idx_links_source ON knowledge_links(source_doc_id);
CREATE INDEX idx_links_target ON knowledge_links(target_doc_id);
CREATE INDEX idx_links_type ON knowledge_links(link_type);

-- Hierarchical categories
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    parent_id UUID REFERENCES categories(id),
    description TEXT,
    icon TEXT,                       -- emoji or icon class
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_categories_parent ON categories(parent_id);

-- Semantic search index with vector embeddings
CREATE TABLE search_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content_chunk TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_document ON search_index(document_id);
CREATE INDEX idx_search_embedding ON search_index USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Prompt usage tracking
CREATE TABLE prompt_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    used_by TEXT,
    used_at TIMESTAMPTZ DEFAULT NOW(),
    variables_used JSONB,
    feedback_rating INTEGER,         -- 1-5 rating
    feedback_notes TEXT
);

CREATE INDEX idx_usage_prompt ON prompt_usage(prompt_id);
CREATE INDEX idx_usage_date ON prompt_usage(used_at DESC);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + knowledge stats
GET /status              # Knowledge base status
GET /metrics             # Prometheus-compatible metrics
```

### Documents & SOPs
```
POST /documents          # Create new document/SOP
GET /documents           # List documents (with filters)
GET /documents/{id}      # Get document by ID
PUT /documents/{id}      # Update document (creates version)
DELETE /documents/{id}   # Soft delete document
GET /documents/{id}/versions    # Get version history
GET /documents/{id}/versions/{v}  # Get specific version
POST /documents/{id}/restore/{v}  # Restore to version
POST /documents/{id}/link        # Link to another document
GET /documents/{id}/links        # Get linked documents
```

### Prompts
```
POST /prompts            # Create new prompt
GET /prompts             # List prompts (with filters)
GET /prompts/{id}        # Get prompt by ID
PUT /prompts/{id}        # Update prompt
DELETE /prompts/{id}     # Delete prompt
POST /prompts/{id}/use   # Record usage and get rendered prompt
POST /prompts/{id}/rate  # Rate a prompt
GET /prompts/popular     # Get most used prompts
GET /prompts/top-rated   # Get highest rated prompts
```

### Categories
```
GET /categories          # List all categories (hierarchical)
POST /categories         # Create category
PUT /categories/{id}     # Update category
DELETE /categories/{id}  # Delete category (if empty)
GET /categories/{id}/documents  # Get documents in category
```

### Search
```
POST /search             # Semantic search across all content
GET /search/suggest      # Get search suggestions
GET /search/recent       # Recent searches
POST /search/index       # Force re-index document
```

### Knowledge Links
```
GET /links               # List all links
POST /links              # Create link between documents
DELETE /links/{id}       # Remove link
GET /links/graph         # Get knowledge graph data
POST /links/discover     # AI-discover potential links
```

---

## ARIA TOOL INTEGRATION

### Tools for ARIA
```python
# library.find - Search for documents/prompts
{
    "name": "library.find",
    "description": "Search the knowledge library for documents, SOPs, or prompts",
    "parameters": {
        "query": "string - natural language search query",
        "type": "string? - filter by type (sop, prompt, guide, policy)",
        "category": "string? - filter by category",
        "limit": "int? - max results (default 10)"
    }
}

# library.get_sop - Get a specific SOP
{
    "name": "library.get_sop",
    "description": "Retrieve a specific SOP by ID or name",
    "parameters": {
        "identifier": "string - SOP ID or exact name",
        "version": "int? - specific version (default latest)"
    }
}

# library.get_prompt - Get a prompt template
{
    "name": "library.get_prompt",
    "description": "Retrieve a prompt template with optional variable substitution",
    "parameters": {
        "name": "string - prompt name or ID",
        "variables": "object? - key-value pairs for template substitution"
    }
}

# library.add_doc - Add a new document
{
    "name": "library.add_doc",
    "description": "Add a new document to the knowledge library",
    "parameters": {
        "type": "string - document type (sop, guide, policy, reference)",
        "title": "string - document title",
        "content": "string - document content (markdown)",
        "category": "string - category name",
        "tags": "string[]? - optional tags"
    }
}

# library.link - Link related documents
{
    "name": "library.link",
    "description": "Create a link between two documents",
    "parameters": {
        "source_id": "string - source document ID",
        "target_id": "string - target document ID",
        "link_type": "string - relationship type (related, supersedes, references, implements)",
        "context": "string? - explanation of the relationship"
    }
}
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store knowledge insights
await aria_store_memory(
    memory_type="fact",
    content=f"SOP '{title}' updated to version {version}",
    category="knowledge",
    source_type="agent_result",
    tags=["librarian", "sop", category]
)

# Store search patterns
await aria_store_memory(
    memory_type="pattern",
    content=f"Users frequently search for '{query}' - may need new SOP",
    category="knowledge",
    source_type="automated"
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "Find me the deployment SOP"
- Request "Get the code review prompt with language=python"
- Query "What SOPs do we have for incident response?"
- Add new knowledge: "Save this as an SOP for database backup"

**Routing Triggers:**
```javascript
const librarianPatterns = [
  /sop|procedure|process|how (do|to)/i,
  /prompt (for|template|library)/i,
  /document|knowledge|guide|policy/i,
  /find (me|the)|search (for)?|look up/i,
  /version|history|changes to/i
];
```

### Event Bus Integration
```python
# Published events
"library.document.created"
"library.document.updated"
"library.document.deprecated"
"library.document.linked"
"library.prompt.created"
"library.prompt.used"
"library.prompt.rated"
"library.search.executed"
"library.category.created"

# Subscribed events
"agent.task.completed"      # Capture learnings as knowledge
"system.error.resolved"     # Document resolution as SOP
"project.milestone.reached" # Update related documentation
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("LIBRARIAN")

# Log AI embedding costs
await cost_tracker.log_usage(
    endpoint="/search",
    model="text-embedding-3-small",
    input_tokens=input_tokens,
    output_tokens=0,
    metadata={"query_length": len(query), "results_count": len(results)}
)

# Log AI summarization costs
await cost_tracker.log_usage(
    endpoint="/documents",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"operation": "summarize", "doc_type": doc_type}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(knowledge_context: dict) -> str:
    return f"""You are LIBRARIAN - Knowledge Management Agent for LeverEdge AI.

Named after Clio, the Greek muse of history and keeper of records, you preserve and organize all organizational knowledge.

## TIME AWARENESS
- Current: {knowledge_context['current_time']}
- Days to Launch: {knowledge_context['days_to_launch']}

## YOUR IDENTITY
You are the knowledge brain of LeverEdge. You manage SOPs, curate prompts, version documents, and ensure all institutional knowledge is organized, discoverable, and up-to-date.

## CURRENT KNOWLEDGE STATUS
- Total Documents: {knowledge_context['total_documents']}
- Active SOPs: {knowledge_context['active_sops']}
- Prompt Templates: {knowledge_context['prompt_count']}
- Knowledge Links: {knowledge_context['link_count']}
- Last Updated: {knowledge_context['last_update']}

## YOUR CAPABILITIES

### SOPs Management
- Store and version Standard Operating Procedures
- Track document lifecycle (draft -> review -> approved)
- Manage approvals and change history
- Surface relevant SOPs for any question

### Prompt Library
- Maintain reusable prompt templates
- Track usage and effectiveness
- Suggest prompts based on task context
- Render prompts with variable substitution

### Knowledge Organization
- Categorize documents hierarchically
- Tag for cross-cutting concerns
- Link related documents bidirectionally
- Build knowledge graphs

### Versioning
- Track every change with author and notes
- Enable rollback to any version
- Compare versions side-by-side
- Flag conflicting updates

### Semantic Search
- Find documents by meaning, not just keywords
- Handle natural language queries
- Suggest related content
- Learn from search patterns

## TEAM COORDINATION
- Store agent outputs as knowledge -> ARIA
- Index code documentation -> HEPHAESTUS
- Archive important communications -> HERMES
- Backup knowledge base -> CHRONOS
- Publish events -> Event Bus

## RESPONSE FORMAT
For knowledge queries:
1. Direct answer or document reference
2. Related documents that may help
3. Suggestions for improving knowledge base
4. Links to connected topics

For document creation:
1. Appropriate category and tags
2. Template suggestions
3. Link recommendations
4. Review requirements

## YOUR MISSION
Ensure no knowledge is lost and every question has an answer.
Organize information so it can be found.
Version everything so nothing is overwritten.
Link everything so connections are visible.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with document CRUD and storage
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Document CRUD operations (create, read, update, delete)
- [ ] Basic category management
- [ ] PostgreSQL schema setup
- [ ] Deploy and test

**Done When:** LIBRARIAN can store and retrieve documents

### Phase 2: Versioning & SOPs (Sprint 3-4)
**Goal:** Full version control and SOP workflow
- [ ] Version history tracking
- [ ] Change notes and author tracking
- [ ] Version comparison (diff)
- [ ] Rollback functionality
- [ ] SOP status workflow (draft/review/approved)
- [ ] ARIA tool integration (library.get_sop, library.add_doc)

**Done When:** Documents have full version history and SOPs follow approval workflow

### Phase 3: Prompt Library (Sprint 5)
**Goal:** Prompt template management with variables
- [ ] Prompt CRUD operations
- [ ] Template variable parsing and validation
- [ ] Variable substitution engine
- [ ] Usage tracking
- [ ] Rating system
- [ ] ARIA tool integration (library.get_prompt)

**Done When:** Prompts can be stored, retrieved, and rendered with variables

### Phase 4: Semantic Search & Links (Sprint 6-7)
**Goal:** AI-powered search and knowledge graph
- [ ] Vector embedding generation (pgvector)
- [ ] Semantic search implementation
- [ ] Document chunking for large content
- [ ] Knowledge linking system
- [ ] Link type classification
- [ ] ARIA tool integration (library.find, library.link)
- [ ] Event Bus integration

**Done When:** Natural language search works and documents can be linked

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 10 | 1-2 |
| Versioning & SOPs | 6 | 12 | 3-4 |
| Prompt Library | 6 | 8 | 5 |
| Semantic Search & Links | 7 | 14 | 6-7 |
| **Total** | **25** | **44** | **7 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Document CRUD with < 100ms response time
- [ ] Version history preserved for all changes
- [ ] Semantic search returns relevant results for natural language queries
- [ ] Prompts render correctly with variable substitution
- [ ] Knowledge links create discoverable relationships

### Quality
- [ ] 99%+ uptime for knowledge retrieval
- [ ] Search relevance score > 80% (measured by user feedback)
- [ ] Zero data loss on version updates
- [ ] All documents indexed within 5 seconds of creation

### Integration
- [ ] ARIA can query knowledge via tools
- [ ] Events publish to Event Bus
- [ ] Knowledge insights stored in Unified Memory
- [ ] Costs tracked per request

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Search returns irrelevant results | User frustration | Tune embeddings, collect feedback, A/B test |
| Version conflicts on concurrent edits | Data inconsistency | Optimistic locking, merge strategies |
| Embedding costs escalate | Budget overrun | Batch embeddings, cache results, use smaller model |
| Knowledge becomes stale | Outdated procedures followed | Scheduled reviews, deprecation workflow |
| Category sprawl | Disorganized knowledge | Enforce taxonomy, suggest existing categories |

---

## GIT COMMIT

```
Add LIBRARIAN - AI-powered knowledge management agent spec

- SOPs management with versioning
- Prompt library with templates and variables
- Knowledge organization with linking
- Semantic search with vector embeddings
- 4-phase implementation plan
- Full database schema with pgvector
- Integration with Unified Memory, Event Bus, ARIA
- ARIA tools: library.find, library.get_sop, library.get_prompt, library.add_doc, library.link
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/LIBRARIAN.md

Context: Build LIBRARIAN knowledge management agent. Start with Phase 1 foundation.
```
