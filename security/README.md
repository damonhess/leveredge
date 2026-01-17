# LeverEdge Security Hardening Guide

## Overview

This directory contains comprehensive security hardening configurations for the LeverEdge platform. These configurations implement defense-in-depth security measures across multiple layers:

- **Network Layer**: UFW firewall rules and Docker network isolation
- **Application Layer**: Fail2ban intrusion prevention
- **Monitoring Layer**: CERBERUS security agent configuration

## Directory Structure

```
/opt/leveredge/security/
├── README.md                          # This file
├── audit-checklist.md                 # Security audit checklist
├── install.sh                         # Installation script
├── fail2ban/
│   ├── jail.local                     # Main Fail2ban configuration
│   ├── filter.d/
│   │   └── leveredge.conf             # Custom filters for LeverEdge logs
│   └── action.d/
│       └── notify-hermes.conf         # HERMES notification action
├── ufw/
│   └── rules.sh                       # UFW firewall configuration
├── docker/
│   ├── network-isolation.md           # Docker network setup guide
│   └── docker-compose.security.yml    # Security overlay for Docker Compose
└── cerberus/
    └── monitoring-config.yaml         # CERBERUS monitoring configuration
```

## Quick Start

### Prerequisites

- Ubuntu 20.04+ or Debian 11+
- Root access (sudo)
- Docker and Docker Compose installed
- Fail2ban installed: `sudo apt install fail2ban`
- UFW installed: `sudo apt install ufw`

### Installation

```bash
# Make the installation script executable
chmod +x /opt/leveredge/security/install.sh

# Run the installation (requires sudo)
sudo /opt/leveredge/security/install.sh
```

### Verification

After installation, verify each component:

```bash
# Check UFW status
sudo ufw status verbose

# Check Fail2ban status
sudo fail2ban-client status

# Check Fail2ban jails
sudo fail2ban-client status sshd
sudo fail2ban-client status n8n-auth

# Check Docker networks
docker network ls | grep leveredge
```

## Component Details

### 1. Fail2ban Configuration

Fail2ban provides intrusion prevention by monitoring logs and banning IPs that show malicious patterns.

#### Configured Jails

| Jail | Purpose | Max Retries | Ban Time |
|------|---------|-------------|----------|
| sshd | SSH brute force protection | 3 | 1 hour |
| sshd-ddos | SSH DDoS protection | 10 | 48 hours |
| nginx-* | Web server protection | 5-10 | 1-12 hours |
| n8n-auth | n8n authentication | 5 | 1 hour |
| supabase-auth | Supabase authentication | 5 | 1 hour |
| leveredge-agents | Agent API protection | 10 | 30 minutes |
| cerberus-detected | Auto-ban on CERBERUS alerts | 1 | 24 hours |
| portscan | Port scanning detection | 5 | 24 hours |
| recidive | Repeat offenders | 5 | 1 week |

#### Custom Filters

The `leveredge.conf` filter detects:
- Authentication failures across all agents
- API key rejections
- Rate limit violations
- SQL injection attempts
- XSS attempts
- Path traversal attempts
- Command injection attempts

#### HERMES Integration

All bans trigger notifications through HERMES:
- Slack alerts for all bans
- Email notifications for critical events
- SMS/PagerDuty for severe threats

### 2. UFW Firewall Configuration

The firewall implements strict ingress rules with localhost-only access for internal services.

#### Port Access Matrix

| Service | Port(s) | Access |
|---------|---------|--------|
| SSH | 22 | Anywhere (rate limited) |
| HTTP | 80 | Anywhere |
| HTTPS | 443 | Anywhere |
| n8n | 5678-5680 | Localhost only |
| Supabase | 3000, 4000, 5000, 8000-8001, 9999 | Localhost only |
| PostgreSQL | 5432 | Localhost only |
| Agents | 8000-8300 | Localhost only |
| Redis | 6379 | Localhost only |
| Monitoring | 3001, 3100, 9090 | Localhost only |

#### Usage

```bash
# Preview rules without applying
./ufw/rules.sh test

# Apply rules
sudo ./ufw/rules.sh apply

# Check status
sudo ./ufw/rules.sh status

# Reset to defaults
sudo ./ufw/rules.sh reset
```

