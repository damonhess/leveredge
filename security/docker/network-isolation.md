# Docker Network Isolation Guide

## Overview

This guide documents the Docker network architecture for the LeverEdge platform,
implementing defense-in-depth network isolation to limit the blast radius of
potential security breaches.

## Network Architecture

```
                                    ┌─────────────────────────────────────────────┐
                                    │              INTERNET                        │
                                    └─────────────────────┬───────────────────────┘
                                                          │
                                                          ▼
                                    ┌─────────────────────────────────────────────┐
                                    │           DMZ Network (public)               │
                                    │  - Nginx Reverse Proxy                       │
                                    │  - Rate Limiting                             │
                                    │  - WAF Rules                                 │
                                    └─────────────────────┬───────────────────────┘
                                                          │
                          ┌───────────────────────────────┼───────────────────────────────┐
                          │                               │                               │
                          ▼                               ▼                               ▼
        ┌─────────────────────────────┐  ┌─────────────────────────────┐  ┌─────────────────────────────┐
        │   App Network (app-tier)    │  │  Agent Network (agents)     │  │  Data Network (data-tier)   │
        │  - n8n instances            │  │  - CERBERUS                 │  │  - PostgreSQL               │
        │  - API Gateway              │  │  - HERMES                   │  │  - Redis                    │
        │  - Supabase Edge            │  │  - AEGIS                    │  │  - Vector DB                │
        └─────────────────────────────┘  │  - All other agents         │  │  - MinIO                    │
                          │              └─────────────────────────────┘  └─────────────────────────────┘
                          │                               │                               │
                          └───────────────────────────────┼───────────────────────────────┘
                                                          │
                                                          ▼
                                    ┌─────────────────────────────────────────────┐
                                    │        Monitoring Network (monitor)          │
                                    │  - Prometheus                                │
                                    │  - Grafana                                   │
                                    │  - Loki                                      │
                                    └─────────────────────────────────────────────┘
```

## Network Definitions

### 1. DMZ Network (leveredge-dmz)

**Purpose**: Public-facing services, first line of defense

**Subnet**: `172.20.0.0/24`

**Allowed Services**:
- Nginx reverse proxy
- Cloudflare tunnel (if used)
- Load balancer

**Security Properties**:
- No direct database access
- No direct agent access
- All traffic must pass through reverse proxy
- Rate limiting enforced
- WAF rules applied

### 2. Application Network (leveredge-app)

**Purpose**: Core application services

**Subnet**: `172.21.0.0/24`

**Allowed Services**:
- n8n instances (main, webhook, worker)
- Supabase API services
- API Gateway

**Security Properties**:
- Can connect to data-tier
- Can connect to agents (limited)
- Cannot be accessed directly from internet
- Inter-service communication only

### 3. Agent Network (leveredge-agents)

**Purpose**: AI agents and automation services

**Subnet**: `172.22.0.0/24`

**Allowed Services**:
- All LeverEdge agents (CERBERUS, HERMES, AEGIS, etc.)
- Agent-specific databases
- Model inference services

**Security Properties**:
- Isolated from direct internet access
- Can communicate with app-tier (for API calls)
- Can communicate with data-tier (for persistence)
- Inter-agent communication allowed

### 4. Data Network (leveredge-data)

**Purpose**: Database and storage services

**Subnet**: `172.23.0.0/24`

**Allowed Services**:
- PostgreSQL
- Redis
- MinIO object storage
- Vector databases (Qdrant, Pinecone proxy)

**Security Properties**:
- No internet access
- Only accessible from app-tier and agent-tier
- Encrypted connections required
- Backup network access only

### 5. Monitoring Network (leveredge-monitor)

**Purpose**: Observability and monitoring

**Subnet**: `172.24.0.0/24`

**Allowed Services**:
- Prometheus
- Grafana
- Loki
- AlertManager

**Security Properties**:
- Read-only access to all other networks
- Can scrape metrics from all services
- Dashboard access through app-tier only

## Creating the Networks

```bash
#!/bin/bash
# Create isolated Docker networks for LeverEdge

# DMZ Network - Public facing
docker network create \
  --driver bridge \
  --subnet 172.20.0.0/24 \
  --gateway 172.20.0.1 \
  --opt com.docker.network.bridge.name=br-leveredge-dmz \
  --opt com.docker.network.bridge.enable_icc=false \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --label com.leveredge.network=dmz \
  --label com.leveredge.security=high \
  leveredge-dmz

# Application Network
docker network create \
  --driver bridge \
  --subnet 172.21.0.0/24 \
  --gateway 172.21.0.1 \
  --opt com.docker.network.bridge.name=br-leveredge-app \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --label com.leveredge.network=app \
  --label com.leveredge.security=medium \
  leveredge-app

# Agent Network
docker network create \
  --driver bridge \
  --subnet 172.22.0.0/24 \
  --gateway 172.22.0.1 \
  --opt com.docker.network.bridge.name=br-leveredge-agents \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=false \
  --label com.leveredge.network=agents \
  --label com.leveredge.security=high \
  leveredge-agents

# Data Network - Most restricted
docker network create \
  --driver bridge \
  --subnet 172.23.0.0/24 \
  --gateway 172.23.0.1 \
  --internal \
  --opt com.docker.network.bridge.name=br-leveredge-data \
  --opt com.docker.network.bridge.enable_icc=true \
  --label com.leveredge.network=data \
  --label com.leveredge.security=critical \
  leveredge-data

# Monitoring Network
docker network create \
  --driver bridge \
  --subnet 172.24.0.0/24 \
  --gateway 172.24.0.1 \
  --opt com.docker.network.bridge.name=br-leveredge-monitor \
  --opt com.docker.network.bridge.enable_icc=true \
  --label com.leveredge.network=monitor \
  --label com.leveredge.security=medium \
  leveredge-monitor
```

