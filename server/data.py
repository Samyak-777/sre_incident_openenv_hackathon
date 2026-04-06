# Synthetic incident data and runbook registry

EASY_INCIDENT = {
    "alert": {
        "alert_id": "ALT-1001",
        "severity": "P2",
        "service": "auth-service",
        "title": "High Latency in Auth Service",
        "description": "auth-service p99 latency crossed 500ms threshold over 5m window",
        "triggered_at": "2026-04-06T10:15:00Z",
        "threshold": "500ms",
        "current_value": "850ms"
    },
    "dependency_graph": {
        "auth-service": {"upstream": ["api-gateway"], "downstream": ["user-db", "redis-cache"]},
        "api-gateway": {"upstream": ["external-lb"], "downstream": ["auth-service", "checkout-service"]},
        "user-db": {"upstream": ["auth-service"], "downstream": []},
        "redis-cache": {"upstream": ["auth-service"], "downstream": []}
    },
    "metrics": {
        "auth-service": {
            "cpu_pct": [30.0, 32.5, 31.0, 85.0, 92.0],
            "memory_pct": [40.0, 40.1, 40.2, 40.2, 40.3],
            "p99_latency_ms": [45.0, 42.0, 48.0, 600.0, 850.0],
            "error_rate_pct": [0.01, 0.0, 0.05, 0.1, 0.2],
            "queue_depth": [0, 0, 0, 150, 400]
        },
        "redis-cache": {
            "cpu_pct": [10.0, 10.0, 10.0, 99.9, 100.0],
            "memory_pct": [80.0, 85.0, 95.0, 99.0, 100.0],
            "p99_latency_ms": [1.0, 1.2, 5.0, 2000.0, 5000.0],
            "error_rate_pct": [0.0, 0.0, 0.0, 50.0, 100.0],
            "queue_depth": [0, 0, 0, 0, 0]
        }
    },
    "log_stream": [
        {"timestamp": "10:14:00Z", "level": "INFO", "service": "auth-service", "message": "Handling token request"},
        {"timestamp": "10:15:01Z", "level": "WARN", "service": "auth-service", "message": "Redis cache connection timeout, falling back to DB"},
        {"timestamp": "10:15:05Z", "level": "ERROR", "service": "redis-cache", "message": "OOM command not allowed when used memory > 'maxmemory'"},
        {"timestamp": "10:15:20Z", "level": "ERROR", "service": "auth-service", "message": "DB connection pool exhausted"}
    ],
    "ground_truth": {
        "root_cause_service": "redis-cache",
        "severity": "P2",
        "runbook_id": "RB-REDIS-OOM",
        "required_steps": ["step_1_scale_memory", "step_2_restart_redis"]
    }
}

MEDIUM_INCIDENT = {
    "alert": {
        "alert_id": "ALT-2042",
        "severity": "P1",
        "service": "payment-api",
        "title": "Payment API Error Rate Spike",
        "description": "payment-api 5xx error rate > 5%",
        "triggered_at": "2026-04-06T14:30:00Z",
        "threshold": "5%",
        "current_value": "18.5%"
    },
    "dependency_graph": {
        "payment-api": {"upstream": ["checkout-service"], "downstream": ["fraud-service", "shipping-api", "stripe-gateway"]},
        "shipping-api": {"upstream": ["payment-api", "inventory-service"], "downstream": ["logistics-db"]},
        "stripe-gateway": {"upstream": ["payment-api"], "downstream": []}
    },
    "metrics": {
        "payment-api": {
            "cpu_pct": [20.0, 21.0, 20.5, 22.0, 21.5],
            "memory_pct": [50.0, 50.0, 50.5, 51.0, 50.8],
            "p99_latency_ms": [100.0, 110.0, 3050.0, 3100.0, 3080.0],
            "error_rate_pct": [0.1, 0.2, 5.5, 12.0, 18.5],
            "queue_depth": [0, 5, 500, 1200, 2500]
        },
        "shipping-api": {
            "cpu_pct": [15.0, 16.0, 95.0, 98.0, 100.0],
            "memory_pct": [40.0, 42.0, 45.0, 46.0, 47.0],
            "p99_latency_ms": [50.0, 55.0, 5000.0, 5000.0, 5000.0],
            "error_rate_pct": [0.0, 0.0, 2.0, 50.0, 85.0],
            "queue_depth": [0, 0, 100, 500, 1000]
        }
    },
    "log_stream": [
        {"timestamp": "14:28:00Z", "level": "INFO", "service": "payment-api", "message": "Processing transaction TX-991"},
        {"timestamp": "14:29:10Z", "level": "ERROR", "service": "payment-api", "message": "Timeout communicating with shipping-api. Transaction aborted."},
        {"timestamp": "14:29:15Z", "level": "ERROR", "service": "shipping-api", "message": "Failed to acquire lock on logistics-db"},
        {"timestamp": "14:30:05Z", "level": "WARN", "service": "payment-api", "message": "Circuit breaker OPEN for shipping-api"}
    ],
    "ground_truth": {
        "root_cause_service": "shipping-api",
        "severity": "P1",
        "runbook_id": "RB-SHIP-LOCK",
        "required_steps": ["step_1_kill_long_queries", "step_2_scale_replicas", "step_3_reset_circuit_breaker"]
    }
}

