from collections.abc import Generator
from typing import Any

from langgraph.graph import END, StateGraph

from modules.nodes import (
    AuthState,
    build_audit_trail,
    evaluate_policy,
    extract_clinical_facts,
    guardrail,
    make_decision,
    route_after_guardrail,
)


def _build_graph() -> Any:
    builder: StateGraph = StateGraph(AuthState)

    builder.add_node("extract_clinical_facts", extract_clinical_facts)
    builder.add_node("evaluate_policy", evaluate_policy)
    builder.add_node("guardrail", guardrail)
    builder.add_node("make_decision", make_decision)
    builder.add_node("build_audit_trail", build_audit_trail)

    builder.set_entry_point("extract_clinical_facts")
    builder.add_edge("extract_clinical_facts", "evaluate_policy")
    builder.add_edge("evaluate_policy", "guardrail")
    builder.add_conditional_edges("guardrail", route_after_guardrail)
    builder.add_edge("make_decision", "build_audit_trail")
    builder.add_edge("build_audit_trail", END)

    return builder.compile()


_graph = _build_graph()


def _initial_state(chart_text: str, policy_text: str) -> AuthState:
    return {
        "chart_text": chart_text,
        "policy_text": policy_text,
        "extracted_facts": "",
        "evaluation": "",
        "confidence": 0.0,
        "recommendation": "",
        "rationale": "",
        "reference_number": "",
        "missing_fields": [],
        "audit_log": [],
    }


def run_graph(chart_text: str, policy_text: str) -> AuthState:
    """Invoke the full graph synchronously and return the final state."""
    result = _graph.invoke(_initial_state(chart_text, policy_text))
    return result  # type: ignore[return-value]


def stream_graph(chart_text: str, policy_text: str) -> Generator[dict[str, Any], None, None]:
    """Yield per-node state updates as each node completes.

    Each yielded value is ``{node_name: {changed_keys: values}}``.
    """
    yield from _graph.stream(_initial_state(chart_text, policy_text), stream_mode="updates")
