from typing import Optional
from openenv.core.env_server import Environment
from server.models import SREAction, SREObservation, SREState, IncidentAlert, LogEntry, MetricSnapshot, RunbookMetadata
from server.data import INCIDENTS, RUNBOOKS, RUNBOOK_METADATA
from server.rewards import RewardEngine

# ============================================================
# MODULE-LEVEL STATE PERSISTENCE
# The OpenEnv HTTP framework creates a NEW environment instance
# for every /reset and /step HTTP call. We use a module-level
# dictionary to persist the episode state across calls within
# the same process. This enables proper cumulative reward
# tracking, anti-loop checks, and episode continuity.
# ============================================================
_SHARED_STATE: Optional[SREState] = None


class SREIncidentEnvironment(Environment[SREAction, SREObservation, SREState]):
    """
    Core implementation of the SRE Incident Response OpenEnv environment.
    Handles episode lifecycle, action execution, and deterministic reward shaping.
    
    All per-step rewards are in (0, 1) and the CUMULATIVE episode reward
    is tracked and capped at 0.95 to ensure it never reaches 1.0.
    """
    
    MAX_STEPS = 15
    # Max cumulative reward per episode — strictly < 1.0
    MAX_CUMULATIVE = 0.95
    
    def __init__(self):
        super().__init__()
        self._state: Optional[SREState] = None
        
    def _ensure_state(self) -> None:
        """Auto-initialize state from shared global or fresh reset."""
        global _SHARED_STATE
        if _SHARED_STATE is not None:
            self._state = _SHARED_STATE
        elif self._state is None:
            self.reset("task_easy")
        
    def reset(self, task_id: str = "task_easy") -> SREObservation:
        """Called to start a new episode for a given task."""
        global _SHARED_STATE
        
        if task_id not in INCIDENTS:
            task_id = "task_easy"  # Fallback instead of crash
            
        incident = INCIDENTS[task_id]
        
        # Initialize internal episode state
        self._state = SREState(
            task_id=task_id,
            current_service=incident["alert"]["service"],
            cumulative_reward=0.0
        )
        
        # Persist to shared global
        _SHARED_STATE = self._state
        
        # Initial Observation
        obs = SREObservation(
            task_id=task_id,
            alert=IncidentAlert(**incident["alert"]),
            metrics={s: MetricSnapshot(**m) for s, m in incident["metrics"].items()},
            dependency_graph=incident["dependency_graph"],
            available_runbooks=[RunbookMetadata(**rm) for rm in RUNBOOK_METADATA],
            action_feedback="You have been paged. Investigate the alert.",
            reward=0.01  # Strictly > 0.0
        )
        return obs

    def step(self, action: SREAction) -> SREObservation:
        """Processes agent action and returns next observation with reward."""
        global _SHARED_STATE
        
        # Retrieve persisted state
        self._ensure_state()
        
        self._state.step_count += 1
        raw_reward = 0.0
        done = False
        action_feedback = ""
        
        incident = INCIDENTS[self._state.task_id]
        gt = incident["ground_truth"]
        
        # Anti-loop check
        action_sig = f"{action.action_type}|{action.service}|{action.step_id}|{action.level}"
        if action_sig in self._state.action_history:
            raw_reward += RewardEngine.PENALTY_WRONG_ACTION
            action_feedback = f"Penalty: Repeated action '{action.action_type}'"
        self._state.action_history.append(action_sig)
        
        # Build next observation (static data from incident)
        obs = SREObservation(
            task_id=self._state.task_id,
            alert=IncidentAlert(**incident["alert"]),
            metrics={s: MetricSnapshot(**m) for s, m in incident["metrics"].items()},
            dependency_graph=incident["dependency_graph"],
            available_runbooks=[RunbookMetadata(**rm) for rm in RUNBOOK_METADATA]
        )
        
        # ---- Action dispatch ----
        if action.action_type == "classify_severity":
            r = RewardEngine.score_severity(action.level, gt["severity"])
            raw_reward += r
            self._state.classified_severity = action.level
            action_feedback = f"Severity classified as {action.level}."
            
        elif action.action_type == "query_logs":
            logs = incident["log_stream"]
            if action.service:
                logs = [l for l in logs if l["service"] == action.service]
            obs.log_stream = [LogEntry(**l) for l in logs]
            action_feedback = f"Retrieved {len(logs)} logs."
            
        elif action.action_type == "fetch_runbook":
            rb = next((r for r in RUNBOOKS.values() if r["service"] == action.service and r["issue_type"] == action.issue_type), None)
            if rb:
                obs.fetched_runbook_content = rb["content"]
                action_feedback = f"Runbook {rb['runbook_id']} fetched."
            else:
                action_feedback = "No matching runbook found."
                
        elif action.action_type == "execute_runbook_step":
            if action.step_id in gt["required_steps"] and action.step_id not in self._state.runbook_steps_completed:
                raw_reward += RewardEngine.REWARD_RUNBOOK_STEP
                self._state.runbook_steps_completed.append(action.step_id)
                action_feedback = f"Successfully executed {action.step_id}"
            else:
                raw_reward += RewardEngine.PENALTY_WRONG_ACTION
                action_feedback = f"Step {action.step_id} executed, but was incorrect or out of sequence."
                
        elif action.action_type == "escalate":
            if gt.get("required_escalation") == action.team:
                raw_reward += RewardEngine.REWARD_ROOT_CAUSE
                self._state.escalated_team = action.team
                action_feedback = f"Successfully escalated to {action.team}."
            else:
                raw_reward += RewardEngine.PENALTY_WRONG_ACTION
                action_feedback = f"Escalated to {action.team}, but they rejected the page as unactionable."
                
        elif action.action_type == "draft_status_update":
            r = RewardEngine.score_comms_quality(action.message, gt)
            raw_reward += r
            self._state.stakeholder_updates.append(action.message or "")
            action_feedback = "Status update published."
            
        elif action.action_type == "write_postmortem":
            r = RewardEngine.score_postmortem(action.postmortem_fields, gt)
            raw_reward += r
            self._state.postmortem_submitted = action.postmortem_fields
            action_feedback = "Postmortem submitted. Episode complete."
            done = True
            self._state.resolved = True
            
        else:
            raw_reward += RewardEngine.PENALTY_WRONG_ACTION
            action_feedback = f"Unknown action: {action.action_type}"
            
        # Check timeout
        if self._state.step_count >= self.MAX_STEPS:
            done = True
            action_feedback = "On-call shift ended (max steps reached). Episode terminated."
        
        # ============================================================
        # REWARD CLAMPING: Strictly (0, 1)
        # 1. Clamp per-step reward: floor 0.01, ceiling 0.06
        #    (0.06 * 15 steps = 0.90 max, safely < 1.0)
        # 2. Track cumulative and cap at MAX_CUMULATIVE (0.95)
        # ============================================================
        
        # Per-step: clamp to [0.01, 0.06]
        # This ensures even 15 maximum-reward steps sum to 0.90
        step_reward = min(max(raw_reward + 0.01, 0.01), 0.06)
        
        # Track cumulative
        new_cumulative = self._state.cumulative_reward + step_reward
        if new_cumulative >= self.MAX_CUMULATIVE:
            # Cap the step reward so cumulative stays under MAX_CUMULATIVE
            step_reward = max(self.MAX_CUMULATIVE - self._state.cumulative_reward - 0.001, 0.01)
            new_cumulative = self._state.cumulative_reward + step_reward
        
        self._state.cumulative_reward = new_cumulative
        
        # Persist state
        _SHARED_STATE = self._state
        
        # Final safety: ensure step_reward is strictly (0, 1)
        step_reward = min(max(step_reward, 0.01), 0.99)
        
        obs.action_feedback = action_feedback
        obs.done = done
        obs.reward = step_reward
        
        # If episode ends, clear shared state for next episode
        if done:
            _SHARED_STATE = None
        
        return obs
        
    def state(self) -> SREState:
        """Returns the internal state (used by OpenEnv server)."""
        self._ensure_state()
        return self._state
