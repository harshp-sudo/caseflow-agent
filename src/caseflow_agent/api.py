from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .backends import Backend
from .models import Review, Ticket
from .service import AgentService, Conflict, MissingThread


def create_app(database: str | Path = ".caseflow/state.sqlite", backend: Backend | None = None):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with AgentService(database, backend) as service:
            app.state.agent = service
            yield

    app = FastAPI(title="CaseFlow demo", version="0.1.0", lifespan=lifespan,
                  description="Synthetic-data portfolio demo. No authentication; bind to loopback only.")

    def call(action):
        try:
            return action()
        except MissingThread as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Conflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/health")
    def health():
        return {"status": "ok", "data": "synthetic", "backend": type(backend).__name__ if backend else "OfflineBackend"}

    @app.post("/tickets", status_code=201)
    def start(ticket: Ticket):
        return call(lambda: app.state.agent.start(ticket))

    @app.get("/tickets/{thread_id}")
    def get(thread_id: str):
        return call(lambda: app.state.agent.get(thread_id))

    @app.post("/tickets/{thread_id}/review")
    def review(thread_id: str, decision: Review):
        return call(lambda: app.state.agent.resume(thread_id, decision))

    return app

