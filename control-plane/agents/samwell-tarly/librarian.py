#!/usr/bin/env python3
"""
LIBRARIAN - AI-Powered Knowledge Management Agent
Port: 8201

Enterprise-grade SOP management, prompt library curation, document versioning,
and semantic search capabilities. Central knowledge brain for LeverEdge.
Named after Clio, Greek muse of history - keeper of records.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs all knowledge operations

PHASE 1 CAPABILITIES:
- Document CRUD operations
- Basic category management
- Health and status endpoints
- Placeholder stubs for advanced features
"""

import os
import sys
import json
import httpx
import re
from datetime import datetime, date
from uuid import uuid4, UUID
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="LIBRARIAN",
    description="AI-Powered Knowledge Management Agent",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "ARIA": "http://aria:8000",
    "HEPHAESTUS": "http://hephaestus:8011",
    "CHRONOS": "http://chronos:8010",
    "HERMES": "http://hermes:8014",
    "SCHOLAR": "http://scholar:8018",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize cost tracker
cost_tracker = CostTracker("LIBRARIAN")

# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class DocumentType(str, Enum):
    SOP = "sop"
    GUIDE = "guide"
    POLICY = "policy"
    REFERENCE = "reference"
    TEMPLATE = "template"

class DocumentStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"

class LinkType(str, Enum):
    RELATED = "related"
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    IMPLEMENTS = "implements"
    CONTRADICTS = "contradicts"

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class DocumentCreate(BaseModel):
    type: DocumentType
    title: str
    content: str
    category: str
    tags: Optional[List[str]] = []
    created_by: str
    metadata: Optional[Dict[str, Any]] = {}

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[DocumentStatus] = None
    change_notes: str  # Required for versioning
    changed_by: str

class Document(BaseModel):
    id: str
    type: DocumentType
    title: str
    content: str
    category: str
    tags: List[str] = []
    version: int = 1
    status: DocumentStatus = DocumentStatus.DRAFT
    created_by: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = {}

class PromptCreate(BaseModel):
    name: str
    category: str
    template: str
    variables: Optional[List[str]] = []
    description: Optional[str] = None
    created_by: str
    metadata: Optional[Dict[str, Any]] = {}

class PromptUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    template: Optional[str] = None
    variables: Optional[List[str]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class Prompt(BaseModel):
    id: str
    name: str
    category: str
    template: str
    variables: List[str] = []
    description: Optional[str] = None
    usage_count: int = 0
    rating: float = 0
    rating_count: int = 0
    created_by: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = {}

class PromptUseRequest(BaseModel):
    variables: Optional[Dict[str, Any]] = {}
    used_by: Optional[str] = None

class PromptRateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    feedback_notes: Optional[str] = None
    rated_by: Optional[str] = None

class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = 0

class Category(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    created_at: str

class SearchRequest(BaseModel):
    query: str
    type: Optional[DocumentType] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[DocumentStatus] = None
    limit: int = 10

class LinkCreate(BaseModel):
    source_doc_id: str
    target_doc_id: str
    link_type: LinkType
    context: Optional[str] = None
    created_by: str

class KnowledgeLink(BaseModel):
    id: str
    source_doc_id: str
    target_doc_id: str
    link_type: LinkType
    context: Optional[str] = None
    created_by: str
    created_at: str

# ARIA Tool Request Models
class LibraryFindRequest(BaseModel):
    query: str
    type: Optional[str] = None
    category: Optional[str] = None
    limit: int = 10

class LibraryGetSOPRequest(BaseModel):
    identifier: str
    version: Optional[int] = None

class LibraryGetPromptRequest(BaseModel):
    name: str
    variables: Optional[Dict[str, Any]] = None

class LibraryAddDocRequest(BaseModel):
    type: str
    title: str
    content: str
    category: str
    tags: Optional[List[str]] = []
    created_by: str = "ARIA"

class LibraryLinkRequest(BaseModel):
    source_id: str
    target_id: str
    link_type: str
    context: Optional[str] = None
    created_by: str = "ARIA"

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "launch_date": LAUNCH_DATE.isoformat(),
        "days_to_launch": days_to_launch,
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch"
    }

# =============================================================================
# SYSTEM PROMPT BUILDER
# =============================================================================

def build_system_prompt(knowledge_context: dict) -> str:
    """Build LIBRARIAN system prompt with current context"""
    return f"""You are LIBRARIAN - Knowledge Management Agent for LeverEdge AI.

Named after Clio, the Greek muse of history and keeper of records, you preserve and organize all organizational knowledge.

## TIME AWARENESS
- Current: {knowledge_context.get('current_time', 'unknown')}
- Days to Launch: {knowledge_context.get('days_to_launch', 'unknown')}

## YOUR IDENTITY
You are the knowledge brain of LeverEdge. You manage SOPs, curate prompts, version documents, and ensure all institutional knowledge is organized, discoverable, and up-to-date.

## CURRENT KNOWLEDGE STATUS
- Total Documents: {knowledge_context.get('total_documents', 0)}
- Active SOPs: {knowledge_context.get('active_sops', 0)}
- Prompt Templates: {knowledge_context.get('prompt_count', 0)}
- Knowledge Links: {knowledge_context.get('link_count', 0)}
- Last Updated: {knowledge_context.get('last_update', 'unknown')}

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

# =============================================================================
# DATABASE HELPERS
# =============================================================================

async def get_db_headers() -> dict:
    """Get standard headers for Supabase requests"""
    key = SUPABASE_SERVICE_KEY or SUPABASE_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

async def db_query(table: str, params: dict = None, method: str = "GET", body: dict = None) -> dict:
    """Execute a database query via Supabase REST API"""
    try:
        headers = await get_db_headers()
        url = f"{SUPABASE_URL}/rest/v1/{table}"

        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query_string}"

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, timeout=10.0)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=body, timeout=10.0)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, json=body, timeout=10.0)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, timeout=10.0)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code in [200, 201]:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": response.text, "status": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}

# =============================================================================
# EVENT BUS INTEGRATION
# =============================================================================

async def publish_event(event_type: str, details: dict = None):
    """Publish event to Event Bus"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "LIBRARIAN",
                    "data": {
                        **(details or {}),
                        "timestamp": time_ctx['current_datetime'],
                        "days_to_launch": time_ctx['days_to_launch']
                    }
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[LIBRARIAN] Event bus publish failed: {e}")

# =============================================================================
# IN-MEMORY STORAGE (Phase 1 - Will be replaced with DB)
# =============================================================================

# Temporary in-memory storage until database schema is applied
_documents: Dict[str, dict] = {}
_document_versions: Dict[str, List[dict]] = {}
_prompts: Dict[str, dict] = {}
_categories: Dict[str, dict] = {}
_links: Dict[str, dict] = {}
_prompt_usage: List[dict] = []

# Pre-populate with default categories
DEFAULT_CATEGORIES = [
    {"id": str(uuid4()), "name": "Development", "description": "Code and build procedures", "icon": "code", "sort_order": 1},
    {"id": str(uuid4()), "name": "Operations", "description": "Day-to-day operations", "icon": "settings", "sort_order": 2},
    {"id": str(uuid4()), "name": "Security", "description": "Security procedures", "icon": "shield", "sort_order": 3},
    {"id": str(uuid4()), "name": "Business", "description": "Business processes", "icon": "briefcase", "sort_order": 4},
    {"id": str(uuid4()), "name": "Integration", "description": "System integration", "icon": "link", "sort_order": 5},
    {"id": str(uuid4()), "name": "Emergency", "description": "Critical procedures", "icon": "alert", "sort_order": 6},
]

def _init_default_categories():
    """Initialize default categories in memory"""
    for cat in DEFAULT_CATEGORIES:
        cat["created_at"] = datetime.now().isoformat()
        _categories[cat["id"]] = cat

_init_default_categories()

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint with knowledge statistics"""
    time_ctx = get_time_context()

    return {
        "status": "healthy",
        "agent": "LIBRARIAN",
        "role": "Knowledge Management",
        "port": 8201,
        "version": "1.0.0",
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "knowledge_stats": {
            "total_documents": len(_documents),
            "active_sops": len([d for d in _documents.values() if d.get("type") == "sop" and d.get("status") == "approved"]),
            "prompt_templates": len(_prompts),
            "categories": len(_categories),
            "knowledge_links": len(_links)
        }
    }

@app.get("/status")
async def status():
    """Detailed status of the knowledge base"""
    time_ctx = get_time_context()

    # Document counts by type
    doc_by_type = {}
    for doc in _documents.values():
        doc_type = doc.get("type", "unknown")
        doc_by_type[doc_type] = doc_by_type.get(doc_type, 0) + 1

    # Document counts by status
    doc_by_status = {}
    for doc in _documents.values():
        status = doc.get("status", "unknown")
        doc_by_status[status] = doc_by_status.get(status, 0) + 1

    # Prompt usage stats
    total_prompt_usage = sum(p.get("usage_count", 0) for p in _prompts.values())

    return {
        "agent": "LIBRARIAN",
        "status": "operational",
        "time_context": time_ctx,
        "knowledge_base": {
            "documents": {
                "total": len(_documents),
                "by_type": doc_by_type,
                "by_status": doc_by_status
            },
            "prompts": {
                "total": len(_prompts),
                "total_usage": total_prompt_usage
            },
            "categories": len(_categories),
            "links": len(_links)
        },
        "storage_mode": "in_memory",  # Will change to "database" when schema applied
        "capabilities": {
            "document_crud": True,
            "versioning": True,
            "prompts": True,
            "semantic_search": False,  # Phase 4
            "ai_suggestions": False    # Phase 4
        }
    }

# =============================================================================
# DOCUMENT ENDPOINTS
# =============================================================================

@app.post("/documents")
async def create_document(doc: DocumentCreate):
    """Create a new document"""
    doc_id = str(uuid4())
    now = datetime.now().isoformat()

    document = {
        "id": doc_id,
        "type": doc.type.value,
        "title": doc.title,
        "content": doc.content,
        "category": doc.category,
        "tags": doc.tags or [],
        "version": 1,
        "status": DocumentStatus.DRAFT.value,
        "created_by": doc.created_by,
        "created_at": now,
        "updated_at": now,
        "metadata": doc.metadata or {}
    }

    _documents[doc_id] = document

    # Create initial version entry
    _document_versions[doc_id] = [{
        "id": str(uuid4()),
        "document_id": doc_id,
        "version": 1,
        "content": doc.content,
        "changed_by": doc.created_by,
        "changed_at": now,
        "change_notes": "Initial creation"
    }]

    # Publish event
    await publish_event("library.document.created", {
        "document_id": doc_id,
        "type": doc.type.value,
        "title": doc.title,
        "category": doc.category
    })

    return {"success": True, "document": document}

@app.get("/documents")
async def list_documents(
    type: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List documents with optional filters"""
    docs = list(_documents.values())

    # Apply filters
    if type:
        docs = [d for d in docs if d.get("type") == type]
    if category:
        docs = [d for d in docs if d.get("category") == category]
    if status:
        docs = [d for d in docs if d.get("status") == status]
    if tags:
        tag_list = tags.split(",")
        docs = [d for d in docs if any(t in d.get("tags", []) for t in tag_list)]

    # Sort by updated_at descending
    docs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    # Apply pagination
    total = len(docs)
    docs = docs[offset:offset + limit]

    return {
        "documents": docs,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get a document by ID"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"document": _documents[doc_id]}

@app.put("/documents/{doc_id}")
async def update_document(doc_id: str, update: DocumentUpdate):
    """Update a document (creates a new version)"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = _documents[doc_id]
    now = datetime.now().isoformat()
    old_version = doc.get("version", 1)
    new_version = old_version + 1

    # Update fields
    if update.title is not None:
        doc["title"] = update.title
    if update.content is not None:
        doc["content"] = update.content
    if update.category is not None:
        doc["category"] = update.category
    if update.tags is not None:
        doc["tags"] = update.tags
    if update.status is not None:
        doc["status"] = update.status.value

    doc["version"] = new_version
    doc["updated_at"] = now

    # Create version entry
    if doc_id not in _document_versions:
        _document_versions[doc_id] = []

    _document_versions[doc_id].append({
        "id": str(uuid4()),
        "document_id": doc_id,
        "version": new_version,
        "content": doc["content"],
        "changed_by": update.changed_by,
        "changed_at": now,
        "change_notes": update.change_notes
    })

    # Publish event
    await publish_event("library.document.updated", {
        "document_id": doc_id,
        "title": doc["title"],
        "old_version": old_version,
        "new_version": new_version,
        "changed_by": update.changed_by
    })

    return {"success": True, "document": doc}

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Soft delete a document (mark as deprecated)"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = _documents[doc_id]
    doc["status"] = DocumentStatus.DEPRECATED.value
    doc["updated_at"] = datetime.now().isoformat()

    await publish_event("library.document.deprecated", {
        "document_id": doc_id,
        "title": doc["title"]
    })

    return {"success": True, "message": "Document marked as deprecated"}

@app.get("/documents/{doc_id}/versions")
async def get_document_versions(doc_id: str):
    """Get version history for a document"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")

    versions = _document_versions.get(doc_id, [])
    return {"document_id": doc_id, "versions": versions}

@app.get("/documents/{doc_id}/versions/{version}")
async def get_document_version(doc_id: str, version: int):
    """Get a specific version of a document"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")

    versions = _document_versions.get(doc_id, [])
    for v in versions:
        if v.get("version") == version:
            return {"version": v}

    raise HTTPException(status_code=404, detail=f"Version {version} not found")

@app.post("/documents/{doc_id}/restore/{version}")
async def restore_document_version(doc_id: str, version: int, restored_by: str = "system"):
    """Restore a document to a specific version"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")

    versions = _document_versions.get(doc_id, [])
    target_version = None
    for v in versions:
        if v.get("version") == version:
            target_version = v
            break

    if not target_version:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")

    # Create update request to restore
    update = DocumentUpdate(
        content=target_version["content"],
        change_notes=f"Restored to version {version}",
        changed_by=restored_by
    )

    return await update_document(doc_id, update)

