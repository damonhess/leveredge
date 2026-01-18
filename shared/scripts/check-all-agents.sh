#!/bin/bash
# check-all-agents.sh - Check health of all agents

echo "=== Agent Health Check ==="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# All agents with their ports
AGENTS=(
    "GAIA:8000"
    "ATLAS:8007"
    "HADES:8008"
    "CHRONOS:8010"
    "HEPHAESTUS:8011"
    "AEGIS:8012"
    "ATHENA:8013"
    "HERMES:8014"
    "ARGUS:8016"
    "CHIRON:8017"
    "SCHOLAR:8018"
    "SENTINEL:8019"
    "CERBERUS:8020"
    "PORT-MANAGER:8021"
    "MUSE:8030"
    "CALLIOPE:8031"
    "THALIA:8032"
    "ERATO:8033"
    "CLIO:8034"
    "FILE-PROCESSOR:8050"
    "VOICE:8051"
    "EVENT-BUS:8099"
    "NUTRITIONIST:8101"
    "MEAL-PLANNER:8102"
    "ACADEMIC-GUIDE:8103"
    "EROS:8104"
    "GYM-COACH:8110"
    "HERACLES:8200"
    "LIBRARIAN:8201"
    "DAEDALUS:8202"
    "THEMIS:8203"
    "MENTOR:8204"
    "PLUTUS:8205"
    "PROCUREMENT:8206"
    "HEPHAESTUS-SERVER:8207"
    "ATLAS-INFRA:8208"
    "IRIS:8209"
    "CONVENER:8300"
    "SCRIBE:8301"
)

online=0
offline=0

# Group by category
echo "--- Core Agents ---"
for entry in "${AGENTS[@]:0:14}"; do
    IFS=':' read -r agent port <<< "$entry"
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://localhost:$port/health" 2>/dev/null)
    if [ "$response" == "200" ]; then
        echo "  [OK] $agent ($port)"
        ((online++))
    else
        echo "  [--] $agent ($port)"
        ((offline++))
    fi
done

echo ""
echo "--- Creative Fleet ---"
for entry in "${AGENTS[@]:14:5}"; do
    IFS=':' read -r agent port <<< "$entry"
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://localhost:$port/health" 2>/dev/null)
    if [ "$response" == "200" ]; then
        echo "  [OK] $agent ($port)"
        ((online++))
    else
        echo "  [--] $agent ($port)"
        ((offline++))
    fi
done

echo ""
echo "--- Infrastructure ---"
for entry in "${AGENTS[@]:19:3}"; do
    IFS=':' read -r agent port <<< "$entry"
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://localhost:$port/health" 2>/dev/null)
    if [ "$response" == "200" ]; then
        echo "  [OK] $agent ($port)"
        ((online++))
    else
        echo "  [--] $agent ($port)"
        ((offline++))
    fi
done

echo ""
echo "--- Personal Fleet ---"
for entry in "${AGENTS[@]:22:5}"; do
    IFS=':' read -r agent port <<< "$entry"
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://localhost:$port/health" 2>/dev/null)
    if [ "$response" == "200" ]; then
        echo "  [OK] $agent ($port)"
        ((online++))
    else
        echo "  [--] $agent ($port)"
        ((offline++))
    fi
done

echo ""
echo "--- Business Fleet ---"
for entry in "${AGENTS[@]:27:10}"; do
    IFS=':' read -r agent port <<< "$entry"
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://localhost:$port/health" 2>/dev/null)
    if [ "$response" == "200" ]; then
        echo "  [OK] $agent ($port)"
        ((online++))
    else
        echo "  [--] $agent ($port)"
        ((offline++))
    fi
done

echo ""
echo "--- Council Fleet ---"
for entry in "${AGENTS[@]:37:2}"; do
    IFS=':' read -r agent port <<< "$entry"
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://localhost:$port/health" 2>/dev/null)
    if [ "$response" == "200" ]; then
        echo "  [OK] $agent ($port)"
        ((online++))
    else
        echo "  [--] $agent ($port)"
        ((offline++))
    fi
done

echo ""
echo "=== Summary ==="
echo "Online:  $online"
echo "Offline: $offline"
echo "Total:   $((online + offline))"
