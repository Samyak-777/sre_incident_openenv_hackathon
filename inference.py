import os
import json
import requests
import time
from openai import OpenAI

# Mandatory Hackathon Variables
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
HF_TOKEN = os.getenv("HF_TOKEN")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

# Scoring Thresholds (Customizable)
SUCCESS_SCORE_THRESHOLD = 0.5
MAX_STEPS = 15

# Maximum total reward the environment can give (for normalization).
# This is the theoretical max: severity(0.17) + service(0.22) + 3 runbook(0.07*3)
# + escalation(0.27) + comms(0.17) + postmortem(0.22) + per-step base(0.02*15)
# = 1.54 + 0.30 = ~1.84. Round up to 2.0 for safety.
MAX_TOTAL_REWARD = 2.0

SYSTEM_PROMPT = """
You are an expert Site Reliability Engineer (SRE) on-call.
You must triage incidents, investigate logs, execute runbooks, and file postmortems.
Available action_types: classify_severity, query_logs, fetch_runbook, execute_runbook_step, escalate, draft_status_update, write_postmortem.
You MUST respond with a JSON object representing the action.
Example: {"action_type": "query_logs", "service": "auth-service"}
"""

def log_start(task_id: str):
    """[START] Mandatory logging"""
    print(f"[START] {json.dumps({'task_id': task_id, 'model': MODEL_NAME, 'timestamp': time.time()})}", flush=True)

def log_step(step, action, reward, done, error=None):
    """[STEP] Mandatory logging - Strictly matching sample field names"""
    log_data = {
        "step": step,
        "action": action,
        "reward": reward,
        "done": done,
        "error": error
    }
    print(f"[STEP] {json.dumps(log_data)}", flush=True)

def log_end(task_id, success, steps, score, rewards):
    """[END] Mandatory logging - Strictly matching sample field names"""
    log_data = {
        "task_id": task_id,
        "success": success,
        "steps": steps,
        "score": round(score, 4),
        "rewards": [round(r, 4) for r in rewards]
    }
    print(f"[END] {json.dumps(log_data)}", flush=True)

def clamp_score(value):
    """Clamp a value to strictly (0, 1) - never 0.0, never 1.0."""
    return min(max(float(value), 0.01), 0.99)

def run_inference():
    # Strictly using OpenAI client as required by hackathon rules
    llm = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    
    tasks = ["task_easy", "task_medium", "task_hard"]
    
    for task_id in tasks:
        log_start(task_id)
        
        try:
            response = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id})
            response.raise_for_status()
            reset_payload = response.json()
            obs = reset_payload.get("observation", reset_payload)
        except Exception as e:
            # Strictly (0, 1) range: log 0.01 on failure instead of 0.0
            log_end(task_id=task_id, success=False, steps=0, score=0.01, rewards=[0.01])
            continue
            
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        raw_rewards = []
        steps_taken = 0
        success = False
        
        for step in range(1, MAX_STEPS + 1):
            steps_taken = step
            # LLM Prompting
            obs_str = json.dumps(obs)
            messages.append({"role": "user", "content": f"Current Observation: {obs_str}"})
            
            try:
                chat_res = llm.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                action_json = chat_res.choices[0].message.content
                action_dict = json.loads(action_json)
                error = None
            except Exception as e:
                action_dict = {"action_type": "write_postmortem", "postmortem_fields": {"error": f"LLM Error: {str(e)}"}}
                action_json = json.dumps(action_dict)
                error = str(e)
                
            # Environment Interaction
            # IMPORTANT: OpenEnv StepRequest wraps action in {"action": {...}}
            try:
                res = requests.post(f"{ENV_URL}/step", json={"action": action_dict})
                res.raise_for_status()
                result_payload = res.json()
            except Exception as e:
                log_step(step, action_dict, 0.01, True, error=f"Env Failure: {str(e)}")
                raw_rewards.append(0.01)
                break
                
            obs = result_payload.get("observation", {})
            reward = result_payload.get("reward", 0.01)
            done = result_payload.get("done", False)
            
            # Safety: ensure individual reward is a valid number (never None, 0.0, or 1.0)
            if reward is None or not isinstance(reward, (int, float)):
                reward = 0.01
            
            raw_rewards.append(float(reward))
            log_step(step=step, action=action_dict, reward=float(reward), done=done, error=error)
            
            messages.append({"role": "assistant", "content": action_json})
            if done:
                break
        
        # ================================================================
        # FINAL SCORE CALCULATION
        # The validator checks: 0 < score < 1 (strictly)
        # Normalize rewards so the score is always in (0, 1)
        # ================================================================
        if len(raw_rewards) == 0:
            score = 0.01
            normalized_rewards = [0.01]
        else:
            raw_sum = sum(raw_rewards)
            # Normalize: divide by MAX_TOTAL_REWARD to ensure sum is < 1.0
            score = raw_sum / MAX_TOTAL_REWARD
            # Clamp to strict (0, 1) 
            score = clamp_score(score)
            # Normalize individual rewards for the log
            normalized_rewards = [clamp_score(r / MAX_TOTAL_REWARD) for r in raw_rewards]
        
        success = score >= SUCCESS_SCORE_THRESHOLD
        
        log_end(task_id=task_id, success=success, steps=steps_taken, score=score, rewards=normalized_rewards)

if __name__ == "__main__":
    run_inference()
