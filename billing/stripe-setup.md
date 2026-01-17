# Stripe Configuration Guide

Step-by-step guide to configure Stripe for LeverEdge billing.

## Prerequisites

- Stripe account (https://stripe.com)
- Admin access to LeverEdge infrastructure
- Access to environment variable configuration

## Step 1: Create Stripe Account

1. Go to https://dashboard.stripe.com/register
2. Complete business verification
3. Note: Start with Test Mode for development

## Step 2: Get API Keys

### Test Keys (Development)

1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy:
   - **Publishable key**: `pk_test_xxx`
   - **Secret key**: `sk_test_xxx`

### Live Keys (Production)

1. Complete Stripe business verification
2. Go to https://dashboard.stripe.com/apikeys
3. Copy:
   - **Publishable key**: `pk_live_xxx`
   - **Secret key**: `sk_live_xxx`

## Step 3: Configure Webhook

### Create Webhook Endpoint

1. Go to https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. Enter endpoint URL: `https://n8n.leveredgeai.com/webhook/stripe`
4. Select events to listen for:
   - `invoice.paid`
   - `invoice.payment_failed`
   - `invoice.created`
   - `invoice.finalized`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Click "Add endpoint"
6. Copy the **Signing secret**: `whsec_xxx`

## Step 4: Set Environment Variables

Add to n8n environment (docker-compose.yml or .env):

```bash
# Stripe Configuration
STRIPE_API_KEY=sk_live_xxx              # Or sk_test_xxx for testing
STRIPE_PUBLISHABLE_KEY=pk_live_xxx      # For frontend components
STRIPE_WEBHOOK_SECRET=whsec_xxx         # Webhook signing secret

# Optional: Stripe Connect (if using platform payments)
STRIPE_CONNECT_CLIENT_ID=ca_xxx
```

For n8n credentials:
1. Go to n8n Settings > Credentials
2. Create new "Stripe API" credential
3. Enter Secret Key
4. Name it "LeverEdge Stripe"

## Step 5: Create Products and Prices

### Via Stripe Dashboard

1. Go to https://dashboard.stripe.com/products
2. Create product: "LeverEdge AI Platform"
3. Add prices:
   - Monthly Base: $50/month
   - Usage-based: Metered billing per 1K tokens

### Via API (Recommended)

```bash
# Create product
curl https://api.stripe.com/v1/products \
  -u sk_test_xxx: \
  -d name="LeverEdge AI Platform" \
  -d description="AI automation and agent services"

# Create base price
curl https://api.stripe.com/v1/prices \
  -u sk_test_xxx: \
  -d product=prod_xxx \
  -d unit_amount=5000 \
  -d currency=usd \
  -d "recurring[interval]=month" \
  -d nickname="Monthly Base"

# Create metered price for token usage
curl https://api.stripe.com/v1/prices \
  -u sk_test_xxx: \
  -d product=prod_xxx \
  -d currency=usd \
  -d "recurring[interval]=month" \
  -d "recurring[usage_type]=metered" \
  -d unit_amount=1 \
  -d nickname="Token Usage (per 1K)"
```

## Step 6: Configure Customer Portal

1. Go to https://dashboard.stripe.com/settings/billing/portal
2. Enable features:
   - View invoices
   - Download invoices
   - Update payment method
   - Cancel subscription (optional)
3. Configure branding:
   - Business name: LeverEdge AI
   - Logo upload
   - Primary color
4. Save portal configuration

## Step 7: Test Integration

### Test Webhook

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local n8n
stripe listen --forward-to localhost:5678/webhook/stripe

# Trigger test event
stripe trigger invoice.paid
```

### Test Customer Creation

```bash
curl https://api.stripe.com/v1/customers \
  -u sk_test_xxx: \
  -d email="test@example.com" \
  -d name="Test Customer" \
  -d "metadata[leveredge_client_id]=xxx"
```

### Test Invoice Creation

```bash
# Create invoice
curl https://api.stripe.com/v1/invoices \
  -u sk_test_xxx: \
  -d customer=cus_xxx \
  -d collection_method=send_invoice \
  -d days_until_due=30

# Add line item
curl https://api.stripe.com/v1/invoiceitems \
  -u sk_test_xxx: \
  -d customer=cus_xxx \
  -d amount=5000 \
  -d currency=usd \
  -d description="January 2026 Usage"

# Finalize and send
curl https://api.stripe.com/v1/invoices/inv_xxx/finalize -u sk_test_xxx:
curl https://api.stripe.com/v1/invoices/inv_xxx/send -u sk_test_xxx:
```

## Step 8: Sync Existing Clients

Run this script to create Stripe customers for existing clients:

```python
import stripe
import os
from supabase import create_client

stripe.api_key = os.getenv('STRIPE_API_KEY')

# Get clients without Stripe ID
# For each, create customer and update database
```

## Stripe API Reference

### Common Operations

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create customer | /v1/customers | POST |
| Create invoice | /v1/invoices | POST |
| Add line item | /v1/invoiceitems | POST |
| Finalize invoice | /v1/invoices/{id}/finalize | POST |
| Send invoice | /v1/invoices/{id}/send | POST |
| Record usage | /v1/subscription_items/{id}/usage_records | POST |

### Webhook Events

| Event | When Fired | Action |
|-------|------------|--------|
| invoice.paid | Payment successful | Update invoice status |
| invoice.payment_failed | Payment failed | Notify client |
| customer.subscription.created | New subscription | Create billing_config |
| payment_intent.succeeded | Direct payment success | Record payment |

## Troubleshooting

### Webhook not receiving events

1. Check endpoint URL is correct
2. Verify webhook secret matches
3. Check n8n workflow is active
4. Review Stripe webhook logs

### Invoice not created

1. Verify customer exists
2. Check API key has write permissions
3. Review Stripe API errors

### Payment failed

1. Check customer payment method
2. Review decline reason in Stripe
3. Notify customer to update payment

## Security Notes

1. **Never commit API keys** - Use environment variables
2. **Rotate keys** if exposed
3. **Use restricted keys** for limited operations
4. **Verify webhook signatures** - Always verify `Stripe-Signature` header
5. **Use HTTPS** for all webhook endpoints

## Resources

- Stripe API Docs: https://stripe.com/docs/api
- Stripe CLI: https://stripe.com/docs/stripe-cli
- Webhook Testing: https://stripe.com/docs/webhooks/test
- Invoice Guide: https://stripe.com/docs/invoicing
