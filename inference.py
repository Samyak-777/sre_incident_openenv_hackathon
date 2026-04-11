import os
import json
import requests
import time
from openai import OpenAI

# ============================================================
# MANDATORY HACKATHON ENVIRONMENT VARIABLES
# ============================================================
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
HF_TOKEN = os.getenv("HF_TOKEN")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

MAX_STEPS = 15
ENV_NAME = "sre_incident_env"

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) on-call.
You must triage incidents, investigate logs, execute runbooks, and file postmortems.
Available action_types: classify_severity, query_logs, fetch_runbook, execute_runbook_step, escalate, draft_status_update, write_postmortem.
You MUST respond with a JSON object representing the action.
Example: {"action_type": "query_logs", "service": "auth-service"}
"""

# ============================================================
# OUTPUT FORMAT FUNCTIONS
# ============================================================

def clamp(v):
    """Clamp to strictly (0, 1) — never 0.0 or 1.0."""
    return min(max(float(v) if v is not None else 0.01, 0.01), 0.99)

def fmt_r(v):
    """Format reward to 2 decimal places, clamped."""
    return f"{clamp(v):.2f}"

def fmt_b(b):
    """Format boolean as lowercase true/false."""
    return "true" if b else "false"

def log_start(task_id):
    print(f"[START] task={task_id} env={ENV_NAME} model={MODEL_NAME}", flush=True)

def log_step(step, action_str, reward, done, error=None):
    err = str(error) if error else "null"
    print(f"[STEP] step={step} action={action_str} reward={fmt_r(reward)} done={fmt_b(done)} error={err}", flush=True)

def log_end(success, steps, rewards):
    """[END] line — EXACTLY matching guidelines format."""
    rewards_str = ",".join(fmt_r(r) for r in rewards) if rewards else fmt_r(0.01)
    print(f"[END] success={fmt_b(success)} steps={steps} rewards={rewards_str}", flush=True)


def run_inference():
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    tasks = ["task_easy", "task_medium", "task_hard"]
    
    for task_id in tasks:
        log_start(task_id)
        rewards = []
        steps_taken = 0
        
        try:
            r = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=30)
            r.raise_for_status()
            obs = r.json().get("observation", r.json())
        except Exception as e:
            log_step(1, "reset_failed", 0.01, True, error=str(e))
            rewards.append(0.01)
            log_end(success=False, steps=0, rewards=rewards)
            continue
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for step in range(1, MAX_STEPS + 1):
            steps_taken = step
            obs_text = json.dumps(obs, default=str)
            messages.append({"role": "user", "content": f"Current Observation:\n{obs_text}"})
            
            try:
                chat_res = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                action_text = chat_res.choices[0].message.content
                action_dict = json.loads(action_text)
                error = None
            except Exception as e:
                action_dict = {"action_type": "write_postmortem", "postmortem_fields": {"error": f"LLM failure: {e}"}}
                action_text = json.dumps(action_dict)
                error = str(e)
            
            try:
                res = requests.post(f"{ENV_URL}/step", json={"action": action_dict}, timeout=30)
                res.raise_for_status()
                result = res.json()
            except Exception as e:
                log_step(step, action_text, 0.01, True, error=f"env_error:{e}")
                rewards.append(0.01)
                break
            
            obs = result.get("observation", {})
            reward = result.get("reward")
            done = result.get("done", False)
            
            if reward is None or not isinstance(reward, (int, float)):
                reward = 0.01
            reward = float(reward)
            
            rewards.append(reward)
            log_step(step, action_text, reward, done, error=error)
            messages.append({"role": "assistant", "content": action_text})
            
            if done:
                break
        
        if not rewards:
            rewards = [0.01]
        
        # Compute task score: sum of rewards, clamped to (0, 1)
        task_score = clamp(sum(rewards))
        success = task_score > 0.10
        
        log_end(success=success, steps=steps_taken, rewards=rewards)


if __name__ == "__main__":
    run_inference()