@app.post("/documents/{doc_id}/link")
async def link_document(doc_id: str, link: LinkCreate):
    """Link this document to another document"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Source document not found")
    if link.target_doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Target document not found")

    link_id = str(uuid4())
    now = datetime.now().isoformat()

    new_link = {
        "id": link_id,
        "source_doc_id": doc_id,
        "target_doc_id": link.target_doc_id,
        "link_type": link.link_type.value,
        "context": link.context,
        "created_by": link.created_by,
        "created_at": now
    }

    _links[link_id] = new_link

    await publish_event("library.document.linked", {
        "link_id": link_id,
        "source_doc_id": doc_id,
        "target_doc_id": link.target_doc_id,
        "link_type": link.link_type.value
    })

    return {"success": True, "link": new_link}

@app.get("/documents/{doc_id}/links")
async def get_document_links(doc_id: str):
    """Get all links for a document (both as source and target)"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")

    as_source = [l for l in _links.values() if l.get("source_doc_id") == doc_id]
    as_target = [l for l in _links.values() if l.get("target_doc_id") == doc_id]

    return {
        "document_id": doc_id,
        "outgoing_links": as_source,
        "incoming_links": as_target
    }

# =============================================================================
# PROMPT ENDPOINTS
# =============================================================================

@app.post("/prompts")
async def create_prompt(prompt: PromptCreate):
    """Create a new prompt template"""
    # Check for duplicate name
    for p in _prompts.values():
        if p.get("name") == prompt.name:
            raise HTTPException(status_code=400, detail="Prompt with this name already exists")

    prompt_id = str(uuid4())
    now = datetime.now().isoformat()

    # Auto-extract variables from template if not provided
    variables = prompt.variables or []
    if not variables:
        # Extract {{variable}} patterns
        variables = list(set(re.findall(r'\{\{(\w+)\}\}', prompt.template)))

    new_prompt = {
        "id": prompt_id,
        "name": prompt.name,
        "category": prompt.category,
        "template": prompt.template,
        "variables": variables,
        "description": prompt.description,
        "usage_count": 0,
        "rating": 0.0,
        "rating_count": 0,
        "created_by": prompt.created_by,
        "created_at": now,
        "updated_at": now,
        "metadata": prompt.metadata or {}
    }

    _prompts[prompt_id] = new_prompt

    await publish_event("library.prompt.created", {
        "prompt_id": prompt_id,
        "name": prompt.name,
        "category": prompt.category
    })

    return {"success": True, "prompt": new_prompt}

