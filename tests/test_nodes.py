import re
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from modules.nodes import (
    AuthState,
    _generate_reference,
    _parse_confidence,
    _parse_recommendation,
    build_audit_trail,
    evaluate_policy,
    extract_clinical_facts,
    guardrail,
    make_decision,
    route_after_guardrail,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_BASE: AuthState = {
    "chart_text": "Patient has lumbar spinal stenosis. Requesting MRI.",
    "policy_text": "Prior auth required for MRI. Diagnosis must be documented.",
    "extracted_facts": "Diagnosis: Lumbar spinal stenosis. Treatment: MRI lumbar spine.",
    "evaluation": "Criterion 1: met\n**Overall Confidence:** 0.85",
    "confidence": 0.85,
    "recommendation": "",
    "rationale": "",
    "reference_number": "",
    "missing_fields": [],
    "audit_log": [],
}


def _state(**overrides: Any) -> AuthState:
    return {**_BASE, **overrides}  # type: ignore[return-value, typeddict-item]


def _mock_llm_response(content: str) -> MagicMock:
    response = MagicMock()
    response.content = content
    return response


# ---------------------------------------------------------------------------
# _parse_confidence
# ---------------------------------------------------------------------------


def test_parse_confidence_extracts_score() -> None:
    assert _parse_confidence("**Overall Confidence:** 0.85") == pytest.approx(0.85)


def test_parse_confidence_case_insensitive() -> None:
    assert _parse_confidence("overall confidence: 0.72") == pytest.approx(0.72)


def test_parse_confidence_defaults_to_half_when_absent() -> None:
    assert _parse_confidence("no score in this text") == pytest.approx(0.5)


def test_parse_confidence_clamps_above_one() -> None:
    assert _parse_confidence("Overall Confidence: 1.5") == pytest.approx(1.0)


def test_parse_confidence_clamps_below_zero() -> None:
    assert _parse_confidence("Overall Confidence: -0.3") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _parse_recommendation
# ---------------------------------------------------------------------------


def test_parse_recommendation_approved() -> None:
    assert _parse_recommendation("**Recommendation:** APPROVED\n**Rationale:** ok") == "APPROVED"


def test_parse_recommendation_denied() -> None:
    assert _parse_recommendation("**Recommendation:** DENIED") == "DENIED"


def test_parse_recommendation_pended_explicit() -> None:
    assert _parse_recommendation("**Recommendation:** PENDED") == "PENDED"


def test_parse_recommendation_fallback_to_pended() -> None:
    assert _parse_recommendation("cannot determine a clear recommendation") == "PENDED"


# ---------------------------------------------------------------------------
# _generate_reference
# ---------------------------------------------------------------------------


def test_generate_reference_matches_format() -> None:
    today = date.today().strftime("%Y%m%d")
    ref = _generate_reference()
    assert re.match(rf"^PA-{today}-[A-Z0-9]{{6}}$", ref), f"Unexpected format: {ref}"


def test_generate_reference_is_unique() -> None:
    refs = {_generate_reference() for _ in range(20)}
    assert len(refs) > 1  # statistically near-certain


# ---------------------------------------------------------------------------
# extract_clinical_facts
# ---------------------------------------------------------------------------


def test_extract_clinical_facts_returns_extracted_facts() -> None:
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response(
            "**Primary Diagnosis:** Lumbar spinal stenosis"
        )
        result = extract_clinical_facts(_state())

    assert result["extracted_facts"] == "**Primary Diagnosis:** Lumbar spinal stenosis"


def test_extract_clinical_facts_appends_one_audit_entry() -> None:
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response("facts")
        result = extract_clinical_facts(_state(audit_log=[]))

    assert len(result["audit_log"]) == 1
    entry = result["audit_log"][0]
    assert entry["node"] == "extract_clinical_facts"
    assert "timestamp" in entry
    assert "input_summary" in entry
    assert "output_summary" in entry


def test_extract_clinical_facts_audit_entry_has_no_raw_chart_text() -> None:
    sensitive = "SENSITIVE PATIENT DATA DO NOT LOG"
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response("facts")
        result = extract_clinical_facts(_state(chart_text=sensitive))

    entry = result["audit_log"][0]
    assert sensitive not in entry["input_summary"]
    assert sensitive not in entry["output_summary"]


def test_extract_clinical_facts_accumulates_existing_log() -> None:
    prior_entry: dict[str, str] = {
        "node": "prior",
        "timestamp": "t",
        "input_summary": "i",
        "output_summary": "o",
    }
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response("facts")
        result = extract_clinical_facts(_state(audit_log=[prior_entry]))

    assert len(result["audit_log"]) == 2
    assert result["audit_log"][0] is prior_entry


# ---------------------------------------------------------------------------
# evaluate_policy
# ---------------------------------------------------------------------------


def test_evaluate_policy_returns_evaluation_and_confidence() -> None:
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response(
            "Criterion 1: met\n**Overall Confidence:** 0.9"
        )
        result = evaluate_policy(_state())

    assert "evaluation" in result
    assert result["confidence"] == pytest.approx(0.9)


def test_evaluate_policy_appends_one_audit_entry() -> None:
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response(
            "evaluation\n**Overall Confidence:** 0.75"
        )
        result = evaluate_policy(_state(audit_log=[]))

    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0]["node"] == "evaluate_policy"