### 3. Docker Network Isolation

Docker containers are isolated into purpose-specific networks.

#### Network Architecture

| Network | Subnet | Purpose |
|---------|--------|---------|
| leveredge-dmz | 172.20.0.0/24 | Public-facing services |
| leveredge-app | 172.21.0.0/24 | Application services |
| leveredge-agents | 172.22.0.0/24 | AI agents |
| leveredge-data | 172.23.0.0/24 | Databases (internal only) |
| leveredge-monitor | 172.24.0.0/24 | Monitoring stack |

#### Applying Security Overlay

```bash
# Apply with existing docker-compose
docker-compose \
  -f docker-compose.yml \
  -f /opt/leveredge/security/docker/docker-compose.security.yml \
  up -d
```

### 4. CERBERUS Monitoring

CERBERUS continuously monitors for security threats.

#### Monitored Categories

1. **Failed Login Attempts**
   - Brute force detection
   - Credential stuffing detection
   - Distributed attack detection

2. **Rate Limit Breaches**
   - API abuse detection
   - Burst traffic detection
   - DDoS indicators

3. **Unusual API Patterns**
   - Geographic anomalies
   - Time-based anomalies
   - Endpoint scanning
   - Injection attempts

4. **Port Scan Detection**
   - Vertical scans (single IP, multiple ports)
   - Horizontal scans (single port, multiple IPs)
   - SYN flood detection

## Security Hardening Levels

### Level 1: Basic (Default)
- UFW enabled with default rules
- Fail2ban with SSH protection
- Basic Docker isolation

### Level 2: Enhanced
- All custom Fail2ban jails enabled
- CERBERUS monitoring active
- Network segmentation enforced

### Level 3: Maximum
- All features enabled
- Geographic blocking active
- Threat intelligence integration
- Real-time alerting

## Monitoring and Alerts

### Alert Channels

| Severity | Channels |
|----------|----------|
| INFO | Logs only |
| LOW | Slack |
| MEDIUM | Slack, Email |
| HIGH | Slack, Email, SMS |
| CRITICAL | Slack, Email, SMS, PagerDuty |

### Dashboard Access

Security dashboard available at:
- Grafana: `http://localhost:3001/d/security`
- CERBERUS API: `http://localhost:8200/api/v1/security/dashboard`

## Maintenance

### Regular Tasks

```bash
# Check banned IPs
sudo fail2ban-client status sshd

# Unban an IP
sudo fail2ban-client set sshd unbanip 1.2.3.4

# View Fail2ban logs
tail -f /var/log/fail2ban.log

# Check UFW logs
tail -f /var/log/ufw.log

# View CERBERUS alerts
cat /opt/leveredge/cerberus/logs/threats.log
```

### Backup Security Configurations

```bash
# Backup all security configs
tar -czf /opt/leveredge/backups/security-$(date +%Y%m%d).tar.gz \
  /opt/leveredge/security/
```

## Troubleshooting

### Common Issues

**Issue**: Legitimate users getting banned

**Solution**:
```bash
# Check why IP was banned
sudo fail2ban-client status <jail-name>
sudo zgrep "Ban <IP>" /var/log/fail2ban.log*

# Whitelist the IP
sudo fail2ban-client set <jail-name> addignoreip <IP>
```

**Issue**: Services unreachable after UFW update

**Solution**:
```bash
# Check if UFW is blocking
sudo ufw status verbose

# Temporarily disable for testing
sudo ufw disable

# Add missing rule
sudo ufw allow from 127.0.0.1 to any port <PORT>
```

**Issue**: Docker containers can't communicate

**Solution**:
```bash
# Check container network assignment
docker inspect <container> | jq '.[0].NetworkSettings.Networks'

# Verify network exists
docker network ls | grep leveredge

# Reconnect container to correct network
docker network connect leveredge-app <container>
```

## Security Contacts

- Security Team: security@leveredge.internal
- On-Call: oncall@leveredge.internal
- Emergency: +1-XXX-XXX-XXXX

## References

- [Fail2ban Documentation](https://fail2ban.org)
- [UFW Documentation](https://help.ubuntu.com/community/UFW)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [OWASP Security Guidelines](https://owasp.org)
