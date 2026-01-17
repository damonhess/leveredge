# Email Configuration Guide

Complete email setup for LeverEdge using SendGrid and Supabase Auth.

## Table of Contents

1. [SendGrid Account Setup](#sendgrid-account-setup)
2. [API Key Configuration](#api-key-configuration)
3. [Domain Verification](#domain-verification)
4. [DKIM/SPF Setup](#dkimspf-setup)
5. [Supabase Email Templates](#supabase-email-templates)
6. [Testing Email Delivery](#testing-email-delivery)

---

## SendGrid Account Setup

### Step 1: Create SendGrid Account

1. Go to [SendGrid Signup](https://signup.sendgrid.com/)
2. Create an account using your business email
3. Complete email verification
4. Fill out the sender profile information

### Step 2: Choose a Plan

- **Free Plan**: 100 emails/day (good for development)
- **Essentials**: 50,000 emails/month starting at $19.95/month
- **Pro**: 100,000+ emails/month with advanced features

### Step 3: Complete Account Setup

1. Verify your phone number
2. Set up two-factor authentication (required for API access)
3. Complete the sender identity verification

---

## API Key Configuration

### Create API Key

1. Navigate to **Settings** > **API Keys**
2. Click **Create API Key**
3. Name your key (e.g., `leveredge-production`)
4. Select permissions:
   - **Full Access** for production
   - **Restricted Access** for specific services:
     - Mail Send: Full Access
     - Template Engine: Read Access (if using SendGrid templates)

### Store API Key Securely

```bash
# Add to environment variables (production)
export SENDGRID_API_KEY='SG.xxxxxxxxxxxxxxxxxxxx'

# Or add to .env file (development)
echo "SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxx" >> .env
```

### Update config.yaml

```yaml
sendgrid_api_key: ${SENDGRID_API_KEY}  # Reference environment variable
```

---

## Domain Verification

### Why Verify Your Domain?

- Improved email deliverability
- Professional sender identity
- Required for high-volume sending
- Enables custom tracking domains

### Step 1: Add Domain

1. Go to **Settings** > **Sender Authentication**
2. Click **Authenticate Your Domain**
3. Select your DNS provider (or "Other" if not listed)
4. Enter your domain (e.g., `leveredge.io`)

### Step 2: Add DNS Records

SendGrid will provide DNS records to add. Typically includes:

| Type  | Host                          | Value                              |
|-------|-------------------------------|------------------------------------|
| CNAME | em1234.yourdomain.com         | u1234567.wl123.sendgrid.net       |
| CNAME | s1._domainkey.yourdomain.com  | s1.domainkey.u1234567.wl.sendgrid.net |
| CNAME | s2._domainkey.yourdomain.com  | s2.domainkey.u1234567.wl.sendgrid.net |

### Step 3: Verify DNS Propagation

```bash
# Check DNS propagation
dig em1234.yourdomain.com CNAME
dig s1._domainkey.yourdomain.com CNAME
```

### Step 4: Complete Verification

1. Return to SendGrid dashboard
2. Click **Verify** for each DNS record
3. Wait for verification (can take up to 48 hours)

---

## DKIM/SPF Setup

### What is DKIM?

DomainKeys Identified Mail (DKIM) adds a digital signature to emails, proving they came from your domain.

### What is SPF?

Sender Policy Framework (SPF) specifies which mail servers are authorized to send email for your domain.

### DKIM Configuration

DKIM is automatically configured when you verify your domain with SendGrid. The s1 and s2 CNAME records enable DKIM signing.

### SPF Configuration

Add SendGrid to your SPF record:

```
v=spf1 include:sendgrid.net ~all
```

If you have existing SPF records, append SendGrid:

```
v=spf1 include:_spf.google.com include:sendgrid.net ~all
```

### DMARC Configuration (Recommended)

Add a DMARC record for additional protection:

```
Type: TXT
Host: _dmarc.yourdomain.com
Value: v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com
```

DMARC policies:
- `p=none` - Monitor only (start here)
- `p=quarantine` - Send suspicious emails to spam
- `p=reject` - Reject unauthorized emails

### Verify Email Authentication

Use these tools to verify your setup:

1. **MX Toolbox**: https://mxtoolbox.com/
2. **Mail Tester**: https://www.mail-tester.com/
3. **Google Admin Toolbox**: https://toolbox.googleapps.com/apps/checkmx/

---

## Supabase Email Templates

### Configure Supabase Auth Emails

1. Go to your Supabase project dashboard
2. Navigate to **Authentication** > **Email Templates**
3. For each template type, paste the HTML from `supabase-templates/`

### Template Variables

Supabase provides these variables for templates:

| Variable | Description |
|----------|-------------|
| `{{ .ConfirmationURL }}` | Email confirmation link |
| `{{ .Token }}` | OTP token |
| `{{ .TokenHash }}` | Hashed token |
| `{{ .SiteURL }}` | Your application URL |
| `{{ .Email }}` | User's email address |

### SMTP Configuration in Supabase

For custom SMTP (SendGrid) in Supabase:

1. Go to **Project Settings** > **Authentication**
2. Scroll to **SMTP Settings**
3. Enable **Custom SMTP**
4. Enter SendGrid SMTP details:

```
Host: smtp.sendgrid.net
Port: 587
Username: apikey
Password: [Your SendGrid API Key]
Sender email: noreply@yourdomain.com
Sender name: LeverEdge
```

---

## Testing Email Delivery

### Test with Python Script

```bash
cd /opt/leveredge/integrations/email
pip install -r requirements.txt
python email-sender.py --to test@example.com --template welcome
```

### Test with n8n Workflow

1. Import `n8n-email-workflow.json` into n8n
2. Configure the SendGrid credential
3. Trigger the webhook with test data

### Verify Delivery

1. Check SendGrid Activity Feed for delivery status
2. Verify emails in recipient inbox
3. Check spam folder if not delivered
4. Review bounce messages for errors

---

## Directory Structure

```
/opt/leveredge/integrations/email/
├── README.md                    # This file
├── sendgrid-config.md          # SendGrid configuration details
├── config.yaml                  # Email configuration
├── requirements.txt             # Python dependencies
├── email-sender.py              # Email sending utility
├── n8n-email-workflow.json      # n8n workflow for emails
├── templates/                   # Client communication templates
│   ├── welcome.html
│   ├── password-reset.html
│   ├── invoice.html
│   ├── reminder.html
│   ├── notification.html
│   └── weekly-summary.html
└── supabase-templates/          # Supabase Auth templates
    ├── confirm-signup.html
    ├── reset-password.html
    ├── magic-link.html
    └── invite-user.html
```

---

## Troubleshooting

### Common Issues

**Emails going to spam:**
- Verify domain authentication
- Check SPF/DKIM/DMARC records
- Avoid spam trigger words
- Build sender reputation gradually

**Emails not sending:**
- Verify API key is correct
- Check SendGrid account status
- Review API response errors
- Confirm sender email is verified

**Template rendering issues:**
- Validate HTML syntax
- Check variable placeholders
- Test with different email clients

### Support Resources

- SendGrid Documentation: https://docs.sendgrid.com/
- Supabase Auth Docs: https://supabase.com/docs/guides/auth
- Email Deliverability Guide: https://sendgrid.com/solutions/email-deliverability/
