import streamlit as st

MESSAGES = "messages"
CHART_TEXT = "chart_text"
POLICY_TEXT = "policy_text"
AUDIT_LOG = "audit_log"


def init_session_state() -> None:
    if MESSAGES not in st.session_state:
        st.session_state[MESSAGES] = []
    if CHART_TEXT not in st.session_state:
        st.session_state[CHART_TEXT] = ""
    if POLICY_TEXT not in st.session_state:
        st.session_state[POLICY_TEXT] = ""
    if AUDIT_LOG not in st.session_state:
        st.session_state[AUDIT_LOG] = []
