"""
Grader for task_hard: Payment API cascading failure with multiple root causes.
Scores agent's performance on a complex multi-service incident.
"""


def grade(trajectory: list) -> float:
    """
    Grade the agent's performance on the hard task.

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
