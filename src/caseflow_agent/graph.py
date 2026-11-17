import re
import time

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .backends import Backend, OfflineBackend
from .knowledge import lookup_demo_order, search_policies
from .models import AgentState, Draft, Review

MAX_ATTEMPTS = 2
SENSITIVE = re.compile(r"\b(refund|return|reimburse\w*|cancel\w*|chargeback|reverse|transfer|withdraw\w*)\b", re.I)
INJECTION = re.compile(r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions|"
                       r"system\s+prompt|reveal\s+(secrets|passwords)|api[_ -]?key", re.I)


def event(state: AgentState, node: str, **extra) -> list[dict]:
    return [*state.get("trace", []), {"node": node, **extra}]


def classify(state: AgentState) -> dict:
    q = state["question"]
    risk = "injection" if INJECTION.search(q) else "sensitive" if SENSITIVE.search(q) else "normal"
    policies = search_policies(q, limit=1)
    return {"intent": policies[0]["id"] if policies else "unknown", "risk": risk,
            "attempts": 0, "status": "drafting", "trace": event(state, "classify", risk=risk)}


def retrieve(state: AgentState) -> dict:
    # Second pass broadens lexical retrieval by the previously selected intent.
    query = state["question"]
    if state.get("attempts", 0):
        query += " " + state.get("intent", "")
    docs = [] if state["risk"] == "injection" else search_policies(query)
    return {"evidence": docs, "order": lookup_demo_order(state.get("order_id")),
            "trace": event(state, "retrieve", documents=len(docs))}


def validate_draft(draft: Draft, evidence: list[dict], order: dict | None) -> list[str]:
    """Structural and number checks, not semantic-entailment or hallucination detection."""
    available = {d["id"] for d in evidence}
    errors = []
    if not available:
        errors.append("no_relevant_evidence")
    if not draft.citations or not set(draft.citations) <= available:
        errors.append("invalid_or_missing_citations")
    if any(f"[{c}]" not in draft.text for c in draft.citations):
        errors.append("missing_inline_citations")
    allowed_numbers = set(re.findall(r"\d+", str(evidence) + str(order)))
    if not set(re.findall(r"\d+", draft.text)) <= allowed_numbers:
        errors.append("unsupported_number")
    if re.search(r"\b(i have|we have|successfully)\s+(issued|processed|approved|transferred|cancelled)\b",
                 draft.text, re.I):
        errors.append("unsupported_action_claim")
    return errors


def build_graph(checkpointer, backend: Backend | None = None):
    backend = backend or OfflineBackend()

    def draft(state: AgentState) -> dict:
        start = time.perf_counter()
        failure = None
        if state["risk"] == "injection":
            result = Draft(text="A support specialist must review this request.", citations=[])
        else:
            try:
                result = backend.draft(state)
            except Exception as exc:
                # No raw provider errors in state: they can contain credentials or customer text.
                failure = type(exc).__name__
                result = Draft(text="A support specialist must review this request.", citations=[])
        return {"draft": result.model_dump(), "attempts": state["attempts"] + 1,
                "trace": event(state, "draft", backend_error=failure,
                               elapsed_ms=round((time.perf_counter()-start)*1000, 3))}

    def verify(state: AgentState) -> dict:
        errors = validate_draft(Draft.model_validate(state["draft"]), state["evidence"], state["order"])
        if state.get("order_id") and not state["order"]:
            errors.append("unknown_demo_order")
        return {"validation_errors": errors, "trace": event(state, "verify", errors=errors)}

    def route(state: AgentState) -> str:
        if state["risk"] == "injection":
            return "review"
        if state["validation_errors"] and state["attempts"] < MAX_ATTEMPTS:
            return "retrieve"
        if state["validation_errors"] or state["risk"] == "sensitive":
            return "review"
        return "finish"

    def review(state: AgentState) -> dict:
        # No side effect before interrupt: this node restarts on resume.
        payload = interrupt({"reason": state["risk"], "draft": state["draft"],
                             "validation_errors": state["validation_errors"],
                             "action": "Review reply only; no financial operation will occur."})
        decision = Review.model_validate(payload)
        return {"approved": decision.approve, "review_note": decision.note,
                "trace": event(state, "review", approved=decision.approve)}

    def finish(state: AgentState) -> dict:
        # Approval cannot override a failed machine check or a detected injection.
        safe = not state["validation_errors"] and state["risk"] != "injection"
        rejected = "approved" in state and not state["approved"]
        status = "escalated" if not safe or rejected else "reviewed" if state.get("approved") else "answered"
        answer = state["draft"]["text"] if safe and not rejected else (
            "This request has been escalated to a support specialist; no action was performed.")
        return {"answer": answer, "status": status, "trace": event(state, "finish", status=status)}

    graph = StateGraph(AgentState)
    for name, fn in [("classify", classify), ("retrieve", retrieve), ("draft", draft),
                     ("verify", verify), ("review", review), ("finish", finish)]:
        graph.add_node(name, fn)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "draft")
    graph.add_edge("draft", "verify")
    graph.add_conditional_edges("verify", route, {n: n for n in ["retrieve", "review", "finish"]})
    graph.add_edge("review", "finish")
    graph.add_edge("finish", END)
    return graph.compile(checkpointer=checkpointer)

