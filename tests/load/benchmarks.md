# Leveredge Load Testing Benchmarks

Template for recording and tracking load test benchmark results.

---

## Benchmark Summary

| Date | Profile | Users | RPS | Avg (ms) | P95 (ms) | P99 (ms) | Fail % | Notes |
|------|---------|-------|-----|----------|----------|----------|--------|-------|
| YYYY-MM-DD | light | 10 | - | - | - | - | - | Initial baseline |
| | | | | | | | | |

---

## Detailed Benchmark Records

### Benchmark: [DATE] - [DESCRIPTION]

**Test Configuration:**
- Profile: `light` / `medium` / `heavy` / `custom`
- Users: X concurrent
- Spawn Rate: X/second
- Duration: X minutes
- Tags: `all` / `health` / `chat` / `event-bus`
- Host: http://localhost

**System State:**
- Server: [CPU/RAM specs]
- Load before test: [load average]
- Agents running: [list or "all"]

#### Request Statistics

| Endpoint | Requests | Failures | Median (ms) | Avg (ms) | P95 (ms) | P99 (ms) | RPS |
|----------|----------|----------|-------------|----------|----------|----------|-----|
| /health [atlas] | - | - | - | - | - | - | - |
| /health [event-bus] | - | - | - | - | - | - | - |
| /execute [chat] | - | - | - | - | - | - | - |
| /events [publish] | - | - | - | - | - | - | - |
| **TOTAL** | - | - | - | - | - | - | - |

#### Error Analysis

| Error Type | Count | Endpoint | Notes |
|------------|-------|----------|-------|
| Timeout | - | - | - |
| 503 Service Unavailable | - | - | - |
| Connection refused | - | - | - |

#### Resource Usage (during test)

| Metric | Start | Peak | End |
|--------|-------|------|-----|
| CPU % | - | - | - |
| Memory % | - | - | - |
| Open connections | - | - | - |
| Event Bus queue depth | - | - | - |

#### Observations

-
-
-

#### Recommendations

-
-
-

---

## Capacity Limits (Documented)

Based on load testing, these are the observed capacity limits:

### Health Check Endpoints

| Agent | Max RPS (P95 < 100ms) | Max RPS (P95 < 500ms) | Breaking Point |
|-------|----------------------|----------------------|----------------|
| ATLAS | - | - | - |
| EVENT-BUS | - | - | - |
| HEPHAESTUS | - | - | - |
| AEGIS | - | - | - |
| HERMES | - | - | - |

### Event Bus

| Metric | Light Load | Medium Load | Heavy Load | Limit |
|--------|------------|-------------|------------|-------|
| Publish RPS | - | - | - | - |
| Query RPS | - | - | - | - |
| Max queue depth | - | - | - | - |
| Ack latency (P95) | - | - | - | - |

### ARIA Chat (via ATLAS)

| Metric | Light Load | Medium Load | Heavy Load | Limit |
|--------|------------|-------------|------------|-------|
| Concurrent sessions | - | - | - | - |
| Requests/minute | - | - | - | - |
| Response time (P95) | - | - | - | - |
| Token throughput | - | - | - | - |

### Creative Fleet

| Agent | Max concurrent requests | Avg processing time | Queue capacity |
|-------|------------------------|--------------------| ---------------|
| MUSE | - | - | - |
| CALLIOPE | - | - | - |
| THALIA | - | - | - |
| ERATO | - | - | - |
| CLIO | - | - | - |

---

## SLA Targets

Based on benchmarks, recommended SLA targets:

| Service | Availability | Response Time (P95) | Error Rate |
|---------|-------------|---------------------|------------|
| Health endpoints | 99.9% | < 100ms | < 0.1% |
| Event Bus | 99.9% | < 200ms | < 0.5% |
| ATLAS orchestration | 99.5% | < 10s | < 1% |
| Creative tasks | 99% | < 60s | < 2% |

---

## Historical Comparison

### Response Time Trends

```
Date        | Health (P95) | Event Bus (P95) | Chat (P95)
---------------------------------------------------------
YYYY-MM-DD  |     ms       |       ms        |     ms
YYYY-MM-DD  |     ms       |       ms        |     ms
```

### Throughput Trends

```
Date        | Health RPS | Event RPS | Chat RPM
-----------------------------------------------
YYYY-MM-DD  |            |           |
YYYY-MM-DD  |            |           |
```

---

## Testing Checklist

Before running benchmarks:

- [ ] All target agents are running and healthy
- [ ] No other load on the system
- [ ] Monitoring/metrics collection enabled
- [ ] Previous test logs archived
- [ ] Database connections stable

After running benchmarks:

- [ ] Results recorded in this file
- [ ] HTML report saved to `reports/`
- [ ] Anomalies investigated
- [ ] Recommendations documented
- [ ] Team notified of significant findings

---

## Notes

Add general notes, learnings, and context here:

-
-
-

---

*Last updated: [DATE]*
*Benchmark owner: [NAME]*
