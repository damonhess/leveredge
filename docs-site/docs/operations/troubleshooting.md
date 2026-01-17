# Troubleshooting Guide

This guide covers common issues and their solutions.

## Quick Diagnostic Commands

### Check All Agents

```bash
# Check if agents are running
ps aux | grep uvicorn | grep -v grep

# Check specific agent
ps aux | grep "uvicorn.*8007" | grep -v grep  # ATLAS
```

### Check Docker Services

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Health Check All Agents

```bash
# Quick health check script
for port in 8007 8008 8010 8011 8012 8013 8014 8015 8016 8017 8018 8019 8099; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)
  echo "Port $port: $status"
done
```

---

## Agent Issues

### Agent Won't Start

**Symptoms:**
- Health check returns connection refused
- Process not in `ps aux`

**Solutions:**

1. Check if port is in use:
   ```bash
   sudo lsof -i :8007
   ```

2. Kill existing process if needed:
   ```bash
   sudo pkill -f "uvicorn.*8007"
   ```

3. Check Python path:
   ```bash
   which python3.11
   ```

4. Run manually to see errors:
   ```bash
   cd /opt/leveredge/control-plane/agents/atlas
   /usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007
   ```

### Agent Starts But Immediately Dies

**Symptoms:**
- Process starts then stops
- Log shows error then nothing

**Solutions:**

1. Check logs:
   ```bash
   tail -50 /tmp/atlas.log
   ```

2. Check dependencies:
   ```bash
   pip3.11 list | grep fastapi
   pip3.11 list | grep uvicorn
   pip3.11 list | grep anthropic
   ```

3. Check environment variables:
   ```bash
   env | grep SUPABASE
   env | grep ANTHROPIC
   ```

### Agent Responding Slowly

**Symptoms:**
- Health checks taking > 5 seconds
- Timeouts in chain execution

**Solutions:**

1. Check system resources:
   ```bash
   top
   free -h
   df -h
   ```

2. Check network connectivity:
   ```bash
   curl -w "@curl-format.txt" http://localhost:8007/health
   ```

3. Check database connectivity:
   ```bash
   curl http://localhost:54322/rest/v1/ \
     -H "apikey: YOUR_KEY"
   ```

---

## n8n Issues

### n8n Container Won't Start

**Solutions:**

1. Check logs:
   ```bash
   cd /opt/leveredge/data-plane/prod/n8n
   docker compose logs -f
   ```

2. Check disk space:
   ```bash
   df -h
   ```

3. Rebuild container:
   ```bash
   docker compose build --no-cache && docker compose up -d
   ```

### Workflow Not Triggering

**Symptoms:**
- Webhook not responding
- Scheduled workflow not running

**Solutions:**

1. Check webhook is active (green indicator in UI)

2. Check n8n execution queue:
   - Go to Settings > Workflow Queue

3. Check for execution errors in n8n UI

4. Verify webhook URL is correct:
   ```bash
   curl -X POST https://n8n.leveredgeai.com/webhook/... \
     -H "Content-Type: application/json" \
     -d '{}'
   ```

### n8n Database Connection Error

**Solutions:**

1. Check postgres container:
   ```bash
   docker ps | grep n8n-postgres
   docker logs prod-n8n-postgres
   ```

2. Restart postgres:
   ```bash
   docker restart prod-n8n-postgres
   ```

3. Check connection string in `.env`

---

## Supabase Issues

### Can't Connect to Database

**Solutions:**

1. Check container is running:
   ```bash
   docker ps | grep supabase-db
   ```

2. Check port is accessible:
   ```bash
   # PROD
   psql -h 127.0.0.1 -p 54322 -U postgres -d postgres

   # DEV
   psql -h 127.0.0.1 -p 54323 -U postgres -d postgres
   ```

3. Restart Supabase:
   ```bash
   cd /opt/leveredge/data-plane/prod/supabase
   docker compose down && docker compose up -d
   ```

### API Returns 500

**Solutions:**

1. Check Kong logs:
   ```bash
   docker logs supabase-kong
   ```

2. Check PostgREST logs:
   ```bash
   docker logs supabase-rest
   ```

3. Verify API key is correct

---

## Event Bus Issues

### Events Not Being Delivered

**Symptoms:**
- Events published but subscribers don't receive
- Delivery status shows "failed"

**Solutions:**

1. Check Event Bus health:
   ```bash
   curl http://localhost:8099/health
   ```

2. Check subscription status:
   ```bash
   curl http://localhost:8099/subscriptions
   ```

3. Check subscriber health:
   ```bash
   curl http://localhost:8014/health  # HERMES
   ```

4. Verify callback URL is accessible

### Event Bus Database Full

**Solutions:**

