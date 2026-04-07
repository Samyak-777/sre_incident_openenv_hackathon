from typing import Optional
from openenv.core.env_server import Environment
from server.models import SREAction, SREObservation, SREState, IncidentAlert, LogEntry, MetricSnapshot, RunbookMetadata
from server.data import INCIDENTS, RUNBOOKS, RUNBOOK_METADATA
from server.rewards import RewardEngine

class SREIncidentEnvironment(Environment[SREAction, SREObservation, SREState]):
    """
    Core implementation of the SRE Incident Response OpenEnv environment.
    Handles episode lifecycle, action execution, and deterministic reward shaping.
    """
    
    def __init__(self):
        super().__init__()
        self._max_steps = 15
        
    def reset(self, task_id: str = "task_easy") -> SREObservation:
        """Called to start a new episode for a given task"""
        if task_id not in INCIDENTS:
            raise ValueError(f"Unknown task_id: {task_id}")
            
        incident = INCIDENTS[task_id]
        
        # Initialize internal episode state
        self._state = SREState(
            task_id=task_id,
            current_service=incident["alert"]["service"]
        )
        
        # Initial Observation - the "page" the agent receives
        obs = SREObservation(
            task_id=task_id,
            alert=IncidentAlert(**incident["alert"]),
            # Initial metrics for all services visible on dashboard
            metrics={s: MetricSnapshot(**m) for s, m in incident["metrics"].items()},
            dependency_graph=incident["dependency_graph"],
            available_runbooks=[RunbookMetadata(**rm) for rm in RUNBOOK_METADATA],
            action_feedback="You have been paged. Investigate the alert."
        )
        return obs

    def step(self, action: SREAction) -> SREObservation:
        """Processes agent action and returns next observation and reward"""
        self._state.step_count += 1
        reward = 0.0
        done = False
        action_feedback = ""
        
        incident = INCIDENTS[self._state.task_id]
        gt = incident["ground_truth"]
        
        # Anti-loop check
        action_sig = f"{action.action_type}_{action.service}_{action.step_id}_{action.level}"
        if action_sig in self._state.action_history:
            reward += RewardEngine.PENALTY_WRONG_ACTION
            action_feedback = f"Penalty: Repeated action '{action.action_type}'"
        self._state.action_history.append(action_sig)
        
        # Start building next observation (persisting static data)
        obs = SREObservation(
            task_id=self._state.task_id,
            alert=IncidentAlert(**incident["alert"]),
            metrics={s: MetricSnapshot(**m) for s, m in incident["metrics"].items()},
            dependency_graph=incident["dependency_graph"],
            available_runbooks=[RunbookMetadata(**rm) for rm in RUNBOOK_METADATA]
        )
        
        # Action Switch
        if action.action_type == "classify_severity":
            r = RewardEngine.score_severity(action.level, gt["severity"])
            reward += r
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
                r = RewardEngine.REWARD_RUNBOOK_STEP
                self._state.runbook_steps_completed.append(action.step_id)
                reward += r
                action_feedback = f"Successfully executed {action.step_id}"
            else:
                reward += RewardEngine.PENALTY_WRONG_ACTION
                action_feedback = f"Step {action.step_id} executed, but was incorrect or out of sequence."
                
        elif action.action_type == "escalate":
            if gt.get("required_escalation") == action.team:
                reward += RewardEngine.REWARD_ROOT_CAUSE
                self._state.escalated_team = action.team
                action_feedback = f"Successfully escalated to {action.team}."
            else:
                reward += RewardEngine.PENALTY_WRONG_ACTION
                action_feedback = f"Escalated to {action.team}, but they rejected the page as unactionable."
                
        elif action.action_type == "draft_status_update":
            r = RewardEngine.score_comms_quality(action.message, gt)
            reward += r
            self._state.stakeholder_updates.append(action.message)
            action_feedback = "Status update published."
            
        elif action.action_type == "write_postmortem":
            r = RewardEngine.score_postmortem(action.postmortem_fields, gt)
            reward += r
            self._state.postmortem_submitted = action.postmortem_fields
            action_feedback = "Postmortem submitted. Episode complete."
            done = True
            self._state.resolved = True
            
        else:
            reward += RewardEngine.PENALTY_WRONG_ACTION
            action_feedback = f"Unknown action: {action.action_type}"
            
        # Check timeout
        if self._state.step_count >= self._max_steps:
            done = True
            action_feedback = "On-call shift ended (max steps reached). Episode terminated."
        
        # Strictly (0, 1) range enforcement
        # Initial base reward of 0.01 added on first step
        actual_step_reward = reward
        if self._state.step_count == 1:
            actual_step_reward += 0.01 # Base participation reward
            
        # Cumulative safety - ensure total never exceeds 0.99
        new_total = self._state.cumulative_reward + actual_step_reward
        if new_total >= 1.0:
            actual_step_reward = 0.99 - self._state.cumulative_reward
            self._state.cumulative_reward = 0.99
        elif new_total <= 0.0:
            # Although penalties exist, we never drop below a tiny positive floor 
            actual_step_reward = 0.001 - self._state.cumulative_reward
            self._state.cumulative_reward = 0.001
        else:
            self._state.cumulative_reward = new_total

        obs.action_feedback = action_feedback
        obs.done = done
        obs.reward = actual_step_reward 
        
        return obs
        
    def state(self) -> SREState:
        """Returns the internal state (used by OpenEnv server)"""
        return self._state
