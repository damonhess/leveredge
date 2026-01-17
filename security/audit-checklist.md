# LeverEdge Security Audit Checklist

## Overview

This checklist provides a comprehensive security audit framework for the LeverEdge platform. Use this for regular security assessments, compliance checks, and incident reviews.

**Audit Frequency**: Monthly (standard), Weekly (high-security environments), After any security incident

**Last Updated**: 2024-01-15
**Version**: 1.0.0

---

## Pre-Audit Preparation

- [ ] Schedule audit window with stakeholders
- [ ] Gather previous audit reports
- [ ] Collect current architecture diagrams
- [ ] Ensure access to all systems
- [ ] Prepare secure documentation storage
- [ ] Notify on-call team of audit activities

---

## 1. Network Security

### 1.1 Firewall Configuration

| Check | Status | Notes |
|-------|--------|-------|
| [ ] UFW is enabled and active | | |
| [ ] Default policy denies incoming | | |
| [ ] Default policy allows outgoing | | |
| [ ] SSH uses rate limiting | | |
| [ ] Only ports 22, 80, 443 open externally | | |
| [ ] Internal ports (5678, 8000, etc.) localhost only | | |
| [ ] No unnecessary ports open | | |
| [ ] Firewall rules documented | | |

**Verification Commands**:
```bash
sudo ufw status verbose
sudo ufw status numbered
sudo netstat -tlnp | grep LISTEN
```

### 1.2 Docker Network Isolation

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Separate networks for DMZ, app, agents, data | | |
| [ ] Data network marked as internal | | |
| [ ] No containers on default bridge network | | |
| [ ] Inter-container communication restricted | | |
| [ ] Network policies documented | | |

**Verification Commands**:
```bash
docker network ls
docker network inspect leveredge-data
docker ps --format '{{.Names}}: {{.Networks}}'
```

### 1.3 TLS/SSL Configuration

| Check | Status | Notes |
|-------|--------|-------|
| [ ] All external endpoints use HTTPS | | |
| [ ] TLS 1.2+ enforced | | |
| [ ] Strong cipher suites configured | | |
| [ ] Certificates valid and not expiring soon | | |
| [ ] HSTS enabled | | |
| [ ] Certificate chain complete | | |

**Verification Commands**:
```bash
openssl s_client -connect localhost:443 -tls1_2
openssl x509 -in /path/to/cert.pem -noout -dates
curl -I https://your-domain.com
```

---

## 2. Authentication & Authorization

### 2.1 Credential Management

| Check | Status | Notes |
|-------|--------|-------|
| [ ] No hardcoded credentials in code | | |
| [ ] Secrets stored in secure vault | | |
| [ ] API keys rotated within last 90 days | | |
| [ ] Default passwords changed | | |
| [ ] Service accounts have minimal permissions | | |
| [ ] SSH keys use Ed25519 or RSA-4096 | | |

**Verification Commands**:
```bash
# Search for potential secrets in code
grep -r "password\|secret\|api_key" /opt/leveredge --include="*.js" --include="*.py" --include="*.yaml"

# Check SSH key types
for key in ~/.ssh/*.pub; do ssh-keygen -l -f "$key"; done
```

### 2.2 Access Control

| Check | Status | Notes |
|-------|--------|-------|
| [ ] RBAC implemented for n8n | | |
| [ ] Supabase RLS policies active | | |
| [ ] API endpoints require authentication | | |
| [ ] Admin access restricted | | |
| [ ] MFA enabled for admin accounts | | |
| [ ] Session timeouts configured | | |

### 2.3 Password Policies

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Minimum 12 character passwords | | |
| [ ] Complexity requirements enforced | | |
| [ ] Password history enforced | | |
| [ ] Account lockout after failed attempts | | |
| [ ] No password hints exposed | | |

---

## 3. Intrusion Prevention

### 3.1 Fail2ban Configuration

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Fail2ban service running | | |
| [ ] SSH jail enabled | | |
| [ ] n8n auth jail enabled | | |
| [ ] Supabase auth jail enabled | | |
| [ ] Agent protection jails enabled | | |
| [ ] Port scan detection enabled | | |
| [ ] Recidive jail enabled | | |
| [ ] Ban times appropriate | | |
| [ ] HERMES notifications configured | | |

