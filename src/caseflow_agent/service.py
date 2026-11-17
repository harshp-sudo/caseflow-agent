import re
import sqlite3
import threading
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from .backends import Backend
from .graph import build_graph
from .models import Review, Ticket


class MissingThread(ValueError):
    pass


class Conflict(ValueError):
    pass


class AgentService:
    """One process, one serialized SQLite connection. Not a multi-worker deployment."""

    def __init__(self, database: str | Path = ".caseflow/state.sqlite", backend: Backend | None = None):
        database = Path(database)
        database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(database), check_same_thread=False)
        self.saver = SqliteSaver(self.connection)
        self.graph = build_graph(self.saver, backend)
        self.lock = threading.RLock()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @staticmethod
    def config(thread_id: str) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", thread_id):
            raise ValueError("Thread id must be 1-80 letters, digits, underscores or hyphens.")
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}

    def start(self, ticket: Ticket, thread_id: str | None = None) -> dict:
        thread_id = thread_id or str(uuid4())
        config = self.config(thread_id)
        with self.lock:
            if self.graph.get_state(config).values:
                raise Conflict("Thread already exists; inspect or resume it instead of overwriting it.")
            self.graph.invoke(ticket.model_dump(), config)
            return self.get(thread_id)

    def get(self, thread_id: str) -> dict:
        with self.lock:
            snapshot = self.graph.get_state(self.config(thread_id))
            if not snapshot.values:
                raise MissingThread("Thread not found.")
            pending = [item.value for task in snapshot.tasks for item in task.interrupts]
            return {"thread_id": thread_id, **snapshot.values,
                    "status": "needs_review" if pending else snapshot.values.get("status", "drafting"),
                    "pending_review": pending}

    def resume(self, thread_id: str, decision: Review) -> dict:
        with self.lock:
            state = self.get(thread_id)
            if not state["pending_review"]:
                raise Conflict("No pending review; a completed decision cannot be replayed.")
            self.graph.invoke(Command(resume=decision.model_dump()), self.config(thread_id))
            return self.get(thread_id)

