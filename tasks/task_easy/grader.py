"""
Grader for task_easy: Redis OOM incident triage.
Scores agent's performance on a straightforward P2 incident.

The grade function receives the list of (action, observation) pairs
from the episode and returns a score strictly in (0, 1).
"""


def grade(trajectory: list) -> float:
    """
    Grade the agent's performance on the easy task.

    Args:
        trajectory: List of dicts with 'action' and 'observation' keys
                   from the episode.

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
        max_possible += 0.06  # Max per-step reward

    # Normalize to (0, 1) range
    if max_possible > 0:
        normalized = score / max(max_possible, 1.0)
    else:
        normalized = 0.1

    # Strict clamping: never 0.0 or 1.0
    return max(0.1, min(0.99, normalized))
