from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from modules.graph import stream_graph
from modules.pdf_utils import extract_text
from modules.state import AUDIT_LOG, CHART_TEXT, MESSAGES, POLICY_TEXT, init_session_state

st.set_page_config(page_title="Prior Authorization Assistant", layout="wide")

init_session_state()

# --- Sidebar: document uploads + Analyze button ---

with st.sidebar:
    st.header("Documents")

    chart_file = st.file_uploader(
        "Patient Chart (PDF)",
        type="pdf",
        key="chart_uploader",
    )

    policy_file = st.file_uploader(
        "Policy Document (PDF)",
        type="pdf",
        key="policy_uploader",
    )

    if chart_file is not None:
        try:
            text = extract_text(chart_file)
            if text != st.session_state[CHART_TEXT]:
                st.session_state[CHART_TEXT] = text
                st.session_state[MESSAGES].append(
                    {
                        "role": "assistant",
                        "content": f"**Patient chart uploaded.** Extracted text:\n\n{text}",
                    }
                )
        except ValueError as exc:
            st.error(str(exc))

    if policy_file is not None:
        try:
            text = extract_text(policy_file)
            if text != st.session_state[POLICY_TEXT]:
                st.session_state[POLICY_TEXT] = text
                st.session_state[MESSAGES].append(
                    {
                        "role": "assistant",
                        "content": f"**Policy document uploaded.** Extracted text:\n\n{text}",
                    }
                )
        except ValueError as exc:
            st.error(str(exc))

    st.divider()

    both_ready = bool(st.session_state[CHART_TEXT] and st.session_state[POLICY_TEXT])
    analyze_clicked = st.button(
        "Analyze",
        disabled=not both_ready,
        type="primary",
        use_container_width=True,
        help="Upload both documents to enable analysis.",
    )

# --- Analysis run (triggered by Analyze button) ---

if analyze_clicked:
    final_audit_log: list[dict[str, str]] = []

    with st.status("Extracting clinical facts…", expanded=True) as run_status:
        for update in stream_graph(st.session_state[CHART_TEXT], st.session_state[POLICY_TEXT]):
            node_name = list(update.keys())[0]
            node_data: dict = update[node_name]

            if "audit_log" in node_data:
                final_audit_log = node_data["audit_log"]

            if node_name == "extract_clinical_facts":
                facts = node_data.get("extracted_facts", "")
                st.session_state[MESSAGES].append(
                    {
                        "role": "assistant",
                        "content": f"**Clinical Facts Extracted:**\n\n{facts}",
                    }
                )
                run_status.update(label="Evaluating policy criteria…", state="running")

            elif node_name == "evaluate_policy":
                evaluation = node_data.get("evaluation", "")
                st.session_state[MESSAGES].append(
                    {
                        "role": "assistant",
                        "content": f"**Policy Evaluation:**\n\n{evaluation}",
                    }
                )
                run_status.update(label="Running guardrail checks…", state="running")

            elif node_name == "guardrail":
                if node_data.get("recommendation") == "PENDED":
                    rationale = node_data.get("rationale", "")
                    missing = node_data.get("missing_fields", [])
                    content = f"**Prior Authorization: PENDED**\n\n{rationale}"
                    if missing:
                        content += f"\n\n**Missing fields:** {', '.join(missing)}"
                    st.session_state[MESSAGES].append({"role": "assistant", "content": content})
                    run_status.update(
                        label="Analysis complete — prior authorization pended",
                        state="complete",
                    )
                else:
                    run_status.update(label="Making prior authorization decision…", state="running")

            elif node_name == "make_decision":
                rec = node_data.get("recommendation", "")
                rationale = node_data.get("rationale", "")
                ref = node_data.get("reference_number", "")
                st.session_state[MESSAGES].append(
                    {
                        "role": "assistant",
                        "content": (
                            f"**Prior Authorization: {rec}**\n\nReference: `{ref}`\n\n{rationale}"
                        ),
                    }
                )
                run_status.update(label="Finalizing audit trail…", state="running")

        run_status.update(label="Analysis complete", state="complete")

    st.session_state[AUDIT_LOG] = final_audit_log
    st.rerun()

# --- Main area: chat ---

st.title("Prior Authorization Assistant")

for message in st.session_state[MESSAGES]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question or describe the case…"):
    st.session_state[MESSAGES].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    stub_reply = (
        "Use the **Analyze** button in the sidebar to run the prior authorization pipeline."
    )
    st.session_state[MESSAGES].append({"role": "assistant", "content": stub_reply})
    with st.chat_message("assistant"):
        st.markdown(stub_reply)

# --- Audit trail (Phase 4) ---

if st.session_state.get(AUDIT_LOG):
    with st.expander("Audit Trail"):
        for entry in st.session_state[AUDIT_LOG]:
            st.markdown(f"**{entry['node']}** — `{entry['timestamp']}`")
            st.caption(f"Input:  {entry['input_summary']}")
            st.caption(f"Output: {entry['output_summary']}")
            st.divider()