def test_evaluate_policy_audit_entry_has_no_raw_policy_text() -> None:
    sensitive = "SENSITIVE POLICY VERBATIM TEXT"
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response(
            "eval\n**Overall Confidence:** 0.8"
        )
        result = evaluate_policy(_state(policy_text=sensitive))

    entry = result["audit_log"][0]
    assert sensitive not in entry["input_summary"]
    assert sensitive not in entry["output_summary"]


# ---------------------------------------------------------------------------
# guardrail — PENDED cases
# ---------------------------------------------------------------------------


def test_guardrail_pends_when_extracted_facts_empty() -> None:
    result = guardrail(_state(extracted_facts=""))
    assert result["recommendation"] == "PENDED"
    assert "extracted_facts" in result["missing_fields"]


def test_guardrail_pends_when_evaluation_empty() -> None:
    result = guardrail(_state(evaluation=""))
    assert result["recommendation"] == "PENDED"
    assert "evaluation" in result["missing_fields"]


def test_guardrail_pends_when_confidence_below_threshold() -> None:
    result = guardrail(_state(confidence=0.5))
    assert result["recommendation"] == "PENDED"
    assert result["missing_fields"] == []


def test_guardrail_pends_at_just_below_threshold() -> None:
    result = guardrail(_state(confidence=0.699))
    assert result["recommendation"] == "PENDED"


# ---------------------------------------------------------------------------
# guardrail — passing cases
# ---------------------------------------------------------------------------


def test_guardrail_passes_when_complete_and_confident() -> None:
    result = guardrail(_state(confidence=0.85))
    assert result.get("recommendation") != "PENDED"
    assert result.get("missing_fields") == []


def test_guardrail_passes_at_exact_threshold() -> None:
    result = guardrail(_state(confidence=0.70))
    assert result.get("recommendation") != "PENDED"


def test_guardrail_appends_one_audit_entry() -> None:
    result = guardrail(_state(audit_log=[]))
    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0]["node"] == "guardrail"


# ---------------------------------------------------------------------------
# route_after_guardrail
# ---------------------------------------------------------------------------


def test_route_pended_goes_to_build_audit_trail() -> None:
    assert route_after_guardrail(_state(recommendation="PENDED")) == "build_audit_trail"


def test_route_empty_recommendation_goes_to_make_decision() -> None:
    assert route_after_guardrail(_state(recommendation="")) == "make_decision"


def test_route_approved_goes_to_make_decision() -> None:
    assert route_after_guardrail(_state(recommendation="APPROVED")) == "make_decision"


# ---------------------------------------------------------------------------
# make_decision
# ---------------------------------------------------------------------------


def test_make_decision_returns_required_fields() -> None:
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response(
            "**Recommendation:** APPROVED\n**Rationale:** Meets all criteria."
        )
        result = make_decision(_state())

    assert result["recommendation"] in ("APPROVED", "DENIED", "PENDED")
    assert isinstance(result["rationale"], str) and result["rationale"]
    assert isinstance(result["reference_number"], str) and result["reference_number"]


def test_make_decision_reference_number_format() -> None:
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response(
            "**Recommendation:** APPROVED\n**Rationale:** OK."
        )
        result = make_decision(_state())

    today = date.today().strftime("%Y%m%d")
    assert re.match(rf"^PA-{today}-[A-Z0-9]{{6}}$", result["reference_number"])


def test_make_decision_appends_one_audit_entry() -> None:
    with patch("modules.nodes.ChatAnthropic") as MockLLM:
        MockLLM.return_value.invoke.return_value = _mock_llm_response(
            "**Recommendation:** DENIED\n**Rationale:** Does not meet criteria."
        )
        result = make_decision(_state(audit_log=[]))

    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0]["node"] == "make_decision"
    assert "recommendation" in result["audit_log"][0]["output_summary"]


# ---------------------------------------------------------------------------
# build_audit_trail
# ---------------------------------------------------------------------------


def test_build_audit_trail_appends_final_entry() -> None:
    prior: list[dict[str, str]] = [
        {
            "node": "extract_clinical_facts",
            "timestamp": "t",
            "input_summary": "i",
            "output_summary": "o",
        }
    ]
    result = build_audit_trail(_state(audit_log=prior, recommendation="APPROVED"))
    assert len(result["audit_log"]) == 2
    assert result["audit_log"][-1]["node"] == "build_audit_trail"


def test_build_audit_trail_final_entry_contains_recommendation() -> None:
    result = build_audit_trail(_state(audit_log=[], recommendation="DENIED"))
    assert "DENIED" in result["audit_log"][-1]["output_summary"]


def test_build_audit_trail_no_raw_text_in_entry() -> None:
    result = build_audit_trail(
        _state(audit_log=[], chart_text="SENSITIVE_CHART", policy_text="SENSITIVE_POLICY")
    )
    entry = result["audit_log"][-1]
    assert "SENSITIVE_CHART" not in str(entry)
    assert "SENSITIVE_POLICY" not in str(entry)
