"""
Grader for task_medium: Shipping API database lock contention (P1).
Scores agent's performance on a multi-service dependency investigation.
"""


def grade(trajectory: list) -> float:
    """
    Grade the agent's performance on the medium task.

    Args:
        trajectory: List of dicts with 'action' and 'observation' keys.

    Returns:
        Score strictly in (0.1, 0.99)
    """
    if not trajectory:
        return 0.1

    score = 0.0
    max_possible = 0.0

    for step in trajectory:
        obs = step.get("observation", {})
        reward = obs.get("reward", 0.0)
        if isinstance(reward, (int, float)):
            score += float(reward)
        max_possible += 0.06

    if max_possible > 0:
        normalized = score / max(max_possible, 1.0)
    else:
        normalized = 0.1

    return max(0.1, min(0.99, normalized))
