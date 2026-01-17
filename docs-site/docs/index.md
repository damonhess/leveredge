# LeverEdge Documentation

Welcome to the LeverEdge documentation. LeverEdge is a multi-agent AI automation infrastructure with control plane / data plane separation.

## Overview

LeverEdge provides a comprehensive suite of AI agents organized into specialized fleets:

- **Core Infrastructure** - Orchestration, backup, security, monitoring
- **Creative Fleet** - Content production (presentations, video, images)
- **Security Fleet** - Authentication, rate limiting, port management
- **Personal Fleet** - Health, fitness, nutrition, learning assistance
- **Business Fleet** - Project management, legal, financial, procurement

## Architecture Highlights

```
+------------------------------------------------------------------+
|                    LEVEREDGE INFRASTRUCTURE                       |
+------------------------------------------------------------------+
|                                                                   |
|   CONTROL PLANE (control.n8n.leveredgeai.com)                    |
|   +----------------------------------------------------------+   |
|   |  ATLAS   HEPHAESTUS  AEGIS   CHRONOS  HADES  HERMES     |   |
|   |  8007    8011        8012    8010     8008   8014        |   |
|   |                                                          |   |
|   |  ARGUS   ALOY    ATHENA   CHIRON   SCHOLAR  SENTINEL    |   |
|   |  8016    8015    8013     8017     8018     8019        |   |
|   |                                                          |   |
|   |                  EVENT BUS (8099)                        |   |
|   +----------------------------------------------------------+   |
|                                                                   |
|   DATA PLANE                                                      |
|   +---------------------------+  +---------------------------+   |
|   |          PROD             |  |           DEV             |   |
|   |  n8n (5678)               |  |  n8n (5680)               |   |
|   |  n8n.leveredgeai.com      |  |  dev.n8n.leveredgeai.com  |   |
|   |  Supabase, ARIA           |  |  Supabase DEV             |   |
|   +---------------------------+  +---------------------------+   |
|                                                                   |
+------------------------------------------------------------------+
```

## Quick Links

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Install and configure LeverEdge in your environment

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)

-   :material-robot:{ .lg .middle } **Agent Reference**

    ---

    Explore all available agents and their capabilities

    [:octicons-arrow-right-24: Core Agents](agents/core.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation for all agents

    [:octicons-arrow-right-24: ATLAS API](api/atlas.md)

-   :material-chart-line:{ .lg .middle } **Operations**

    ---

    Monitoring, backup, and troubleshooting guides

    [:octicons-arrow-right-24: Monitoring](operations/monitoring.md)

</div>

## Agent Fleets

| Fleet | Agents | Purpose |
|-------|--------|---------|
| **Core** | ATLAS, HEPHAESTUS, AEGIS, CHRONOS, HADES, HERMES, ARGUS, ALOY, ATHENA, CHIRON, SCHOLAR, SENTINEL | Infrastructure orchestration, backup, security, monitoring |
| **Creative** | MUSE, CALLIOPE, THALIA, ERATO, CLIO | Content production (presentations, video, images, copy) |
| **Security** | CERBERUS, PORT-MANAGER | Authentication, rate limiting, network management |
| **Personal** | GYM-COACH, NUTRITIONIST, MEAL-PLANNER, ACADEMIC-GUIDE, EROS | Personal wellness and learning assistance |
| **Business** | HERACLES, LIBRARIAN, DAEDALUS, THEMIS, MENTOR, PLUTUS, PROCUREMENT, HEPHAESTUS-SERVER, ATLAS-INFRA, IRIS | Professional services and business operations |

## Key Principles

### Control Plane / Data Plane Separation

- **Control Plane**: Agent management, orchestration, credentials
- **Data Plane**: Production workflows, user-facing services

### Agent Architecture Pattern

All agents follow a consistent pattern:

1. **n8n Workflow** - Visual orchestration, webhook handling
2. **FastAPI Backend** - Business logic, external API calls
3. **Event Bus Integration** - Inter-agent communication
4. **Cost Tracking** - Usage monitoring and optimization

### Development Workflow

```
DEV -> Test -> PROD
```

All changes flow through the development environment before production deployment.

## Getting Help

- Check the [Troubleshooting Guide](operations/troubleshooting.md)
- Review agent-specific documentation
- Check the Event Bus for recent events and errors
