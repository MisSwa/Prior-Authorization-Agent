# Phase 1: UI Foundation & Document Ingestion — Validation

## Done When (from roadmap)

`streamlit run app.py` launches, a PDF can be uploaded, and its extracted text appears in the chat window.

## Acceptance Checks

Run these manually before merging to `main`.

### 1. App Starts
- `pip install -r requirements.txt` completes without errors
- `streamlit run app.py` opens in the browser without a Python traceback

### 2. Chat Loop Works Without Files
- Type a message in the chat input and press Enter
- The user message appears in the chat history
- A stub assistant reply appears immediately below it
- Refreshing the page clears history (session-scoped only — no persistence to disk expected)

### 3. Patient Chart Upload
- Upload any multi-page PDF as the patient chart
- A chat message appears containing the full extracted text of the PDF
- `st.session_state["chart_text"]` is non-empty (confirm via Streamlit's built-in session state viewer or a sidebar debug print if present)
- Policy text slot remains unaffected

### 4. Policy Document Upload
- Upload a separate PDF as the policy document
- A second chat message appears containing the full extracted text of that PDF
- `st.session_state["policy_text"]` is non-empty
- Chart text slot remains unaffected

### 5. Both Files Uploaded Independently
- Upload chart first, then policy (and vice versa) — both extractions appear as separate messages
- Uploading a new file in a slot replaces the previous value in session state without corrupting the other slot

### 6. Multi-Page Extraction
- Upload a PDF with more than one page
- The extracted text in the chat message includes content from all pages, not just page 1

## What This Phase Does Not Validate

- Agent reasoning or Claude API responses (Phase 2)
- Guardrail or decision logic (Phase 3)
- LangSmith traces (Phase 4)
- Correctness of clinical extraction — there is no model in this phase

## Merge Criteria

All 6 checks above pass manually. No Python exceptions appear in the terminal during normal use. Branch is merged to `main`.
