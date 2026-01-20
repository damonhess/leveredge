# Frontend Project Sources

## Current Strategy
- **ARIA Frontend:** GitHub is source of truth. Sync between Bolt.new and Claude Code via git.
- **New Projects:** Start in Bolt.new, export to GitHub, deploy from GitHub.
- **Future:** Migrate to Bolt.diy for self-hosted visual editing with API integration.

---

## ARIA Frontend (DEV)

| Source | Location |
|--------|----------|
| Bolt.new | [URL TBD - need to import from GitHub] |
| GitHub | https://github.com/damonhess/leveredge (data-plane/dev/aria-frontend) |
| Server | /opt/leveredge/data-plane/dev/aria-frontend |
| Live URL | https://dev.aria.leveredgeai.com |

### Sync Workflow

**Before Bolt.new work:**
```bash
# Ensure GitHub has latest server changes
cd /opt/leveredge
git add . && git commit -m "Pre-Bolt sync" && git push
```

**After Bolt.new work:**
```bash
# On server, pull Bolt changes
cd /opt/leveredge
git pull
cd data-plane/dev/aria-frontend
npm install  # if dependencies changed
npm run build
docker restart aria-frontend-dev
```

---

## Command Center (DEV)

| Source | Location |
|--------|----------|
| Bolt.new | [Separate project - URL TBD] |
| GitHub | https://github.com/damonhess/leveredge (data-plane/dev/command-center) |
| Server | /opt/leveredge/data-plane/dev/command-center |
| Live URL | https://dev.command.leveredgeai.com |

Status: Skeleton exists, needs major work. Consider rebuilding in Bolt.new.

---

## Future Projects (Use Bolt.new → GitHub → Server)

| Project | Status | Bolt Project |
|---------|--------|--------------|
| Customer Portal | Not started | TBD |
| Marketing Site | Not started | TBD |
| Client Dashboards | Not started | TBD |

---

## Bolt.diy Migration Plan

**Goal:** Self-hosted Bolt.diy for:
- Direct GitHub integration
- Custom component libraries
- LeverEdge design system
- One-click deploy to server

**Timeline:** After March 1 launch, when revenue justifies time investment.

**Steps:**
1. Deploy Bolt.diy to server (Docker)
2. Connect to GitHub repos
3. Create LeverEdge component library
4. Migrate active projects

---

## Rules

1. **GitHub is source of truth** - Not Bolt, not server
2. **Always commit before Bolt work** - Prevent losing Claude Code changes
3. **Always pull after Bolt work** - Get visual changes to server
4. **Never edit deployed code directly** - Goes through git
