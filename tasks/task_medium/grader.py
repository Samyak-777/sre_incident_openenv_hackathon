"""
Grader for task_medium: Shipping API database lock contention (P1).
Scores agent's performance on a multi-service dependency investigation.
"""


def grade(trajectory: list = None, *args, **kwargs) -> float:
    """
    Grade the agent's performance on the medium task.
    Robust signature to handle any evaluator input.
    """
    try:
        score = 0.5
        trajectory = None
        
        if args and isinstance(args[0], list):
            trajectory = args[0]
        elif "trajectory" in kwargs and isinstance(kwargs["trajectory"], list):
            trajectory = kwargs["trajectory"]
        elif "history" in kwargs and isinstance(kwargs["history"], list):
            trajectory = kwargs["history"]
            
        if trajectory is not None:
            sum_score = 0.0
            max_possible = 0.0
            for step in trajectory:
                if isinstance(step, dict):
                    obs = step.get("observation", {})
                    if isinstance(obs, dict):
                        reward = obs.get("reward", 0.0)
                        if isinstance(reward, (int, float)):
                            sum_score += float(reward)
                max_possible += 0.06
            if max_possible > 0:
                score = sum_score / max(max_possible, 1.0)
                
        return max(0.001, min(float(score), 0.999))
    except Exception:
        return 0.5

