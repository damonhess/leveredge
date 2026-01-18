# DOCUMENTATION RULES

*Effective: January 18, 2026*

---

## Single Source of Truth

**ALL documentation lives in `/opt/leveredge/` root directory.**

| Document | Location | Purpose |
|----------|----------|---------|
| AGENT-ROUTING.md | /opt/leveredge/ | Agent routing matrix (AUTHORITATIVE) |
| ARCHITECTURE.md | /opt/leveredge/ | System architecture |
| LOOSE-ENDS.md | /opt/leveredge/ | Current status and priorities |
| FUTURE-VISION.md | /opt/leveredge/ | Long-term roadmap |
| LESSONS-LEARNED.md | /opt/leveredge/ | Consolidated lessons |
| LESSONS-SCRATCH.md | /opt/leveredge/ | Raw lesson captures |
| OPS-RUNBOOK.md | /opt/leveredge/ | Operations procedures |
| README.md | /opt/leveredge/ | Project overview |

---

## Forbidden Actions

**NEVER:**
1. Create dated versions of existing documents (e.g., `20260118_LOOSE-ENDS.md`)
2. Create documents in `/opt/leveredge/docs/` that duplicate root files
3. Create `*-CORRECTED.md` or `*-UPDATED.md` variants
4. Leave multiple versions of the same document

**ALWAYS:**
- Edit the existing document in-place
- Use git for version history (not filename dates)
- Archive superseded documents to `/opt/leveredge/archive/docs/`

---

## Document Hierarchy

```
/opt/leveredge/
├── *.md                    # AUTHORITATIVE - edit these
├── config/
│   └── agent-registry.yaml # AUTHORITATIVE - agent definitions
├── specs/                  # Build specifications (executable)
│   └── agents/             # Agent specs
├── archive/
│   ├── docs/               # Superseded documentation
│   └── specs/              # Completed/old specs
├── docs/                   # DEPRECATED - do not add files here
└── mission/                # Mission-critical constants
```

---

## Update Protocol

### For Claude Code (GSD):
1. Edit root documents directly
2. Commit changes with descriptive message
3. If document doesn't exist, create in root (never in docs/)

### For Claude Desktop (via HEPHAESTUS):
1. Edit root documents via HEPHAESTUS MCP
2. Never create new documents in /docs/
3. If unsure, ASK before creating new files

### For Both:
- Before creating ANY new .md file, check if similar exists
- Search: `ls /opt/leveredge/*.md` and `grep -r "topic" /opt/leveredge/*.md`
- Prefer editing over creating

---

## Consolidation Reference

The following documents were consolidated on January 18, 2026:

| Archived From | Merged Into |
|---------------|-------------|
| docs/20260118_LOOSE-ENDS.md | LOOSE-ENDS.md |
| docs/20260118_ARCHITECTURE.md | ARCHITECTURE.md |
| docs/20260118_FUTURE-VISION.md | FUTURE-VISION.md |
| docs/20260118_AGENT-REGISTRY-CORRECTED.md | AGENT-ROUTING.md + config/agent-registry.yaml |
| docs/20260118_STRATEGIC-DECISIONS.md | LOOSE-ENDS.md (decisions section) |
| docs/20260118_LOOSE-ENDS-CHECKLIST.md | LOOSE-ENDS.md |
| docs/20260118_PM-TOOL-COMPARISON.md | archive/docs/ (reference only) |
| docs/20260118_ARIA-SUPREMACY.md | archive/docs/ (reference only) |

---

## Config Files

| File | Location | Authoritative For |
|------|----------|-------------------|
| agent-registry.yaml | /opt/leveredge/config/ | Agent definitions, ports, capabilities |
| EXECUTION_RULES.md | /home/damon/.claude/ | Claude Code behavior rules |

**Never duplicate config information in multiple places.**

---

## When to Create New Documents

Create a new document ONLY when:
1. It covers a genuinely new topic not in any existing doc
2. It's a build spec in /specs/ (temporary, archive after build)
3. It's component-specific (e.g., agent README in its own directory)

Do NOT create new documents for:
- Updates to existing topics (edit in place)
- "Corrected" versions (edit original)
- Point-in-time snapshots (use git)
