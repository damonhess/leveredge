#!/bin/bash
# LeverEdge Health Check Script
# /opt/leveredge/shared/scripts/check-leveredge.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              LEVEREDGE HEALTH CHECK                          ║${NC}"
echo -e "${BLUE}║              $(date '+%Y-%m-%d %H:%M:%S')                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track failures
FAILURES=0

# =============================================================================
# 1. DOCKER CONTAINERS
# =============================================================================
echo -e "${YELLOW}1. Docker Containers${NC}"
echo "─────────────────────────────────────────────────────────────────"

EXPECTED_CONTAINERS=(
  "gaia:8000"
  "hades:8008"
  "chronos:8010"
  "hephaestus:8011"
  "aegis:8012"
  "athena:8013"
  "hermes:8014"
  "aloy:8015"
  "argus:8016"
  "chiron:8017"
  "scholar:8018"
  "event-bus:8099"
)

for container_port in "${EXPECTED_CONTAINERS[@]}"; do
  container="${container_port%%:*}"
  if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
    echo -e "  ${GREEN}✓${NC} $container"
  else
    echo -e "  ${RED}✗${NC} $container - NOT RUNNING"
    ((FAILURES++))
  fi
done
echo ""

# =============================================================================
# 2. AGENT HEALTH ENDPOINTS
# =============================================================================
echo -e "${YELLOW}2. Agent Health Endpoints${NC}"
echo "─────────────────────────────────────────────────────────────────"

declare -A AGENTS=(
  ["GAIA"]=8000
  ["HADES"]=8008
  ["CHRONOS"]=8010
  ["HEPHAESTUS"]=8011
  ["AEGIS"]=8012
  ["ATHENA"]=8013
  ["HERMES"]=8014
  ["ALOY"]=8015
  ["ARGUS"]=8016
  ["CHIRON"]=8017
  ["SCHOLAR"]=8018
  ["EVENT-BUS"]=8099
)

for agent in "${!AGENTS[@]}"; do
  port="${AGENTS[$agent]}"
  if curl -s --max-time 3 "http://localhost:$port/health" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $agent (:$port)"
  else
    echo -e "  ${RED}✗${NC} $agent (:$port) - NO RESPONSE"
    ((FAILURES++))
  fi
done
echo ""

# =============================================================================
# 3. DATABASE SERVICES
# =============================================================================
echo -e "${YELLOW}3. Database Services${NC}"
echo "─────────────────────────────────────────────────────────────────"

# Supabase Kong (API Gateway)
if curl -s --max-time 5 "http://localhost:8000/rest/v1/" -H "apikey: ${SUPABASE_ANON_KEY:-dummy}" > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} Supabase API (Kong :8000)"
else
  echo -e "  ${RED}✗${NC} Supabase API - NO RESPONSE"
  ((FAILURES++))
fi

# Supabase Studio
if curl -s --max-time 5 "http://localhost:3000" > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} Supabase Studio (:3000)"
else
  echo -e "  ${YELLOW}⚠${NC} Supabase Studio (:3000) - May be normal"
fi

# PostgreSQL direct
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} PostgreSQL (:5432)"
else
  echo -e "  ${RED}✗${NC} PostgreSQL - NOT READY"
  ((FAILURES++))
fi
echo ""

# =============================================================================
# 4. N8N INSTANCES
# =============================================================================
echo -e "${YELLOW}4. n8n Instances${NC}"
echo "─────────────────────────────────────────────────────────────────"

# Production n8n
if curl -s --max-time 5 "http://localhost:5678/healthz" > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} n8n PROD (:5678)"
else
  echo -e "  ${RED}✗${NC} n8n PROD - NO RESPONSE"
  ((FAILURES++))
fi

# Development n8n
if curl -s --max-time 5 "http://localhost:5680/healthz" > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} n8n DEV (:5680)"
else
  echo -e "  ${RED}✗${NC} n8n DEV - NO RESPONSE"
  ((FAILURES++))
fi

