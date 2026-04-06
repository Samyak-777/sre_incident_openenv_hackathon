from typing import Dict, Any

class RewardEngine:
    REWARD_SEVERITY = 0.15
    REWARD_CORRECT_SERVICE = 0.20
    REWARD_RUNBOOK_STEP = 0.05
    REWARD_ROOT_CAUSE = 0.25 # Implicitly scored in postmortem or escalation
    PENALTY_WRONG_ACTION = -0.05
    
    @staticmethod
    def score_severity(predicted: str, actual: str) -> float:
        if predicted and actual and predicted.upper() == actual.upper():
            return RewardEngine.REWARD_SEVERITY
        return RewardEngine.PENALTY_WRONG_ACTION
        
    @staticmethod
    def score_comms_quality(message: str, ground_truth: Dict[str, Any]) -> float:
        """Deterministic heuristic for communication quality"""
        score = 0.0
        if not message:
            return score
            
        message_lower = message.lower()
        if len(message) > 20:
            score += 0.05
            
        # Mention service or severity
        if ground_truth.get("root_cause_service", "") in message_lower or ground_truth.get("severity", "").lower() in message_lower:
            score += 0.05
            
        # Action-oriented words
        if any(w in message_lower for w in ["investigating", "mitigated", "resolved", "update", "impact"]):
            score += 0.05
            
        return min(score, 0.15)
        
    @staticmethod
    def score_postmortem(fields: Dict[str, str], ground_truth: Dict[str, Any]) -> float:
        """Deterministic heuristic scoring for RCA document"""
        score = 0.0
        if not fields:
            return score
            
        field_str = " ".join(fields.values()).lower()
        
        # Completeness
        if len(fields) >= 2:
            score += 0.05
            
        if "action_items" in fields or any("action" in k.lower() for k in fields.keys()):
            score += 0.05
            
        # Root cause identification
        rc_service = ground_truth.get("root_cause_service", "").lower()
        if rc_service and rc_service in field_str:
            score += 0.10
            
        return min(score, 0.20)
