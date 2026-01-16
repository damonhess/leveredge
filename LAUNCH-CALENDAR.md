# LAUNCH CALENDAR: March 1, 2026

*Created: January 16, 2026*
*45 days to launch*

---

## CURRENT BLOCKERS

| Blocker | Why it matters | Effort |
|---------|----------------|--------|
| ARIA not migrated | Can't demo without working ARIA | 2-3 days |
| No dev/prod mirror | Can't safely develop ARIA | 1-2 days |
| No outreach prep | Don't know how to reach clients | 1 week |
| No niche selected | Don't know WHO to reach | 2-3 days |

---

## THE CALENDAR

### WEEK 1: January 16-22 (Infrastructure)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Jan 16 | ✅ DONE | Control plane + HEPHAESTUS MCP + Phase 4 agents |
| Fri | Jan 17 | Data plane setup | Dev n8n (5680) + Prod n8n (5678) mirrored |
| Sat | Jan 18 | ARIA migration | ARIA on new infrastructure |
| Sun | Jan 19 | ARIA testing | ARIA demo-ready, all modes working |
| Mon | Jan 20 | Buffer / fixes | Handle whatever broke |
| Tue | Jan 21 | Dev workflow | promote-to-prod.sh working for ARIA |
| Wed | Jan 22 | **ARIA DEMO-READY** | Can show ARIA to anyone |

### WEEK 2: January 23-29 (Outreach Prep)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Jan 23 | Niche research | Top 3 niches identified |
| Fri | Jan 24 | Niche selection | Pick ONE niche, document ICP |
| Sat | Jan 25 | TRW Module start | Begin outreach training |
| Sun | Jan 26 | TRW Module | Continue outreach training |
| Mon | Jan 27 | TRW Module | Complete outreach training |
| Tue | Jan 28 | Outreach materials | Loom video, case studies packaged |
| Wed | Jan 29 | **OUTREACH READY** | Scripts, materials, list of 50 targets |

### WEEK 3: January 30 - February 5 (First Outreach)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Jan 30 | Outreach Day 1 | 3 outreach attempts |
| Fri | Jan 31 | Outreach Day 2 | 3 outreach attempts |
| Sat | Feb 1 | Outreach Day 3 | 2 outreach attempts |
| Sun | Feb 2 | Rest / follow-up | Respond to any replies |
| Mon | Feb 3 | Outreach Day 4 | 2 outreach attempts |
| Tue | Feb 4 | **10 ATTEMPTS DONE** | Review what's working |
| Wed | Feb 5 | Refine approach | Adjust based on responses |

### WEEK 4: February 6-12 (Discovery Calls)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Feb 6 | Outreach continues | Target warm leads |
| Fri | Feb 7 | Discovery call prep | Script, demo flow ready |
| Sat | Feb 8 | Discovery call 1 | First real sales call |
| Sun | Feb 9 | Debrief / adjust | What worked, what didn't |
| Mon | Feb 10 | Discovery call 2 | Second sales call |
| Tue | Feb 11 | Discovery call 3 | Third sales call |
| Wed | Feb 12 | **3 CALLS DONE** | Lessons learned documented |

### WEEK 5: February 13-19 (Close or Learn)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Feb 13 | Follow-up calls | Close interested leads |
| Fri | Feb 14 | Proposal writing | Send proposals if needed |
| Sat | Feb 15 | More outreach | Expand to 20 attempts |
| Sun | Feb 16 | Rest | Recharge |
| Mon | Feb 17 | Pipeline review | Where are deals? |
| Tue | Feb 18 | Adjust strategy | Pivot if needed |
| Wed | Feb 19 | Continue outreach | Keep pipeline full |

### WEEK 6: February 20-26 (Pre-Launch Push)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Feb 20 | Close deals | Convert proposals |
| Fri | Feb 21 | Onboarding prep | How to onboard first client |
| Sat | Feb 22 | Systems check | Everything working? |
| Sun | Feb 23 | Rest | Recharge before launch |
| Mon | Feb 24 | Final outreach push | Last attempts |
| Tue | Feb 25 | Close pipeline | Follow up on everything |
| Wed | Feb 26 | Launch prep | Finalize everything |

### WEEK 7: February 27 - March 1 (LAUNCH)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Feb 27 | Final prep | All systems go |
| Fri | Feb 28 | Soft launch | Ready to take clients |
| Sat | **Mar 1** | **LAUNCH DAY** | IN BUSINESS |

---

## MILESTONES

| Date | Milestone | Success Criteria |
|------|-----------|------------------|
| Jan 22 | ARIA Demo-Ready | Can show working demo to anyone |
| Jan 29 | Outreach Ready | Scripts, materials, 50 targets |
| Feb 4 | 10 Attempts | Sent 10 real outreach messages |
| Feb 12 | 3 Calls | Completed 3 discovery calls |
| Mar 1 | LAUNCH | First paying client or active pipeline |

---

## IMMEDIATE NEXT STEPS (Tomorrow - Jan 17)

### Data Plane Migration

1. **Dev n8n** (port 5680)
   - Fresh PostgreSQL
   - Connect to control plane Event Bus
   - Mirror of prod workflows

2. **Prod n8n** (port 5678)
   - Fresh PostgreSQL
   - Production ARIA workflows
   - Client-facing

3. **Dev → Prod workflow**
   - promote-to-prod.sh script
   - CHRONOS backup before promote
   - HADES rollback if fails

### ARIA Migration

1. Export ARIA workflows from current location
2. Import to new Prod n8n
3. Clone to Dev n8n
4. Verify all modes work
5. Test full conversation flow

---

## WHAT'S NOT ON THIS CALENDAR

Intentionally deferred:
- LinkedIn posting (after first clients)
- Website improvements
- Additional agent features
- Credential manager automation
- Monitoring dashboards

These don't help get first client. They can wait.

---

## ACCOUNTABILITY

Weekly check-ins:
- **Jan 22**: Is ARIA demo-ready? Y/N
- **Jan 29**: Is outreach ready? Y/N
- **Feb 4**: Did you send 10 attempts? Y/N
- **Feb 12**: Did you complete 3 calls? Y/N
- **Mar 1**: Do you have a client or active pipeline? Y/N

If any answer is NO, we need to understand why and adjust.
