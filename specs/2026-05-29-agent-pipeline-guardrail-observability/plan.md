# MVP: Agent Pipeline, Guardrail & Decision, Observability — Plan

## Task Groups

Tasks are ordered so each group produces something runnable or testable before the next
group builds on it. Phase boundaries are noted but implementation flows continuously.

---

### 1. Dependencies & Bootstrap

- Add to `requirements.txt`: `langgraph`, `langchain-anthropic`, `langsmith`, `python-dotenv`
- Create `.env.example` documenting `ANTHROPIC_API_KEY`, `LANGCHAIN_TRACING_V2`,
  `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`
- Confirm `.gitignore` excludes `.env`
- Run `pip install -r requirements.txt` and verify no conflicts

---

### 2. AuthState Schema

- Create `modules/graph.py`
- Define `AuthState` TypedDict with all fields:
  `chart_text`, `policy_text`, `extracted_facts`, `evaluation`, `confidence`,
  `recommendation`, `rationale`, `reference_number`, `missing_fields`, `audit_log`
- Confirm `mypy .` passes on the schema alone before adding node functions

---

### 3. Node Functions — Phase 2

- Create `modules/nodes.py`
- Implement `extract_clinical_facts(state: AuthState) -> dict`:
  - Prompts `ChatAnthropic` (`claude-sonnet-4-6`) to extract diagnosis, treatment requested,
    clinical history, supporting evidence
  - Returns `{"extracted_facts": str, "audit_log": updated_list}`
- Implement `evaluate_policy(state: AuthState) -> dict`:
  - Prompts Claude with `extracted_facts` + `policy_text`
  - Returns `{"evaluation": str, "confidence": float, "audit_log": updated_list}`
- Both functions are pure over `AuthState`; no Streamlit calls inside node functions

---

### 4. Node Functions — Phase 3

- Implement `guardrail(state: AuthState) -> dict`:
  - Checks required fields populated and `confidence >= 0.7`
  - Returns PENDED state with `missing_fields` if checks fail
  - Returns pass-through state for `make_decision` if checks pass
- Implement `make_decision(state: AuthState) -> dict`:
  - Synthesizes recommendation, rationale paragraph, reference number (`PA-YYYYMMDD-XXXXXX`)
  - Returns `{"recommendation": str, "rationale": str, "reference_number": str,
    "audit_log": updated_list}`

---

### 5. Node Function — Phase 4 Audit Trail

- Implement `build_audit_trail(state: AuthState) -> dict`:
  - Final terminal node; returns `{"audit_log": finalized_list}`
  - Each preceding node already appends its entry; this node marks completion timestamp
- Audit log entries follow the schema from `requirements.md`; no raw document text included

---

### 6. Build & Wire the Graph

- In `modules/graph.py`:
  - Instantiate `StateGraph(AuthState)`
  - Add nodes: `extract_clinical_facts`, `evaluate_policy`, `guardrail`, `make_decision`,
    `build_audit_trail`
  - Define edges:
    ```
    extract_clinical_facts → evaluate_policy → guardrail
    guardrail → make_decision  (when complete + confident)
    guardrail → build_audit_trail  (when PENDED)
    make_decision → build_audit_trail
    ```
  - Implement conditional edge function for `guardrail` routing
  - Compile graph
- Expose `run_graph(chart_text: str, policy_text: str) -> AuthState` as the public API for
  `app.py` to call

---

### 7. Streamlit Integration — Analyze Button

- In `app.py`:
  - Add "Analyze" button to sidebar; disabled unless both `CHART_TEXT` and `POLICY_TEXT`
    are non-empty in session state
  - On click: call `run_graph()`, show `st.spinner` per phase, post each node's output to
    `st.session_state[MESSAGES]` after its spinner clears
  - Button remains disabled during graph execution; re-enables on completion

---

### 8. Streamlit Integration — Audit Trail Expander

- After the graph result is stored, render `st.expander("Audit Trail")` in the main area
- Iterate `state["audit_log"]`; display each entry as a labeled block:
  node name, timestamp, input summary, output summary
- Raw chart or policy text must not appear in any displayed entry

---

### 9. LangSmith Configuration

- Load env vars via `python-dotenv` at the top of `app.py` (before any LangChain imports)
- Add `run_name` to each node's `ChatAnthropic` invocation
- Manually verify a trace appears in LangSmith after a full graph run
- Spot-check that no PII fields appear in any span

---

### 10. Mock Data Bundle

- Create `mock_data/` directory
- Generate `mock_data/sample_chart.pdf`:
  - Synthetic patient: named diagnosis (e.g., lumbar spinal stenosis), treatment plan
    (e.g., MRI of lumbar spine), 6-month clinical history, supporting evidence
  - Clearly labeled "SYNTHETIC — NOT REAL PATIENT DATA"
- Generate `mock_data/sample_policy.pdf`:
  - Synthetic payer policy with 3–5 prior auth criteria aligned to the sample chart scenario
  - Criteria designed so the sample chart produces an `APPROVED` recommendation
  - Clearly labeled "SYNTHETIC — NOT REAL POLICY DATA"

---

### 11. Unit Tests for Nodes

- Create `tests/test_nodes.py`
- For each node: mock `ChatAnthropic`, call the node function with a minimal `AuthState`
  fixture, assert the returned dict has correct keys and value types
- Guardrail routing tests:
  - Missing required field → `recommendation == "PENDED"`, `missing_fields` non-empty
  - `confidence < 0.7` → `recommendation == "PENDED"`
  - Complete state, `confidence >= 0.7` → no `recommendation` set (routes to `make_decision`)
- `make_decision` test:
  - Reference number matches `PA-\d{8}-[A-Z0-9]{6}` pattern
  - `recommendation` is one of `APPROVED`, `DENIED`, `PENDED`
- Audit log tests:
  - Each node appends exactly one entry to `audit_log`
  - Entry contains `node`, `timestamp`, `input_summary`, `output_summary` keys
  - No raw `chart_text` or `policy_text` in any entry value

---

### 12. Code Quality Pass

- `ruff check .` and `ruff format .` — fix any issues
- `mypy .` — verify `AuthState` types flow correctly through all node signatures
- `pytest` — all tests in `tests/` pass, including new `test_nodes.py`
- `npm test` — Vitest smoke test passes
- `pre-commit run --all-files` — confirm hooks pass clean