@app.get("/prompts")
async def list_prompts(
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List prompt templates"""
    prompts = list(_prompts.values())

    if category:
        prompts = [p for p in prompts if p.get("category") == category]

    # Sort by usage_count descending
    prompts.sort(key=lambda x: x.get("usage_count", 0), reverse=True)

    total = len(prompts)
    prompts = prompts[offset:offset + limit]

    return {
        "prompts": prompts,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/prompts/popular")
async def get_popular_prompts(limit: int = 10):
    """Get most used prompts"""
    prompts = list(_prompts.values())
    prompts.sort(key=lambda x: x.get("usage_count", 0), reverse=True)
    return {"prompts": prompts[:limit]}

@app.get("/prompts/top-rated")
async def get_top_rated_prompts(limit: int = 10):
    """Get highest rated prompts"""
    prompts = [p for p in _prompts.values() if p.get("rating_count", 0) > 0]
    prompts.sort(key=lambda x: x.get("rating", 0), reverse=True)
    return {"prompts": prompts[:limit]}

@app.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Get a prompt by ID"""
    if prompt_id not in _prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"prompt": _prompts[prompt_id]}

@app.put("/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, update: PromptUpdate):
    """Update a prompt template"""
    if prompt_id not in _prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt = _prompts[prompt_id]

    if update.name is not None:
        prompt["name"] = update.name
    if update.category is not None:
        prompt["category"] = update.category
    if update.template is not None:
        prompt["template"] = update.template
        # Re-extract variables
        prompt["variables"] = list(set(re.findall(r'\{\{(\w+)\}\}', update.template)))
    if update.variables is not None:
        prompt["variables"] = update.variables
    if update.description is not None:
        prompt["description"] = update.description
    if update.metadata is not None:
        prompt["metadata"] = update.metadata

    prompt["updated_at"] = datetime.now().isoformat()

    return {"success": True, "prompt": prompt}

@app.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt template"""
    if prompt_id not in _prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")

    del _prompts[prompt_id]
    return {"success": True, "message": "Prompt deleted"}

@app.post("/prompts/{prompt_id}/use")
async def use_prompt(prompt_id: str, req: PromptUseRequest):
    """Record usage and get rendered prompt with variable substitution"""
    if prompt_id not in _prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt = _prompts[prompt_id]
    template = prompt["template"]

    # Substitute variables
    rendered = template
    for var, value in (req.variables or {}).items():
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        rendered = rendered.replace(f"{{{{{var}}}}}", str(value))

    # Record usage
    prompt["usage_count"] = prompt.get("usage_count", 0) + 1

    _prompt_usage.append({
        "id": str(uuid4()),
        "prompt_id": prompt_id,
        "used_by": req.used_by,
        "used_at": datetime.now().isoformat(),
        "variables_used": req.variables
    })

    await publish_event("library.prompt.used", {
        "prompt_id": prompt_id,
        "name": prompt["name"],
        "used_by": req.used_by
    })

    return {
        "prompt_id": prompt_id,
        "name": prompt["name"],
        "rendered": rendered,
        "variables_used": req.variables,
        "usage_count": prompt["usage_count"]
    }

@app.post("/prompts/{prompt_id}/rate")
async def rate_prompt(prompt_id: str, req: PromptRateRequest):
    """Rate a prompt template"""
    if prompt_id not in _prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt = _prompts[prompt_id]

    # Update rating (simple average)
    current_rating = prompt.get("rating", 0)
    current_count = prompt.get("rating_count", 0)

    new_count = current_count + 1
    new_rating = ((current_rating * current_count) + req.rating) / new_count

    prompt["rating"] = round(new_rating, 2)
    prompt["rating_count"] = new_count

    await publish_event("library.prompt.rated", {
        "prompt_id": prompt_id,
        "name": prompt["name"],
        "rating": req.rating,
        "new_average": prompt["rating"]
    })

    return {
        "success": True,
        "prompt_id": prompt_id,
        "new_rating": prompt["rating"],
        "rating_count": prompt["rating_count"]
    }

# =============================================================================
# CATEGORY ENDPOINTS
# =============================================================================

@app.get("/categories")
async def list_categories():
    """List all categories (hierarchical)"""
    cats = list(_categories.values())
    cats.sort(key=lambda x: x.get("sort_order", 0))

    # Build hierarchy
    root_cats = [c for c in cats if not c.get("parent_id")]

    def get_children(parent_id):
        return [c for c in cats if c.get("parent_id") == parent_id]

    def build_tree(cat):
        children = get_children(cat["id"])
        return {
            **cat,
            "children": [build_tree(c) for c in children]
        }

    tree = [build_tree(c) for c in root_cats]

    return {"categories": tree, "flat": cats}

@app.post("/categories")
async def create_category(cat: CategoryCreate):
    """Create a new category"""
    # Check for duplicate name
    for c in _categories.values():
        if c.get("name") == cat.name:
            raise HTTPException(status_code=400, detail="Category with this name already exists")

    cat_id = str(uuid4())
    now = datetime.now().isoformat()

    new_cat = {
        "id": cat_id,
        "name": cat.name,
        "parent_id": cat.parent_id,
        "description": cat.description,
        "icon": cat.icon,
        "sort_order": cat.sort_order or 0,
        "created_at": now
    }

    _categories[cat_id] = new_cat

    await publish_event("library.category.created", {
        "category_id": cat_id,
        "name": cat.name
    })

    return {"success": True, "category": new_cat}

@app.put("/categories/{cat_id}")
async def update_category(cat_id: str, update: CategoryCreate):
    """Update a category"""
    if cat_id not in _categories:
        raise HTTPException(status_code=404, detail="Category not found")

    cat = _categories[cat_id]
    cat["name"] = update.name
    cat["parent_id"] = update.parent_id
    cat["description"] = update.description
    cat["icon"] = update.icon
    cat["sort_order"] = update.sort_order or 0

    return {"success": True, "category": cat}

@app.delete("/categories/{cat_id}")
async def delete_category(cat_id: str):
    """Delete a category (only if no documents use it)"""
    if cat_id not in _categories:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if any documents use this category
    cat_name = _categories[cat_id]["name"]
    docs_using = [d for d in _documents.values() if d.get("category") == cat_name]

    if docs_using:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category: {len(docs_using)} documents use it"
        )

    del _categories[cat_id]
    return {"success": True, "message": "Category deleted"}

@app.get("/categories/{cat_id}/documents")
async def get_category_documents(cat_id: str):
    """Get all documents in a category"""
    if cat_id not in _categories:
        raise HTTPException(status_code=404, detail="Category not found")

    cat_name = _categories[cat_id]["name"]
    docs = [d for d in _documents.values() if d.get("category") == cat_name]

    return {
        "category": _categories[cat_id],
        "documents": docs,
        "count": len(docs)
    }

# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@app.post("/search")
async def search(req: SearchRequest):
    """Search across all content (basic text search - semantic search is Phase 4)"""
    query_lower = req.query.lower()
    results = []

    # Search documents
    for doc in _documents.values():
        score = 0
        if query_lower in doc.get("title", "").lower():
            score += 3
        if query_lower in doc.get("content", "").lower():
            score += 1
        if any(query_lower in tag.lower() for tag in doc.get("tags", [])):
            score += 2

        if score > 0:
            # Apply filters
            if req.type and doc.get("type") != req.type.value:
                continue
            if req.category and doc.get("category") != req.category:
                continue
            if req.status and doc.get("status") != req.status.value:
                continue
            if req.tags and not any(t in doc.get("tags", []) for t in req.tags):
                continue

            results.append({
                "type": "document",
                "score": score,
                "item": doc
            })

    # Search prompts
    for prompt in _prompts.values():
        score = 0
        if query_lower in prompt.get("name", "").lower():
            score += 3
        if query_lower in prompt.get("template", "").lower():
            score += 1
        if query_lower in (prompt.get("description") or "").lower():
            score += 2

        if score > 0:
            if req.type and req.type.value != "prompt":
                continue
            if req.category and prompt.get("category") != req.category:
                continue

            results.append({
                "type": "prompt",
                "score": score,
                "item": prompt
            })

    # Sort by score and limit
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:req.limit]

    await publish_event("library.search.executed", {
        "query": req.query,
        "result_count": len(results)
    })

    return {
        "query": req.query,
        "results": results,
        "total": len(results),
        "search_type": "text"  # Will be "semantic" in Phase 4
    }

@app.get("/search/suggest")
async def search_suggestions(q: str = Query(..., min_length=2)):
    """Get search suggestions based on query prefix"""
    q_lower = q.lower()
    suggestions = []

    # Suggest from document titles
    for doc in _documents.values():
        title = doc.get("title", "")
        if q_lower in title.lower():
            suggestions.append({"type": "document", "text": title, "id": doc["id"]})

    # Suggest from prompt names
    for prompt in _prompts.values():
        name = prompt.get("name", "")
        if q_lower in name.lower():
            suggestions.append({"type": "prompt", "text": name, "id": prompt["id"]})

    # Suggest from tags
    all_tags = set()
    for doc in _documents.values():
        all_tags.update(doc.get("tags", []))
    for tag in all_tags:
        if q_lower in tag.lower():
            suggestions.append({"type": "tag", "text": tag})

    return {"suggestions": suggestions[:10]}

@app.get("/search/recent")
async def recent_searches():
    """Get recent searches (placeholder - will be implemented with DB)"""
    return {"recent": [], "message": "Recent search tracking not yet implemented"}

@app.post("/search/index")
async def reindex_document(doc_id: str):
    """Force re-index a document (placeholder for semantic search)"""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")

    # Placeholder - will implement with vector embeddings in Phase 4
    return {
        "success": True,
        "message": "Semantic indexing not yet implemented (Phase 4)",
        "document_id": doc_id
    }

# =============================================================================
# KNOWLEDGE LINKS ENDPOINTS
# =============================================================================

@app.get("/links")
async def list_links(
    link_type: Optional[str] = None,
    limit: int = 100
):
    """List all knowledge links"""
    links = list(_links.values())

    if link_type:
        links = [l for l in links if l.get("link_type") == link_type]

    return {"links": links[:limit], "total": len(links)}

@app.post("/links")
async def create_link(link: LinkCreate):
    """Create a link between documents"""
    if link.source_doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Source document not found")
    if link.target_doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Target document not found")

    link_id = str(uuid4())
    now = datetime.now().isoformat()

    new_link = {
        "id": link_id,
        "source_doc_id": link.source_doc_id,
        "target_doc_id": link.target_doc_id,
        "link_type": link.link_type.value,
        "context": link.context,
        "created_by": link.created_by,
        "created_at": now
    }

    _links[link_id] = new_link

    await publish_event("library.document.linked", {
        "link_id": link_id,
        "source_doc_id": link.source_doc_id,
        "target_doc_id": link.target_doc_id,
        "link_type": link.link_type.value
    })

    return {"success": True, "link": new_link}

@app.delete("/links/{link_id}")
async def delete_link(link_id: str):
    """Remove a knowledge link"""
    if link_id not in _links:
        raise HTTPException(status_code=404, detail="Link not found")

    del _links[link_id]
    return {"success": True, "message": "Link deleted"}

@app.get("/links/graph")
async def get_knowledge_graph():
    """Get knowledge graph data for visualization"""
    nodes = []
    edges = []

    # Add documents as nodes
    for doc in _documents.values():
        nodes.append({
            "id": doc["id"],
            "type": "document",
            "subtype": doc["type"],
            "label": doc["title"],
            "category": doc["category"]
        })

    # Add prompts as nodes
    for prompt in _prompts.values():
        nodes.append({
            "id": prompt["id"],
            "type": "prompt",
            "label": prompt["name"],
            "category": prompt["category"]
        })

    # Add links as edges
    for link in _links.values():
        edges.append({
            "id": link["id"],
            "source": link["source_doc_id"],
            "target": link["target_doc_id"],
            "type": link["link_type"],
            "context": link["context"]
        })

    return {"nodes": nodes, "edges": edges}

@app.post("/links/discover")
async def discover_links():
    """AI-discover potential links (placeholder - Phase 4)"""
    return {
        "success": True,
        "message": "AI link discovery not yet implemented (Phase 4)",
        "suggested_links": []
    }

# =============================================================================
# ARIA TOOL ENDPOINTS
# =============================================================================

@app.post("/tools/library.find")
async def tool_library_find(req: LibraryFindRequest):
    """ARIA tool: Search the knowledge library"""
    search_req = SearchRequest(
        query=req.query,
        type=DocumentType(req.type) if req.type else None,
        category=req.category,
        limit=req.limit
    )
    return await search(search_req)

@app.post("/tools/library.get_sop")
async def tool_library_get_sop(req: LibraryGetSOPRequest):
    """ARIA tool: Get a specific SOP by ID or name"""
    # Try by ID first
    if req.identifier in _documents:
        doc = _documents[req.identifier]
        if req.version:
            versions = _document_versions.get(req.identifier, [])
            for v in versions:
                if v.get("version") == req.version:
                    return {"sop": {**doc, "content": v["content"], "version": v["version"]}}
            raise HTTPException(status_code=404, detail=f"Version {req.version} not found")
        return {"sop": doc}

    # Try by name
    for doc in _documents.values():
        if doc.get("title", "").lower() == req.identifier.lower() and doc.get("type") == "sop":
            if req.version:
                versions = _document_versions.get(doc["id"], [])
                for v in versions:
                    if v.get("version") == req.version:
                        return {"sop": {**doc, "content": v["content"], "version": v["version"]}}
                raise HTTPException(status_code=404, detail=f"Version {req.version} not found")
            return {"sop": doc}

    raise HTTPException(status_code=404, detail="SOP not found")

@app.post("/tools/library.get_prompt")
async def tool_library_get_prompt(req: LibraryGetPromptRequest):
    """ARIA tool: Get a prompt template with optional variable substitution"""
    # Find by name
    prompt = None
    for p in _prompts.values():
        if p.get("name", "").lower() == req.name.lower():
            prompt = p
            break

    if not prompt:
        # Try by ID
        if req.name in _prompts:
            prompt = _prompts[req.name]

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Render with variables if provided
    rendered = prompt["template"]
    if req.variables:
        for var, value in req.variables.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            rendered = rendered.replace(f"{{{{{var}}}}}", str(value))

    return {
        "prompt": prompt,
        "rendered": rendered,
        "variables_applied": req.variables or {}
    }

@app.post("/tools/library.add_doc")
async def tool_library_add_doc(req: LibraryAddDocRequest):
    """ARIA tool: Add a new document to the library"""
    doc_create = DocumentCreate(
        type=DocumentType(req.type),
        title=req.title,
        content=req.content,
        category=req.category,
        tags=req.tags or [],
        created_by=req.created_by
    )
    return await create_document(doc_create)

@app.post("/tools/library.link")
async def tool_library_link(req: LibraryLinkRequest):
    """ARIA tool: Create a link between documents"""
    link_create = LinkCreate(
        source_doc_id=req.source_id,
        target_doc_id=req.target_id,
        link_type=LinkType(req.link_type),
        context=req.context,
        created_by=req.created_by
    )
    return await create_link(link_create)

# =============================================================================
# METRICS ENDPOINT (Prometheus-compatible)
# =============================================================================

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    time_ctx = get_time_context()

    lines = []

    # Document metrics
    lines.append(f"librarian_documents_total {len(_documents)}")
    lines.append(f"librarian_documents_active {len([d for d in _documents.values() if d.get('status') != 'deprecated'])}")

    # By type
    for doc_type in DocumentType:
        count = len([d for d in _documents.values() if d.get('type') == doc_type.value])
        lines.append(f'librarian_documents_by_type{{type="{doc_type.value}"}} {count}')

    # By status
    for status in DocumentStatus:
        count = len([d for d in _documents.values() if d.get('status') == status.value])
        lines.append(f'librarian_documents_by_status{{status="{status.value}"}} {count}')

    # Prompt metrics
    lines.append(f"librarian_prompts_total {len(_prompts)}")
    total_usage = sum(p.get("usage_count", 0) for p in _prompts.values())
    lines.append(f"librarian_prompt_usage_total {total_usage}")

    # Category metrics
    lines.append(f"librarian_categories_total {len(_categories)}")

    # Link metrics
    lines.append(f"librarian_links_total {len(_links)}")

    # Version metrics
    total_versions = sum(len(v) for v in _document_versions.values())
    lines.append(f"librarian_document_versions_total {total_versions}")

    return "\n".join(lines)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8201)
