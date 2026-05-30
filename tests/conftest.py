import pytest


@pytest.fixture
def fake_session_state(monkeypatch):
    """A clean dict standing in for ``streamlit.session_state``.

    Tests that call Streamlit state functions can receive this fixture instead
    of manually calling ``monkeypatch.setattr`` in every test body.
    """
    state: dict = {}
    monkeypatch.setattr("streamlit.session_state", state)
    return state
