# Healthcare Prior Authorization Assistant

AI-assisted prototype that helps care coordinators evaluate doctor charts against payer policy PDFs for prior authorization decisions.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

## Usage

1. Upload a **patient chart PDF** using the sidebar widget on the left.
2. Upload a **policy document PDF** using the second sidebar widget.
3. The extracted text from each document appears in the chat window.
4. Type questions in the chat input at the bottom of the page.

## Project Structure

```
app.py              # Streamlit entry point
modules/
  pdf_utils.py      # pdfplumber text extraction
  state.py          # session state key constants and initializer
specs/              # Requirements, plans, and validation criteria
```

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | UI Foundation & Document Ingestion | In progress |
| 2 | Core Agent Pipeline (LangGraph + Claude) | Planned |
| 3 | Guardrail & Decision | Planned |
| 4 | Observability, Audit & Demo | Planned |
