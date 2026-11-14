"""OWNER: Member 2. Demo data loading, only ever called from a "Load demo data" button."""
from core.contracts import (K_DOC_TEXT, K_TOPICS, K_GOAL, K_PLAN, K_CONTENT, K_SCHEDULE,
                            K_CALENDAR, K_RESULTS, K_CURRENT, load_mock_state)

_APP_KEYS = (K_DOC_TEXT, K_TOPICS, K_GOAL, K_PLAN, K_CONTENT, K_SCHEDULE,
             K_CALENDAR, K_RESULTS, K_CURRENT)
_SCHEDULE_EDITOR_KEYS = ("schedule_rows", "schedule_editor")  # core/schedule_input.py


def load_demo_data(st) -> None:
    """Replace everything with the demo. load_mock_state only fills missing keys,
    so clear first: otherwise a half-finished real session (e.g. topics from
    uploaded PDFs) would mix with the demo plan."""
    for key in _APP_KEYS + _SCHEDULE_EDITOR_KEYS:
        st.session_state.pop(key, None)
    load_mock_state(st)
