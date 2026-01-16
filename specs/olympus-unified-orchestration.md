# ATLAS UNIFIED ORCHESTRATION SYSTEM
## Codename: OLYMPUS

*"One Registry to rule them all, One Sentinel to find them,
One Router to bring them all, and in the mesh bind them."*

---

# EXECUTIVE SUMMARY

The OLYMPUS system is a fault-tolerant, self-healing orchestration layer that provides:

- **Dual Execution Engines**: n8n (visual) + FastAPI (programmatic)
- **Single Source of Truth**: YAML registry drives both implementations
- **Smart Routing**: SENTINEL routes based on complexity + health
- **Zero Drift**: Automated validation + generation
- **Auto-Failover**: If one engine dies, traffic flows to the other
- **Maximum Power**: Simple chains get visual debugging, complex chains get programmatic power

---

# ARCHITECTURE

```
                                    ┌─────────────────────────────────────┐
                                    │         AGENT REGISTRY              │
                                    │    /opt/leveredge/config/           │
                                    │       agent-registry.yaml           │
                                    │                                     │
                                    │  • Agent definitions                │
                                    │  • Endpoints & capabilities         │
                                    │  • Pre-built chain templates        │
                                    │  • Routing rules                    │
                                    └───────────────┬─────────────────────┘
                                                    │
                          ┌─────────────────────────┼─────────────────────────┐
                          │                         │                         │
                          ▼                         ▼                         ▼
              ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
              │    n8n ATLAS      │    │  FastAPI ATLAS    │    │     SENTINEL      │
              │    Port: 5679     │    │    Port: 8007     │    │    Port: 8019     │
              │                   │    │                   │    │                   │
              │ • Visual chains   │    │ • Async parallel  │    │ • Smart routing   │
              │ • Easy debugging  │    │ • Complex logic   │    │ • Health monitor  │
              │ • Quick edits     │    │ • Full Python     │    │ • Drift detection │
              │ • Native nodes    │    │ • Error recovery  │    │ • Auto-failover   │
              │                   │    │                   │    │ • Sync validation │
              └─────────┬─────────┘    └─────────┬─────────┘    └─────────┬─────────┘
                        │                        │                        │
                        └────────────────────────┼────────────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                    EVENT BUS (8099)                                     │
│                              • Orchestration events                                     │
│                              • Health status updates                                    │
│                              • Cost aggregation                                         │
│                              • Audit trail                                              │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                                 │
          ┌──────────┬──────────┬───────────────┼───────────────┬──────────┬──────────┐
          ▼          ▼          ▼               ▼               ▼          ▼          ▼
     ┌─────────┐┌─────────┐┌─────────┐    ┌─────────┐    ┌─────────┐┌─────────┐┌─────────┐
     │ SCHOLAR ││ CHIRON  ││ HERMES  │    │  AEGIS  │    │ CHRONOS ││  HADES  ││  ARGUS  │
     │  8018   ││  8017   ││  8014   │    │  8012   │    │  8010   ││  8008   ││  8016   │
     └─────────┘└─────────┘└─────────┘    └─────────┘    └─────────┘└─────────┘└─────────┘
```

---

# ENTRY POINTS

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               ENTRY POINTS                                           │
├──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────┤
│     ARIA     │   Telegram   │     CLI      │     API      │    Cron      │  Agents  │
│   (Web UI)   │   (HERMES)   │   (Direct)   │  (Webhook)   │  (Scheduled) │  (Inter) │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┴─────┬────┘
       │              │              │              │              │             │
       └──────────────┴──────────────┴──────────────┴──────────────┴─────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │       SENTINEL         │
                              │    (Smart Router)      │
                              │                        │
                              │  POST /orchestrate     │
                              │  GET  /health          │
                              │  GET  /status          │
                              └────────────┬───────────┘
                                           │
                            ┌──────────────┼──────────────┐
                            ▼              ▼              ▼
                    ┌──────────────┐ ┌──────────┐ ┌──────────────┐
                    │ n8n ATLAS    │ │ Direct   │ │ FastAPI      │
                    │ (simple)     │ │ (single) │ │ ATLAS        │
                    │              │ │          │ │ (complex)    │
                    └──────────────┘ └──────────┘ └──────────────┘
```

---

# COMPONENT 1: AGENT REGISTRY

## File: `/opt/leveredge/config/agent-registry.yaml`

This is the **SINGLE SOURCE OF TRUTH**. Both ATLAS implementations read from here.
Changes here automatically propagate to both engines.

```yaml
# ╔═══════════════════════════════════════════════════════════════════════════════╗
# ║                        LEVEREDGE AGENT REGISTRY                                ║
# ║                         Single Source of Truth                                 ║
# ║                                                                                ║
# ║  Both n8n ATLAS and FastAPI ATLAS read from this file.                        ║
# ║  SENTINEL validates sync between implementations.                              ║
# ║  ATHENA can auto-generate n8n workflows from this.                            ║
# ╚═══════════════════════════════════════════════════════════════════════════════╝

version: "2.0"
updated: "2026-01-17T15:00:00Z"

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

config:
  default_timeout_ms: 60000
  max_chain_depth: 10
  max_parallel_calls: 5
  retry_attempts: 2
  retry_delay_ms: 1000
  circuit_breaker_threshold: 5
  circuit_breaker_reset_ms: 30000
  
  # Cost tracking
  cost_tracking_enabled: true
  cost_log_table: agent_usage_logs
  
  # Event bus
  event_bus_url: http://event-bus:8099
  publish_events: true
  
  # Health check intervals
  health_check_interval_ms: 30000
  health_check_timeout_ms: 5000

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

