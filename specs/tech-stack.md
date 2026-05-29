# Tech Stack

## Frontend: Streamlit

- **Library:** `streamlit`
- **Responsibilities:**
  - Chat layout with persistent message history (`st.session_state`)
  - File upload widgets for patient chart and policy PDF
  - Streaming output — agent responses rendered incrementally as they arrive
  - Sidebar for configuration and session controls
- **Rationale:** Zero-boilerplate Python UI. No separate frontend build step. Ideal for internal tooling where iteration speed matters more than pixel-perfect design.

## Agent Orchestration: LangGraph

- **Library:** `langgraph`
- **Core constructs:** `StateGraph`, typed state schema, one node per agent, directed edges defining flow
- **Graph topology:**
  ```
  upload → extract_clinical_facts → evaluate_policy → guardrail → make_decision → audit_trail
                                                           ↓
                                                    human_review_queue (on low confidence or missing fields)
  ```
- **Guardrail node:** A conditional edge node that runs after `evaluate_policy`. Checks that all required `AuthState` fields are populated and that confidence is above threshold. If not, halts with `PENDED` + missing-fields flag or routes to human review. `make_decision` never runs on incomplete state.
- **Rationale:** Explicit, inspectable graph structure makes the agent pipeline auditable. Each node is a pure function over state, easy to test in isolation. Supports streaming so Streamlit can render partial output.

## AI Model: Claude via ChatAnthropic

- **Model:** `claude-sonnet-4-6`
- **Integration library:** `langchain-anthropic` (`ChatAnthropic`)
- **Usage pattern:** Each LangGraph node that requires reasoning instantiates a `ChatAnthropic` client and invokes it with a structured prompt. Streaming enabled via `.stream()`.
- **Rationale:** Claude excels at long-document comprehension (full policy PDFs), structured extraction, and producing citation-grounded rationale — all critical for prior authorization.

## Document Parsing: pdfplumber

- **Library:** `pdfplumber`
- **Responsibilities:** Extract raw text from uploaded PDF files (patient charts, payer policy documents)
- **Rationale:** Pure Python, no external service dependency, reliable text extraction including tables. Keeps the stack self-contained.

## Observability: LangSmith

- **Service:** LangSmith (LangChain)
- **Configuration:** `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` environment variables
- **What is traced:** Per-node spans with run name, session ID, timestamp, and recommendation outcome
- **What is never traced:** Chart text, policy text, extracted clinical facts — no raw patient data leaves the application
- **Rationale:** End-to-end visibility into graph execution for debugging and performance monitoring without compromising patient privacy.

## Architecture Note: No Separate API Server

Streamlit invokes the LangGraph graph directly in-process. There is no REST API layer between the UI and the agent graph. This eliminates deployment complexity for the initial versions. If a server layer is needed later (e.g., for async job queues or multi-user scaling), it can be added without changing the graph logic.

## Code Quality & Testing

### Linting & Formatting: Ruff

- **Library:** `ruff`
- **Responsibilities:** Lint and auto-format all Python source files
- **Commands:** `ruff check .` (lint), `ruff format .` (format)
- **Rationale:** Single tool replaces flake8, isort, and black. Fast enough to run on every save and in CI without friction.

### Type Checking: mypy

- **Library:** `mypy`
- **Responsibilities:** Static type analysis of all Python modules; catches type mismatches before runtime
- **Command:** `mypy .`
- **Rationale:** The typed `AuthState` schema in LangGraph depends on correct types flowing through every node. mypy enforces this at development time.

### Python Unit Tests: pytest

- **Library:** `pytest`
- **Responsibilities:** Unit tests for Python modules (`modules/pdf_utils.py`, `modules/state.py`) and LangGraph node logic
- **Command:** `pytest`
- **Rationale:** Each LangGraph node is a pure function over state, making it straightforward to test in isolation without running the full Streamlit app.

### JS/UI Validation Tests: Vitest

- **Library:** `vitest`
- **Responsibilities:** Validation tests for the application, runnable via `npm test`
- **Script:** Defined in `package.json` as `"test": "vitest"`
- **Rationale:** Fast, ESM-native test runner with minimal configuration. Tests live alongside the source they validate and can be run in watch mode during development.

### Pre-commit Hooks: pre-commit

- **Library:** `pre-commit`
- **Configuration:** `.pre-commit-config.yaml` at the repository root
- **Hooks run on every commit:**
  - `ruff check` — fail on lint errors
  - `ruff format --check` — fail if formatting is inconsistent
  - `mypy` — fail on type errors
- **Rationale:** Prevents unformatted or type-unsafe code from entering the repository without requiring developers to remember to run checks manually.

## Dependency Summary

| Component            | Package                  |
|----------------------|--------------------------|
| UI                   | `streamlit`              |
| Agent graph          | `langgraph`              |
| LLM client           | `langchain-anthropic`    |
| LLM model            | `claude-sonnet-4-6`      |
| PDF parsing          | `pdfplumber`             |
| Tracing              | `langsmith`              |
| Linting & formatting | `ruff`                   |
| Type checking        | `mypy`                   |
| Python tests         | `pytest`                 |
| JS/UI tests          | `vitest`                 |
| Pre-commit hooks     | `pre-commit`             |
