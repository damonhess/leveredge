# Client Onboarding Manual Checklist

This checklist covers manual tasks that complement the automated workflow. Use this for each new client engagement.

---

## Pre-Onboarding

### Lead Qualification

- [ ] Verify client contact information
- [ ] Confirm company details and industry
- [ ] Assess technical requirements
- [ ] Review budget and timeline expectations
- [ ] Determine appropriate plan tier
- [ ] Identify key stakeholders

### Internal Preparation

- [ ] Assign account manager
- [ ] Assign technical lead
- [ ] Create internal Slack channel: `#client-{company-name}`
- [ ] Schedule internal kickoff sync
- [ ] Review any special requirements or customizations

---

## Initial Meeting Agenda

### Kickoff Call Structure (60 minutes)

**1. Welcome & Introductions (10 min)**
- [ ] Introduce team members and roles
- [ ] Have client introduce key stakeholders
- [ ] Confirm primary point of contact

**2. Company Overview (5 min)**
- [ ] Brief LeverEdge AI introduction
- [ ] Highlight relevant case studies
- [ ] Share support contact information

**3. Client Goals & Objectives (15 min)**
- [ ] Understand business challenges
- [ ] Document specific automation goals
- [ ] Identify success metrics/KPIs
- [ ] Discuss timeline expectations

**4. Technical Discussion (15 min)**
- [ ] Review existing systems and tools
- [ ] Discuss integration requirements
- [ ] Identify data sources and formats
- [ ] Address security/compliance needs

**5. Service Overview (10 min)**
- [ ] Explain selected plan features
- [ ] Walk through portal and documentation
- [ ] Demonstrate API basics
- [ ] Show monitoring dashboard

**6. Next Steps & Q&A (5 min)**
- [ ] Confirm action items
- [ ] Schedule follow-up meetings
- [ ] Answer remaining questions

---

## Requirements Gathering Template

### Business Requirements

