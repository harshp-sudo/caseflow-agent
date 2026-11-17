# Design and implementation plan

Implemented scope: an inspectable support workflow over synthetic policies and orders, with durable human review. The project demonstrates new LangGraph work, separate from any previous employment.

## State and control flow

1. Validate the ticket at the CLI/API boundary. Reject unexpected fields and malformed demo order ids.
2. Classify an intent using lexical policy overlap and apply explicit sensitive-request/suspicious-input heuristics.
3. Retrieve policy snippets and, when supplied, look up an allowlisted synthetic order. No network or customer-system tool is available here.
4. Draft a reply using the selected backend. Offline mode extracts fixture text. OpenAI mode receives a system instruction plus JSON data and returns a Pydantic schema.
5. Check citation membership, inline citation presence, numeric support, and a limited set of forbidden completed-action phrases. If checks fail, broaden retrieval once and retry.
6. Pause via LangGraph `interrupt` for sensitive or unsupported requests. SQLite stores the checkpoint; a fresh process can resume using `Command`.
7. Release the checked draft only when its checks pass and any pending review approves it. Otherwise return an escalation. Human approval cannot turn failed checks into a successful answer.

The trace records node execution and draft duration. It is an application trace, not a claim of LangSmith or OpenTelemetry integration. Exact timings vary and are not production latency measurements.

## Persistence and failure semantics

An existing thread cannot be overwritten. Review requires a currently pending interrupt; replaying a completed review is rejected. An in-process lock covers the read/check/resume sequence. It does not solve competing reviewers in independent processes; that needs a transactional claim or compare-and-swap layer and a suitable production datastore.

The interrupt node performs no side effects before pausing. SQLite is used through the supported checkpointer API. Provider exceptions become failed drafts with only an exception class in the trace; raw error text is not exposed. Attempts stop at two. The checkpointer can preserve intermediate failed runs, but automated recovery of arbitrary interrupted provider calls is outside this demo.

## Evaluation plan

Test functional routing, invalid/unsupported drafts, actual retry correction, unknown orders, provider failure, strict review payloads, rejection, replay, duplicate ids, cross-process persistence, API validation and the model adapter contract. Run a separate small synthetic routing/citation evaluation and publish the observed results with their limitations.

## Deliberate limits and next work

- Citation and number checks are structural: a cited but semantically wrong sentence may pass. Add claim-level evaluation with labeled held-out examples before trusting model output.
- Keyword risk detection is incomplete and is not a prompt-injection security boundary. No financial tool exists, so this demo cannot issue money-changing actions regardless of the model's output.
- The lexical retriever suits four fixtures, not a production knowledge base. Measure retrieval recall before replacing it with embeddings or hybrid search.
- The local API has no authentication or tenant authorization. Real deployment needs identity, order entitlements, reviewed audit retention, encrypted sensitive data, rate limits, transactional reviewer coordination, and integration-specific idempotency.
- No claim of live-model quality, token-cost reduction, production traffic, human adoption or employer impact is made. Those require measurements not performed here.

