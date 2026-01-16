# CLEANUP COMPLETED SPECS

Move completed spec files to archive directory.

## Create Archive Directory

```bash
mkdir -p /opt/leveredge/archive/specs
```

## Move Completed Specs

```bash
cd /opt/leveredge

# Move all completed specs
mv PHASE-0-GAIA-EVENT-BUS-SPEC.md archive/specs/
mv PHASE-1-CONTROL-PLANE-N8N-ATLAS.md archive/specs/
mv PHASE-2-HEPHAESTUS-AEGIS.md archive/specs/
mv PHASE-3-CHRONOS-HADES.md archive/specs/
mv PHASE4-N8N-WORKFLOWS-FIX.md archive/specs/
mv GSD-PHASE-4-AGENTS.md archive/specs/
mv GSD-ROADMAP-20260116.md archive/specs/
mv HEPHAESTUS-MCP-SPEC.md archive/specs/
mv HEPHAESTUS-ACTUAL-MCP-SPEC.md archive/specs/
mv DATA-PLANE-MIGRATION-SPEC.md archive/specs/
mv EXECUTE-MIGRATION-NOW.md archive/specs/
mv SUPABASE-MIGRATION-SPEC.md archive/specs/
mv HERMES-TELEGRAM-SPEC.md archive/specs/
mv HERMES-MULTICHANNEL-SPEC.md archive/specs/
mv ARGUS-PROMETHEUS-SPEC.md archive/specs/
mv PROMOTE-TO-PROD-SPEC.md archive/specs/
mv UPDATE-EXECUTION-RULES-SPEC.md archive/specs/
mv COMMAND-CENTER-ESTABLISHED.md archive/specs/
mv HANDOFF-LEVEREDGE-BUILD.md archive/specs/
```

## Delete Redundant Files

```bash
# These are superseded by consolidated docs
rm -f 20260116_ARCHITECTURE.md
rm -f LAUNCH-CALENDAR.md
rm -f FUTURE-VISION-AND-EXPLORATION.md
```

## Final Structure Should Be

```
/opt/leveredge/
├── README.md                      # Quick reference
├── ARCHITECTURE.md                # Full system design
├── MASTER-LAUNCH-CALENDAR.md      # Timeline & milestones
├── LESSONS-LEARNED.md             # Knowledge base
├── LESSONS-SCRATCH.md             # Quick capture
├── FUTURE-VISION.md               # Business roadmap
├── archive/
│   └── specs/                     # Completed specs for reference
├── control-plane/
├── data-plane/
├── gaia/
├── shared/
└── monitoring/
```

## Git Commit

```bash
cd /opt/leveredge
git add -A
git commit -m "Consolidate documentation, archive completed specs"
```
