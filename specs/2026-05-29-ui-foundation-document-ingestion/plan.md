# Phase 1: UI Foundation & Document Ingestion — Plan

## Task Groups

### 1. Project Bootstrap
- Create `requirements.txt` with `streamlit`, `pdfplumber`
- Create `modules/__init__.py` (empty)
- Verify `streamlit run app.py` launches without errors on a skeleton `app.py`

### 2. Session State Initializer
- Create `modules/state.py` defining:
  - String constants for all session state keys (`MESSAGES`, `CHART_TEXT`, `POLICY_TEXT`)
  - `init_session_state()` function that sets defaults in `st.session_state` if keys are absent
- `init_session_state()` is called once at the top of `app.py`

### 3. PDF Extraction Module
- Create `modules/pdf_utils.py` with a `extract_text(file) -> str` function
- Uses `pdfplumber.open()` to iterate all pages and concatenate extracted text
- Returns the full concatenated string; raises a descriptive error if the file yields no text

### 4. Streamlit Layout — Chat Area
- Render message history from `st.session_state[MESSAGES]` using `st.chat_message`
- Add `st.chat_input` at the bottom
- On submit: append the user message to history, append the stub assistant reply, rerun

### 5. Streamlit Layout — Sidebar Upload Widgets
- Add `st.sidebar` with two `st.file_uploader` widgets (patient chart, policy document), accepting PDF only
- On each upload: call `extract_text()`, store result in the appropriate session state key, post a chat message with the extracted content

### 6. Integration Pass
- Wire task groups 2–5 together in `app.py`
- Confirm both upload slots work independently (upload chart only, upload policy only, upload both)
- Confirm chat input → stub reply loop works when no files are uploaded
- Confirm extracted text appears in the chat after upload

### 7. Documentation
- Add a `README.md` section (or update existing) with setup and run instructions: `pip install -r requirements.txt` then `streamlit run app.py`
