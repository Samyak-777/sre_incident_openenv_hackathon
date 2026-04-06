import uvicorn
from fastapi import FastAPI
from openenv.core.env_server import create_fastapi_app
from server.environment import SREIncidentEnvironment
from server.models import SREAction, SREObservation

# Let OpenEnv core handle the endpoint generation
app = create_fastapi_app(SREIncidentEnvironment, SREAction, SREObservation)

@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect root to /docs for better DX"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

def main():
    """
    Entrypoint function for 'uv run server' as expected by OpenEnv.
    """
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)

if __name__ == "__main__":
    main()
