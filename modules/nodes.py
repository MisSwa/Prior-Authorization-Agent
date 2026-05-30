import random
import re
import string
from datetime import date, datetime, timezone
from typing import Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


class AuthState(TypedDict):
    chart_text: str
    policy_text: str
    extracted_facts: str
    evaluation: str
    confidence: float
    recommendation: str
    rationale: str
    reference_number: str
    missing_fields: list[str]
    audit_log: list[dict[str, str]]


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM = """\
You are a clinical documentation analyst preparing a prior authorization review.
Extract the following from the patient chart text:

1. Primary diagnosis (include ICD-10 code if present)
2. Treatment requested (procedure, medication, or service)
3. Clinical history (concise summary of relevant history)
4. Supporting evidence (lab results, imaging, prior treatments, clinical notes)

Format your response exactly as:

**Primary Diagnosis:** <value>
**Treatment Requested:** <value>
**Clinical History:** <summary>
**Supporting Evidence:** <evidence>"""

_EVALUATION_SYSTEM = """\
You are a prior authorization policy evaluator for a health insurance payer.
Given the extracted clinical facts and the payer policy document, evaluate each
policy criterion for prior authorization.

For each criterion found in the policy, state one of:
- met
- not met
- insufficient information

At the very end, on its own line, provide an overall confidence score from 0.0 to 1.0
reflecting how clearly the clinical evidence satisfies the policy criteria.

Format your response as:

**Criterion: <name>** — met / not met / insufficient information
...

**Overall Confidence:** <score>"""

