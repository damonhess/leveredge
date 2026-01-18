#!/bin/bash
# Fix known port conflicts discovered by audit

echo "🔧 Fixing known port conflicts..."

# Issue 1: VARYS (8020) vs CERBERUS (8020)
# Decision: VARYS gets 8023, CERBERUS keeps 8020
echo "→ VARYS: Moving from 8020 to 8023"
# Update will be in registry

# Issue 2: DAEDALUS vs GENDRY (both 8202)
# Decision: Keep DAEDALUS at 8202, GENDRY is duplicate - remove
echo "→ Removing duplicate gendry directory (same as daedalus)"

# Issue 3: Duplicate directories to clean up
echo "→ Marking duplicate directories for review:"
echo "   - arwen/ (duplicate of eros/)"
echo "   - gandalf/ (duplicate of academic-guide/)"
echo "   - aragorn/ (duplicate of gym-coach/)"
echo "   - atlas/ (old wrong code, atlas-orchestrator/ is correct)"

echo ""
echo "Registry updates needed:"
echo "1. Change VARYS port from 8020 to 8023"
echo "2. Verify CERBERUS stays at 8020"
echo ""
echo "Run PANOPTES scan after fixes to verify: curl http://localhost:8022/scan"