agents:

  # ─────────────────────────────────────────────────────────────────────────────
  # SCHOLAR - Market Research & Intelligence (LLM-Powered)
  # ─────────────────────────────────────────────────────────────────────────────
  scholar:
    name: SCHOLAR
    version: "2.0"
    description: "Elite market research with web search capabilities"
    category: business
    llm_powered: true
    
    connection:
      url: http://scholar:8018
      health_endpoint: /health
      timeout_ms: 120000
      
    capabilities:
      - market_research
      - competitive_intelligence
      - web_search
      - data_synthesis
      
    actions:
      
      research:
        endpoint: /research
        method: POST
        description: "General research on a topic"
        timeout_ms: 60000
        params:
          - name: topic
            type: string
            required: true
            description: "Topic to research"
          - name: depth
            type: string
            required: false
            default: "standard"
            enum: [quick, standard, deep]
        returns:
          type: object
          fields: [research, sources, confidence]
          
      deep-research:
        endpoint: /deep-research
        method: POST
        description: "Comprehensive multi-source research with web search"
        timeout_ms: 180000
        cost_tier: high
        params:
          - name: question
            type: string
            required: true
            description: "Research question"
          - name: context
            type: string
            required: false
            description: "Additional context"
          - name: required_sources
            type: integer
            required: false
            default: 5
        returns:
          type: object
          fields: [research, methodology, findings, sources, confidence_level]
          
      competitors:
        endpoint: /competitors
        method: POST
        description: "Competitive analysis for a niche"
        timeout_ms: 120000
        cost_tier: high
        params:
          - name: niche
            type: string
            required: true
        returns:
          type: object
          fields: [competitors, analysis, market_position]
          
      competitor-profile:
        endpoint: /competitor-profile
        method: POST
        description: "Deep dive on specific competitor"
        timeout_ms: 120000
        cost_tier: high
        params:
          - name: company_name
            type: string
            required: true
          - name: website
            type: string
            required: false
        returns:
          type: object
          fields: [company, products, pricing, strengths, weaknesses, threat_level]
          
      market-size:
        endpoint: /market-size
        method: POST
        description: "TAM/SAM/SOM market sizing"
        timeout_ms: 120000
        cost_tier: high
        params:
          - name: market
            type: string
            required: true
          - name: geography
            type: string
            required: false
            default: "United States"
          - name: segment
            type: string
            required: false
        returns:
          type: object
          fields: [tam, sam, som, methodology, sources]
          
      pain-discovery:
        endpoint: /pain-discovery
        method: POST
        description: "Discover and quantify pain points"
        timeout_ms: 120000
        cost_tier: high
        params:
          - name: role
            type: string
            required: true
            description: "Target role (e.g., 'Compliance Officer')"
          - name: industry
            type: string
            required: true
        returns:
          type: object
          fields: [pain_points, quantification, trigger_events]
          
      validate-assumption:
        endpoint: /validate-assumption
        method: POST
        description: "Test business assumption with evidence"
        timeout_ms: 120000
        cost_tier: high
        params:
          - name: assumption
            type: string
            required: true
          - name: importance
            type: string
            required: false
            default: "high"
            enum: [low, medium, high, critical]
        returns:
          type: object
          fields: [verdict, evidence_for, evidence_against, confidence, recommendation]
          
      icp:
        endpoint: /icp
        method: POST
        description: "Develop Ideal Customer Profile"
        timeout_ms: 90000
        cost_tier: medium
        params:
          - name: niche
            type: string
            required: true
        returns:
          type: object
          fields: [company_profile, buyer_profile, trigger_events, disqualifiers]
          
      niche:
        endpoint: /niche
        method: POST
        description: "Analyze niche viability"
        timeout_ms: 90000
        cost_tier: medium
        params:
          - name: niche
            type: string
            required: true
        returns:
          type: object
          fields: [analysis, score, recommendation]
          
      compare:
        endpoint: /compare
        method: POST
        description: "Compare multiple niches"
        timeout_ms: 180000
        cost_tier: high
        params:
          - name: niches
            type: array
            required: true
            items: string
        returns:
          type: object
          fields: [comparison_matrix, recommendation, rationale]
          
      lead:
        endpoint: /lead
        method: POST
        description: "Research specific company as potential lead"
        timeout_ms: 90000
        cost_tier: medium
        params:
          - name: company
            type: string
            required: true
          - name: context
            type: string
            required: false
        returns:
          type: object
          fields: [company_info, fit_score, talking_points, concerns]

  # ─────────────────────────────────────────────────────────────────────────────
  # CHIRON - Business Strategy & ADHD Planning (LLM-Powered)
  # ─────────────────────────────────────────────────────────────────────────────
  chiron:
    name: CHIRON
    version: "2.0"
    description: "Elite business mentor with ADHD-optimized frameworks"
    category: business
    llm_powered: true
    
    connection:
      url: http://chiron:8017
      health_endpoint: /health
      timeout_ms: 60000
      
    capabilities:
      - strategic_planning
      - adhd_optimization
      - pricing_strategy
      - accountability
      - fear_analysis
      
    actions:
      
      chat:
        endpoint: /chat
        method: POST
        description: "General strategic conversation"
        timeout_ms: 60000
        params:
          - name: message
            type: string
            required: true
        returns:
          type: object
          fields: [response]
          
      sprint-plan:
        endpoint: /sprint-plan
        method: POST
        description: "ADHD-optimized sprint planning"
        timeout_ms: 60000
        params:
          - name: goals
            type: array
            required: true
            items: string
          - name: time_available
            type: string
            required: false
            default: "this week"
          - name: energy_level
            type: string
            required: false
            default: "medium"
            enum: [low, medium, high]
          - name: blockers
            type: array
            required: false
            items: string
        returns:
          type: object
          fields: [daily_priorities, time_blocks, dopamine_stacking, done_criteria]
          
      pricing-help:
        endpoint: /pricing-help
        method: POST
        description: "Value-based pricing strategy"
        timeout_ms: 60000
        params:
          - name: service_description
            type: string
            required: true
          - name: client_context
            type: string
            required: false
          - name: budget_signals
            type: string
            required: false
          - name: value_delivered
            type: string
            required: false
        returns:
          type: object
          fields: [value_quantification, price_recommendation, anchoring_strategy, three_tier_options, objection_prep]
          
      fear-check:
        endpoint: /fear-check
        method: POST
        description: "Rapid fear analysis and reframe"
        timeout_ms: 45000
        params:
          - name: situation
            type: string
            required: true
          - name: what_im_avoiding
            type: string
            required: false
        returns:
          type: object
          fields: [fear_named, worst_case, survivability, evidence_against, smallest_experiment, reframe, immediate_action]
          
      weekly-review:
        endpoint: /weekly-review
        method: POST
        description: "Structured weekly accountability"
        timeout_ms: 60000
        params:
          - name: wins
            type: array
            required: true
            items: string
          - name: losses
            type: array
            required: false
            items: string
          - name: lessons
            type: array
            required: false
            items: string
          - name: next_week_goals
            type: array
            required: false
            items: string
        returns:
          type: object
          fields: [win_analysis, loss_autopsy, pattern_check, one_thing_focus, accountability_commitment]
          
      accountability:
        endpoint: /accountability
        method: POST
        description: "Accountability check-in"
        timeout_ms: 45000
        params:
          - name: commitment
            type: string
            required: true
          - name: deadline
            type: string
            required: false
        returns:
          type: object
          fields: [status, blockers, next_actions]
          
      challenge:
        endpoint: /challenge
        method: POST
        description: "Challenge assumptions and beliefs"
        timeout_ms: 45000
        params:
          - name: assumption
            type: string
            required: true
        returns:
          type: object
          fields: [analysis, counter_evidence, reframe, verdict]
          
      hype:
        endpoint: /hype
        method: POST
        description: "Evidence-based motivation boost"
        timeout_ms: 30000
        params: []
        returns:
          type: object
          fields: [message, evidence, call_to_action]
          
      decide:
        endpoint: /decide
        method: POST
        description: "Decision framework analysis"
        timeout_ms: 60000
        params:
          - name: decision
            type: string
            required: true
          - name: options
            type: array
            required: false
            items: string
          - name: constraints
            type: string
            required: false
        returns:
          type: object
          fields: [analysis, recommendation, confidence, reversibility]
          
      framework:
        endpoint: /framework/{name}
        method: GET
        description: "Get specific framework"
        timeout_ms: 10000
        params:
          - name: name
            type: string
            required: true
            enum: [decision, accountability, strategic, fear, launch, adhd, pricing, sales, mvp]
        returns:
          type: object
          fields: [framework, principles, examples]

  # ─────────────────────────────────────────────────────────────────────────────
  # HERMES - Notifications & Messaging
  # ─────────────────────────────────────────────────────────────────────────────
  hermes:
    name: HERMES
    version: "1.0"
    description: "Multi-channel notifications and messaging"
    category: infrastructure
    llm_powered: false
    
    connection:
      url: http://hermes:8014
      health_endpoint: /health
      timeout_ms: 10000
      
    capabilities:
      - telegram
      - email
      - event_bus
      - multi_channel
      
    actions:
      
      notify:
        endpoint: /notify
        method: POST
        description: "Send notification to specified channel"
        timeout_ms: 10000
        params:
          - name: channel
            type: string
            required: true
            enum: [telegram, email, event_bus, all]
          - name: message
            type: string
            required: true
          - name: priority
            type: string
            required: false
            default: "normal"
            enum: [low, normal, high, critical]
        returns:
          type: object
          fields: [sent, channel, timestamp]
          
      telegram:
        endpoint: /telegram
        method: POST
        description: "Send Telegram message directly"
        timeout_ms: 10000
        params:
          - name: message
            type: string
            required: true
          - name: chat_id
            type: string
            required: false
        returns:
          type: object
          fields: [sent, message_id]

  # ─────────────────────────────────────────────────────────────────────────────
  # CHRONOS - Backup Management
  # ─────────────────────────────────────────────────────────────────────────────
  chronos:
    name: CHRONOS
    version: "1.0"
    description: "Backup and snapshot management"
    category: infrastructure
    llm_powered: false
    
    connection:
      url: http://chronos:8010
      health_endpoint: /health
      timeout_ms: 300000  # Backups can take time
      
    capabilities:
      - backup
      - restore
      - scheduling
      
    actions:
      
      backup:
        endpoint: /backup
        method: POST
        description: "Create backup"
        timeout_ms: 300000
        params:
          - name: target
            type: string
            required: false
            default: "all"
          - name: tag
            type: string
            required: false
        returns:
          type: object
          fields: [backup_id, timestamp, size, components]
          
      list:
        endpoint: /list
        method: GET
        description: "List available backups"
        timeout_ms: 10000
        params:
          - name: target
            type: string
            required: false
        returns:
          type: array
          items:
            fields: [backup_id, timestamp, size, tag]
            
      restore:
        endpoint: /restore
        method: POST
        description: "Restore from backup"
        timeout_ms: 300000
        requires_confirmation: true
        params:
          - name: backup_id
            type: string
            required: true
          - name: confirm
            type: boolean
            required: true
        returns:
          type: object
          fields: [restored, backup_id, components]

  # ─────────────────────────────────────────────────────────────────────────────
  # HADES - Rollback & Recovery
  # ─────────────────────────────────────────────────────────────────────────────
  hades:
    name: HADES
    version: "1.0"
    description: "Rollback and disaster recovery"
    category: infrastructure
    llm_powered: false
    
    connection:
      url: http://hades:8008
      health_endpoint: /health
      timeout_ms: 300000
      
    capabilities:
      - rollback
      - recovery
      - version_management
      
    actions:
      
      rollback:
        endpoint: /rollback
        method: POST
        description: "Rollback to previous state"
        timeout_ms: 300000
        requires_confirmation: true
        params:
          - name: target
            type: string
            required: true
          - name: backup_id
            type: string
            required: true
          - name: confirm
            type: boolean
            required: true
        returns:
          type: object
          fields: [rolled_back, previous_state, new_state]
          
      emergency:
        endpoint: /emergency
        method: POST
        description: "Emergency rollback (last known good)"
        timeout_ms: 60000
        requires_confirmation: true
        params:
          - name: component
            type: string
            required: true
          - name: confirm
            type: boolean
            required: true
        returns:
          type: object
          fields: [rolled_back, state]

  # ─────────────────────────────────────────────────────────────────────────────
  # AEGIS - Credential Management
  # ─────────────────────────────────────────────────────────────────────────────
  aegis:
    name: AEGIS
    version: "1.0"
    description: "Credential vault and secret management"
    category: infrastructure
    llm_powered: false
    sensitive: true
    
    connection:
      url: http://aegis:8012
      health_endpoint: /health
      timeout_ms: 10000
      
    capabilities:
      - credential_storage
      - rotation
      - audit
      
    actions:
      
      list:
        endpoint: /credentials
        method: GET
        description: "List credentials (metadata only)"
        timeout_ms: 5000
        params: []
        returns:
          type: array
          items:
            fields: [name, type, created_at, expires_at]
            
      get:
        endpoint: /credentials/{name}
        method: GET
        description: "Get credential metadata"
        timeout_ms: 5000
        sensitive: true
        params:
          - name: name
            type: string
            required: true
        returns:
          type: object
          fields: [name, type, metadata]
          
      sync:
        endpoint: /sync
        method: POST
        description: "Sync credentials from n8n"
        timeout_ms: 30000
        params: []
        returns:
          type: object
          fields: [synced_count, credentials]
          
      audit:
        endpoint: /audit
        method: GET
        description: "Audit credential access"
        timeout_ms: 10000
        params:
          - name: since
            type: string
            required: false
        returns:
          type: array
          items:
            fields: [credential, action, timestamp, source]

  # ─────────────────────────────────────────────────────────────────────────────
  # ARGUS - Monitoring & Metrics
  # ─────────────────────────────────────────────────────────────────────────────
  argus:
    name: ARGUS
    version: "1.0"
    description: "System monitoring and metrics"
    category: infrastructure
    llm_powered: false
    
    connection:
      url: http://argus:8016
      health_endpoint: /health
      timeout_ms: 10000
      
    capabilities:
      - health_monitoring
      - metrics
      - alerting
      - cost_tracking
      
    actions:
      
      status:
        endpoint: /status
        method: GET
        description: "Get system status"
        timeout_ms: 10000
        params: []
        returns:
          type: object
          fields: [healthy, components, issues]
          
      health:
        endpoint: /health
        method: GET
        description: "Health check"
        timeout_ms: 5000
        params: []
        returns:
          type: object
          fields: [status, timestamp]
          
      costs:
        endpoint: /costs
        method: GET
        description: "Get cost summary"
        timeout_ms: 10000
        params:
          - name: days
            type: integer
            required: false
            default: 30
        returns:
          type: object
          fields: [period_days, costs_by_agent, total_cost]
          
      costs-daily:
        endpoint: /costs/daily
        method: GET
        description: "Get daily cost trend"
        timeout_ms: 10000
        params:
          - name: days
            type: integer
            required: false
            default: 30
        returns:
          type: object
          fields: [daily_costs]

  # ─────────────────────────────────────────────────────────────────────────────
  # ALOY - Audit & Anomaly Detection
  # ─────────────────────────────────────────────────────────────────────────────
  aloy:
    name: ALOY
    version: "1.0"
    description: "Audit logging and anomaly detection"
    category: infrastructure
    llm_powered: false
    
    connection:
      url: http://aloy:8015
      health_endpoint: /health
      timeout_ms: 10000
      
    capabilities:
      - audit_logging
      - anomaly_detection
      - compliance
      
    actions:
      
      logs:
        endpoint: /logs
        method: GET
        description: "Query audit logs"
        timeout_ms: 10000
        params:
          - name: since
            type: string
            required: false
            default: "1h"
          - name: agent
            type: string
            required: false
          - name: level
            type: string
            required: false
            enum: [debug, info, warn, error]
        returns:
          type: array
          items:
            fields: [timestamp, agent, action, level, details]
            
      anomalies:
        endpoint: /anomalies
        method: GET
        description: "Get detected anomalies"
        timeout_ms: 10000
        params:
          - name: since
            type: string
            required: false
            default: "24h"
        returns:
          type: array
          items:
            fields: [timestamp, type, severity, description]

  # ─────────────────────────────────────────────────────────────────────────────
  # ATHENA - Documentation Generation
  # ─────────────────────────────────────────────────────────────────────────────
  athena:
    name: ATHENA
    version: "1.0"
    description: "Automated documentation generation"
    category: infrastructure
    llm_powered: false
    
    connection:
      url: http://athena:8013
      health_endpoint: /health
      timeout_ms: 60000
      
    capabilities:
      - documentation
      - api_docs
      - changelog
      
    actions:
      
      generate:
        endpoint: /generate
        method: POST
        description: "Generate documentation"
        timeout_ms: 60000
        params:
          - name: type
            type: string
            required: true
            enum: [readme, api, changelog, architecture]
          - name: path
            type: string
            required: true
          - name: format
            type: string
            required: false
            default: "markdown"
        returns:
          type: object
          fields: [content, path, format]

  # ─────────────────────────────────────────────────────────────────────────────
  # HEPHAESTUS - Builder & Deployer
  # ─────────────────────────────────────────────────────────────────────────────
  hephaestus:
    name: HEPHAESTUS
    version: "1.0"
    description: "File operations, commands, and deployment"
    category: infrastructure
    llm_powered: false
    
    connection:
      url: http://hephaestus:8011
      health_endpoint: /health
      timeout_ms: 30000
      
    capabilities:
      - file_operations
      - command_execution
      - deployment
      - git_operations
      
    actions:
      
      read-file:
        endpoint: /tools/file/read
        method: GET
        description: "Read file contents"
        timeout_ms: 10000
        params:
          - name: path
            type: string
            required: true
        returns:
          type: object
          fields: [content, path, size]
          
      create-file:
        endpoint: /tools/file/create
        method: POST
        description: "Create or update file"
        timeout_ms: 10000
        params:
          - name: path
            type: string
            required: true
          - name: content
            type: string
            required: true
        returns:
          type: object
          fields: [created, path]
          
      list-directory:
        endpoint: /tools/file/list
        method: GET
        description: "List directory contents"
        timeout_ms: 10000
        params:
          - name: path
            type: string
            required: true
        returns:
          type: array
          items:
            fields: [name, type, size]
            
      run-command:
        endpoint: /tools/command/run
        method: POST
        description: "Execute whitelisted command"
        timeout_ms: 30000
        params:
          - name: command
            type: string
            required: true
          - name: working_dir
            type: string
            required: false
        returns:
          type: object
          fields: [stdout, stderr, exit_code]
          
      git-commit:
        endpoint: /tools/git/commit
        method: POST
        description: "Git commit changes"
        timeout_ms: 30000
        params:
          - name: message
            type: string
            required: true
          - name: files
            type: array
            required: false
            items: string
        returns:
          type: object
          fields: [committed, hash, files]