HARD_INCIDENT = {
    "alert": {
        "alert_id": "ALT-9099",
        "severity": "P1",
        "service": "checkout-service",
        "title": "Catastrophic Failure in Checkout",
        "description": "checkout-service CPU at 100%, queue depth > 10000, latency flatlined",
        "triggered_at": "2026-04-06T23:50:00Z",
        "threshold": "queue=1000",
        "current_value": "queue=15420"
    },
    "dependency_graph": {
        "api-gateway": {"upstream": ["public-lb"], "downstream": ["checkout-service"]},
        "checkout-service": {"upstream": ["api-gateway"], "downstream": ["inventory-service", "promo-service"]}
    },
    "metrics": {
        "checkout-service": {
            "cpu_pct": [40.0, 45.0, 100.0, 100.0, 100.0],
            "memory_pct": [60.0, 62.0, 65.0, 65.0, 65.0],
            "p99_latency_ms": [80.0, 85.0, 30000.0, 30000.0, 30000.0],
            "error_rate_pct": [0.0, 0.0, 99.9, 100.0, 100.0],
            "queue_depth": [10, 15, 8000, 12000, 15420]
        }
    },
    "log_stream": [
        {"timestamp": "23:48:00Z", "level": "INFO", "service": "checkout-service", "message": "Received payload size: 2kb"},
        {"timestamp": "23:49:05Z", "level": "WARN", "service": "checkout-service", "message": "Payload regex parsing took > 5000ms. Potential ReDoS."},
        {"timestamp": "23:49:30Z", "level": "ERROR", "service": "checkout-service", "message": "Worker thread blocked for 30s. Event loop stalled."},
        {"timestamp": "23:50:00Z", "level": "FATAL", "service": "checkout-service", "message": "Healthcheck failed. Instance terminating."}
    ],
    "ground_truth": {
        "root_cause_service": "checkout-service",
        "severity": "P1",
        "runbook_id": "NONE",
        "required_escalation": "sec-ops",
        "required_steps": [] # ReDoS requires code rollback, no standard runbook
    }
}

INCIDENTS = {
    "task_easy": EASY_INCIDENT,
    "task_medium": MEDIUM_INCIDENT,
    "task_hard": HARD_INCIDENT
}

RUNBOOKS = {
    "RB-REDIS-OOM": {
        "runbook_id": "RB-REDIS-OOM",
        "service": "redis-cache",
        "issue_type": "Out of Memory",
        "title": "Handling Redis OOM Events",
        "content": "When Redis hits maxmemory, evictions may fail or cause timeouts.\nSteps:\n1. Execute step_1_scale_memory to increase maxmemory by 20%.\n2. Execute step_2_restart_redis to apply config and flush temporary buffers.",
        "valid_steps": ["step_1_scale_memory", "step_2_restart_redis"]
    },
    "RB-AUTH-GENERIC": {
        "runbook_id": "RB-AUTH-GENERIC",
        "service": "auth-service",
        "issue_type": "High Latency",
        "title": "Auth Service Generic Troubleshooting",
        "content": "If auth-service is slow, scale up pods.\nSteps:\n1. Execute step_1_scale_auth to add 5 pods.",
        "valid_steps": ["step_1_scale_auth"]
    },
    "RB-SHIP-LOCK": {
        "runbook_id": "RB-SHIP-LOCK",
        "service": "shipping-api",
        "issue_type": "Database Lock Contention",
        "title": "Shipping API DB Lock Recovery",
        "content": "Shipping DB locks can cascade to payments. Clear locks and reset circuit breakers.\nSteps:\n1. Execute step_1_kill_long_queries on logistics-db.\n2. Execute step_2_scale_replicas for read offloading.\n3. Execute step_3_reset_circuit_breaker on payment-api.",
        "valid_steps": ["step_1_kill_long_queries", "step_2_scale_replicas", "step_3_reset_circuit_breaker"]
    },
    "RB-PAYMENT-RESTART": {
        "runbook_id": "RB-PAYMENT-RESTART",
        "service": "payment-api",
        "issue_type": "High Error Rate",
        "title": "Payment API Restart",
        "content": "If errors spike, restarting might clear bad state.\nSteps:\n1. Execute step_1_rolling_restart on payment-api.",
        "valid_steps": ["step_1_rolling_restart"]
    }
}

RUNBOOK_METADATA = [
    {
        "runbook_id": v["runbook_id"],
        "service": v["service"],
        "issue_type": v["issue_type"],
        "title": v["title"]
    } for v in RUNBOOKS.values()
]
