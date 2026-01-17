# LeverEdge Billing System

Invoice and billing foundation for LeverEdge AI automation services.

## Overview

This billing system integrates with:
- **Stripe** - Payment processing and subscription management
- **Supabase** - Usage tracking and invoice storage
- **n8n** - Automated monthly billing workflows

## Directory Structure

```
/opt/leveredge/billing/
├── README.md              # This file
├── schema.sql             # Database schema for billing tables
├── stripe-setup.md        # Stripe configuration guide
├── usage-tracker.py       # Aggregate usage from agent_usage_logs
├── billing-workflow.json  # n8n workflow for monthly billing
└── templates/
    └── invoice.html       # Invoice HTML template
```

## Quick Start

### 1. Database Setup

Run the schema in Supabase PROD:

```bash
# Connect to Supabase
psql -h localhost -p 5432 -U postgres -d postgres

# Run schema
\i /opt/leveredge/billing/schema.sql
```

### 2. Stripe Configuration

See [stripe-setup.md](./stripe-setup.md) for detailed Stripe configuration.

Required environment variables:
```bash
STRIPE_API_KEY=sk_live_xxx           # Or sk_test_xxx for testing
STRIPE_WEBHOOK_SECRET=whsec_xxx      # Webhook signing secret
STRIPE_PUBLISHABLE_KEY=pk_live_xxx   # For frontend (if needed)
```

### 3. Usage Tracking

The usage tracker aggregates data from `agent_usage_logs` table:

```bash
# Aggregate usage for all clients (last 30 days)
python3 /opt/leveredge/billing/usage-tracker.py

# Aggregate for specific client
python3 /opt/leveredge/billing/usage-tracker.py --client-id 123

# Aggregate for specific date range
python3 /opt/leveredge/billing/usage-tracker.py --start 2026-01-01 --end 2026-01-31
```

### 4. n8n Workflow

Import the billing workflow into n8n:

1. Open n8n (n8n.leveredgeai.com)
2. Create New Workflow
3. Import from JSON: `billing-workflow.json`
4. Configure credentials (Stripe, SMTP)
5. Activate workflow

The workflow runs monthly and:
- Aggregates usage per client
- Calculates charges based on billing_config
- Generates invoices
- Sends invoice emails
- Creates Stripe invoices (optional)

## Pricing Model

Default pricing (configurable per client in `billing_config`):

| Metric | Rate |
|--------|------|
| Claude Sonnet tokens | $3.00 / 1M input, $15.00 / 1M output |
| Claude Opus tokens | $15.00 / 1M input, $75.00 / 1M output |
| Web searches | $0.01 per search |
| Minimum monthly | $50.00 |

## Database Tables

| Table | Purpose |
|-------|---------|
| `clients` | Client information and Stripe customer ID |
| `invoices` | Generated invoices with status tracking |
| `usage_records` | Aggregated usage per client per agent |
| `billing_config` | Per-client billing configuration |

## API Endpoints

Future: Add PLUTUS agent endpoints for billing management.

```
GET  /billing/clients           # List clients
GET  /billing/clients/:id/usage # Get client usage
POST /billing/invoices/generate # Generate invoice
GET  /billing/invoices/:id      # Get invoice details
```

## Integration with Existing Systems

### Cost Tracking Integration

Usage flows from:
1. Agents log to `agent_usage_logs` (via cost_tracker.py)
2. `usage-tracker.py` aggregates by client
3. Billing workflow calculates charges
4. Invoice generated and sent

### HERMES Notifications

The billing workflow can notify via HERMES:
- Invoice generated
- Payment received
- Payment failed

## Maintenance

### Monthly Tasks

1. Review usage aggregation accuracy
2. Check for failed invoice deliveries
3. Reconcile Stripe payments

### Quarterly Tasks

1. Update pricing if needed
2. Review client billing configs
3. Archive old invoices

## Troubleshooting

### Invoice not sent
1. Check n8n workflow execution logs
2. Verify SMTP credentials
3. Check client email in database

### Stripe sync issues
1. Verify webhook is receiving events
2. Check STRIPE_WEBHOOK_SECRET
3. Review Stripe dashboard for errors

### Usage mismatch
1. Compare `agent_usage_logs` with `usage_records`
2. Check aggregation date ranges
3. Verify client_id mapping
