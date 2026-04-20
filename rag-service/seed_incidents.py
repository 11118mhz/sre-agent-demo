SEED_INCIDENTS = [
    {
        "id": "inc-001",
        "timestamp": "2026-03-15T02:34:00Z",
        "duration_minutes": 23,
        "service": "payment-api",
        "alert_text": "payment-api elevated error rates and high latency",
        "symptoms": {
            "error_rate_percent": 21.3,
            "latency_p99_ms": 3800,
            "key_log_messages": [
                "Connection pool exhausted: timeout waiting for connection",
                "DB_POOL_SIZE=10 connections all in use",
                "Transaction failed: could not acquire DB connection"
            ]
        },
        "root_cause": "DB_POOL_SIZE reduced from 20 to 10 in ConfigMap during deploy",
        "root_cause_category": "misconfiguration",
        "evidence": [
            "Deploy 2 hours prior changed DB_POOL_SIZE via ConfigMap",
            "All 10 connections active at time of incident",
            "Error rate dropped immediately after rollback"
        ],
        "remediation": "Rolled back to previous deployment restoring DB_POOL_SIZE to 20",
        "remediation_successful": True,
        "narrative": "payment-api started throwing elevated error rates shortly after a routine deployment. Metrics showed all database connections maxed out at 10/10. Investigation revealed a ConfigMap change in the same deployment had halved the connection pool size from 20 to 10. At the service's normal request rate this was insufficient. Rollback to the previous version immediately restored normal operation.",
        "follow_up_actions": [
            "Add DB connection pool utilisation alert at 80% threshold",
            "Review ConfigMap changes as part of deployment checklist"
        ],
        "tags": ["database", "connection-pool", "misconfiguration", "rollback"]
    },
    {
        "id": "inc-002",
        "timestamp": "2026-02-28T14:12:00Z",
        "duration_minutes": 41,
        "service": "user-service",
        "alert_text": "user-service OOMKilled pods and elevated error rates",
        "symptoms": {
            "error_rate_percent": 45.2,
            "latency_p99_ms": 1200,
            "key_log_messages": [
                "OOMKilled: container exceeded memory limit",
                "Pod restarting due to memory limit exceeded",
                "Java heap space: OutOfMemoryError"
            ]
        },
        "root_cause": "Memory limit in deployment manifest reduced from 2Gi to 512Mi during a resource optimisation pass",
        "root_cause_category": "misconfiguration",
        "evidence": [
            "Deploy 3 hours prior changed memory limit from 2Gi to 512Mi",
            "Pods repeatedly OOMKilled within minutes of starting",
            "JVM heap requirements exceed new limit under normal load"
        ],
        "remediation": "Rolled back deployment to restore memory limit to 2Gi",
        "remediation_successful": True,
        "narrative": "user-service pods were cycling repeatedly with OOMKilled status. Error rates spiked as pods could not stay up long enough to serve traffic. A recent deployment had aggressively reduced memory limits as part of a cost optimisation effort. The new limit of 512Mi was insufficient for the JVM heap under normal load. Rolling back restored stable pod operation immediately.",
        "follow_up_actions": [
            "Establish memory baseline before reducing limits",
            "Add OOMKilled alert to monitoring"
        ],
        "tags": ["memory", "oom", "misconfiguration", "rollback", "kubernetes"]
    },
    {
        "id": "inc-003",
        "timestamp": "2026-01-19T09:45:00Z",
        "duration_minutes": 67,
        "service": "api-gateway",
        "alert_text": "api-gateway blocking legitimate traffic, high 429 error rate",
        "symptoms": {
            "error_rate_percent": 38.7,
            "latency_p99_ms": 95,
            "key_log_messages": [
                "Rate limit exceeded for client 10.0.0.0/8",
                "429 Too Many Requests: rate limit threshold reached",
                "Rejecting request: client quota exhausted"
            ]
        },
        "root_cause": "Rate limit configuration changed to apply per-IP instead of per-user, causing internal service IPs to share a single quota",
        "root_cause_category": "misconfiguration",
        "evidence": [
            "Config change 4 hours prior modified rate limit scope from per-user to per-IP",
            "All 429 errors originating from internal service subnet 10.0.0.0/8",
            "Error rate dropped immediately after reverting rate limit config"
        ],
        "remediation": "Reverted rate limit configuration to per-user scope",
        "remediation_successful": True,
        "narrative": "api-gateway began rejecting a large fraction of requests with 429 errors. Latency was low, indicating the gateway was healthy — it was just refusing requests. Investigation showed a recent config change had switched rate limiting from per-user to per-IP. Internal services sharing the same IP subnet were collectively exhausting a single quota within seconds. Reverting the config immediately resolved the issue.",
        "follow_up_actions": [
            "Add internal service IPs to rate limit allowlist",
            "Test rate limit config changes in staging before production"
        ],
        "tags": ["rate-limiting", "misconfiguration", "api-gateway", "429"]
    },
    {
        "id": "inc-004",
        "timestamp": "2026-02-10T03:22:00Z",
        "duration_minutes": 38,
        "service": "image-processor",
        "alert_text": "image-processor memory climbing steadily, latency degrading",
        "symptoms": {
            "error_rate_percent": 4.1,
            "latency_p99_ms": 5200,
            "key_log_messages": [
                "GC overhead warning: GC time exceeding 15% of runtime",
                "GC overhead warning: GC time exceeding 24% of runtime",
                "Heap usage at 89%, approaching critical threshold"
            ]
        },
        "root_cause": "Memory leak in image thumbnail generation library introduced in v3.2.1 — image buffers not released after processing",
        "root_cause_category": "runtime_degradation",
        "evidence": [
            "Memory climbing steadily over 72 hours since deployment of v3.2.1",
            "GC overhead increasing progressively — 8% to 24% over 6 hours",
            "Pod uptime of 72 hours correlates with memory accumulation",
            "No memory leak present in v3.2.0"
        ],
        "remediation": "Rolled back to v3.2.0, memory stabilised within 10 minutes",
        "remediation_successful": True,
        "narrative": "image-processor showed progressively worsening latency and memory pressure over several days. GC logs showed overhead climbing hour by hour. No recent config changes — the only change was a library update in v3.2.1 three days prior. The long pod uptime and progressive memory growth pattern pointed clearly to a memory leak. Rollback to v3.2.0 confirmed the diagnosis as memory stabilised immediately.",
        "follow_up_actions": [
            "Profile v3.2.1 image buffer handling in staging",
            "Add memory growth rate alert to catch leaks earlier"
        ],
        "tags": ["memory-leak", "gc", "runtime-degradation", "rollback"]
    },
    {
        "id": "inc-005",
        "timestamp": "2026-01-08T11:55:00Z",
        "duration_minutes": 29,
        "service": "notification-service",
        "alert_text": "notification-service latency spiking, thread pool exhausted",
        "symptoms": {
            "error_rate_percent": 12.8,
            "latency_p99_ms": 8900,
            "key_log_messages": [
                "Thread pool exhausted: no threads available",
                "Task rejected from executor: queue full",
                "Timeout waiting for thread pool slot"
            ]
        },
        "root_cause": "Thread pool exhaustion after 18 days of uptime — slow accumulation of blocked threads waiting on an external email provider with high latency",
        "root_cause_category": "runtime_degradation",
        "evidence": [
            "Pod uptime of 18 days — no restarts since last deployment",
            "Thread pool at 100% utilisation",
            "External email provider p99 latency at 4200ms over past week",
            "Thread dump shows majority of threads blocked on email provider HTTP calls"
        ],
        "remediation": "Restarted pods to clear thread pool, implemented circuit breaker for email provider",
        "remediation_successful": True,
        "narrative": "notification-service latency degraded sharply with thread pool exhaustion errors. Pod uptime of 18 days and no recent deployments ruled out a code change. Thread dump revealed most threads blocked waiting on an external email provider with high latency. Over 18 days, slow accumulation of these blocked threads had eventually exhausted the pool. Pod restart cleared the immediate issue while a circuit breaker was added to prevent recurrence.",
        "follow_up_actions": [
            "Implement circuit breaker for all external provider calls",
            "Add thread pool utilisation alert at 70% threshold",
            "Schedule regular pod restarts as interim mitigation"
        ],
        "tags": ["thread-pool", "runtime-degradation", "external-dependency", "restart"]
    },
    {
        "id": "inc-006",
        "timestamp": "2026-03-02T16:33:00Z",
        "duration_minutes": 51,
        "service": "search-service",
        "alert_text": "search-service elevated latency and error rate",
        "symptoms": {
            "error_rate_percent": 28.4,
            "latency_p99_ms": 6100,
            "key_log_messages": [
                "Upstream timeout: index-service failed to respond within 5000ms",
                "Circuit breaker OPEN: index-service error rate exceeded threshold",
                "Search request failed: index-service unavailable"
            ]
        },
        "root_cause": "index-service experiencing high load due to a scheduled full re-index job consuming all available resources",
        "root_cause_category": "dependency_failure",
        "evidence": [
            "search-service pods healthy — CPU, memory, restarts all normal",
            "All errors trace to index-service timeouts",
            "index-service CPU at 98% — full re-index job running",
            "No recent deployments to search-service or index-service"
        ],
        "remediation": "Paused re-index job, index-service recovered, search-service errors resolved",
        "remediation_successful": True,
        "narrative": "search-service error rate climbed steeply but the service itself appeared healthy. All errors traced to timeouts on index-service calls. index-service investigation revealed a scheduled full re-index job had been running for several hours and was consuming all available CPU, leaving insufficient resources to serve live queries. Pausing the job immediately freed resources and search-service recovered without any rollback or restart.",
        "follow_up_actions": [
            "Schedule re-index jobs during off-peak hours",
            "Add resource limits to background jobs",
            "Add circuit breaker between search-service and index-service"
        ],
        "tags": ["dependency-failure", "cascade", "background-job", "resource-contention"]
    },
    {
        "id": "inc-007",
        "timestamp": "2026-02-14T07:18:00Z",
        "duration_minutes": 34,
        "service": "order-service",
        "alert_text": "order-service elevated latency, database read timeouts",
        "symptoms": {
            "error_rate_percent": 16.9,
            "latency_p99_ms": 4400,
            "key_log_messages": [
                "Database read timeout after 3000ms",
                "Replica lag detected: 47 seconds behind primary",
                "Falling back to primary for read queries"
            ]
        },
        "root_cause": "Database read replica lagging 47 seconds behind primary due to a large batch write operation overwhelming replication",
        "root_cause_category": "dependency_failure",
        "evidence": [
            "order-service pods healthy — no recent deployments",
            "Read queries routed to replica timing out",
            "Replica lag at 47 seconds — normally under 1 second",
            "Large batch import job running on primary for past 2 hours"
        ],
        "remediation": "Paused batch import job, replica lag recovered to under 1 second within 5 minutes",
        "remediation_successful": True,
        "narrative": "order-service read queries began timing out with database replica lag errors. The service itself was healthy. Investigation showed the read replica was 47 seconds behind the primary — far outside normal. A large batch data import job had been running on the primary for two hours, generating more write load than the replica could keep up with. Pausing the import job allowed the replica to catch up within minutes.",
        "follow_up_actions": [
            "Run batch import jobs during off-peak hours",
            "Add replica lag monitoring alert at 5 second threshold",
            "Consider read replica promotion if lag persists"
        ],
        "tags": ["database", "replica-lag", "dependency-failure", "batch-job"]
    },
    {
        "id": "inc-008",
        "timestamp": "2026-01-25T20:44:00Z",
        "duration_minutes": 88,
        "service": "email-service",
        "alert_text": "email-service processing backlog growing, consumer latency high",
        "symptoms": {
            "error_rate_percent": 8.3,
            "latency_p99_ms": 12000,
            "key_log_messages": [
                "Message queue depth: 47832 messages pending",
                "Consumer processing time exceeding SLA",
                "Queue backlog growing faster than consumption rate"
            ]
        },
        "root_cause": "Message queue backlog caused by a burst of promotional emails triggered by a marketing campaign, overwhelming consumer throughput",
        "root_cause_category": "dependency_failure",
        "evidence": [
            "Queue depth grew from 200 to 47000 within 30 minutes",
            "Marketing campaign launch coincided exactly with backlog start",
            "Consumer throughput normal — queue production rate 10x normal",
            "email-service pods healthy with no recent deployments"
        ],
        "remediation": "Scaled email-service consumers from 3 to 12 pods, backlog cleared within 45 minutes",
        "remediation_successful": True,
        "narrative": "email-service processing latency climbed sharply as queue depth exploded. The service was healthy — the problem was message volume. A marketing campaign had triggered a bulk email send that produced messages 10x faster than the normal consumer throughput. Scaling consumers from 3 to 12 pods cleared the backlog within 45 minutes. The campaign team had not coordinated with engineering before launch.",
        "follow_up_actions": [
            "Establish process for marketing to notify engineering before bulk sends",
            "Implement auto-scaling for email consumers based on queue depth",
            "Add queue depth alert at 5000 messages"
        ],
        "tags": ["message-queue", "backlog", "scaling", "dependency-failure"]
    },
    {
        "id": "inc-009",
        "timestamp": "2026-03-08T13:27:00Z",
        "duration_minutes": 44,
        "service": "billing-service",
        "alert_text": "billing-service TLS handshake failures, authentication errors rising",
        "symptoms": {
            "error_rate_percent": 31.2,
            "latency_p99_ms": 290,
            "key_log_messages": [
                "TLS handshake failed: certificate verify error — unknown CA",
                "SSL certificate problem: unable to get local issuer certificate",
                "Certificate CN=billing-service.prod not trusted by clients"
            ]
        },
        "root_cause": "Internal CA certificate rotated but new CA bundle not distributed to all client services before rotation completed",
        "root_cause_category": "infrastructure_change",
        "evidence": [
            "billing-service pods healthy — all running, no restarts",
            "No code deployments in past 48 hours",
            "TLS errors began exactly when cert rotation completed 35 minutes ago",
            "Clients presenting old CA bundle that does not trust new certificate"
        ],
        "remediation": "Rolled back to previous certificate, coordinated CA bundle distribution before re-rotating",
        "remediation_successful": True,
        "narrative": "billing-service error rate spiked with TLS handshake failures. Pods were healthy and there had been no code changes. The errors started precisely when a certificate rotation completed. The new certificate was signed by an updated internal CA, but the CA bundle had not been pushed to all client services before the rotation happened. Rolling back to the previous certificate restored service immediately. The rotation was subsequently redone with proper CA bundle distribution first.",
        "follow_up_actions": [
            "Establish CA bundle distribution checklist before cert rotation",
            "Implement dual-trust period for CA rotations",
            "Add TLS handshake failure rate alert"
        ],
        "tags": ["tls", "certificate", "infrastructure-change", "rollback"]
    },
    {
        "id": "inc-010",
        "timestamp": "2026-02-03T08:15:00Z",
        "duration_minutes": 56,
        "service": "analytics-service",
        "alert_text": "analytics-service intermittent connectivity failures and timeouts",
        "symptoms": {
            "error_rate_percent": 22.7,
            "latency_p99_ms": 7800,
            "key_log_messages": [
                "DNS resolution failed for data-warehouse.internal",
                "Connection timeout: unable to reach data-warehouse.internal",
                "Intermittent name resolution errors"
            ]
        },
        "root_cause": "Internal DNS record for data-warehouse.internal updated to new IP during infrastructure migration, but TTL caused stale records to persist on some nodes",
        "root_cause_category": "infrastructure_change",
        "evidence": [
            "analytics-service pods healthy — no recent deployments",
            "Errors intermittent — some pods affected, others not",
            "DNS change to data-warehouse.internal made 90 minutes ago",
            "Affected pods caching old IP that no longer routes correctly",
            "Errors resolved on pods that had restarted after DNS change"
        ],
        "remediation": "Rolling restart of analytics-service pods to flush DNS cache, all pods resolved correctly after restart",
        "remediation_successful": True,
        "narrative": "analytics-service showed intermittent connectivity failures — some requests succeeded while others timed out. The inconsistency across pods pointed to a DNS issue rather than a service problem. An internal DNS record had been updated 90 minutes prior as part of a data warehouse migration. Pods that had started before the change were caching the old IP. A rolling restart flushed the DNS cache across all pods and resolved the issue within minutes.",
        "follow_up_actions": [
            "Reduce DNS TTL for internal service records during migrations",
            "Add DNS resolution health check to pod startup",
            "Coordinate infrastructure DNS changes with dependent service teams"
        ],
        "tags": ["dns", "infrastructure-change", "connectivity", "restart"]
    }
]