```
Company Name: ____________________
Industry: ____________________
Primary Contact: ____________________
Date: ____________________

1. CURRENT STATE
----------------
What manual processes are you looking to automate?
_________________________________________________________________
_________________________________________________________________

What tools/systems do you currently use?
- CRM: ____________________
- Accounting: ____________________
- Communication: ____________________
- Other: ____________________

What are your biggest pain points?
1. ____________________
2. ____________________
3. ____________________

2. DESIRED OUTCOME
------------------
What does success look like for this project?
_________________________________________________________________

What metrics will you use to measure success?
- [ ] Time saved (target: _____ hours/week)
- [ ] Cost reduction (target: $_____/month)
- [ ] Error reduction (target: _____%)
- [ ] Other: ____________________

What is your timeline for implementation?
- Start date: ____________________
- Go-live target: ____________________

3. TECHNICAL REQUIREMENTS
-------------------------
Data volume estimates:
- Records per day: ____________________
- API calls per hour: ____________________
- Storage needs: ____________________

Integration priorities (rank 1-5):
___ Email/SMTP
___ Slack/Teams
___ CRM (specify: ___________)
___ Database (specify: ___________)
___ Custom API
___ Other: ____________________

Security requirements:
- [ ] SOC 2 compliance required
- [ ] HIPAA compliance required
- [ ] GDPR compliance required
- [ ] Data residency requirements: ____________________
- [ ] SSO/SAML required
- [ ] IP whitelisting required

4. STAKEHOLDERS
---------------
Decision maker: ____________________
Technical lead: ____________________
Billing contact: ____________________
Additional users: ____________________

5. NOTES
--------
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

---

## Service Agreement Template

### Key Sections to Cover

**1. Scope of Services**
- [ ] Define included services
- [ ] Specify API/usage limits
- [ ] List integrations covered
- [ ] Note any exclusions

**2. Pricing & Payment**
- [ ] Confirm monthly/annual pricing
- [ ] Document any discounts applied
- [ ] Specify payment terms (Net 30, etc.)
- [ ] Clarify overage charges

**3. Service Level Agreement (SLA)**
- [ ] Uptime commitment (99.9%)
- [ ] Support response times
- [ ] Escalation procedures
- [ ] Maintenance windows

**4. Data & Security**
- [ ] Data handling procedures
- [ ] Encryption standards
- [ ] Backup frequency
- [ ] Disaster recovery

**5. Terms & Conditions**
- [ ] Contract duration
- [ ] Renewal terms
- [ ] Cancellation policy
- [ ] Liability limitations

**6. Signatures**
- [ ] Client signature
- [ ] LeverEdge authorized signature
- [ ] Effective date

---

## Technical Setup Checklist

### Client-Side Setup

- [ ] Client creates dedicated email for API notifications
- [ ] Client provides list of IP addresses for whitelisting (if applicable)
- [ ] Client prepares test data/sandbox environment
- [ ] Client assigns technical point of contact

### LeverEdge Setup

- [ ] Generate API credentials (automated via workflow)
- [ ] Configure rate limits per plan tier
- [ ] Set up monitoring alerts for client
- [ ] Create client-specific documentation (if custom)
- [ ] Configure backup schedule

### Integration Setup

For each integration:

| Integration | Status | Notes |
|-------------|--------|-------|
| Webhook endpoints | [ ] Configured | |
| API authentication | [ ] Tested | |
| Data mapping | [ ] Documented | |
| Error handling | [ ] Configured | |
| Logging | [ ] Enabled | |

### Security Verification

- [ ] API key securely delivered
- [ ] Client confirmed key storage
- [ ] Test authentication successful
- [ ] Webhook signatures enabled
- [ ] Access logs reviewed

---

## Training Checklist

### Portal Training (30 min)

- [ ] Login and navigation
- [ ] Dashboard overview
- [ ] Workflow management
- [ ] Settings and preferences
- [ ] Viewing execution logs

### API Training (45 min)

- [ ] Authentication methods
- [ ] Making basic API calls
- [ ] Handling responses
- [ ] Error handling
- [ ] Rate limits and best practices

### Workflow Training (60 min)

- [ ] Understanding workflow structure
- [ ] Common patterns and templates
- [ ] Testing and debugging
- [ ] Monitoring and alerts

### Documentation Review

- [ ] API documentation walkthrough
- [ ] Sample code review
- [ ] FAQ and troubleshooting guide
- [ ] Support ticket process

---

## Go-Live Checklist

### Pre-Launch

- [ ] All integrations tested
- [ ] Client signed off on requirements
- [ ] Training completed
- [ ] Documentation delivered
- [ ] Support contacts exchanged

### Launch Day

- [ ] Activate production workflows
- [ ] Monitor initial executions
- [ ] Verify data flowing correctly
- [ ] Confirm notifications working
- [ ] Check for any errors

### Post-Launch (First Week)

- [ ] Daily check-in with client
- [ ] Review execution logs
- [ ] Address any issues
- [ ] Gather initial feedback
- [ ] Optimize as needed

### Post-Launch (First Month)

- [ ] Weekly status calls
- [ ] Performance review
- [ ] Usage analytics report
- [ ] ROI assessment
- [ ] Plan renewal discussion

---

## Handoff Checklist

### Documentation Delivered

- [ ] API credentials and endpoints
- [ ] Workflow documentation
- [ ] Integration guides
- [ ] Troubleshooting playbook
- [ ] Support escalation path

### Knowledge Transfer

- [ ] Training sessions completed
- [ ] Recordings shared (if applicable)
- [ ] Q&A session held
- [ ] Client team confident

### Support Transition

- [ ] Support channels confirmed
- [ ] SLA acknowledged
- [ ] Emergency contacts exchanged
- [ ] First monthly review scheduled

---

## Quick Reference

### Client Information Card

```
Client ID: cli_________
Company: ____________________
Plan: [ ] Starter [ ] Professional [ ] Enterprise [ ] Custom

Primary Contact: ____________________
Email: ____________________
Phone: ____________________

Account Manager: ____________________
Technical Lead: ____________________

Start Date: ____________________
Renewal Date: ____________________

Slack Channel: #client-________
Internal Notes: ____________________
```

### Important Links

- Client Portal: https://portal.leveredgeai.com
- API Docs: https://docs.leveredgeai.com
- Status Page: https://status.leveredgeai.com
- Support: support@leveredgeai.com

---

## Notes

Use this section to document client-specific notes, preferences, and important details:

```
Date: ____________________

Notes:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

Action Items:
1. ____________________  Due: ______  Owner: ______
2. ____________________  Due: ______  Owner: ______
3. ____________________  Due: ______  Owner: ______
```

---

*Template Version: 1.0.0*
*Last Updated: January 2026*
