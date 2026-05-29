from modules.state import CHART_TEXT, MESSAGES, POLICY_TEXT, init_session_state


def test_constants_have_expected_values() -> None:
    assert MESSAGES == "messages"
    assert CHART_TEXT == "chart_text"
    assert POLICY_TEXT == "policy_text"


def test_init_sets_defaults_when_keys_absent(monkeypatch: object) -> None:
    fake_state: dict = {}
    monkeypatch.setattr("streamlit.session_state", fake_state)
    init_session_state()
    assert fake_state[MESSAGES] == []
    assert fake_state[CHART_TEXT] == ""
    assert fake_state[POLICY_TEXT] == ""


def test_init_does_not_overwrite_existing_values(monkeypatch: object) -> None:
    existing_messages = [{"role": "user", "content": "hello"}]
    fake_state: dict = {MESSAGES: existing_messages}
    monkeypatch.setattr("streamlit.session_state", fake_state)
    init_session_state()
    assert fake_state[MESSAGES] is existing_messages
