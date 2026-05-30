# MVP: Agent Pipeline, Guardrail & Decision, Observability — Requirements

## Scope

Build the remaining three phases of the Prior Authorization Assistant on top of the Phase 1 UI
foundation. Each phase extends the working slice without leaving unused infrastructure behind.

- **Phase 2 — Core Agent Pipeline:** Wire LangGraph with `extract_clinical_facts` and
  `evaluate_policy` nodes that read from session state and post results into the chat.
- **Phase 3 — Guardrail & Decision:** Add a `guardrail` conditional node and a `make_decision`
  node to produce a final approve/deny/pend recommendation.
- **Phase 4 — Observability, Audit & Demo:** Add a per-step audit log, LangSmith tracing,
  and a synthetic mock data bundle for demos and onboarding.

## Module Structure

```
modules/
  graph.py          # StateGraph definition, AuthState schema, compiled graph, run_graph()
  nodes.py          # All node functions: extract_clinical_facts, evaluate_policy,
                    #   guardrail, make_decision, build_audit_trail
mock_data/
  sample_chart.pdf  # Synthetic patient chart (realistic clinical content)
  sample_policy.pdf # Synthetic payer policy with prior auth criteria
.env.example        # Documents all required environment variables
```

`app.py` remains a thin UI layer. All agent logic lives in `modules/`.

---

## Functional Requirements

### Trigger Model

- A disabled "Analyze" button appears in the sidebar once the app loads.
- The button becomes **enabled** only when both `st.session_state["chart_text"]` and
  `st.session_state["policy_text"]` are non-empty strings.
- Clicking the button invokes the LangGraph graph synchronously; the button is disabled for
  the duration of the run.
- The button is not shown — or remains disabled — if either document slot is empty.

### Streaming UX

Each node shows a spinner while running, then posts its full output as a chat message when
complete. There is no live token-level streaming in this phase.

---

### Phase 2: Core Agent Pipeline

#### AuthState Schema

```python
class AuthState(TypedDict):
    chart_text: str            # from session state — input only
    policy_text: str           # from session state — input only
    extracted_facts: str       # output of extract_clinical_facts
    evaluation: str            # output of evaluate_policy
    confidence: float          # 0.0–1.0, set by evaluate_policy
    recommendation: str        # "APPROVED" | "DENIED" | "PENDED"
    rationale: str             # final rationale paragraph from make_decision
    reference_number: str      # generated ID, format PA-YYYYMMDD-XXXXXX
    missing_fields: list[str]  # populated by guardrail when required fields are absent
    audit_log: list[dict]      # one entry per node, appended by each node function
```

#### `extract_clinical_facts` Node

- Input: `state["chart_text"]`
- Calls `ChatAnthropic` (`claude-sonnet-4-6`) with a structured prompt to extract:
  diagnosis, treatment requested, clinical history, and supporting evidence.
- Returns `{"extracted_facts": str}` and appends to `audit_log`.
- UI: spinner labeled **"Extracting clinical facts…"**; on completion, posts a chat message
  with the extracted facts.

#### `evaluate_policy` Node

- Input: `state["extracted_facts"]` + `state["policy_text"]`
- Calls Claude to evaluate each policy criterion: met / not met / insufficient information.
- Returns `{"evaluation": str, "confidence": float}` and appends to `audit_log`.
- UI: spinner labeled **"Evaluating against policy criteria…"**; on completion, posts a
  criterion-by-criterion breakdown as a chat message.

---

### Phase 3: Guardrail & Decision

#### `guardrail` Node (conditional edge)

- Checks that all required `AuthState` fields are populated.
- If any required field is missing → sets `recommendation = "PENDED"`, populates
  `missing_fields`, halts graph execution before `make_decision`.
- If `confidence < 0.7` → routes to `make_decision` with `recommendation` pre-set to
  `"PENDED"` and a rationale noting low confidence; `make_decision` records the pend.
- If state is complete and `confidence >= 0.7` → routes to `make_decision` with no
  pre-set recommendation.

#### `make_decision` Node

- Synthesizes a final recommendation (`APPROVED` / `DENIED` / `PENDED`) with a rationale
  paragraph that cites specific policy criteria.
- Generates a reference number: `PA-YYYYMMDD-XXXXXX` (date-stamped, six random alphanumeric
  characters).
