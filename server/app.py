import uvicorn
from fastapi import FastAPI
from openenv.core.env_server import create_fastapi_app
from server.environment import SREIncidentEnvironment
from server.models import SREAction, SREObservation

# Let OpenEnv core handle the endpoint generation
# Note: create_fastapi_app expects (1) Env Factory, (2) Action Class, (3) Observation Class.
# SREState is managed internal to the environment and not required by create_fastapi_app.
app = create_fastapi_app(SREIncidentEnvironment, SREAction, SREObservation)

def main():
    """
    Entrypoint function for 'uv run server' as expected by OpenEnv.
    """
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)

if __name__ == "__main__":
    main()
