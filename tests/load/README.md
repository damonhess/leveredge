# Leveredge Load Testing Suite

Comprehensive load testing for the Leveredge agent fleet using [Locust](https://locust.io/).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run light load test (10 users)
./run_tests.sh light

# Start web UI for interactive testing
./run_tests.sh web
# Then open http://localhost:8089
```

## Test Profiles

| Profile | Users | Spawn Rate | Duration | Use Case |
|---------|-------|------------|----------|----------|
| `light` | 10 | 1/s | 5 min | Development, smoke testing |
| `medium` | 50 | 5/s | 10 min | Staging, pre-production |
| `heavy` | 200 | 20/s | 15 min | Capacity testing, stress |
| `stress` | 500 | 50/s | 5 min | Maximum throughput test |

## Available Test Scenarios

### 1. Health Checks (`scenarios/health_checks.py`)
Tests health endpoints across all agents in the fleet.

**Tags:** `health`, `core`, `support`, `creative`, `security`

```bash
./run_tests.sh health-only
```

### 2. ARIA Chat (`scenarios/aria_chat.py`)
Simulates users having conversations with ARIA through ATLAS orchestration.

**Tags:** `chat`, `new-conversation`, `followup`, `research`, `workflow`

```bash
./run_tests.sh chat-only
```

### 3. Event Bus (`scenarios/event_bus.py`)
Tests Event Bus throughput for agent communication.

**Tags:** `event-bus`, `publish`, `query`, `acknowledge`, `throughput`, `burst`

```bash
./run_tests.sh event-bus-only
```

### 4. Creative Fleet (`scenarios/creative_fleet.py`)
Tests creative content generation agents (MUSE, CALLIOPE, THALIA, ERATO, CLIO).

**Tags:** `creative`, `muse`, `calliope`, `thalia`, `clio`, `batch`

```bash
./run_tests.sh light --tags creative
```

## Running Tests

### Command Line (Headless)

```bash
# Basic run with profile
./run_tests.sh light
./run_tests.sh medium
./run_tests.sh heavy

# Custom configuration
./run_tests.sh custom --users 25 --spawn-rate 5 --run-time 10m

# Filter by tags
./run_tests.sh light --tags health
./run_tests.sh medium --tags "event-bus,throughput"

# Target different host
HOST=https://staging.leveredge.ai ./run_tests.sh medium
```

### Web UI (Interactive)

```bash
./run_tests.sh web
```

Then open http://localhost:8089 and configure:
- Number of users
- Spawn rate
- Host URL

### Direct Locust Commands

```bash
# With config file
locust -f locustfile.py --config configs/medium.conf

# Specific user class
locust -f locustfile.py --class-picker

# Export CSV results
locust -f locustfile.py --headless --csv=results
```

## Test Architecture

```
/opt/leveredge/tests/load/
├── locustfile.py          # Main entry point
├── scenarios/
│   ├── health_checks.py   # Agent health monitoring
│   ├── aria_chat.py       # Conversation simulation
│   ├── event_bus.py       # Event throughput
│   └── creative_fleet.py  # Creative agent load
├── configs/
│   ├── light.conf         # 10 users
│   ├── medium.conf        # 50 users
│   └── heavy.conf         # 200 users
├── reports/               # HTML/CSV reports (generated)
├── logs/                  # Test logs (generated)
├── run_tests.sh           # Helper script
├── requirements.txt       # Dependencies
├── README.md              # This file
└── benchmarks.md          # Benchmark recording template
```

## Agent Port Reference

| Agent | Port | Category | Description |
|-------|------|----------|-------------|
| ATLAS | 8007 | Core | Orchestration engine |
| HADES | 8008 | Core | Storage & persistence |
| CHRONOS | 8010 | Core | Scheduler |
| HEPHAESTUS | 8011 | Core | Code forge |
| AEGIS | 8012 | Core | Security guardian |
| ATHENA | 8013 | Core | Knowledge base |
| HERMES | 8014 | Core | Messenger |
| ALOY | 8015 | Core | Audit & anomaly |
| ARGUS | 8016 | Core | System monitor |
| CHIRON | 8017 | Core | Healer |
| SCHOLAR | 8018 | Core | Research |
| SENTINEL | 8019 | Core | Watchdog |
| EVENT-BUS | 8099 | Core | Event system |
| CERBERUS | 8020 | Security | Access control |
| PORT-MANAGER | 8021 | Security | Port registry |
| MUSE | 8030 | Creative | Creative director |
| CALLIOPE | 8031 | Creative | Content writer |
| THALIA | 8032 | Creative | Visual designer |
| ERATO | 8033 | Creative | Video producer |
| CLIO | 8034 | Creative | Asset manager |

## Interpreting Results

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **RPS** | Requests per second | Higher is better |
| **Avg Response Time** | Mean response time | < 500ms for health, < 5s for chat |
| **P95** | 95th percentile latency | < 2x average |
| **P99** | 99th percentile latency | < 5x average |
| **Failure Rate** | % of failed requests | < 1% under normal load |

### Response Time Expectations

| Endpoint Type | Light Load | Medium Load | Heavy Load |
|--------------|------------|-------------|------------|
| Health checks | < 50ms | < 100ms | < 500ms |
| Event publish | < 100ms | < 200ms | < 1s |
| Chat queries | < 5s | < 10s | < 30s |
| Creative tasks | < 30s | < 60s | < 120s |

### Warning Signs

- **High failure rate (>1%)**: System may be overloaded
- **Increasing latency**: Check for memory leaks or resource exhaustion
- **Connection errors**: Check agent availability
- **Timeout errors**: May need to increase timeout values

## Reports

After each test run, reports are generated in:

- `reports/[profile]_[timestamp].html` - Visual HTML report
- `reports/[profile]_[timestamp]_stats.csv` - Request statistics
- `reports/[profile]_[timestamp]_failures.csv` - Failure details
- `reports/[profile]_[timestamp]_stats_history.csv` - Time series data
- `logs/[profile]_[timestamp].log` - Detailed test log

## Extending Tests

### Adding New Scenarios

1. Create new file in `scenarios/`
2. Define `HttpUser` subclass with `@task` methods
3. Import in `scenarios/__init__.py`
4. Import in `locustfile.py`

Example:

```python
# scenarios/my_scenario.py
from locust import HttpUser, task, between, tag

class MyScenarioUser(HttpUser):
    wait_time = between(1, 5)

    @task
    @tag('my-tag')
    def my_test(self):
        with self.client.get("/my-endpoint", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Failed")
```

### Custom Tags

Use tags to organize and filter tests:

```python
@task
@tag('health', 'core', 'critical')
def critical_health_check(self):
    ...
```

Run filtered:
```bash
locust -f locustfile.py --tags critical
locust -f locustfile.py --exclude-tags stress
```

## Troubleshooting

### "Connection refused" errors

```bash
# Check if agents are running
curl http://localhost:8007/health
curl http://localhost:8099/health

# Check Docker containers
docker ps | grep leveredge
```

### "Too many open files" error

```bash
# Increase file descriptor limit
ulimit -n 65536
```

### Memory issues with many users

```bash
# Use multiple worker processes
locust -f locustfile.py --master &
locust -f locustfile.py --worker &
locust -f locustfile.py --worker &
```

## Best Practices

1. **Start small**: Begin with `light` profile and increase gradually
2. **Monitor resources**: Watch CPU, memory, and network during tests
3. **Test in isolation**: Avoid running other heavy processes during load tests
4. **Compare baselines**: Record benchmarks after each major change
5. **Use tags**: Focus on specific areas rather than running everything
6. **Review failures**: Investigate any failures before increasing load
