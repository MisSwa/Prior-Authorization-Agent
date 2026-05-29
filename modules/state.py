import streamlit as st

MESSAGES = "messages"
CHART_TEXT = "chart_text"
POLICY_TEXT = "policy_text"


def init_session_state() -> None:
    if MESSAGES not in st.session_state:
        st.session_state[MESSAGES] = []
    if CHART_TEXT not in st.session_state:
        st.session_state[CHART_TEXT] = ""
    if POLICY_TEXT not in st.session_state:
        st.session_state[POLICY_TEXT] = ""
