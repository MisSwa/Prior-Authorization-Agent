# MVP: Agent Pipeline, Guardrail & Decision, Observability — Validation

## Done When (from roadmap)

**Phase 2:** Uploading a real patient chart and policy PDF causes structured clinical facts
followed by a criterion-by-criterion policy evaluation to appear in the chat.

**Phase 3:** Submitting an incomplete chart halts with `PENDED` + missing-fields flag;
submitting a complete chart produces a prior authorization recommendation with cited rationale.

**Phase 4:** A reviewer can expand the audit panel and trace every step back to source
documents; a full graph run appears in LangSmith with per-node spans and no PII in the trace;
a new developer can clone the repo, upload mock files, and see a complete end-to-end
recommendation.

---

## Acceptance Checks

Run these manually before merging to `main`. All checks must pass.

### 1. Analyze Button Gating

- With no files uploaded: "Analyze" button is **disabled**.
- With only the chart uploaded: button is **disabled**.
- With only the policy uploaded: button is **disabled**.
- With both files uploaded: button is **enabled**.
- While the graph is running: button is **disabled**.

### 2. Clinical Extraction (Phase 2)

- Upload `mock_data/sample_chart.pdf` and `mock_data/sample_policy.pdf`.
- Click "Analyze".
- A spinner appears labeled **"Extracting clinical facts…"**.
- The spinner clears and a chat message appears containing extracted diagnosis, treatment
  requested, clinical history, and supporting evidence.
- The message is posted by the assistant role (not the user).

### 3. Policy Evaluation (Phase 2)

- Immediately after clinical extraction completes, a spinner appears labeled
  **"Evaluating against policy criteria…"**.
- The spinner clears and a chat message appears with a criterion-by-criterion breakdown,
  each criterion labeled met / not met / insufficient information.

### 4. Approved Decision (Phase 3 — happy path)

- Using `mock_data/sample_chart.pdf` and `mock_data/sample_policy.pdf` (designed to approve):
  - A spinner appears labeled **"Making prior authorization decision…"**.
  - The spinner clears and a chat message appears containing:
    - `recommendation: APPROVED` (or `DENIED` depending on Claude's evaluation)
    - A rationale paragraph citing specific policy criteria
    - A reference number in the format `PA-YYYYMMDD-XXXXXX`

### 5. PENDED Decision — Incomplete Chart (Phase 3)

- Create or upload a PDF with minimal content (e.g., only a patient name and date, no
  clinical history or diagnosis).
- Click "Analyze".
- The chat shows a `PENDED` message listing the specific missing fields (e.g.,
  "clinical history", "diagnosis").
- No recommendation, rationale, or reference number appears.
- `make_decision` did not run (confirm by checking that no decision spinner appeared).

### 6. PENDED Decision — Low Confidence (Phase 3)

- Upload a chart where the clinical evidence is vague or contradicts the policy criteria.
- Click "Analyze".
- The chat shows a `PENDED` message citing low confidence as the reason.
- No `APPROVED` or `DENIED` recommendation appears.

### 7. Audit Trail Expander (Phase 4)

- After any complete graph run (happy path), an **"Audit Trail"** expander is visible in the
  main area.
- Expanding it shows one entry per agent step: `extract_clinical_facts`, `evaluate_policy`,
  `guardrail`, `make_decision`, `build_audit_trail`.
- Each entry shows: node name, timestamp (ISO 8601), input summary, output summary.
- None of the following appear anywhere in the audit trail:
  - Raw chart text
  - Raw policy text
  - Extracted facts verbatim

### 8. LangSmith Trace (Phase 4)

- Run the app with `LANGCHAIN_TRACING_V2=true` and a valid `LANGCHAIN_API_KEY`.
- Click "Analyze" to run a full graph.
- In the LangSmith dashboard, a trace appears for the run with per-node spans.
- Span metadata includes: node name, session ID, timestamp, recommendation outcome.
- **Confirm no PII:** inspect all span inputs and outputs — `chart_text`, `policy_text`, and
  `extracted_facts` values must not appear in any span payload.

### 9. Mock Data End-to-End (Phase 4)

- From a clean clone of the repository:
  - `pip install -r requirements.txt` completes without errors.
  - `streamlit run app.py` opens in the browser without a traceback.
  - Upload `mock_data/sample_chart.pdf` and `mock_data/sample_policy.pdf`.
  - Click "Analyze".
  - Clinical facts, policy evaluation, and a final recommendation all appear in the chat.
  - The audit trail expander shows all node steps.

### 10. No PII in LangSmith (explicit recheck)

- Inspect at least two traces from different graph runs.
- Confirm none of the following strings appear in any span metadata, input, or output field:
  `chart_text` value, `policy_text` value, `extracted_facts` value.

### 11. Python Unit Tests

- `pytest` exits 0.
- All tests in `tests/test_nodes.py` pass with mocked `ChatAnthropic` (no live API key
  required).
- All existing tests in `tests/test_pdf_utils.py` and `tests/test_state.py` continue to pass.

### 12. Linting, Formatting, and Type Checking

- `ruff check .` exits 0 with no errors.
- `ruff format --check .` exits 0 (no files need reformatting).
- `mypy .` exits 0 — `AuthState` types verified across all node signatures.

### 13. Vitest

- `npm test` exits 0; all tests in `tests/smoke.test.js` pass.

---

## What This Phase Does Not Validate

- Direct payer submission or API integration with payers
- Live EHR data access
- Multi-user session isolation or authentication
- Real-time token-level streaming (spinner-per-node is the accepted UX for this MVP)
- Human review queue routing beyond the `PENDED` flag in the chat

---

## Merge Criteria

All 13 checks above pass. No Python exceptions appear in the terminal during a full graph run
with mock data. No PII appears in any LangSmith trace. Branch is merged to `main`.
