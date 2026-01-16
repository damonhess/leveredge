# ARGUS Prometheus Connection Fix

*Quick fix - January 16, 2026*

## Current State
- ARGUS uses `PROMETHEUS_URL = http://host.docker.internal:9090`
- Docker containers can reach host via `host.docker.internal`
- But Prometheus may not be accepting connections or firewall blocks it

## Diagnosis Steps

```bash
# 1. Is Prometheus running?
sudo systemctl status prometheus

# 2. What address is it bound to?
ss -tlnp | grep 9090

# 3. Can we reach it from host?
curl http://localhost:9090/api/v1/status/config

# 4. Test from inside a Docker container
docker exec argus curl -s http://host.docker.internal:9090/api/v1/status/config
```

## Common Fixes

### Fix A: Prometheus bound to 127.0.0.1 only
Edit `/etc/prometheus/prometheus.yml` or systemd service:
```bash
# Check current binding
sudo cat /etc/systemd/system/prometheus.service | grep web.listen

# If bound to 127.0.0.1, change to 0.0.0.0:9090
# Or use iptables to forward
```

### Fix B: UFW blocking Docker
```bash
# Allow Docker bridge to reach host
sudo ufw allow from 172.17.0.0/16 to any port 9090
sudo ufw allow from 172.18.0.0/16 to any port 9090
```

### Fix C: Prometheus in Docker instead of host
If Prometheus runs in Docker, ARGUS should connect via Docker network:
```yaml
# In docker-compose.yml
PROMETHEUS_URL=http://prometheus:9090
```

## Verification

After fix:
```bash
# Test ARGUS metrics endpoint
curl http://localhost:8016/metrics

# Should return actual values, not empty
```

## Update ARGUS docker-compose if needed

```yaml
argus:
  environment:
    - PROMETHEUS_URL=http://host.docker.internal:9090
  extra_hosts:
    - "host.docker.internal:host-gateway"
```
