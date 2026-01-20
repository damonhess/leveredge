# GSD: [TITLE]

**Priority:** [HIGH/MEDIUM/LOW]
**Estimated Time:** [X hours]
**Created:** [DATE]
**Status:** Ready for execution

---

## OVERVIEW

[What this GSD accomplishes in 2-3 sentences]

---

## ENVIRONMENT

**Target:** DEV FIRST (always)

```
Location: /opt/leveredge/data-plane/dev/[service]/
Test URL: dev-[service].leveredgeai.com
```

⚠️ **NEVER modify /data-plane/prod/ directly. Use promote-to-prod.sh after DEV verification.**

---

## DELIVERABLES

- [ ] Deliverable 1 (DEV)
- [ ] Deliverable 2 (DEV)
- [ ] Test in DEV environment
- [ ] Promote to PROD

---

## BUILD STEPS

### Phase 1: [Name] (DEV)

```bash
# All commands target DEV
cd /opt/leveredge/data-plane/dev/[service]/
```

### Phase 2: [Name] (DEV)

```bash
# More DEV changes
```

### Phase 3: Test in DEV

```bash
# Verify at dev-[service].leveredgeai.com
curl https://dev-[service].leveredgeai.com/health
```

### Phase 4: Promote to PROD

```bash
# Only after DEV verification passes
cd /opt/leveredge
./shared/scripts/promote-[service]-to-prod.sh
```

---

## VERIFICATION

```bash
# DEV verification
curl http://localhost:XXXX/health

# PROD verification (after promotion)
curl https://[service].leveredgeai.com/health
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
# DEV rollback
cd /opt/leveredge/data-plane/dev/[service]
git checkout HEAD~1 -- .

# PROD rollback (if promoted)
curl -X POST http://localhost:8008/rollback  # HADES
```

---

*Template version: 1.1 | DEV-FIRST ENFORCED | All specs MUST include ON COMPLETION section*
