# GSD Rules & Standards

*Last Updated: January 20, 2026*

---

## MANDATORY RULES

### Rule 1: ON COMPLETION Section

**Every spec MUST include an "ON COMPLETION" section with:**

1. **Move to done** - `mv /opt/leveredge/specs/[spec].md /opt/leveredge/specs/done/`
2. **Log to LCIS** - POST to http://localhost:8050/lessons with success entry
3. **Update GSD-TRACKER.md** - Add to DONE section
4. **Git commit** - With descriptive message referencing the spec
5. **Notify ARIA** (optional) - Log to aria_knowledge

### Rule 2: Use the Template

All new specs must be based on `/opt/leveredge/specs/SPEC-TEMPLATE.md`

### Rule 3: Spec Lifecycle

```
/specs/           → Active, ready to run
/specs/done/      → Completed and verified
/specs/deferred/  → Post-launch or low priority
/specs/archive/   → Superseded or abandoned
```

### Rule 4: Naming Convention

- `gsd-[action]-[target].md` for executable tasks
- `[AGENT-NAME]-SPEC.md` for agent design docs
- `[feature]-v2.md` for upgrade specs

### Rule 5: Never Leave Specs Behind

After running a GSD:
- ✅ Move to /done
- ✅ Update tracker
- ✅ Commit
- ❌ Never leave completed specs in /specs/ root

---

## CLAUDE CODE INSTRUCTIONS

When Claude Code completes a GSD, it MUST:

```bash
# 1. Move spec
mv /opt/leveredge/specs/[spec].md /opt/leveredge/specs/done/

# 2. Log to LCIS
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{"content": "GSD completed: [summary]", "domain": "[domain]", "type": "success", "source_agent": "CLAUDE_CODE", "tags": ["gsd"]}'

# 3. Commit
git add -A && git commit -m "feat: [title] - GSD complete"
```

---

## SPEC QUALITY CHECKLIST

Before a spec is ready to run:

- [ ] Clear OVERVIEW (what and why)
- [ ] Specific DELIVERABLES (checkboxes)
- [ ] Step-by-step BUILD STEPS
- [ ] VERIFICATION commands
- [ ] ON COMPLETION section (mandatory)
- [ ] ROLLBACK instructions
- [ ] Realistic time estimate

---

*These rules ensure no work is lost and all builds are tracked.*
