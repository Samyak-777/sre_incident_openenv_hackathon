from typing import Tuple
from openenv.core.env_client import EnvClient
from app.models import SREAction, SREObservation, SREState

class SREClient(EnvClient[SREAction, SREObservation, SREState]):
    """
    Client for the SRE Incident Response Environment.
    Implements mandatory parsing and payload serialization hooks.
    """
    
    def _step_payload(self, action: SREAction) -> dict:
        # Convert Pydantic model to dictionary payload for the WebSocket
        return action.model_dump()
        
    def _parse_result(self, result: dict) -> Tuple[SREObservation, float, bool]:
        # result typically contains {"observation": dict, "reward": float, "done": bool}
        obs_data = result.get("observation", {})
        
        obs = SREObservation(**obs_data)
        reward = result.get("reward", 0.0)
        done = result.get("done", False)
        
        return obs, reward, done
        
    def _parse_state(self, state_dict: dict) -> SREState:
        return SREState(**state_dict)