**Verification Commands**:
```bash
sudo systemctl status fail2ban
sudo fail2ban-client status
sudo fail2ban-client status sshd
cat /var/log/fail2ban.log | tail -50
```

### 3.2 Rate Limiting

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Nginx rate limiting configured | | |
| [ ] API rate limits enforced | | |
| [ ] Webhook rate limits enforced | | |
| [ ] Rate limit responses logged | | |
| [ ] Burst limits appropriate | | |

---

## 4. Monitoring & Logging

### 4.1 CERBERUS Configuration

| Check | Status | Notes |
|-------|--------|-------|
| [ ] CERBERUS service running | | |
| [ ] Failed login detection enabled | | |
| [ ] Rate limit detection enabled | | |
| [ ] Unusual API pattern detection enabled | | |
| [ ] Port scan detection enabled | | |
| [ ] Alert thresholds appropriate | | |
| [ ] Alert channels configured | | |

**Verification Commands**:
```bash
docker logs cerberus --tail 100
curl http://localhost:8200/api/v1/health
cat /opt/leveredge/cerberus/logs/threats.log | tail -20
```

### 4.2 Log Management

| Check | Status | Notes |
|-------|--------|-------|
| [ ] All services logging to central location | | |
| [ ] Log rotation configured | | |
| [ ] Logs retained for 90+ days | | |
| [ ] Sensitive data not logged | | |
| [ ] Logs protected from tampering | | |
| [ ] Log shipping to SIEM configured | | |

**Verification Commands**:
```bash
ls -la /var/log/leveredge/
cat /etc/logrotate.d/leveredge
du -sh /var/log/
```

### 4.3 Alerting

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Critical alerts go to SMS/PagerDuty | | |
| [ ] Alert escalation configured | | |
| [ ] Alert aggregation prevents fatigue | | |
| [ ] On-call rotation documented | | |
| [ ] Alert testing performed recently | | |

---

## 5. Container Security

### 5.1 Image Security

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Base images from trusted sources | | |
| [ ] Images scanned for vulnerabilities | | |
| [ ] No high/critical CVEs in images | | |
| [ ] Images pinned to specific versions | | |
| [ ] Image signing enabled | | |

**Verification Commands**:
```bash
docker images --format "{{.Repository}}:{{.Tag}}"
# If Trivy installed:
trivy image n8nio/n8n:latest
```

### 5.2 Container Hardening

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Containers run as non-root | | |
| [ ] no-new-privileges enabled | | |
| [ ] Unnecessary capabilities dropped | | |
| [ ] Read-only filesystems where possible | | |
| [ ] Resource limits configured | | |
| [ ] Health checks defined | | |

**Verification Commands**:
```bash
docker inspect --format '{{.Config.User}}' <container>
docker inspect --format '{{.HostConfig.SecurityOpt}}' <container>
docker inspect --format '{{.HostConfig.CapDrop}}' <container>
```

### 5.3 Docker Daemon Security

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Docker socket not exposed | | |
| [ ] Remote API disabled or secured | | |
| [ ] User namespaces enabled | | |
| [ ] Content trust enabled | | |
| [ ] Audit logging enabled | | |

---

## 6. Application Security

### 6.1 n8n Security

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Basic auth or SSO enabled | | |
| [ ] Secure cookie flag enabled | | |
| [ ] Execution data encrypted | | |
| [ ] Webhook URLs not guessable | | |
| [ ] External connections validated | | |
| [ ] Code node restricted (if applicable) | | |

### 6.2 Supabase Security

| Check | Status | Notes |
|-------|--------|-------|
| [ ] RLS enabled on all tables | | |
| [ ] Service role key protected | | |
| [ ] Anon key has minimal permissions | | |
| [ ] JWT secret rotated | | |
| [ ] Auth rate limiting enabled | | |
| [ ] Realtime subscriptions secured | | |

