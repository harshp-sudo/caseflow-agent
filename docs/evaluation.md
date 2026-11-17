# Recorded verification

Run date: 2026-11-17. Environment: Linux, Python 3.10.12, LangGraph 1.2.22 and SQLite checkpoint package 3.1.3. Exact dependency versions are recorded in `requirements.lock`.

- `pytest -q`: **17 passed** locally. The suite covers graph routing, rejection/approval, process restart, retries, unsupported output, provider failure, API validation, duplicate/replayed requests, and an OpenAI adapter contract using a mocked client.
- `ruff check .`: passed.
- `python -m pip check`: no broken requirements.
- `python -m caseflow_agent.evaluate --out docs/evaluation.json`: **7/7 expected routes**, **7/7 required-citation checks**. The raw per-case record is in [evaluation.json](evaluation.json).

The seven cases are shipping, password reset, pending payment, refund, cancellation, an unknown topic, and a suspicious instruction request. Citation checks on the unknown/suspicious cases have empty expected citation sets, so those passes must not be interpreted as grounded-answer successes. They check the expected routing behavior.

These are small synthetic regression results. The draft backend was deterministic extractive code. No live OpenAI request was made, no real users participated, and no production outcome was measured. Per-case timings include local checkpoint overhead and vary between runs; they are not a latency service-level objective or a model-comparison result.

The test client required local event-loop/socket access outside the restricted Codex sandbox. The same unchanged tests passed there. This did not require live provider credentials or external customer data. CI is configured for Python 3.10 and 3.12; its status is reported by GitHub separately from these local observations.

