# Roadmap

## Approach: Vertical Slices

Each phase ships a thin, working slice of the full system end-to-end. No phase produces infrastructure that sits unused waiting for a future phase. Every phase produces something runnable and demonstrable.

---

## Phase 1: UI Foundation & Document Ingestion

**Deliverable:** A running Streamlit app that accepts file uploads and displays extracted PDF text in the chat.

- Chat layout: user message input, assistant message display area
- Message history persisted in `st.session_state`
- Sidebar panel with file upload widgets (patient chart, policy document)
- `pdfplumber` extracts text on upload; extracted text preview posted as a chat message
- State stores raw extracted text for downstream agents
- No agent logic yet — messages echo back as stubs

**Done when:** `streamlit run app.py` launches, a PDF can be uploaded, and its extracted text appears in the chat window.

---

## Phase 2: Core Agent Pipeline

**Deliverable:** A fully wired LangGraph graph with working clinical extraction and policy evaluation nodes that stream output into the chat.

- `AuthState` typed dict defined (fields for chart text, policy text, extracted facts, evaluation, decision, audit log)
- All nodes defined and edges connected in correct sequence; graph compiled and invokable from Streamlit
- `extract_clinical_facts` node calls `ChatAnthropic` (`claude-sonnet-4-6`), streams extracted facts (diagnosis, treatment requested, clinical history) into chat
- `evaluate_policy` node receives extracted facts + policy text, prompts Claude to evaluate each criterion (met / not met / insufficient information), streams criterion-by-criterion breakdown into chat

**Done when:** Uploading a real patient chart and policy PDF causes structured clinical facts followed by a criterion-by-criterion policy evaluation to stream into the chat.

---

## Phase 3: Guardrail & Decision

**Deliverable:** A guardrail node that enforces completeness before a decision is made, followed by a decision node that produces the final prior authorization recommendation.

- `guardrail` node checks that all required `AuthState` fields are populated and confidence is above threshold
- If any required field is missing → sets recommendation to `PENDED`, adds a flag explaining what is missing, halts graph execution
- If confidence is low → routes to human review queue; `make_decision` never runs on incomplete state
- Routing logic implemented as a LangGraph conditional edge
- `make_decision` node synthesizes a recommendation (approve / deny / pend) with rationale paragraph and generated reference number; streams final decision into chat

**Done when:** Submitting an incomplete chart halts with a `PENDED` + missing-fields flag; submitting a complete chart produces a streamed prior authorization recommendation with cited rationale.

---

## Phase 4: Observability, Audit & Demo

**Deliverable:** Full traceability from input documents to decision, plus a mock data bundle for demo and development use.

- Each agent step appends a structured entry to the `audit_log` field in `AuthState`
- Streamlit renders an `st.expander` per decision showing: inputs used, agent step, output — human-readable and copy-pasteable
- LangSmith tracing enabled via `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY`; each node tagged with a descriptive `run_name`
- Metadata logged per trace: node name, session ID, timestamp, recommendation outcome — **no raw patient data** (chart text, policy text, extracted facts excluded from trace payload)
- `.env.example` documents required env vars; `.gitignore` excludes `.env`
- `mock_data/sample_chart.pdf` — synthetic patient chart with realistic clinical content
- `mock_data/sample_policy.pdf` — synthetic payer policy with prior auth criteria

**Done when:** A reviewer can expand the audit panel and trace every step back to source documents; a full graph run appears in LangSmith with per-node spans and no PII in the trace; a new developer can clone the repo, upload mock files, and see a complete end-to-end recommendation.