### 6.3 API Security

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Input validation on all endpoints | | |
| [ ] Output encoding implemented | | |
| [ ] CORS properly configured | | |
| [ ] API versioning in place | | |
| [ ] Deprecation policy documented | | |

---

## 7. Data Security

### 7.1 Encryption at Rest

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Database encryption enabled | | |
| [ ] Backup encryption enabled | | |
| [ ] Volume encryption enabled | | |
| [ ] Encryption keys properly managed | | |

### 7.2 Encryption in Transit

| Check | Status | Notes |
|-------|--------|-------|
| [ ] All internal communication encrypted | | |
| [ ] Database connections use SSL | | |
| [ ] Redis connections use TLS | | |
| [ ] Agent-to-agent TLS enabled | | |

### 7.3 Data Classification

| Check | Status | Notes |
|-------|--------|-------|
| [ ] PII identified and tagged | | |
| [ ] Sensitive data inventoried | | |
| [ ] Data retention policies defined | | |
| [ ] Data deletion procedures documented | | |

---

## 8. Backup & Recovery

### 8.1 Backup Configuration

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Automated backups configured | | |
| [ ] Backups encrypted | | |
| [ ] Backups stored off-site | | |
| [ ] Backup retention appropriate | | |
| [ ] Backup integrity verified | | |

### 8.2 Recovery Testing

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Recovery tested within last quarter | | |
| [ ] RTO/RPO documented | | |
| [ ] Recovery procedures documented | | |
| [ ] Recovery keys accessible | | |

---

## 9. Patch Management

### 9.1 System Patches

| Check | Status | Notes |
|-------|--------|-------|
| [ ] OS patches current | | |
| [ ] Unattended upgrades configured | | |
| [ ] Kernel version current | | |
| [ ] Security patches applied within SLA | | |

**Verification Commands**:
```bash
apt list --upgradable
uname -r
cat /etc/os-release
```

### 9.2 Application Patches

| Check | Status | Notes |
|-------|--------|-------|
| [ ] n8n version current | | |
| [ ] Supabase version current | | |
| [ ] Docker version current | | |
| [ ] Node.js version current | | |
| [ ] Python version current (if used) | | |

**Verification Commands**:
```bash
docker exec n8n n8n --version
docker --version
node --version
```

---

## 10. Compliance & Documentation

### 10.1 Security Documentation

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Security policies documented | | |
| [ ] Incident response plan current | | |
| [ ] Business continuity plan current | | |
| [ ] Change management process defined | | |
| [ ] Security contacts documented | | |

### 10.2 Compliance

| Check | Status | Notes |
|-------|--------|-------|
| [ ] Relevant compliance frameworks identified | | |
| [ ] Compliance controls mapped | | |
| [ ] Audit trails maintained | | |
| [ ] Privacy policy current | | |
| [ ] Terms of service current | | |

---

## Audit Summary

### Critical Findings (Fix Immediately)

| Finding | Risk | Remediation | Owner | Due Date |
|---------|------|-------------|-------|----------|
| | | | | |

### High Findings (Fix Within 7 Days)

| Finding | Risk | Remediation | Owner | Due Date |
|---------|------|-------------|-------|----------|
| | | | | |

### Medium Findings (Fix Within 30 Days)

| Finding | Risk | Remediation | Owner | Due Date |
|---------|------|-------------|-------|----------|
| | | | | |

### Low Findings (Fix Within 90 Days)

| Finding | Risk | Remediation | Owner | Due Date |
|---------|------|-------------|-------|----------|
| | | | | |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Auditor | | | |
| Security Lead | | | |
| System Owner | | | |
| Management | | | |

---

## Appendix

### A. Tools Used

- [ ] Nmap (network scanning)
- [ ] Trivy (container scanning)
- [ ] OWASP ZAP (web application scanning)
- [ ] Lynis (system auditing)
- [ ] Docker Bench (container security)

### B. References

- OWASP Top 10
- CIS Docker Benchmark
- NIST Cybersecurity Framework
- ISO 27001

### C. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2024-01-15 | Security Team | Initial release |