# ═══════════════════════════════════════════════════════════════════════════════
# CHAIN DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

chains:

  # ─────────────────────────────────────────────────────────────────────────────
  # RESEARCH CHAINS
  # ─────────────────────────────────────────────────────────────────────────────
  
  research-and-plan:
    name: "Research & Plan"
    description: "Research a topic, then create an actionable plan"
    complexity: simple
    estimated_cost: 0.25
    estimated_time_ms: 180000
    
    triggers:
      - "research .+ (then|and) .*(plan|create|make)"
      - "find out .+ (then|and) .*(plan|recommend)"
      - "look up .+ (then|and) .*(plan|strategy)"
      
    steps:
      - id: research
        agent: scholar
        action: deep-research
        params:
          question: "{{input.topic}}"
          
      - id: plan
        agent: chiron
        action: chat
        input_template: |
          Based on this comprehensive research:
          
          {{steps.research.output.research}}
          
          Create a detailed, actionable plan with:
          1. Key insights from the research
          2. Recommended actions (prioritized)
          3. Potential obstacles and mitigations
          4. Timeline and milestones
          
          Make it ADHD-friendly: clear steps, one priority per phase.
          
    output_template: |
      ## Research Summary
      
      {{steps.research.output.research}}
      
      ---
      
      ## Action Plan
      
      {{steps.plan.output.response}}
      
  validate-and-decide:
    name: "Validate & Decide"
    description: "Validate an assumption, then decide next steps"
    complexity: simple
    estimated_cost: 0.25
    estimated_time_ms: 150000
    
    triggers:
      - "validate .+ (then|and) .*(decide|plan|recommend)"
      - "is it true .+ (then|what should)"
      - "check if .+ (then|and) .*(advise|suggest)"
      
    steps:
      - id: validate
        agent: scholar
        action: validate-assumption
        params:
          assumption: "{{input.assumption}}"
          importance: high
          
      - id: decide
        agent: chiron
        action: chat
        input_template: |
          I need to validate this assumption: "{{input.assumption}}"
          
          Validation results:
          - Verdict: {{steps.validate.output.verdict}}
          - Evidence FOR: {{steps.validate.output.evidence_for}}
          - Evidence AGAINST: {{steps.validate.output.evidence_against}}
          - Confidence: {{steps.validate.output.confidence}}
          
          Based on this validation, what should I do next?
          Consider both scenarios: if the assumption holds AND if it doesn't.
          
    output_template: |
      ## Assumption Validation
      
      **Assumption:** {{input.assumption}}
      **Verdict:** {{steps.validate.output.verdict}} ({{steps.validate.output.confidence}} confidence)
      
      ### Evidence
      **For:** {{steps.validate.output.evidence_for}}
      **Against:** {{steps.validate.output.evidence_against}}
      
      ---
      
      ## Decision & Next Steps
      
      {{steps.decide.output.response}}

  # ─────────────────────────────────────────────────────────────────────────────
  # COMPREHENSIVE ANALYSIS CHAINS
  # ─────────────────────────────────────────────────────────────────────────────
  
  comprehensive-market-analysis:
    name: "Comprehensive Market Analysis"
    description: "Parallel research on competitors, market size, and pain points, then strategic synthesis"
    complexity: complex
    estimated_cost: 0.75
    estimated_time_ms: 300000
    
    triggers:
      - "(comprehensive|full|complete) .*(analysis|research|report)"
      - "analyze .*(market|industry|niche) .*(thoroughly|completely)"
      - "give me everything on"
      
    steps:
      - id: parallel_research
        type: parallel
        substeps:
          - id: competitors
            agent: scholar
            action: competitors
            params:
              niche: "{{input.market}}"
              
          - id: market_size
            agent: scholar
            action: market-size
            params:
              market: "{{input.market}}"
              
          - id: pain_points
            agent: scholar
            action: pain-discovery
            params:
              role: "{{input.target_role | default: 'decision maker'}}"
              industry: "{{input.market}}"
              
      - id: synthesis
        agent: chiron
        action: chat
        input_template: |
          I've gathered comprehensive market intelligence on "{{input.market}}":
          
          ## COMPETITOR ANALYSIS
          {{steps.parallel_research.competitors.output.competitors}}
          
          ## MARKET SIZE (TAM/SAM/SOM)
          {{steps.parallel_research.market_size.output}}
          
          ## PAIN POINTS
          {{steps.parallel_research.pain_points.output.pain_points}}
          
          Synthesize this into:
          1. **Executive Summary** (3-5 bullet points)
          2. **Market Opportunity Assessment** (Go/No-Go with reasoning)
          3. **Competitive Positioning Recommendation**
          4. **Top 3 Pain Points to Address** (with value quantification)
          5. **Recommended Entry Strategy**
          6. **Key Risks & Mitigations**
          
    output_template: |
      # Comprehensive Market Analysis: {{input.market}}
      
      ## Competitor Landscape
      {{steps.parallel_research.competitors.output}}
      
      ## Market Size
      {{steps.parallel_research.market_size.output}}
      
      ## Customer Pain Points
      {{steps.parallel_research.pain_points.output}}
      
      ---
      
      ## Strategic Synthesis
      {{steps.synthesis.output.response}}

  niche-evaluation:
    name: "Niche Evaluation"
    description: "Compare multiple niches and recommend best option"
    complexity: complex
    estimated_cost: 0.60
    estimated_time_ms: 240000
    
    triggers:
      - "compare .*(niches|markets|industries)"
      - "which (niche|market) should"
      - "evaluate .*(options|niches)"
      
    steps:
      - id: compare
        agent: scholar
        action: compare
        params:
          niches: "{{input.niches}}"
          
      - id: recommend
        agent: chiron
        action: decide
        params:
          decision: "Which niche should I focus on for my AI automation agency?"
          options: "{{input.niches}}"
        input_template: |
          I need to choose a niche for my AI automation agency.
          
          Here's the comparison research:
          {{steps.compare.output.comparison_matrix}}
          
          SCHOLAR's recommendation: {{steps.compare.output.recommendation}}
          
          My constraints:
          - 44 days to launch (March 1, 2026)
          - Background in civil engineering + law + government compliance
          - Goal: $30K MRR to quit government job
          - Need to close first client fast
          
          Analyze and give me a final recommendation.
          
    output_template: |
      # Niche Evaluation
      
      ## Comparison Matrix
      {{steps.compare.output.comparison_matrix}}
      
      ## SCHOLAR's Analysis
      {{steps.compare.output.rationale}}
      
      ---
      
      ## CHIRON's Recommendation
      {{steps.recommend.output.response}}

  # ─────────────────────────────────────────────────────────────────────────────
  # PLANNING CHAINS
  # ─────────────────────────────────────────────────────────────────────────────
  
  weekly-planning:
    name: "Weekly Planning"
    description: "Review last week, research blockers, plan next week"
    complexity: moderate
    estimated_cost: 0.40
    estimated_time_ms: 180000
    
    triggers:
      - "plan (my|the|this) week"
      - "weekly planning"
      - "what should i do this week"
      
    steps:
      - id: review
        agent: chiron
        action: weekly-review
        params:
          wins: "{{input.wins | default: []}}"
          losses: "{{input.losses | default: []}}"
          lessons: "{{input.lessons | default: []}}"
          
      - id: research_blockers
        agent: scholar
        action: deep-research
        condition:
          field: input.blockers
          operator: exists
        params:
          question: "How to overcome: {{input.blockers | join: ', '}}"
          
      - id: sprint_plan
        agent: chiron
        action: sprint-plan
        input_template: |
          Weekly review insights:
          {{steps.review.output}}
          
          {{#if steps.research_blockers}}
          Research on blockers:
          {{steps.research_blockers.output.research}}
          {{/if}}
          
          Create my sprint plan for this week.
        params:
          goals: "{{input.goals | default: ['Launch progress']}}"
          time_available: "this week"
          energy_level: "{{input.energy | default: 'medium'}}"
          blockers: "{{input.blockers | default: []}}"
          
    output_template: |
      # Weekly Planning Session
      
      ## Last Week Review
      {{steps.review.output}}
      
      {{#if steps.research_blockers}}
      ## Blocker Research
      {{steps.research_blockers.output.research}}
      {{/if}}
      
      ## This Week's Sprint Plan
      {{steps.sprint_plan.output}}

  # ─────────────────────────────────────────────────────────────────────────────
  # FEAR & MOTIVATION CHAINS
  # ─────────────────────────────────────────────────────────────────────────────
  
  fear-to-action:
    name: "Fear to Action"
    description: "Analyze fear, research evidence against it, create action plan"
    complexity: simple
    estimated_cost: 0.30
    estimated_time_ms: 120000
    
    triggers:
      - "i'm (afraid|scared|nervous|anxious) .*(about|of|to)"
      - "help me overcome"
      - "i keep avoiding"
      
    steps:
      - id: fear_analysis
        agent: chiron
        action: fear-check
        params:
          situation: "{{input.situation}}"
          what_im_avoiding: "{{input.avoiding}}"
          
      - id: evidence
        agent: scholar
        action: deep-research
        params:
          question: "Success stories and strategies for: {{input.situation}}"
          
      - id: action_plan
        agent: chiron
        action: sprint-plan
        input_template: |
          Fear analysis:
          {{steps.fear_analysis.output}}
          
          Evidence and strategies from research:
          {{steps.evidence.output.research}}
          
          Create a "smallest experiment" action plan to overcome this fear.
          Make it ADHD-friendly: tiny steps, immediate wins.
        params:
          goals:
            - "Overcome fear: {{input.situation}}"
          time_available: "next 3 days"
          energy_level: high
          
    output_template: |
      # Fear → Action Transformation
      
      ## The Fear
      **Situation:** {{input.situation}}
      
      ## Analysis
      {{steps.fear_analysis.output}}
      
      ## Evidence Against Your Fear
      {{steps.evidence.output.research}}
      
      ## Your Action Plan
      {{steps.action_plan.output}}

  # ─────────────────────────────────────────────────────────────────────────────
  # INFRASTRUCTURE CHAINS
  # ─────────────────────────────────────────────────────────────────────────────
  
  safe-deployment:
    name: "Safe Deployment"
    description: "Backup, deploy, verify, rollback if needed"
    complexity: moderate
    estimated_cost: 0.05
    estimated_time_ms: 600000
    
    triggers:
      - "deploy .* safely"
      - "safe deployment"
      
    steps:
      - id: backup
        agent: chronos
        action: backup
        params:
          target: "{{input.target | default: 'all'}}"
          tag: "pre-deploy-{{timestamp}}"
          
      - id: notify_start
        agent: hermes
        action: notify
        params:
          channel: telegram
          message: "🚀 Starting deployment of {{input.component}}. Backup: {{steps.backup.output.backup_id}}"
          priority: normal
          
      - id: deploy
        type: external
        description: "Actual deployment happens via GSD/Claude Code"
        pass_through: true
        
      - id: verify
        agent: argus
        action: status
        
      - id: notify_complete
        agent: hermes
        action: notify
        condition:
          field: steps.verify.output.healthy
          operator: eq
          value: true
        params:
          channel: telegram
          message: "✅ Deployment complete. All systems healthy."
          priority: normal
          
      - id: rollback
        agent: hades
        action: rollback
        condition:
          field: steps.verify.output.healthy
          operator: eq
          value: false
        params:
          target: "{{input.target}}"
          backup_id: "{{steps.backup.output.backup_id}}"
          confirm: true
          
      - id: notify_rollback
        agent: hermes
        action: notify
        condition:
          field: steps.verify.output.healthy
          operator: eq
          value: false
        params:
          channel: telegram
          message: "⚠️ Deployment failed. Rolled back to {{steps.backup.output.backup_id}}"
          priority: critical

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING RULES
# ═══════════════════════════════════════════════════════════════════════════════

routing:
  
  # Which implementation handles which complexity
  engine_selection:
    simple:
      preferred: n8n
      fallback: fastapi
    moderate:
      preferred: n8n
      fallback: fastapi
    complex:
      preferred: fastapi
      fallback: n8n
      
  # Direct agent routing (single calls - skip ATLAS)
  direct_routing:
    enabled: true
    threshold_ms: 100  # If ATLAS adds more than this latency, go direct
    
  # Health-based routing
  health_routing:
    enabled: true
    unhealthy_threshold: 3  # Consecutive failures before marking unhealthy
    recovery_check_ms: 30000

# ═══════════════════════════════════════════════════════════════════════════════
# INTENT PATTERNS (for ARIA intent extraction)
# ═══════════════════════════════════════════════════════════════════════════════

intent_patterns:
  
  # Chain detection
  chains:
    - pattern: "research .+ (then|and then|,\\s*then|,\\s*and) .*(plan|analyze|recommend|decide)"
      chain: research-and-plan
      extract:
        topic: "research (.+?) (then|and)"
        
    - pattern: "validate .+ (then|and) .*(decide|plan|recommend)"
      chain: validate-and-decide
      extract:
        assumption: "validate (.+?) (then|and)"
        
    - pattern: "(comprehensive|full|complete) .*(analysis|research|report)"
      chain: comprehensive-market-analysis
      extract:
        market: "(analysis|research|report) .*(on|of|about) (.+)"
        
    - pattern: "compare .*(niches|markets|industries)"
      chain: niche-evaluation
      extract:
        niches: "compare (.+)"
        
    - pattern: "plan (my|the|this) week"
      chain: weekly-planning
      
    - pattern: "i'm (afraid|scared|nervous|anxious)"
      chain: fear-to-action
      extract:
        situation: "(?:afraid|scared|nervous|anxious) (?:of |about |to )?(.+)"
        
  # Direct agent routing
  agents:
    chiron:
      - "sprint plan"
      - "plan my (day|week)"
      - "pricing"
      - "fear check"
      - "weekly review"
      - "accountability"
      - "business strategy"
      - "adhd"
      - "overwhelmed"
      
    scholar:
      - "research"
      - "competitor"
      - "market size"
      - "tam|sam|som"
      - "icp"
      - "niche"
      - "pain point"
      - "validate"
```

---

# COMPONENT 2: FASTAPI ATLAS

## File: `/opt/leveredge/control-plane/agents/atlas/atlas.py`

```python
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           ATLAS ORCHESTRATION ENGINE                           ║
║                              FastAPI Implementation                            ║
║                                                                                ║
║  The programmatic brain of the OLYMPUS orchestration system.                  ║
║  Handles complex chains, parallel execution, and sophisticated error handling. ║
║                                                                                ║
║  Zero LLM cost - pure execution of structured intents.                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import httpx
import yaml
import re
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import jinja2

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SENTINEL_URL = os.getenv("SENTINEL_URL", "http://sentinel:8019")

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class Registry:
    """Loads and caches the agent registry."""
    
    _instance = None
    _registry = None
    _loaded_at = None
    _reload_interval = 60  # Reload every 60 seconds
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, force: bool = False) -> dict:
        """Load registry, with caching."""
        now = datetime.utcnow()
        
        if (not force and 
            self._registry and 
            self._loaded_at and 
            (now - self._loaded_at).seconds < self._reload_interval):
            return self._registry
            
        with open(REGISTRY_PATH) as f:
            self._registry = yaml.safe_load(f)
            self._loaded_at = now
            
        return self._registry
    
    def get_agent(self, name: str) -> Optional[dict]:
        """Get agent configuration."""
        registry = self.load()
        return registry.get("agents", {}).get(name.lower())
    
    def get_action(self, agent_name: str, action_name: str) -> Optional[dict]:
        """Get action configuration."""
        agent = self.get_agent(agent_name)
        if agent:
            return agent.get("actions", {}).get(action_name)
        return None
    
    def get_chain(self, name: str) -> Optional[dict]:
        """Get chain definition."""
        registry = self.load()
        return registry.get("chains", {}).get(name)
    
    def list_agents(self) -> List[dict]:
        """List all agents."""
        registry = self.load()
        return [
            {"name": k, "description": v.get("description")}
            for k, v in registry.get("agents", {}).items()
        ]
    
    def list_chains(self) -> List[dict]:
        """List all chains."""
        registry = self.load()
        return [
            {"name": k, "description": v.get("description"), "complexity": v.get("complexity")}
            for k, v in registry.get("chains", {}).items()
        ]
    
    def get_config(self) -> dict:
        """Get global config."""
        registry = self.load()
        return registry.get("config", {})


registry = Registry()

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class StepResult:
    """Result of a single step execution."""
    step_id: str
    agent: str
    action: str
    status: ExecutionStatus
    output: Any = None
    error: Optional[str] = None
    cost: float = 0.0
    duration_ms: int = 0
    retries: int = 0


@dataclass
class ExecutionContext:
    """Holds state during intent execution."""
    intent_id: str
    source: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    status: ExecutionStatus = ExecutionStatus.RUNNING
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    errors: List[dict] = field(default_factory=list)
    
    def get_step_output(self, step_id: str) -> Any:
        """Get output from a completed step."""
        result = self.step_results.get(step_id)
        return result.output if result else None
    
    def set_step_result(self, result: StepResult):
        """Store step result."""
        self.step_results[result.step_id] = result
    
    def add_error(self, step_id: str, error: str):
        """Add error to context."""
        self.errors.append({
            "step_id": step_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @property
    def total_cost(self) -> float:
        """Sum of all step costs."""
        return sum(r.cost for r in self.step_results.values())
    
    @property
    def duration_ms(self) -> int:
        """Total execution duration."""
        return int((datetime.utcnow() - self.started_at).total_seconds() * 1000)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for response."""
        return {
            "intent_id": self.intent_id,
            "source": self.source,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "total_cost": round(self.total_cost, 6),
            "steps_completed": len([r for r in self.step_results.values() if r.status == ExecutionStatus.COMPLETED]),
            "steps_failed": len([r for r in self.step_results.values() if r.status == ExecutionStatus.FAILED]),
            "step_results": {
                k: {
                    "agent": v.agent,
                    "action": v.action,
                    "status": v.status.value,
                    "output": v.output,
                    "error": v.error,
                    "cost": v.cost,
                    "duration_ms": v.duration_ms
                }
                for k, v in self.step_results.items()
            },
            "errors": self.errors if self.errors else None,
            "timestamp": datetime.utcnow().isoformat()
        }

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TemplateEngine:
    """Resolves templates with step outputs."""
    
    def __init__(self):
        self.env = jinja2.Environment(
            undefined=jinja2.StrictUndefined,
            autoescape=False
        )
        # Add custom filters
        self.env.filters['default'] = lambda x, d: x if x else d
        self.env.filters['join'] = lambda x, d: d.join(x) if isinstance(x, list) else x
    
    def resolve(self, template: str, context: ExecutionContext, input_data: dict) -> str:
        """Resolve template placeholders."""
        
        # Build template context
        template_ctx = {
            "input": input_data,
            "steps": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add step outputs
        for step_id, result in context.step_results.items():
            template_ctx["steps"][step_id] = {
                "output": result.output,
                "agent": result.agent,
                "action": result.action
            }
        
        # Handle nested paths like {{steps.research.output.research}}
        # First, try simple replacement for common patterns
        resolved = template
        
        # Pattern: {{steps.STEP_ID.output.FIELD}}
        pattern = r'\{\{steps\.(\w+)\.output\.(\w+)\}\}'
        for match in re.finditer(pattern, template):
            step_id, field = match.groups()
            if step_id in context.step_results:
                output = context.step_results[step_id].output
                if isinstance(output, dict) and field in output:
                    value = output[field]
                    if isinstance(value, (dict, list)):
                        value = yaml.dump(value, default_flow_style=False)
                    resolved = resolved.replace(match.group(0), str(value))
                elif isinstance(output, dict):
                    # Try to get any available content
                    value = output.get(field, output.get('response', str(output)))
                    resolved = resolved.replace(match.group(0), str(value))
        
        # Pattern: {{steps.STEP_ID.output}} (entire output)
        pattern = r'\{\{steps\.(\w+)\.output\}\}'
        for match in re.finditer(pattern, resolved):
            step_id = match.group(1)
            if step_id in context.step_results:
                output = context.step_results[step_id].output
                if isinstance(output, dict):
                    value = yaml.dump(output, default_flow_style=False)
                else:
                    value = str(output)
                resolved = resolved.replace(match.group(0), value)
        
        # Pattern: {{input.FIELD}}
        pattern = r'\{\{input\.(\w+)\}\}'
        for match in re.finditer(pattern, resolved):
            field = match.group(1)
            if field in input_data:
                value = input_data[field]
                if isinstance(value, (dict, list)):
                    value = yaml.dump(value, default_flow_style=False)
                resolved = resolved.replace(match.group(0), str(value))
        
        return resolved


template_engine = TemplateEngine()

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class Executor:
    """Executes agent calls and chains."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=180.0)
        self.config = registry.get_config()
    
    async def execute_step(
        self, 
        step: dict, 
        context: ExecutionContext,
        input_data: dict
    ) -> StepResult:
        """Execute a single step."""
        
        step_id = step.get("id") or step.get("step_id") or str(uuid4())[:8]
        agent_name = step.get("agent")
        action_name = step.get("action")
        
        start_time = datetime.utcnow()
        
        # Get configurations
        agent = registry.get_agent(agent_name)
        action = registry.get_action(agent_name, action_name)
        
        if not agent or not action:
            return StepResult(
                step_id=step_id,
                agent=agent_name,
                action=action_name,
                status=ExecutionStatus.FAILED,
                error=f"Unknown agent/action: {agent_name}/{action_name}",
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
        
        # Build URL
        endpoint = action["endpoint"]
        base_url = agent["connection"]["url"]
        
        # Handle path parameters
        if "{" in endpoint:
            params = step.get("params", {})
            for key, value in params.items():
                endpoint = endpoint.replace(f"{{{key}}}", str(value))
        
        url = f"{base_url}{endpoint}"
        method = action.get("method", "POST")
        timeout = (step.get("options", {}).get("timeout_ms") or 
                  action.get("timeout_ms") or 
                  self.config.get("default_timeout_ms", 60000)) / 1000
        
        # Build request body
        params = step.get("params", {}).copy()
        
        # Resolve input template if present
        if "input_template" in step:
            resolved = template_engine.resolve(step["input_template"], context, input_data)
            params["message"] = resolved
        
        # Make request with retries
        max_retries = self.config.get("retry_attempts", 2)
        retry_delay = self.config.get("retry_delay_ms", 1000) / 1000
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if method == "GET":
                    response = await self.client.get(url, params=params, timeout=timeout)
                else:
                    response = await self.client.post(url, json=params, timeout=timeout)
                
                response.raise_for_status()
                result = response.json()
                
                # Extract cost if present
                cost = result.pop("_cost", result.pop("total_cost", 0))
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                return StepResult(
                    step_id=step_id,
                    agent=agent_name,
                    action=action_name,
                    status=ExecutionStatus.COMPLETED,
                    output=result,
                    cost=cost,
                    duration_ms=duration_ms,
                    retries=attempt
                )
                
            except httpx.TimeoutException as e:
                last_error = f"Timeout after {timeout}s"
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            except Exception as e:
                last_error = str(e)
            
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
        
        # All retries failed
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return StepResult(
            step_id=step_id,
            agent=agent_name,
            action=action_name,
            status=ExecutionStatus.FAILED,
            error=last_error,
            duration_ms=duration_ms,
            retries=max_retries
        )
    
    async def execute_parallel(
        self,
        substeps: List[dict],
        context: ExecutionContext,
        input_data: dict
    ) -> Dict[str, StepResult]:
        """Execute multiple steps in parallel."""
        
        tasks = [self.execute_step(step, context, input_data) for step in substeps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for i, step in enumerate(substeps):
            step_id = step.get("id") or step.get("step_id") or f"parallel_{i}"
            
            if isinstance(results[i], Exception):
                output[step_id] = StepResult(
                    step_id=step_id,
                    agent=step.get("agent", "unknown"),
                    action=step.get("action", "unknown"),
                    status=ExecutionStatus.FAILED,
                    error=str(results[i])
                )
            else:
                output[step_id] = results[i]
            
            context.set_step_result(output[step_id])
        
        return output
    
    async def execute_chain(
        self,
        chain_def: dict,
        input_data: dict,
        context: ExecutionContext
    ) -> dict:
        """Execute a chain of steps."""
        
        steps = chain_def.get("steps", [])
        
        for step in steps:
            # Check condition
            if not self._check_condition(step, context):
                continue
            
            # Handle parallel substeps
            if step.get("type") == "parallel":
                substeps = step.get("substeps", [])
                parallel_results = await self.execute_parallel(substeps, context, input_data)
                
                # Store parallel results as nested
                context.set_step_result(StepResult(
                    step_id=step.get("id", "parallel"),
                    agent="parallel",
                    action="execute",
                    status=ExecutionStatus.COMPLETED,
                    output={k: v.output for k, v in parallel_results.items()}
                ))
            else:
                result = await self.execute_step(step, context, input_data)
                context.set_step_result(result)
                
                # Check if we should fail fast
                if result.status == ExecutionStatus.FAILED:
                    fail_fast = chain_def.get("options", {}).get("fail_fast", True)
                    if fail_fast:
                        context.status = ExecutionStatus.FAILED
                        break
        
        # Determine final status
        failed_steps = [r for r in context.step_results.values() if r.status == ExecutionStatus.FAILED]
        if failed_steps:
            context.status = ExecutionStatus.PARTIAL if len(failed_steps) < len(steps) else ExecutionStatus.FAILED
        else:
            context.status = ExecutionStatus.COMPLETED
        
        # Format output using template if provided
        output = context.to_dict()
        if "output_template" in chain_def:
            output["formatted_output"] = template_engine.resolve(
                chain_def["output_template"], 
                context, 
                input_data
            )
        
        return output
    
    def _check_condition(self, step: dict, context: ExecutionContext) -> bool:
        """Check if step condition is met."""
        condition = step.get("condition")
        if not condition:
            return True
        
        field_path = condition["field"].split(".")
        value = None
        
        # Navigate to value
        if field_path[0] == "steps":
            step_id = field_path[1]
            if step_id in context.step_results:
                result = context.step_results[step_id]
                value = result.output
                for key in field_path[2:]:
                    if isinstance(value, dict):
                        value = value.get(key)
        elif field_path[0] == "input":
            # Would need input_data passed in
            pass
        
        # Evaluate
        operator = condition["operator"]
        target = condition["value"]
        
        if operator == "eq":
            return value == target
        elif operator == "ne":
            return value != target
        elif operator == "gt":
            return value > target
        elif operator == "lt":
            return value < target
        elif operator == "contains":
            return target in value if value else False
        elif operator == "exists":
            return value is not None
        
        return False
    
    async def log_event(self, event_type: str, data: dict):
        """Log event to Event Bus."""
        try:
            await self.client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "ATLAS",
                    "data": data
                },
                timeout=2.0
            )
        except:
            pass


executor = Executor()

# ═══════════════════════════════════════════════════════════════════════════════
# API MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Step(BaseModel):
    id: Optional[str] = None
    step_id: Optional[str] = None
    agent: str
    action: str
    params: Dict[str, Any] = {}
    input_template: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

class ParallelStep(BaseModel):
    id: Optional[str] = None
    type: str = "parallel"
    substeps: List[Step]

class Intent(BaseModel):
    intent_id: Optional[str] = None
    source: str = "api"
    type: str = "single"  # single, chain
    chain_name: Optional[str] = None  # For pre-defined chains
    steps: Optional[List[Dict[str, Any]]] = None  # For ad-hoc chains
    input: Dict[str, Any] = {}
    options: Optional[Dict[str, Any]] = None

class QuickRequest(BaseModel):
    message: str
    source: str = "api"
    context: Dict[str, Any] = {}

# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ATLAS Orchestration Engine",
    description="Programmatic orchestration for complex chains and parallel execution",
    version="2.0.0"
)

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & INFO
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "agent": "ATLAS",
        "implementation": "fastapi",
        "version": "2.0.0",
        "registry_loaded": registry._loaded_at.isoformat() if registry._loaded_at else None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/agents")
async def list_agents():
    """List available agents."""
    return {
        "agents": registry.list_agents(),
        "count": len(registry.list_agents())
    }

@app.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get agent details."""
    agent = registry.get_agent(agent_name)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    return agent

@app.get("/chains")
async def list_chains():
    """List available chains."""
    return {
        "chains": registry.list_chains(),
        "count": len(registry.list_chains())
    }

@app.get("/chains/{chain_name}")
async def get_chain(chain_name: str):
    """Get chain definition."""
    chain = registry.get_chain(chain_name)
    if not chain:
        raise HTTPException(404, f"Chain '{chain_name}' not found")
    return chain

# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/execute")
async def execute_intent(intent: Intent, background_tasks: BackgroundTasks):
    """
    Execute an orchestration intent.
    
    Supports:
    - Single agent calls
    - Pre-defined chains (by name)
    - Ad-hoc chains (custom steps)
    """
    intent_id = intent.intent_id or str(uuid4())
    context = ExecutionContext(intent_id=intent_id, source=intent.source)
    
    # Log start
    await executor.log_event("orchestration_started", {
        "intent_id": intent_id,
        "type": intent.type,
        "chain_name": intent.chain_name
    })
    
    try:
        if intent.chain_name:
            # Execute pre-defined chain
            chain_def = registry.get_chain(intent.chain_name)
            if not chain_def:
                raise HTTPException(404, f"Chain '{intent.chain_name}' not found")
            
            result = await executor.execute_chain(chain_def, intent.input, context)
            
        elif intent.type == "single" and intent.steps:
            # Execute single step
            step = intent.steps[0]
            step_result = await executor.execute_step(step, context, intent.input)
            context.set_step_result(step_result)
            context.status = step_result.status
            result = context.to_dict()
            
        elif intent.steps:
            # Execute ad-hoc chain
            chain_def = {"steps": intent.steps, "options": intent.options or {}}
            result = await executor.execute_chain(chain_def, intent.input, context)
            
        else:
            raise HTTPException(400, "Intent must have chain_name or steps")
        
        # Log completion
        background_tasks.add_task(
            executor.log_event,
            "orchestration_completed",
            {
                "intent_id": intent_id,
                "status": context.status.value,
                "duration_ms": context.duration_ms,
                "total_cost": context.total_cost
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        context.status = ExecutionStatus.FAILED
        context.add_error("executor", str(e))
        
        background_tasks.add_task(
            executor.log_event,
            "orchestration_failed",
            {"intent_id": intent_id, "error": str(e)}
        )
        
        return context.to_dict()

# ─────────────────────────────────────────────────────────────────────────────
# QUICK ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/quick/research-and-plan")
async def quick_research_and_plan(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Research something, then create action plan."""
    intent = Intent(
        source=request.source,
        chain_name="research-and-plan",
        input={"topic": request.message, **request.context}
    )
    return await execute_intent(intent, background_tasks)

@app.post("/quick/validate-and-decide")
async def quick_validate_and_decide(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Validate assumption, then decide next steps."""
    intent = Intent(
        source=request.source,
        chain_name="validate-and-decide",
        input={"assumption": request.message, **request.context}
    )
    return await execute_intent(intent, background_tasks)

@app.post("/quick/comprehensive-analysis")
async def quick_comprehensive_analysis(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Full market analysis with parallel research."""
    intent = Intent(
        source=request.source,
        chain_name="comprehensive-market-analysis",
        input={"market": request.message, **request.context}
    )
    return await execute_intent(intent, background_tasks)

@app.post("/quick/weekly-planning")
async def quick_weekly_planning(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Weekly planning session."""
    intent = Intent(
        source=request.source,
        chain_name="weekly-planning",
        input=request.context
    )
    return await execute_intent(intent, background_tasks)

@app.post("/quick/fear-to-action")
async def quick_fear_to_action(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Transform fear into action."""
    intent = Intent(
        source=request.source,
        chain_name="fear-to-action",
        input={"situation": request.message, **request.context}
    )
    return await execute_intent(intent, background_tasks)

# ─────────────────────────────────────────────────────────────────────────────
# RELOAD
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/reload")
async def reload_registry():
    """Force reload of agent registry."""
    registry.load(force=True)
    return {
        "reloaded": True,
        "timestamp": datetime.utcnow().isoformat(),
        "agents": len(registry.list_agents()),
        "chains": len(registry.list_chains())
    }

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    registry.load()
    await executor.log_event("agent_started", {
        "agent": "ATLAS",
        "implementation": "fastapi",
        "version": "2.0.0"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
```

---

# COMPONENT 3: SENTINEL

## File: `/opt/leveredge/control-plane/agents/sentinel/sentinel.py`

```python
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              SENTINEL                                          ║
║                    The Guardian of OLYMPUS                                     ║
║                                                                                ║
║  Responsibilities:                                                             ║
║  • Smart routing (n8n vs FastAPI ATLAS)                                       ║
║  • Health monitoring                                                           ║
║  • Drift detection                                                             ║
║  • Auto-failover                                                               ║
║  • Sync validation                                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import httpx
import yaml
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
FASTAPI_ATLAS_URL = os.getenv("FASTAPI_ATLAS_URL", "http://atlas:8007")
N8N_ATLAS_URL = os.getenv("N8N_ATLAS_URL", "http://control-n8n:5679")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class EngineStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class EngineHealth:
    """Tracks health of an execution engine."""
    name: str
    url: str
    status: EngineStatus = EngineStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    response_time_ms: int = 0
    error: Optional[str] = None


class HealthMonitor:
    """Monitors health of ATLAS implementations."""
    
    def __init__(self):
        self.engines: Dict[str, EngineHealth] = {
            "fastapi": EngineHealth(name="FastAPI ATLAS", url=FASTAPI_ATLAS_URL),
            "n8n": EngineHealth(name="n8n ATLAS", url=N8N_ATLAS_URL)
        }
        self.client = httpx.AsyncClient(timeout=10.0)
        self.unhealthy_threshold = 3
    
    async def check_engine(self, engine_id: str) -> EngineHealth:
        """Check health of specific engine."""
        engine = self.engines.get(engine_id)
        if not engine:
            return None
        
        start = datetime.utcnow()
        
        try:
            if engine_id == "fastapi":
                response = await self.client.get(f"{engine.url}/health")
            else:
                # n8n health check
                response = await self.client.get(f"{engine.url}/healthz")
            
            response.raise_for_status()
            
            engine.status = EngineStatus.HEALTHY
            engine.last_success = datetime.utcnow()
            engine.consecutive_failures = 0
            engine.error = None
            
        except Exception as e:
            engine.consecutive_failures += 1
            engine.error = str(e)
            
            if engine.consecutive_failures >= self.unhealthy_threshold:
                engine.status = EngineStatus.UNHEALTHY
            else:
                engine.status = EngineStatus.DEGRADED
        
        engine.last_check = datetime.utcnow()
        engine.response_time_ms = int((engine.last_check - start).total_seconds() * 1000)
        
        return engine
    
    async def check_all(self) -> Dict[str, EngineHealth]:
        """Check all engines."""
        await asyncio.gather(
            self.check_engine("fastapi"),
            self.check_engine("n8n")
        )
        return self.engines
    
    def get_healthy_engine(self, preferred: str = None, complexity: str = "simple") -> Optional[str]:
        """Get healthiest engine, considering preference and complexity."""
        
        # Load routing config from registry
        with open(REGISTRY_PATH) as f:
            registry = yaml.safe_load(f)
        
        routing = registry.get("routing", {})
        engine_selection = routing.get("engine_selection", {})
        
        # Get preferred engine for complexity
        complexity_pref = engine_selection.get(complexity, {})
        preferred = preferred or complexity_pref.get("preferred", "n8n")
        fallback = complexity_pref.get("fallback", "fastapi")
        
        # Check preferred first
        if self.engines[preferred].status == EngineStatus.HEALTHY:
            return preferred
        
        # Try fallback
        if self.engines[fallback].status == EngineStatus.HEALTHY:
            return fallback
        
        # Return least-bad option
        if self.engines[preferred].status == EngineStatus.DEGRADED:
            return preferred
        if self.engines[fallback].status == EngineStatus.DEGRADED:
            return fallback
        
        return None


health_monitor = HealthMonitor()

# ═══════════════════════════════════════════════════════════════════════════════
# DRIFT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class DriftDetector:
    """Detects drift between implementations and registry."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def validate_sync(self) -> dict:
        """Validate both implementations are in sync with registry."""
        
        with open(REGISTRY_PATH) as f:
            registry = yaml.safe_load(f)
        
        issues = []
        
        # Check FastAPI ATLAS
        try:
            response = await self.client.get(f"{FASTAPI_ATLAS_URL}/chains")
            fastapi_chains = {c["name"] for c in response.json().get("chains", [])}
            registry_chains = set(registry.get("chains", {}).keys())
            
            missing_in_fastapi = registry_chains - fastapi_chains
            if missing_in_fastapi:
                issues.append({
                    "engine": "fastapi",
                    "type": "missing_chains",
                    "chains": list(missing_in_fastapi)
                })
                
        except Exception as e:
            issues.append({
                "engine": "fastapi",
                "type": "unreachable",
                "error": str(e)
            })
        
        # Check n8n ATLAS (would need to query n8n API for workflows)
        # This is a placeholder - actual implementation would check n8n workflows
        
        return {
            "synced": len(issues) == 0,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    async def auto_repair(self, issues: list) -> dict:
        """Attempt to auto-repair drift issues."""
        repairs = []
        
        for issue in issues:
            if issue["type"] == "missing_chains":
                # Could trigger ATHENA to regenerate n8n workflows
                repairs.append({
                    "issue": issue,
                    "action": "regenerate_required",
                    "manual": True
                })
        
        return {"repairs": repairs}


drift_detector = DriftDetector()

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class Router:
    """Routes intents to appropriate engine."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=180.0)
    
    def determine_complexity(self, intent: dict) -> str:
        """Determine complexity of an intent."""
        
        # Check for parallel steps
        steps = intent.get("steps", [])
        for step in steps:
            if step.get("type") == "parallel":
                return "complex"
        
        # Check chain name
        chain_name = intent.get("chain_name")
        if chain_name:
            with open(REGISTRY_PATH) as f:
                registry = yaml.safe_load(f)
            chain = registry.get("chains", {}).get(chain_name, {})
            return chain.get("complexity", "simple")
        
        # Check step count
        if len(steps) > 3:
            return "moderate"
        
        return "simple"
    
    async def route(self, intent: dict) -> dict:
        """Route intent to best available engine."""
        
        complexity = self.determine_complexity(intent)
        engine = health_monitor.get_healthy_engine(complexity=complexity)
        
        if not engine:
            raise HTTPException(503, "No healthy orchestration engine available")
        
        # Forward to selected engine
        if engine == "fastapi":
            response = await self.client.post(
                f"{FASTAPI_ATLAS_URL}/execute",
                json=intent
            )
        else:
            # Forward to n8n webhook
            response = await self.client.post(
                f"{N8N_ATLAS_URL}/webhook/atlas",
                json=intent
            )
        
        result = response.json()
        result["_routed_to"] = engine
        result["_complexity"] = complexity
        
        return result


router = Router()

# ═══════════════════════════════════════════════════════════════════════════════
# API MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Intent(BaseModel):
    intent_id: Optional[str] = None
    source: str = "api"
    type: str = "single"
    chain_name: Optional[str] = None
    steps: Optional[list] = None
    input: dict = {}
    options: Optional[dict] = None
    
    # Routing hints
    prefer_engine: Optional[str] = None  # "fastapi" or "n8n"
    force_engine: Optional[str] = None   # Override routing decision

# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="SENTINEL - The Guardian",
    description="Smart routing, health monitoring, and drift detection for OLYMPUS",
    version="1.0.0"
)

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & STATUS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "agent": "SENTINEL",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/status")
async def status():
    """Get full system status."""
    await health_monitor.check_all()
    
    return {
        "sentinel": "healthy",
        "engines": {
            name: {
                "status": eng.status.value,
                "last_check": eng.last_check.isoformat() if eng.last_check else None,
                "response_time_ms": eng.response_time_ms,
                "consecutive_failures": eng.consecutive_failures,
                "error": eng.error
            }
            for name, eng in health_monitor.engines.items()
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/engines")
async def list_engines():
    """List available engines and their status."""
    await health_monitor.check_all()
    
    return {
        "engines": [
            {
                "id": name,
                "name": eng.name,
                "url": eng.url,
                "status": eng.status.value,
                "healthy": eng.status == EngineStatus.HEALTHY
            }
            for name, eng in health_monitor.engines.items()
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/orchestrate")
async def orchestrate(intent: Intent, background_tasks: BackgroundTasks):
    """
    Main orchestration endpoint.
    
    Routes to the best available engine based on:
    - Intent complexity
    - Engine health
    - User preference
    """
    
    # Check health first
    await health_monitor.check_all()
    
    # Honor force_engine if specified
    if intent.force_engine:
        engine = intent.force_engine
        eng_health = health_monitor.engines.get(engine)
        if not eng_health or eng_health.status == EngineStatus.UNHEALTHY:
            raise HTTPException(503, f"Forced engine '{engine}' is unhealthy")
    else:
        # Smart routing
        complexity = router.determine_complexity(intent.dict())
        engine = health_monitor.get_healthy_engine(
            preferred=intent.prefer_engine,
            complexity=complexity
        )
    
    if not engine:
        raise HTTPException(503, "No healthy orchestration engine available")
    
    # Log routing decision
    background_tasks.add_task(
        log_event,
        "orchestration_routed",
        {
            "intent_id": intent.intent_id,
            "engine": engine,
            "complexity": router.determine_complexity(intent.dict())
        }
    )
    
    # Forward to engine
    return await router.route(intent.dict())

# ─────────────────────────────────────────────────────────────────────────────
# SYNC VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/validate-sync")
async def validate_sync(background_tasks: BackgroundTasks):
    """Validate both engines are in sync with registry."""
    result = await drift_detector.validate_sync()
    
    if not result["synced"]:
        # Alert on drift
        background_tasks.add_task(
            alert_drift,
            result["issues"]
        )
    
    return result

@app.post("/repair-drift")
async def repair_drift():
    """Attempt to repair drift between implementations."""
    validation = await drift_detector.validate_sync()
    
    if validation["synced"]:
        return {"message": "No drift detected, nothing to repair"}
    
    repairs = await drift_detector.auto_repair(validation["issues"])
    return repairs

# ─────────────────────────────────────────────────────────────────────────────
# DIRECT ROUTING (bypass ATLAS for simple single-agent calls)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/direct/{agent}/{action}")
async def direct_call(agent: str, action: str, params: dict = {}):
    """
    Direct call to an agent, bypassing ATLAS.
    
    Use for simple single-agent calls where orchestration overhead isn't needed.
    """
    with open(REGISTRY_PATH) as f:
        registry = yaml.safe_load(f)
    
    agent_config = registry.get("agents", {}).get(agent.lower())
    if not agent_config:
        raise HTTPException(404, f"Agent '{agent}' not found")
    
    action_config = agent_config.get("actions", {}).get(action)
    if not action_config:
        raise HTTPException(404, f"Action '{action}' not found for agent '{agent}'")
    
    # Build request
    url = f"{agent_config['connection']['url']}{action_config['endpoint']}"
    method = action_config.get("method", "POST")
    timeout = action_config.get("timeout_ms", 60000) / 1000
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        if method == "GET":
            response = await client.get(url, params=params)
        else:
            response = await client.post(url, json=params)
        
        return response.json()

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

async def log_event(event_type: str, data: dict):
    """Log event to Event Bus."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={"event_type": event_type, "source": "SENTINEL", "data": data},
                timeout=2.0
            )
    except:
        pass

async def alert_drift(issues: list):
    """Alert on drift detection."""
    message = f"⚠️ ATLAS Drift Detected:\n"
    for issue in issues:
        message += f"• {issue['engine']}: {issue['type']}\n"
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{HERMES_URL}/notify",
                json={"channel": "telegram", "message": message, "priority": "high"},
                timeout=5.0
            )
    except:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND TASKS
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    await health_monitor.check_all()
    await log_event("agent_started", {"agent": "SENTINEL", "version": "1.0.0"})

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8019)
```

---

# COMPONENT 4: N8N ATLAS WORKFLOW

## File: `/opt/leveredge/control-plane/workflows/atlas-orchestrator.json`

This is a visual n8n workflow that:
1. Receives intents via webhook
2. Loads chain definitions from registry
3. Executes steps sequentially or parallel
4. Returns formatted response

```json
{
  "name": "ATLAS Orchestrator",
  "nodes": [
    {
      "id": "webhook",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "webhookId": "atlas",
      "parameters": {
        "httpMethod": "POST",
        "path": "atlas",
        "responseMode": "responseNode"
      }
    },
    {
      "id": "load_registry",
      "name": "Load Registry",
      "type": "n8n-nodes-base.readBinaryFiles",
      "position": [450, 300],
      "parameters": {
        "fileSelector": "/opt/leveredge/config/agent-registry.yaml"
      }
    },
    {
      "id": "parse_intent",
      "name": "Parse Intent",
      "type": "n8n-nodes-base.code",
      "position": [650, 300],
      "parameters": {
        "jsCode": "// Parse intent and load chain definition\nconst intent = $('Webhook').first().json.body;\nconst registry = require('js-yaml').load($('Load Registry').first().binary.data.toString());\n\nlet chain = null;\nif (intent.chain_name) {\n  chain = registry.chains[intent.chain_name];\n}\n\nreturn {\n  json: {\n    intent,\n    chain,\n    registry_config: registry.config,\n    steps_to_execute: chain ? chain.steps : intent.steps,\n    current_step: 0,\n    step_outputs: {},\n    errors: []\n  }\n};"
      }
    },
    {
      "id": "step_loop",
      "name": "Step Loop",
      "type": "n8n-nodes-base.splitInBatches",
      "position": [850, 300],
      "parameters": {
        "batchSize": 1
      }
    },
    {
      "id": "execute_step",
      "name": "Execute Step",
      "type": "n8n-nodes-base.httpRequest",
      "position": [1050, 300],
      "parameters": {
        "method": "={{ $json.step.method || 'POST' }}",
        "url": "={{ $json.agent_url }}{{ $json.step.endpoint }}",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "={{ Object.keys($json.resolved_params) }}",
              "value": "={{ Object.values($json.resolved_params) }}"
            }
          ]
        }
      }
    },
    {
      "id": "collect_results",
      "name": "Collect Results",
      "type": "n8n-nodes-base.code",
      "position": [1250, 300],
      "parameters": {
        "jsCode": "// Collect step results\nconst stepId = $json.step.id;\nconst output = $('Execute Step').first().json;\n\n// Store in accumulated outputs\nconst accumulated = $json.step_outputs || {};\naccumulated[stepId] = output;\n\nreturn {\n  json: {\n    ...$json,\n    step_outputs: accumulated,\n    current_step: $json.current_step + 1\n  }\n};"
      }
    },
    {
      "id": "format_response",
      "name": "Format Response",
      "type": "n8n-nodes-base.code",
      "position": [1450, 300],
      "parameters": {
        "jsCode": "// Format final response\nconst outputs = $json.step_outputs;\nconst chain = $json.chain;\n\nlet formatted = '';\nif (chain && chain.output_template) {\n  // Apply output template\n  formatted = chain.output_template;\n  for (const [stepId, output] of Object.entries(outputs)) {\n    const placeholder = `{{steps.${stepId}.output}}`;\n    formatted = formatted.replace(placeholder, JSON.stringify(output, null, 2));\n  }\n}\n\nreturn {\n  json: {\n    status: 'completed',\n    implementation: 'n8n',\n    step_outputs: outputs,\n    formatted_output: formatted || null,\n    timestamp: new Date().toISOString()\n  }\n};"
      }
    },
    {
      "id": "respond",
      "name": "Respond",
      "type": "n8n-nodes-base.respondToWebhook",
      "position": [1650, 300],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ $json }}"
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Load Registry", "type": "main", "index": 0}]]
    },
    "Load Registry": {
      "main": [[{"node": "Parse Intent", "type": "main", "index": 0}]]
    },
    "Parse Intent": {
      "main": [[{"node": "Step Loop", "type": "main", "index": 0}]]
    },
    "Step Loop": {
      "main": [
        [{"node": "Execute Step", "type": "main", "index": 0}],
        [{"node": "Format Response", "type": "main", "index": 0}]
      ]
    },
    "Execute Step": {
      "main": [[{"node": "Collect Results", "type": "main", "index": 0}]]
    },
    "Collect Results": {
      "main": [[{"node": "Step Loop", "type": "main", "index": 0}]]
    },
    "Format Response": {
      "main": [[{"node": "Respond", "type": "main", "index": 0}]]
    }
  }
}
```

*Note: This is a simplified template. The actual n8n workflow will need proper error handling, parallel execution nodes, and template resolution.*

---

# COMPONENT 5: ARIA INTEGRATION

## Updated ARIA Pre-Router

```javascript
/**
 * ARIA Pre-Router V3
 * 
 * Routes to SENTINEL for orchestration
 * SENTINEL handles engine selection (n8n vs FastAPI)
 */

const message = $json.message;
const messageLower = message.toLowerCase();

// Load intent patterns from registry (could be fetched dynamically)
const chainPatterns = [
  { pattern: /research .+ (then|and then|,\s*then|,\s*and) .*(plan|analyze|recommend|decide)/i, chain: "research-and-plan" },
  { pattern: /validate .+ (then|and) .*(decide|plan|recommend)/i, chain: "validate-and-decide" },
  { pattern: /(comprehensive|full|complete) .*(analysis|research|report)/i, chain: "comprehensive-market-analysis" },
  { pattern: /compare .*(niches|markets|industries)/i, chain: "niche-evaluation" },
  { pattern: /plan (my|the|this) week/i, chain: "weekly-planning" },
  { pattern: /i'm (afraid|scared|nervous|anxious)/i, chain: "fear-to-action" }
];

const agentPatterns = {
  chiron: [
    /\b(ask chiron|chiron,|sprint plan|plan my (day|week)|pricing|fear check|weekly review|accountability|adhd|overwhelmed)\b/i
  ],
  scholar: [
    /\b(ask scholar|scholar,|research|competitor|market size|tam|sam|som|icp|niche|pain point|validate)\b/i
  ]
};

// ═══════════════════════════════════════════════════════════════════════════
// DETECT CHAINS
// ═══════════════════════════════════════════════════════════════════════════

for (const { pattern, chain } of chainPatterns) {
  if (pattern.test(messageLower)) {
    // Extract input from message
    const input = { raw_message: message };
    
    // Try to extract specific fields
    const topicMatch = message.match(/research (.+?) (then|and)/i);
    if (topicMatch) input.topic = topicMatch[1];
    
    const assumptionMatch = message.match(/validate (.+?) (then|and)/i);
    if (assumptionMatch) input.assumption = assumptionMatch[1];
    
    const marketMatch = message.match(/(analysis|research|report) .*(on|of|about) (.+)/i);
    if (marketMatch) input.market = marketMatch[3];
    
    const fearMatch = message.match(/(?:afraid|scared|nervous|anxious) (?:of |about |to )?(.+)/i);
    if (fearMatch) input.situation = fearMatch[1];
    
    return {
      json: {
        ...$json,
        route: 'sentinel',
        sentinel_payload: {
          source: 'aria',
          chain_name: chain,
          input: input
        }
      }
    };
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// DETECT SINGLE AGENT CALLS
// ═══════════════════════════════════════════════════════════════════════════

for (const [agent, patterns] of Object.entries(agentPatterns)) {
  for (const pattern of patterns) {
    if (pattern.test(messageLower)) {
      
      // Determine action based on patterns
      let action = 'chat';
      let params = { message };
      
      if (agent === 'chiron') {
        if (/sprint|plan my (week|day)/i.test(messageLower)) {
          action = 'sprint-plan';
          params = { goals: [message], time_available: 'this week' };
        } else if (/pricing/i.test(messageLower)) {
          action = 'pricing-help';
          params = { service_description: message };
        } else if (/afraid|fear|scared/i.test(messageLower)) {
          action = 'fear-check';
          params = { situation: message };
        }
      } else if (agent === 'scholar') {
        if (/competitor/i.test(messageLower)) {
          action = 'deep-research';
          params = { question: message };
        } else if (/market size|tam|sam|som/i.test(messageLower)) {
          action = 'market-size';
          params = { market: message };
        } else if (/pain point/i.test(messageLower)) {
          action = 'pain-discovery';
          params = { role: 'compliance officer', industry: 'water utilities' };
        } else {
          action = 'deep-research';
          params = { question: message };
        }
      }
      
      return {
        json: {
          ...$json,
          route: 'sentinel',
          sentinel_payload: {
            source: 'aria',
            type: 'single',
            steps: [{
              id: `${agent}_call`,
              agent: agent,
              action: action,
              params: params
            }],
            input: { raw_message: message }
          }
        }
      };
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// DEFAULT: ARIA HANDLES
// ═══════════════════════════════════════════════════════════════════════════

return {
  json: {
    ...$json,
    route: 'aria'
  }
};
```

## ARIA HTTP Node for SENTINEL

```
URL: http://sentinel:8019/orchestrate
Method: POST
Body: {{ JSON.stringify($json.sentinel_payload) }}
Headers:
  Content-Type: application/json
```

## ARIA Response Formatter for Orchestration Results

```javascript
/**
 * Format orchestration results for human-friendly display
 */

const result = $json;
const route = $('Pre-Router').first().json.route;

// If not orchestrated, pass through
if (route !== 'sentinel') {
  return $json;
}

// Check for errors
if (result.status === 'failed') {
  return {
    json: {
      message: `❌ **Request Failed**\n\n${result.errors?.map(e => e.error).join('\n') || 'Unknown error'}`,
      mode: 'DEFAULT'
    }
  };
}

// Format based on what was executed
const stepOutputs = result.step_outputs || result.step_results || {};
const stepsCompleted = Object.keys(stepOutputs).length;
const routedTo = result._routed_to || 'unknown';
const totalCost = result.total_cost || 0;

let formatted = '';

// Single agent result
if (stepsCompleted === 1) {
  const [stepId, step] = Object.entries(stepOutputs)[0];
  const agent = (step.agent || stepId).toUpperCase();
  const output = step.output || step;
  
  const content = output.response || output.research || output.sprint_plan || 
                  output.pricing_strategy || output.fear_analysis ||
                  (typeof output === 'object' ? JSON.stringify(output, null, 2) : output);
  
  const icon = agent === 'CHIRON' ? '🎯' : agent === 'SCHOLAR' ? '📚' : '🤖';
  formatted = `${icon} **${agent}:**\n\n${content}`;
}
// Chain result
else if (stepsCompleted > 1) {
  formatted = `🔗 **Multi-Agent Analysis Complete** *(${stepsCompleted} steps)*\n\n`;
  
  // Use formatted output if available
  if (result.formatted_output) {
    formatted += result.formatted_output;
  } else {
    // Build from step outputs
    for (const [stepId, step] of Object.entries(stepOutputs)) {
      const agent = (step.agent || stepId).toUpperCase();
      const output = step.output || step;
      
      const content = output.response || output.research || output.sprint_plan ||
                      (typeof output === 'object' ? JSON.stringify(output, null, 2).substring(0, 1000) : output);
      
      formatted += `### ${agent}\n\n${content}\n\n---\n\n`;
    }
  }
}

// Add footer
if (totalCost > 0) {
  formatted += `\n\n*💰 Cost: $${totalCost.toFixed(4)} | ⚡ Engine: ${routedTo} | ⏱️ ${result.duration_ms}ms*`;
}

return {
  json: {
    message: formatted,
    orchestration_result: result,
    mode: stepsCompleted > 1 ? 'STRATEGY' : 'DEFAULT'
  }
};
```

---

# COMPONENT 6: DOCKER CONFIGURATION

## docker-compose.yml additions

```yaml
# Add to /opt/leveredge/control-plane/docker-compose.yml

  atlas:
    build: ./agents/atlas
    container_name: atlas
    restart: unless-stopped
    ports:
      - "8007:8007"
    volumes:
      - /opt/leveredge/config:/opt/leveredge/config:ro
    environment:
      - REGISTRY_PATH=/opt/leveredge/config/agent-registry.yaml
      - EVENT_BUS_URL=http://event-bus:8099
      - SENTINEL_URL=http://sentinel:8019
    networks:
      - control-plane-net
      - stack_net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8007/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - event-bus

  sentinel:
    build: ./agents/sentinel
    container_name: sentinel
    restart: unless-stopped
    ports:
      - "8019:8019"
    volumes:
      - /opt/leveredge/config:/opt/leveredge/config:ro
    environment:
      - REGISTRY_PATH=/opt/leveredge/config/agent-registry.yaml
      - EVENT_BUS_URL=http://event-bus:8099
      - FASTAPI_ATLAS_URL=http://atlas:8007
      - N8N_ATLAS_URL=http://control-n8n:5679
      - HERMES_URL=http://hermes:8014
    networks:
      - control-plane-net
      - stack_net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8019/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - atlas
      - event-bus
```

## Dockerfile for ATLAS

```dockerfile
# /opt/leveredge/control-plane/agents/atlas/Dockerfile

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8007

CMD ["uvicorn", "atlas:app", "--host", "0.0.0.0", "--port", "8007"]
```

## requirements.txt for ATLAS

```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.26.0
pydantic==2.5.3
pyyaml==6.0.1
jinja2==3.1.3
```

## Dockerfile for SENTINEL

```dockerfile
# /opt/leveredge/control-plane/agents/sentinel/Dockerfile

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8019

CMD ["uvicorn", "sentinel:app", "--host", "0.0.0.0", "--port", "8019"]
```

## requirements.txt for SENTINEL

```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.26.0
pydantic==2.5.3
pyyaml==6.0.1
```

---

# IMPLEMENTATION ORDER

## Phase 1: Foundation (2 hours)
1. Create `/opt/leveredge/config/` directory
2. Create `agent-registry.yaml`
3. Validate YAML syntax

## Phase 2: FastAPI ATLAS (1 hour)
1. Create `/opt/leveredge/control-plane/agents/atlas/` directory
2. Create `atlas.py`
3. Create `Dockerfile` and `requirements.txt`
4. Build and test container
5. Verify `/health` and `/chains` endpoints

## Phase 3: SENTINEL (1 hour)
1. Create `/opt/leveredge/control-plane/agents/sentinel/` directory
2. Create `sentinel.py`
3. Create `Dockerfile` and `requirements.txt`
4. Build and test container
5. Verify routing logic

## Phase 4: n8n ATLAS Workflow (30 min)
1. Create workflow in control n8n
2. Test webhook endpoint
3. Verify step execution

## Phase 5: ARIA Integration (30 min)
1. Update ARIA Pre-Router
2. Add SENTINEL HTTP node
3. Update Response Formatter
4. Test end-to-end

## Phase 6: Validation (30 min)
1. Test single agent calls via SENTINEL
2. Test chain execution
3. Test failover (stop one engine, verify routing)
4. Test drift detection

---

# TESTING

## Test Single Agent Call
```bash
curl -X POST http://localhost:8019/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "type": "single",
    "steps": [{
      "id": "test",
      "agent": "chiron",
      "action": "chat",
      "params": {"message": "What should I focus on today?"}
    }]
  }'
```

## Test Chain
```bash
curl -X POST http://localhost:8019/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "chain_name": "research-and-plan",
    "input": {"topic": "water utility compliance automation"}
  }'
```

## Test Direct Call (bypass ATLAS)
```bash
curl -X POST http://localhost:8019/direct/scholar/deep-research \
  -H "Content-Type: application/json" \
  -d '{"question": "What are compliance pain points?"}'
```

## Test Engine Status
```bash
curl http://localhost:8019/status
```

## Test Drift Validation
```bash
curl http://localhost:8019/validate-sync
```

## Test via ARIA
```
"Research AEGIS best practices, then create a plan to enhance our credential manager"
```

---

# SUCCESS CRITERIA

- [ ] Agent registry loads correctly in both implementations
- [ ] FastAPI ATLAS executes single and chain intents
- [ ] n8n ATLAS executes single and chain intents
- [ ] SENTINEL routes based on complexity
- [ ] SENTINEL detects unhealthy engines
- [ ] SENTINEL fails over to healthy engine
- [ ] Drift detection identifies missing chains
- [ ] ARIA routes through SENTINEL
- [ ] ARIA displays formatted multi-agent responses
- [ ] Cost tracking aggregates across chains
- [ ] Event Bus receives all orchestration events
- [ ] All containers healthy in Docker

---

# GIT COMMIT MESSAGE

```
OLYMPUS: Unified Orchestration System

The One Registry to rule them all.

Components:
- Agent Registry (YAML) - Single source of truth
- FastAPI ATLAS - Complex chains, parallel execution
- n8n ATLAS - Visual debugging, simple chains
- SENTINEL - Smart routing, health monitoring, drift detection

Features:
- Zero LLM cost orchestration
- Auto-failover between engines
- Drift detection with alerting
- 6 pre-built chain templates
- Parallel and conditional execution
- Full Event Bus integration
- Cost aggregation

Chain templates:
- research-and-plan
- validate-and-decide
- comprehensive-market-analysis
- niche-evaluation
- weekly-planning
- fear-to-action
```
