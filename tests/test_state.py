import pytest

from modules.state import CHART_TEXT, MESSAGES, POLICY_TEXT, init_session_state


def test_constants_have_expected_values() -> None:
    assert MESSAGES == "messages"
    assert CHART_TEXT == "chart_text"
    assert POLICY_TEXT == "policy_text"


def test_init_sets_defaults_when_keys_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_state: dict = {}
    monkeypatch.setattr("streamlit.session_state", fake_state)
    init_session_state()
    assert fake_state[MESSAGES] == []
    assert fake_state[CHART_TEXT] == ""
    assert fake_state[POLICY_TEXT] == ""


def test_init_does_not_overwrite_existing_values(monkeypatch: pytest.MonkeyPatch) -> None:
    existing_messages = [{"role": "user", "content": "hello"}]
    fake_state: dict = {MESSAGES: existing_messages}
    monkeypatch.setattr("streamlit.session_state", fake_state)
    init_session_state()
    assert fake_state[MESSAGES] is existing_messages


# ---------------------------------------------------------------------------
# Preservation: each individual key is left alone when pre-populated
# ---------------------------------------------------------------------------


def test_chart_text_not_overwritten_when_present(fake_session_state: dict) -> None:
    """A pre-existing chart text value must survive initialisation."""
    existing = "MRI results: within normal limits"
    fake_session_state[CHART_TEXT] = existing
    init_session_state()
    assert fake_session_state[CHART_TEXT] is existing


def test_policy_text_not_overwritten_when_present(fake_session_state: dict) -> None:
    """A pre-existing policy text value must survive initialisation."""
    existing = "Coverage requires prior auth for advanced imaging"
    fake_session_state[POLICY_TEXT] = existing
    init_session_state()
    assert fake_session_state[POLICY_TEXT] is existing


# ---------------------------------------------------------------------------
# Partial state: only the absent keys should be filled in
# ---------------------------------------------------------------------------


def test_partial_state_fills_only_missing_keys(fake_session_state: dict) -> None:
    """When only MESSAGES is present the two text keys must be defaulted."""
    existing_messages = [{"role": "user", "content": "hi"}]
    fake_session_state[MESSAGES] = existing_messages
    init_session_state()
    assert fake_session_state[MESSAGES] is existing_messages
    assert fake_session_state[CHART_TEXT] == ""
    assert fake_session_state[POLICY_TEXT] == ""


# ---------------------------------------------------------------------------
# Idempotence: calling init multiple times must not change anything
# ---------------------------------------------------------------------------


def test_multiple_sequential_inits_are_idempotent(fake_session_state: dict) -> None:
    """Calling init_session_state twice must leave state identical to once."""
    init_session_state()
    messages_ref = fake_session_state[MESSAGES]
    init_session_state()
    init_session_state()
    assert fake_session_state[MESSAGES] is messages_ref
    assert fake_session_state[CHART_TEXT] == ""
    assert fake_session_state[POLICY_TEXT] == ""


# ---------------------------------------------------------------------------
# Type assertions: defaults must be the correct Python types
# ---------------------------------------------------------------------------


def test_messages_default_is_a_list(fake_session_state: dict) -> None:
    init_session_state()
    assert isinstance(fake_session_state[MESSAGES], list)


def test_chart_text_default_is_an_empty_string(fake_session_state: dict) -> None:
    init_session_state()
    assert fake_session_state[CHART_TEXT] == ""
    assert isinstance(fake_session_state[CHART_TEXT], str)


def test_policy_text_default_is_an_empty_string(fake_session_state: dict) -> None:
    init_session_state()
    assert fake_session_state[POLICY_TEXT] == ""
    assert isinstance(fake_session_state[POLICY_TEXT], str)
