import streamlit as st

from modules.state import CHART_TEXT, MESSAGES, POLICY_TEXT, init_session_state
from modules.pdf_utils import extract_text

st.set_page_config(page_title="Prior Authorization Assistant", layout="wide")

init_session_state()

# --- Sidebar: document uploads ---

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

# --- Main area: chat ---

st.title("Prior Authorization Assistant")

for message in st.session_state[MESSAGES]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question or describe the case…"):
    st.session_state[MESSAGES].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    stub_reply = "Agent pipeline not yet wired — Phase 2 coming."
    st.session_state[MESSAGES].append({"role": "assistant", "content": stub_reply})
    with st.chat_message("assistant"):
        st.markdown(stub_reply)
