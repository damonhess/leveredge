# UPDATE EXECUTION_RULES.md

Add the following section to /home/damon/.claude/EXECUTION_RULES.md:

---

## Lesson Capture (MANDATORY)

After debugging any issue or discovering a non-obvious fix:

1. **Append to /opt/leveredge/LESSONS-SCRATCH.md** using this format:

```markdown
### YYYY-MM-DD HH:MM - [Component]
**Symptom:** What broke
**Cause:** Why it broke  
**Fix:** How it was fixed
**Prevention:** How to avoid next time (optional)
```

2. **Examples of when to capture:**
   - Any error that took >5 minutes to debug
   - Any workaround for unexpected behavior
   - Any "gotcha" that isn't obvious
   - Container/network/credential issues
   - n8n expression or data flow fixes

3. **Do NOT skip this step.** Future sessions depend on captured knowledge.

---

Also ensure EXECUTION_RULES.md references:
- MCP server mapping: n8n-control (5679), n8n-troubleshooter (5678), n8n-troubleshooter-dev (5680)
- CHRONOS backup before major changes
- Check LESSONS-LEARNED.md before debugging known issues
