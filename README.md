---
title: SRE Incident Response OpenEnv
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
tags: [openenv, reinforcement-learning, sre, agentic-ai]
---

# SRE Incident Response Environment

A production-grade [OpenEnv](https://github.com/openenv-ai/openenv) environment for the Meta PyTorch Hackathon (Round 1).

## 🚀 Motivation & Real-World Utility
Site Reliability Engineers (SREs) are the backbone of modern tech companies, but training them is expensive and reactive. This environment models a genuine, high-stakes SRE on-call workflow: **Alert → Investigation → Remediation → Documentation**.
Unlike toy environments, this requires an agent to:
1.  **Parse Multi-modal Telemetry**: Correlate structured JSON logs with metric time-series (CPU, latency, etc.).
2.  **Follow Runbooks**: Execute deterministic procedures from a markdown registry.
3.  **Handle Non-Standard Outages**: Identify when a runbook fails and escalate to the correct specialized team (e.g., Security for DDoS).

## 🧠 Environment Design
### Observation Space
The agent receives a rich `SREObservation` containing:
-   **Alert Payload**: Severity, triggered threshold, and service identity.
-   **Log Stream**: Recent JSON log lines filtered by service.
-   **Metrics Dashboard**: `cpu_pct`, `memory_pct`, `p99_latency_ms`, `error_rate`, `queue_depth`.
-   **Dependency Graph**: Upstream/Downstream service mappings.
-   **Runbook Registry**: Metadata for all available remediation procedures.

### Action Space
The agent can perform 7 distinct `SREAction` types:
1.  `classify_severity`: Initial impact assessment.
2.  `query_logs`: Retrieve targeted logs for a service.
3.  `fetch_runbook`: Read a specific runbook document.
4.  `execute_runbook_step`: Execute a step by ID.
5.  `escalate`: Contact a human expert if the issue is novel.
6.  `draft_status_update`: Communicate with stakeholders.
7.  `write_postmortem`: Finalize the Root Cause Analysis (RCA).

## 🎯 Task Success & Graders
We provide three deterministic tasks:
-   **Easy (`task_easy`)**: `auth-service` degradation. Remediation via standard scaling runbook.
-   **Medium (`task_medium`)**: Cascading failure in `payment-api` due to database locks. Requires multi-service investigation.
-   **Hard (`task_hard`)**: Zero-day `checkout-service` ReDoS attack. Standard runbooks fail; agent must identify the attack pattern and escalate to the Security team.

Graders score performance on a **0.0 to 1.0** scale based on:
-   Accuracy of severity classification.
-   Identification of the correct root-cause service.
-   Adherence to required remediation steps.
-   Quality and completeness of the final postmortem.

## 🛠 Setup and Usage
### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn server.app:app --port 7860
```

### Run Baseline Inference
```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export HF_TOKEN="your_key_here"

python inference.py
```

### Docker
```bash
docker build -t sre-openenv .
docker run -p 7860:7860 sre-openenv
```