1. Check database size:
   ```bash
   ls -lh /opt/leveredge/control-plane/event-bus/events.db
   ```

2. Manually clean old events:
   ```bash
   sqlite3 /opt/leveredge/control-plane/event-bus/events.db \
     "DELETE FROM events WHERE published_at < datetime('now', '-7 days');"
   ```

3. Restart Event Bus:
   ```bash
   sudo pkill -f "uvicorn.*8099"
   cd /opt/leveredge/control-plane/event-bus
   sudo nohup /usr/local/bin/python3.11 -m uvicorn event_bus:app \
     --host 0.0.0.0 --port 8099 > /tmp/eventbus.log 2>&1 &
   ```

---

## LLM Agent Issues (SCHOLAR, CHIRON)

### API Rate Limit Errors

**Symptoms:**
- 429 errors in logs
- "Rate limit exceeded" messages

**Solutions:**

1. Check rate limit status in Anthropic dashboard

2. Implement backoff:
   - Wait and retry
   - Reduce concurrent requests

3. Check cost tracking for unusual usage:
   ```bash
   curl http://localhost:8016/costs?days=1
   ```

### Invalid API Key

**Symptoms:**
- 401 errors
- "Invalid API key" messages

**Solutions:**

1. Verify API key in environment:
   ```bash
   echo $ANTHROPIC_API_KEY | head -c 20
   ```

2. Update API key in AEGIS

3. Restart agent after updating

### Response Timeout

**Symptoms:**
- Requests timing out
- Chain execution failing at LLM step

**Solutions:**

1. Increase timeout in agent config:
   ```python
   client = Anthropic(timeout=120.0)
   ```

2. Check for complex prompts causing slow responses

3. Consider using a smaller/faster model for simple tasks

---

## Network Issues

### Port Conflict

**Symptoms:**
- "Address already in use" error
- Agent won't start

**Solutions:**

1. Find what's using the port:
   ```bash
   sudo lsof -i :8007
   sudo netstat -tlnp | grep 8007
   ```

2. Kill the conflicting process:
   ```bash
   sudo kill -9 <PID>
   ```

3. If Docker, check for orphaned containers:
   ```bash
   docker ps -a | grep <port>
   docker rm -f <container>
   ```

### DNS Resolution Failing

**Symptoms:**
- Can't reach external APIs
- "Name resolution failed"

**Solutions:**

1. Check DNS:
   ```bash
   nslookup api.anthropic.com
   ```

2. Check `/etc/resolv.conf`

3. Try direct IP if DNS is down

### SSL Certificate Issues

**Symptoms:**
- "Certificate verify failed"
- HTTPS requests failing

**Solutions:**

1. Check certificate expiry:
   ```bash
   echo | openssl s_client -servername n8n.leveredgeai.com \
     -connect n8n.leveredgeai.com:443 2>/dev/null | \
     openssl x509 -noout -dates
   ```

2. Renew certificate (Caddy auto-renews)

3. Check Caddy logs:
   ```bash
   docker logs caddy
   ```

---

## Full System Restart

If everything is broken, restart in this order:

```bash
# 1. Event Bus first (all agents depend on it)
cd /opt/leveredge/control-plane/event-bus
sudo pkill -f "uvicorn.*8099"
sudo nohup /usr/local/bin/python3.11 -m uvicorn event_bus:app \
  --host 0.0.0.0 --port 8099 > /tmp/eventbus.log 2>&1 &
sleep 2

# 2. Core agents
cd /opt/leveredge/control-plane/agents/atlas
sudo pkill -f "uvicorn.*8007"
sudo nohup /usr/local/bin/python3.11 -m uvicorn atlas:app \
  --host 0.0.0.0 --port 8007 > /tmp/atlas.log 2>&1 &

cd /opt/leveredge/control-plane/agents/hephaestus
sudo pkill -f "uvicorn.*8011"
sudo nohup /usr/local/bin/python3.11 -m uvicorn hephaestus_mcp_server:app \
  --host 0.0.0.0 --port 8011 > /tmp/hephaestus.log 2>&1 &

# 3. Docker services
cd /opt/leveredge/control-plane/n8n && docker compose up -d
cd /opt/leveredge/data-plane/prod/n8n && docker compose up -d
cd /opt/leveredge/data-plane/prod/supabase && docker compose up -d

# 4. Verify
curl http://localhost:8099/health
curl http://localhost:8007/health
```

---

## Getting Help

1. Check agent logs: `/tmp/<agent>.log`
2. Check Event Bus for recent errors
3. Review LESSONS-LEARNED.md for known issues
4. Check ARCHITECTURE.md for system design

---

## Related Documentation

- [Monitoring Guide](monitoring.md)
- [Backup & Restore](backup-restore.md)
- [Architecture Overview](../architecture/overview.md)
