# Prior Authorization Assistant

An AI-powered tool that helps healthcare teams get insurance approvals faster — so patients spend less time waiting and more time receiving care.

---

## What Is This?

Before many medical treatments, procedures, or medications can happen, insurance companies require a formal approval called a **prior authorization**. Getting that approval means a healthcare coordinator must:

- Read through a patient's full clinical chart
- Cross-reference it against the insurance company's coverage policy
- Manually match the clinical evidence to each approval criterion
- File the paperwork — completely and correctly — for every single patient

One missing detail triggers a denial. The process restarts. The patient waits.

The **Prior Authorization Assistant** changes that. Upload the patient's chart and the insurance policy. In seconds, the assistant reads both documents, checks every coverage criterion, and delivers a clear recommendation — with its full reasoning shown. A human coordinator reviews it, makes the final call, and submits.

**The AI supports the decision. A human always makes it.**

---

## Who Is This For?

- **Care coordinators** managing high volumes of prior auth requests
- **Clinicians** who want faster turnaround on treatment approvals
- **Healthcare administrators** looking to reduce denial rates and administrative burden
- **Developers** building on top of this prototype

---

## Key Features

- **Document upload** — accepts patient chart and payer policy as PDF files
- **Clinical fact extraction** — identifies diagnosis, treatment requested, clinical history, and supporting evidence
- **Policy evaluation** — checks extracted facts against each coverage criterion (met / not met / insufficient information)
- **Guardrail checks** — flags incomplete submissions before a decision is made; routes low-confidence cases for human review
- **Final recommendation** — produces APPROVED / DENIED / PENDED with a cited rationale and a unique reference number
- **Audit trail** — every step the AI took is logged and viewable in the app; nothing is hidden
- **Privacy by design** — patient data never leaves your system; nothing is sent to external logging services

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- An [Anthropic API key](https://console.anthropic.com/) (required to run the AI pipeline)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up your environment

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
ANTHROPIC_API_KEY=your-key-here
```

Optional — enable LangSmith tracing for observability:

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=prior-auth-assistant
```

### 3. Run the app

```bash
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

---

## How to Use It

1. **Upload the patient chart** using the sidebar on the left (PDF only)
2. **Upload the insurance policy document** using the second sidebar slot (PDF only)
3. Once both documents are uploaded, the **Analyze** button becomes active
4. Click **Analyze** — the assistant works through the documents step by step
5. Results appear in the chat window:
   - Extracted clinical facts
   - Policy evaluation, criterion by criterion
   - A final recommendation with reference number and rationale
6. Expand the **Audit Trail** at the bottom to see every step the AI took

### Try it with the sample files

The `mock_data/` folder contains synthetic (non-real) documents you can use to test the full flow:

- `mock_data/sample_chart.pdf` — a synthetic patient chart for a lumbar spinal stenosis case
- `mock_data/sample_policy.pdf` — a synthetic payer policy with five prior auth criteria

Upload both, click Analyze, and you will see a complete end-to-end recommendation.

---

## How It Works

The assistant is built as a sequential pipeline of AI steps:

```
Upload documents
      ↓
Extract clinical facts from patient chart
      ↓
Evaluate facts against policy criteria
      ↓
Guardrail check (complete? confident?)
      ↓ (if PENDED)          ↓ (if ready)
  Flag for review        Make final decision
      ↓                        ↓
         Build audit trail
```

Each step is a separate, testable function. The coordinator sees the output of every step — not just the final answer.

---

## Project Structure

```
app.py                          # Streamlit app — UI entry point
modules/
  graph.py                      # LangGraph pipeline definition and run_graph()
  nodes.py                      # All AI node functions + AuthState schema
  pdf_utils.py                  # PDF text extraction (pdfplumber)
  state.py                      # Streamlit session state keys and initializer
mock_data/
  sample_chart.pdf              # Synthetic patient chart for testing
  sample_policy.pdf             # Synthetic payer policy for testing
tests/
  conftest.py                   # Shared pytest fixtures
  test_nodes.py                 # Unit tests for all AI node functions
  test_pdf_utils.py             # Unit tests for PDF extraction
  test_state.py                 # Unit tests for session state management
  smoke.test.js                 # Vitest smoke test
specs/                          # Requirements, plans, and validation docs per phase
.env.example                    # Environment variable template
```

---

## Development

### Run tests

```bash
pytest
```

### Lint and format

```bash
ruff check .
ruff format .
```

### Type checking

```bash
mypy .
```

### JavaScript tests

```bash
npm test
```

### Pre-commit hooks

```bash
pre-commit install   # run once after cloning
```

Hooks run automatically on every commit: linting, formatting check, and type checking.

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | UI Foundation & Document Ingestion | Complete |
| 2 | Core Agent Pipeline (LangGraph + Claude) | Complete |
| 3 | Guardrail & Decision | Complete |
| 4 | Observability, Audit & Demo | Complete |

---

## Important Notes

- **A human always makes the final decision.** The assistant produces a recommendation; a coordinator reviews and approves before anything is submitted.
- **This tool does not connect to live EHR systems** or submit directly to insurance companies.
- **Patient data is never sent to external logging services.** LangSmith tracing, if enabled, excludes all document content and clinical facts.
- The mock data files are entirely synthetic and labeled as such. They contain no real patient information.
