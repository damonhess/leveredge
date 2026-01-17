# SendGrid Configuration Guide

Detailed configuration steps for integrating SendGrid with LeverEdge.

## Initial Setup

### 1. Account Creation

1. Visit https://signup.sendgrid.com/
2. Enter your email, password, and company information
3. Verify your email address
4. Complete the account setup wizard

### 2. Two-Factor Authentication

Required for API access:

1. Go to **Settings** > **Two-Factor Authentication**
2. Choose authentication method (SMS or Authenticator app)
3. Complete setup and save backup codes

## API Configuration

### Creating API Keys

#### Production Key (Full Access)

```
Settings > API Keys > Create API Key
Name: leveredge-production
Access: Full Access
```

#### Restricted Keys (Recommended for Services)

Create separate keys for different services:

**Email Sending Key:**
```
Name: leveredge-email-send
Permissions:
  - Mail Send: Full Access
  - Suppressions: Read Access
```

**Analytics Key:**
```
Name: leveredge-analytics
Permissions:
  - Stats: Read Access
  - Tracking: Read Access
```

### API Key Security

1. Never commit API keys to version control
2. Use environment variables
3. Rotate keys periodically
4. Use restricted access when possible

```bash
# Store in environment
export SENDGRID_API_KEY='SG.xxxxx'

# Or use secret manager
aws secretsmanager create-secret \
    --name sendgrid-api-key \
    --secret-string "SG.xxxxx"
```

## Sender Authentication

### Single Sender Verification

For quick setup (development):

1. Go to **Settings** > **Sender Authentication** > **Single Sender Verification**
2. Click **Create New Sender**
3. Fill in sender details:
   - From Name: LeverEdge
   - From Email: noreply@leveredge.io
   - Reply To: support@leveredge.io
   - Company Address: [Your address]
4. Verify via email link

### Domain Authentication

For production (recommended):

1. Go to **Settings** > **Sender Authentication** > **Domain Authentication**
2. Click **Authenticate Your Domain**
3. Select DNS host or choose "I will manage my own DNS"
4. Enter your sending domain: `leveredge.io`
5. Choose branding options:
   - Use automated security: Yes
   - Custom link domain: Optional

### DNS Records to Add

After initiating domain authentication, add these records:

#### CNAME Records (Domain Verification)

```
Host: em1234.leveredge.io
Value: u1234567.wl123.sendgrid.net
TTL: 3600
```

#### CNAME Records (DKIM)

```
Host: s1._domainkey.leveredge.io
Value: s1.domainkey.u1234567.wl.sendgrid.net
TTL: 3600

Host: s2._domainkey.leveredge.io
Value: s2.domainkey.u1234567.wl.sendgrid.net
TTL: 3600
```

### Link Branding (Optional)

Customize tracking links to use your domain:

1. Go to **Settings** > **Sender Authentication** > **Link Branding**
2. Add your domain
3. Add the provided CNAME record
4. Verify after DNS propagation

## Email Settings

### Tracking Settings

Configure at **Settings** > **Tracking**:

| Setting | Recommendation | Purpose |
|---------|---------------|---------|
| Click Tracking | Enabled | Track link clicks |
| Open Tracking | Enabled | Track email opens |
| Subscription Tracking | Enabled | Add unsubscribe links |
| Google Analytics | Optional | UTM parameters |

### Suppression Management

Configure bounce/unsubscribe handling:

1. Go to **Suppressions** > **Unsubscribes**
2. Enable **Subscription Tracking**
3. Set up **Group Unsubscribes** for different email types:
   - Marketing
   - Transactional
   - Notifications

### Mail Settings

Configure at **Settings** > **Mail Settings**:

```yaml
address_whitelist: disabled  # Enable for testing
bcc: disabled
bypass_list_management: disabled
footer: disabled  # We use custom footers
forward_bounce: enabled  # Forward to support@leveredge.io
forward_spam: enabled
plain_content: enabled  # Generate plain text version
spam_check: enabled
```

## Webhooks Configuration

### Event Webhook

Receive email events in real-time:

1. Go to **Settings** > **Mail Settings** > **Event Webhook**
2. Set HTTP Post URL: `https://api.leveredge.io/webhooks/sendgrid`
3. Select events:
   - Processed
   - Delivered
   - Open
   - Click
   - Bounce
   - Dropped
   - Spam Report
   - Unsubscribe

### Inbound Parse

Process incoming emails:

1. Go to **Settings** > **Inbound Parse**
2. Add host/URL for incoming email handling
3. Configure MX record for receiving domain

## Rate Limits and Quotas

### Default Limits

| Plan | Daily Limit | Monthly Limit |
|------|-------------|---------------|
| Free | 100 emails | 100 emails |
| Essentials | 100,000 emails | 50,000+ emails |
| Pro | Unlimited | 100,000+ emails |

### Rate Limiting Best Practices

```python
# Implement exponential backoff
import time

def send_with_retry(email_data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = sg.send(email_data)
            return response
        except Exception as e:
            if '429' in str(e):  # Rate limited
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise
```

## Testing Configuration

### Sandbox Mode

Test without sending real emails:

```python
import sendgrid

sg = sendgrid.SendGridAPIClient(api_key='SG.xxxxx')
sg.client.mail.send.post(
    request_body={
        "personalizations": [...],
        "from": {...},
        "subject": "Test",
        "content": [...],
        "mail_settings": {
            "sandbox_mode": {
                "enable": True
            }
        }
    }
)
```

### Test Email Addresses

SendGrid provides test addresses that won't affect sender reputation:

- `bounce@simulator.amazonses.com` - Simulates bounce
- `complaint@simulator.amazonses.com` - Simulates spam complaint
- `success@simulator.amazonses.com` - Simulates successful delivery

## Environment-Specific Configuration

### Development

```yaml
# config.development.yaml
sendgrid:
  api_key: ${SENDGRID_API_KEY_DEV}
  sandbox_mode: true
  from_email: dev@leveredge.io
  tracking:
    click: false
    open: false
```

### Staging

```yaml
# config.staging.yaml
sendgrid:
  api_key: ${SENDGRID_API_KEY_STAGING}
  sandbox_mode: false
  from_email: staging@leveredge.io
  tracking:
    click: true
    open: true
```

### Production

```yaml
# config.production.yaml
sendgrid:
  api_key: ${SENDGRID_API_KEY_PROD}
  sandbox_mode: false
  from_email: noreply@leveredge.io
  tracking:
    click: true
    open: true
```

## Monitoring and Analytics

### Activity Feed

Monitor sent emails in real-time:

1. Go to **Activity** in the dashboard
2. Filter by:
   - Status (Delivered, Bounced, etc.)
   - Date range
   - Email address
   - Category/Tag

### Email Statistics

Track aggregate metrics:

- Delivered
- Opens (unique/total)
- Clicks (unique/total)
- Bounces
- Spam reports
- Unsubscribes

### Alerts

Set up alerts for:

1. High bounce rates
2. Spam complaint thresholds
3. Delivery failures
4. API errors

## Security Best Practices

1. **API Key Rotation**: Rotate keys quarterly
2. **IP Access Management**: Whitelist known IPs
3. **Subuser Accounts**: Isolate different applications
4. **Audit Logs**: Review API access regularly
5. **Webhook Validation**: Verify webhook signatures

### Webhook Signature Verification

```python
import hashlib
import hmac

def verify_webhook(payload, signature, timestamp, secret):
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}{payload}".encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```
