# Phase 1: UI Foundation & Document Ingestion — Requirements

## Scope

Build a running Streamlit app that accepts PDF file uploads and displays extracted text in the chat window. No agent logic — this phase establishes the UI skeleton, session state structure, and document ingestion pipeline that every later phase will build on.

## Structure

```
app.py              # Streamlit entry point
modules/
  pdf_utils.py      # pdfplumber extraction helpers
  state.py          # session_state key constants and initializers
```

## Functional Requirements

### Chat Layout
- User message input at the bottom of the page
- Assistant message display area above it, scrollable
- Message history stored in `st.session_state["messages"]` as a list of `{"role": ..., "content": ...}` dicts
- Messages persist across Streamlit reruns within the same session

### Sidebar
- Two independent file upload widgets: one for the patient chart PDF, one for the policy document PDF
- Each upload slot is labeled and can be used in any order
- On upload, the file is immediately processed (text extracted) and a chat message is posted confirming extraction

### PDF Extraction
- `modules/pdf_utils.py` uses `pdfplumber` to extract text from all pages of an uploaded PDF
- All pages are extracted and concatenated into a single string
- Full extracted text (no truncation) is rendered in the chat as an assistant message
- Extracted text is stored in session state: `st.session_state["chart_text"]` and `st.session_state["policy_text"]`

### Stub Assistant Replies
- When the user types a message in the chat input and submits, the assistant responds with a hardcoded stub reply (e.g., "Agent pipeline not yet wired — Phase 2 coming.") so the chat loop is exercised end-to-end

### No Agent Logic
- No LangGraph, no Claude API calls in this phase
- `AuthState` is not defined yet
- Agent stubs are not created in this phase (that is Phase 2's starting point)

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Multi-page PDF support | Yes — all pages extracted and concatenated | Realistic patient charts and payer policies span many pages |
| Extracted text in chat | Full text, no truncation | Downstream agents need the complete document; previewing a truncated version would be misleading |
| Upload order | Either file can be uploaded first; state updates independently | Coordinators don't always have both documents at once |
| Stub replies | Hardcoded echo when user types | Validates the chat input → message history → display loop without requiring agents |
| Module structure | `app.py` + `modules/` subdirectory | Avoids a God-file from the start; extraction logic is unit-testable in isolation |

## Code Quality & Testing

### Tooling

| Tool | Role | Command |
|------|------|---------|
| `ruff` | Lint and auto-format all Python source | `ruff check .` / `ruff format .` |
| `mypy` | Static type checking for all Python modules | `mypy .` |
| `pytest` | Unit tests for Python modules | `pytest` |
| `vitest` | JS/UI validation tests | `npm test` |
| `pre-commit` | Enforce ruff and mypy on every commit | `pre-commit install` |

### Structure

```
tests/
  __init__.py
  test_pdf_utils.py   # unit tests for extract_text()
  test_state.py       # unit tests for constants and init_session_state()
  smoke.test.js       # Vitest placeholder for future UI validation tests
pyproject.toml        # ruff and mypy configuration
.pre-commit-config.yaml
```

### Requirements

- All Python source files pass `ruff check .` with no errors
- All Python source files are formatted consistently per `ruff format --check .`
- `mypy .` reports no type errors
- `pytest` passes all tests in `tests/`
- `npm test` passes all Vitest tests
- `pre-commit install` is run once after cloning so hooks fire automatically

## Out of Scope

- Agent nodes or LangGraph graph
- Claude API integration
- LangSmith tracing
- Guardrail or decision logic
- Mock data files (Phase 4)
- Multi-user support or authentication

## Context

This phase exists to de-risk the UI layer and establish the data flow contract that later phases depend on. Phase 2 will import `st.session_state["chart_text"]` and `st.session_state["policy_text"]` directly — so those keys must be set correctly here.

Refer to `specs/mission.md` for why auditability and speed matter. Refer to `specs/tech-stack.md` for the full dependency rationale.