- Returns `{"recommendation": str, "rationale": str, "reference_number": str}` and appends
  to `audit_log`.
- UI: spinner labeled **"Making prior authorization decision…"**; on completion, posts a
  formatted chat message with recommendation, rationale, and reference number.

---

### Phase 4: Observability, Audit & Demo

#### Audit Log

- Each node appends a structured entry to `audit_log`:
  ```python
  {
      "node": str,            # node function name
      "timestamp": str,       # ISO 8601
      "input_summary": str,   # brief description of inputs used — no raw document text
      "output_summary": str,  # brief description of what was produced
  }
  ```
- Raw patient data (`chart_text`, `policy_text`, `extracted_facts`) must **not** appear in
  any audit log entry.
- After the graph completes, `app.py` renders an `st.expander("Audit Trail")` in the main
  area showing each entry as a labeled block.

#### LangSmith Tracing

- Enabled when `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set.
- Each node tagged with a descriptive `run_name`.
- Metadata logged per trace: node name, session ID, timestamp, recommendation outcome.
- **No PII in trace payload:** `chart_text`, `policy_text`, and `extracted_facts` are
  excluded from all span metadata and inputs.

#### Environment Variables

- `.env.example` documents:
  - `ANTHROPIC_API_KEY` — required for Claude API calls
  - `LANGCHAIN_TRACING_V2` — set to `true` to enable LangSmith
  - `LANGCHAIN_API_KEY` — LangSmith API key
  - `LANGCHAIN_PROJECT` — LangSmith project name
- `.gitignore` must exclude `.env`.

#### Mock Data Bundle

- `mock_data/sample_chart.pdf` — synthetic patient chart, 1–3 pages, with a realistic clinical
  scenario: named diagnosis, treatment plan, clinical history, and supporting evidence.
- `mock_data/sample_policy.pdf` — synthetic payer policy, 1–2 pages, with 3–5 prior
  authorization criteria that align with the sample chart scenario so a complete graph run
  produces an `APPROVED` recommendation.
- No real patient data; all content is synthetic and clearly labeled as such.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Trigger model | Explicit "Analyze" button | Gives coordinators control; prevents accidental graph runs on re-upload |
| Streaming UX | Spinner per node, then full message | Simpler than live token streaming; avoids Streamlit re-render complexity; adequate UX for MVP |
| Confidence threshold | 0.7 | Conservative starting point; can be tuned from feedback without changing graph structure |
| Graph invocation | In-process, no API server | Consistent with Phase 1 architecture; see `specs/tech-stack.md` |
| Reference number format | `PA-YYYYMMDD-XXXXXX` | Human-readable, date-stamped, unique enough for a single-coordinator workload |
| PII exclusion from traces | chart_text, policy_text, extracted_facts never in LangSmith spans | Mission requirement: decisions are fully auditable but patient data stays local |
| Mock data format | Synthetic PDFs, not code fixtures | Tests the full pdfplumber → session state → agent pipeline path end-to-end |

## Code Quality & Testing

All Phase 1 tooling requirements continue to apply (`ruff`, `mypy`, `pytest`, `vitest`,
`pre-commit`). Additional requirements for this phase:

- Each LangGraph node function is a **pure function over `AuthState`** and has a
  corresponding unit test in `tests/test_nodes.py`.
- Unit tests mock `ChatAnthropic`; no live API key required to run `pytest`.
- `mypy` must pass with the `AuthState` typed dict and all node signatures typed correctly.
- No raw patient data committed to the repository (mock data is synthetic).

## Out of Scope

- Direct payer submission
- Live EHR integration
- Multi-user authentication or session isolation
- Real-time token-level streaming (future enhancement opportunity)
- Human review queue routing beyond the PENDED flag in the chat

## Context

Phase 1 established `st.session_state["chart_text"]` and `st.session_state["policy_text"]`
as the handoff contract. Phase 2 consumes those keys as graph inputs, so `app.py` passes
them directly to `run_graph()` without transformation.

Refer to `specs/mission.md` for the auditability and speed requirements that motivate the
LangSmith tracing and audit log decisions. Refer to `specs/tech-stack.md` for the full
rationale behind LangGraph, `ChatAnthropic`, and the in-process graph invocation pattern.