## Network Connection Matrix

| Source Network | DMZ | App | Agents | Data | Monitor |
|----------------|-----|-----|--------|------|---------|
| **DMZ**        | -   | Yes | No     | No   | No      |
| **App**        | Yes | -   | Yes    | Yes  | Yes     |
| **Agents**     | No  | Yes | -      | Yes  | Yes     |
| **Data**       | No  | No  | No     | -    | Yes     |
| **Monitor**    | Yes | Yes | Yes    | Yes  | -       |

## Service Network Assignments

### DMZ Network Services
```yaml
services:
  nginx:
    networks:
      - leveredge-dmz
      - leveredge-app  # To proxy to app services
```

### Application Network Services
```yaml
services:
  n8n:
    networks:
      - leveredge-app
      - leveredge-data  # Database access

  supabase-api:
    networks:
      - leveredge-app
      - leveredge-data
```

### Agent Network Services
```yaml
services:
  cerberus:
    networks:
      - leveredge-agents
      - leveredge-app     # API access
      - leveredge-monitor # Metrics

  hermes:
    networks:
      - leveredge-agents
      - leveredge-app
```

### Data Network Services
```yaml
services:
  postgres:
    networks:
      - leveredge-data

  redis:
    networks:
      - leveredge-data
```

## IPTables Rules for Network Isolation

Apply these rules on the Docker host to enforce network boundaries:

```bash
#!/bin/bash
# Additional iptables rules for Docker network isolation

# Block direct communication between DMZ and Data networks
iptables -I DOCKER-USER -s 172.20.0.0/24 -d 172.23.0.0/24 -j DROP
iptables -I DOCKER-USER -s 172.23.0.0/24 -d 172.20.0.0/24 -j DROP

# Block direct communication between DMZ and Agent networks
iptables -I DOCKER-USER -s 172.20.0.0/24 -d 172.22.0.0/24 -j DROP
iptables -I DOCKER-USER -s 172.22.0.0/24 -d 172.20.0.0/24 -j DROP

# Block Data network from initiating external connections
iptables -I DOCKER-USER -s 172.23.0.0/24 ! -d 172.0.0.0/8 -j DROP

# Log dropped packets for security monitoring
iptables -I DOCKER-USER -j LOG --log-prefix "DOCKER-DROP: " --log-level 4
```

## Security Best Practices

### 1. Use Internal Networks for Databases
- Mark database networks as `internal: true`
- This prevents any external routing

### 2. Disable ICC Where Not Needed
- Set `enable_icc=false` for DMZ network
- Prevents container-to-container communication within network

### 3. Use Network Aliases
```yaml
services:
  postgres:
    networks:
      leveredge-data:
        aliases:
          - db.internal
          - postgres.leveredge.local
```

### 4. Implement Network Policies (Kubernetes)
If migrating to Kubernetes, implement NetworkPolicy resources.

### 5. Regular Audits
```bash
# List all networks and their connections
docker network ls
docker network inspect leveredge-dmz
docker network inspect leveredge-app
docker network inspect leveredge-agents
docker network inspect leveredge-data

# Check container network connections
docker inspect --format='{{json .NetworkSettings.Networks}}' <container>
```

## Troubleshooting

### Container Cannot Reach Database
1. Verify container is on correct network:
   ```bash
   docker inspect <container> | jq '.[0].NetworkSettings.Networks'
   ```

2. Check if service is on data network:
   ```bash
   docker network inspect leveredge-data
   ```

3. Test connectivity:
   ```bash
   docker exec <container> ping postgres.leveredge.local
   ```

### Network Performance Issues
1. Check for IP conflicts
2. Verify MTU settings match
3. Review iptables rules for excessive logging

## Maintenance

### Removing Unused Networks
```bash
# List dangling networks
docker network ls -f dangling=true

# Prune unused networks (careful!)
docker network prune
```

### Rotating Network Configuration
When updating network configuration:
1. Create new networks with updated config
2. Migrate services one at a time
3. Verify connectivity after each migration
4. Remove old networks
