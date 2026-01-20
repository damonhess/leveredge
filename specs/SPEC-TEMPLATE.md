# GSD: [TITLE]

**Priority:** [HIGH/MEDIUM/LOW]
**Estimated Time:** [X hours]
**Created:** [DATE]
**Status:** Ready for execution

---

## OVERVIEW

[What this GSD accomplishes in 2-3 sentences]

---

## DELIVERABLES

- [ ] Deliverable 1
- [ ] Deliverable 2
- [ ] Deliverable 3

---

## BUILD STEPS

### Phase 1: [Name]

```bash
# Commands here
```

### Phase 2: [Name]

```bash
# Commands here
```

---

## VERIFICATION

```bash
# How to verify it worked
curl http://localhost:XXXX/health
```

---

## ON COMPLETION

**This section is MANDATORY for all specs.**

### 1. Move Spec to Done

```bash
mv /opt/leveredge/specs/[THIS-SPEC].md /opt/leveredge/specs/done/
```

### 2. Log to LCIS

```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "GSD [TITLE] completed: [SUMMARY OF WHAT WAS BUILT]",
    "domain": "[DOMAIN]",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "build", "[relevant-tags]"]
  }'
```

### 3. Update GSD-TRACKER.md

Add entry to the DONE section:
```markdown
| `[this-spec].md` | [What it built] | [Agent/Result] |
```

### 4. Git Commit

```bash
git add -A
git commit -m "feat: [TITLE]

- [Bullet point of what was built]
- [Bullet point of what was built]
- [Bullet point of what was built]

GSD: /opt/leveredge/specs/done/[this-spec].md"
```

### 5. Notify ARIA (Optional)

```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Build complete: [TITLE]. [1-sentence summary]",
    "domain": "aria_knowledge",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "importance": "normal"
  }'
```

---

## ROLLBACK

If something goes wrong:

```bash
# CHRONOS restore
curl -X POST http://localhost:8010/restore/latest

# Or HADES rollback
curl -X POST http://localhost:8008/rollback
```

---

*Template version: 1.0 | All specs MUST include the ON COMPLETION section*