# Control plane n8n
if curl -s --max-time 5 "http://localhost:5679/healthz" > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} n8n CONTROL (:5679)"
else
  echo -e "  ${YELLOW}⚠${NC} n8n CONTROL (:5679) - May not be running"
fi
echo ""

# =============================================================================
# 5. MONITORING
# =============================================================================
echo -e "${YELLOW}5. Monitoring Stack${NC}"
echo "─────────────────────────────────────────────────────────────────"

# Prometheus
if curl -s --max-time 5 "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} Prometheus (:9090)"
else
  echo -e "  ${YELLOW}⚠${NC} Prometheus - Not running"
fi

# Grafana
if curl -s --max-time 5 "http://localhost:3001/api/health" > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓${NC} Grafana (:3001)"
else
  echo -e "  ${YELLOW}⚠${NC} Grafana - Not running"
fi
echo ""

# =============================================================================
# 6. DISK SPACE
# =============================================================================
echo -e "${YELLOW}6. Disk Space${NC}"
echo "─────────────────────────────────────────────────────────────────"

DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')

if [ "$DISK_USAGE" -lt 80 ]; then
  echo -e "  ${GREEN}✓${NC} Disk: ${DISK_USAGE}% used ($DISK_AVAIL available)"
elif [ "$DISK_USAGE" -lt 90 ]; then
  echo -e "  ${YELLOW}⚠${NC} Disk: ${DISK_USAGE}% used ($DISK_AVAIL available) - Getting full"
else
  echo -e "  ${RED}✗${NC} Disk: ${DISK_USAGE}% used ($DISK_AVAIL available) - CRITICAL"
  ((FAILURES++))
fi
echo ""

# =============================================================================
# 7. MEMORY
# =============================================================================
echo -e "${YELLOW}7. Memory Usage${NC}"
echo "─────────────────────────────────────────────────────────────────"

MEM_TOTAL=$(free -h | awk '/^Mem:/ {print $2}')
MEM_USED=$(free -h | awk '/^Mem:/ {print $3}')
MEM_PCT=$(free | awk '/^Mem:/ {printf("%.0f", $3/$2 * 100)}')

if [ "$MEM_PCT" -lt 80 ]; then
  echo -e "  ${GREEN}✓${NC} Memory: ${MEM_USED} / ${MEM_TOTAL} (${MEM_PCT}%)"
elif [ "$MEM_PCT" -lt 90 ]; then
  echo -e "  ${YELLOW}⚠${NC} Memory: ${MEM_USED} / ${MEM_TOTAL} (${MEM_PCT}%) - High usage"
else
  echo -e "  ${RED}✗${NC} Memory: ${MEM_USED} / ${MEM_TOTAL} (${MEM_PCT}%) - CRITICAL"
  ((FAILURES++))
fi
echo ""

# =============================================================================
# 8. LAUNCH COUNTDOWN
# =============================================================================
echo -e "${YELLOW}8. Launch Status${NC}"
echo "─────────────────────────────────────────────────────────────────"

LAUNCH_DATE="2026-03-01"
TODAY=$(date +%Y-%m-%d)
DAYS_TO_LAUNCH=$(( ($(date -d "$LAUNCH_DATE" +%s) - $(date -d "$TODAY" +%s)) / 86400 ))

if [ "$DAYS_TO_LAUNCH" -gt 0 ]; then
  echo -e "  ${BLUE}🚀${NC} $DAYS_TO_LAUNCH days to launch (March 1, 2026)"
elif [ "$DAYS_TO_LAUNCH" -eq 0 ]; then
  echo -e "  ${GREEN}🎉${NC} LAUNCH DAY!"
else
  echo -e "  ${GREEN}✓${NC} Launched $((-DAYS_TO_LAUNCH)) days ago"
fi
echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
if [ "$FAILURES" -eq 0 ]; then
  echo -e "${GREEN}✓ All critical systems healthy!${NC}"
else
  echo -e "${RED}✗ $FAILURES critical issue(s) detected${NC}"
fi
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

exit $FAILURES
