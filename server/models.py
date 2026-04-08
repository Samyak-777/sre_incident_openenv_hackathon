from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from openenv.core.env_server import Action, Observation, State

class IncidentAlert(BaseModel):
    alert_id: str
    severity: str
    service: str
    title: str
    description: str
    triggered_at: str
    threshold: str
    current_value: str

class LogEntry(BaseModel):
    timestamp: str
    level: str
    service: str
    message: str

class MetricSnapshot(BaseModel):
    cpu_pct: List[float]
    memory_pct: List[float]
    p99_latency_ms: List[float]
    error_rate_pct: List[float]
    queue_depth: List[int]

class RunbookMetadata(BaseModel):
    runbook_id: str
    service: str
    issue_type: str
    title: str

class SREObservation(Observation):
    """
    Observation payload the agent receives.
    Base class provides 'done' (bool) and 'reward' (Optional[float]).
    """
    alert: Optional[IncidentAlert] = None
    log_stream: List[LogEntry] = Field(default_factory=list)
    metrics: Dict[str, MetricSnapshot] = Field(default_factory=dict)
    dependency_graph: Dict[str, Dict[str, List[str]]] = Field(default_factory=dict)
    available_runbooks: List[RunbookMetadata] = Field(default_factory=list)
    reward: float = 0.01
    
    # Context-dependent fields returned after specific actions
    fetched_runbook_content: Optional[str] = None
    action_feedback: Optional[str] = None
    postmortem_history: List[str] = Field(default_factory=list)
    task_id: str = ""

class SREAction(Action):
    """
    The action the agent executes. 
    action_type can be: classify_severity, query_logs, fetch_runbook, 
    execute_runbook_step, escalate, draft_status_update, write_postmortem
    """
    action_type: str = Field(..., description="Action to perform (e.g., classify_severity, query_logs)")
    
    # Optional parameters based on action_type
    level: Optional[str] = Field(None, description="P1/P2/P3/P4 for classify_severity")
    service: Optional[str] = Field(None, description="Target service for query_logs or fetch_runbook")
    time_range: Optional[str] = Field(None, description="Time range for query_logs")
    filter_query: Optional[str] = Field(None, description="Filter string for query_logs")
    issue_type: Optional[str] = Field(None, description="Issue type for fetch_runbook")
    step_id: Optional[str] = Field(None, description="Runbook step ID to execute for execute_runbook_step")
    team: Optional[str] = Field(None, description="Team to escalate to")
    audience: Optional[str] = Field(None, description="internal or external for draft_status_update")
    message: Optional[str] = Field(None, description="Message content for escalate or draft_status_update")
    postmortem_fields: Optional[Dict[str, str]] = Field(None, description="RCA document fields for write_postmortem")

class SREState(State):
    """
    Internal environment episode tracking.
    Base class provides 'episode_id' and 'step_count'.
    """
    task_id: str = ""
    current_service: str = ""
    classified_severity: Optional[str] = None
    resolved: bool = False
    runbook_steps_completed: List[str] = Field(default_factory=list)
    escalated_team: Optional[str] = None
    stakeholder_updates: List[str] = Field(default_factory=list)
    postmortem_submitted: Optional[Dict[str, str]] = None
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    
    # To prevent loops
    action_history: List[str] = Field(default_factory=list)