_DECISION_SYSTEM = """\
You are a senior prior authorization reviewer making a final determination.
Based on the clinical facts and policy evaluation provided, make a prior authorization decision.

Your response must include:
1. A recommendation: exactly one of APPROVED, DENIED, or PENDED
2. A rationale paragraph that cites specific policy criteria and clinical evidence

Format your response as:

**Recommendation:** APPROVED
**Rationale:** <paragraph>"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_log(
    log: list[dict[str, str]],
    node: str,
    input_summary: str,
    output_summary: str,
) -> list[dict[str, str]]:
    return log + [
        {
            "node": node,
            "timestamp": _now(),
            "input_summary": input_summary,
            "output_summary": output_summary,
        }
    ]


def _parse_confidence(text: str) -> float:
    # [^0-9-]* skips any non-numeric characters (colons, asterisks, spaces)
    # before the score so markdown formatting like `:** 0.85` is handled.
    match = re.search(r"Overall Confidence[^0-9-]*(-?[0-9]*\.?[0-9]+)", text, re.IGNORECASE)
    if match:
        try:
            return max(0.0, min(1.0, float(match.group(1))))
        except ValueError:
            pass
    return 0.5


def _parse_recommendation(text: str) -> str:
    match = re.search(r"\*\*Recommendation:\*\*\s*(APPROVED|DENIED|PENDED)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    for word in ("APPROVED", "DENIED", "PENDED"):
        if word in text.upper():
            return word
    return "PENDED"


def _parse_rationale(text: str) -> str:
    match = re.search(r"\*\*Rationale:\*\*\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _generate_reference() -> str:
    date_str = date.today().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"PA-{date_str}-{suffix}"


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def extract_clinical_facts(state: AuthState) -> dict[str, Any]:
    """Phase 2 — extract structured clinical facts from the patient chart."""
    client = ChatAnthropic(model="claude-sonnet-4-6")  # type: ignore[call-arg]
    response = client.invoke(
        [
            SystemMessage(content=_EXTRACTION_SYSTEM),
            HumanMessage(content=f"Patient Chart:\n\n{state['chart_text']}"),
        ]
    )
    facts = str(response.content)
    log = _append_log(
        state["audit_log"],
        node="extract_clinical_facts",
        input_summary=f"Patient chart ({len(state['chart_text'])} chars)",
        output_summary=f"Extracted facts ({len(facts)} chars)",
    )
    return {"extracted_facts": facts, "audit_log": log}


def evaluate_policy(state: AuthState) -> dict[str, Any]:
    """Phase 2 — evaluate extracted facts against payer policy criteria."""
    client = ChatAnthropic(model="claude-sonnet-4-6")  # type: ignore[call-arg]
    response = client.invoke(
        [
            SystemMessage(content=_EVALUATION_SYSTEM),
            HumanMessage(
                content=(
                    f"Clinical Facts:\n\n{state['extracted_facts']}"
                    f"\n\nPolicy Document:\n\n{state['policy_text']}"
                )
            ),
        ]
    )
    evaluation = str(response.content)
    confidence = _parse_confidence(evaluation)
    log = _append_log(
        state["audit_log"],
        node="evaluate_policy",
        input_summary=f"Extracted facts + policy document ({len(state['policy_text'])} chars)",
        output_summary=f"Criteria evaluated; confidence={confidence:.2f}",
    )
    return {"evaluation": evaluation, "confidence": confidence, "audit_log": log}


def guardrail(state: AuthState) -> dict[str, Any]:
    """Phase 3 — enforce completeness and confidence threshold before decision."""
    missing = [f for f in ["extracted_facts", "evaluation"] if not state.get(f)]

    if missing:
        log = _append_log(
            state["audit_log"],
            node="guardrail",
            input_summary=f"confidence={state['confidence']:.2f}",
            output_summary=f"PENDED — missing fields: {missing}",
        )
        return {
            "recommendation": "PENDED",
            "missing_fields": missing,
            "rationale": (
                "Prior authorization pended. Required information is missing: "
                f"{', '.join(missing)}. Please provide a more complete patient chart."
            ),
            "audit_log": log,
        }

    if state["confidence"] < 0.7:
        log = _append_log(
            state["audit_log"],
            node="guardrail",
            input_summary=f"confidence={state['confidence']:.2f}",
            output_summary=f"PENDED — low confidence ({state['confidence']:.2f} < 0.70)",
        )
        return {
            "recommendation": "PENDED",
            "missing_fields": [],
            "rationale": (
                f"Prior authorization pended. Confidence score {state['confidence']:.2f} "
                "is below the required threshold of 0.70. The clinical evidence does not "
                "clearly satisfy or fail the policy criteria. Human review is recommended."
            ),
            "audit_log": log,
        }

    log = _append_log(
        state["audit_log"],
        node="guardrail",
        input_summary=f"confidence={state['confidence']:.2f}",
        output_summary="All checks passed — routing to make_decision",
    )
    return {"missing_fields": [], "audit_log": log}


def route_after_guardrail(state: AuthState) -> str:
    """Conditional edge function: routes to audit trail if PENDED, else to make_decision."""
    if state.get("recommendation") == "PENDED":
        return "build_audit_trail"
    return "make_decision"


def make_decision(state: AuthState) -> dict[str, Any]:
    """Phase 3 — synthesize final prior authorization recommendation."""
    client = ChatAnthropic(model="claude-sonnet-4-6")  # type: ignore[call-arg]
    response = client.invoke(
        [
            SystemMessage(content=_DECISION_SYSTEM),
            HumanMessage(
                content=(
                    f"Clinical Facts:\n\n{state['extracted_facts']}"
                    f"\n\nPolicy Evaluation:\n\n{state['evaluation']}"
                )
            ),
        ]
    )
    decision_text = str(response.content)
    recommendation = _parse_recommendation(decision_text)
    rationale = _parse_rationale(decision_text)
    reference_number = _generate_reference()

    log = _append_log(
        state["audit_log"],
        node="make_decision",
        input_summary="Extracted facts + policy evaluation",
        output_summary=f"recommendation={recommendation}, ref={reference_number}",
    )
    return {
        "recommendation": recommendation,
        "rationale": rationale,
        "reference_number": reference_number,
        "audit_log": log,
    }


def build_audit_trail(state: AuthState) -> dict[str, Any]:
    """Phase 4 — finalize the audit log as the terminal graph node."""
    log = _append_log(
        state["audit_log"],
        node="build_audit_trail",
        input_summary=f"{len(state['audit_log'])} preceding entries",
        output_summary=(
            f"Audit trail finalized. Recommendation: {state.get('recommendation', 'UNKNOWN')}"
        ),
    )
    return {"audit_log": log}
