"""OWNER: Member 2. Demo datasets, loaded ONLY from a "Load demo data" button.

Each dataset is a folder mock_data/<name>/ with topics.json, plan.json, session_*.json,
schedule.json, calendar.json and deadlines.json. The selected dataset is kept per
visitor in st.session_state[DATASET_KEY] (never a module global: on Streamlit Cloud
globals are shared by all visitors). Mock-mode AI functions read from it too.
"""
import json
import os
from core.contracts import (K_DOC_TEXT, K_TOPICS, K_GOAL, K_PLAN, K_CONTENT, K_SCHEDULE,
                            K_CALENDAR, K_RESULTS, K_CURRENT, MOCK_DIR)

DATASET_KEY = "demo_dataset"
DATASETS = {"yassine": "1 — My real term (Network Applications I)",
            "calculus": "2 — Calculus I Test 1"}
DEFAULT_DATASET = "yassine"
DEADLINES_KEY = "course_deadlines"  # owned by Home / core/schedule_input.py
DATA_SOURCE_KEY = "data_source"     # "demo" (Load demo data) | "user" (Analyze my documents)

_APP_KEYS = (K_DOC_TEXT, K_TOPICS, K_GOAL, K_PLAN, K_CONTENT, K_SCHEDULE,
             K_CALENDAR, K_RESULTS, K_CURRENT, DEADLINES_KEY, DATA_SOURCE_KEY)
_WIDGET_KEYS = ("schedule_rows", "schedule_editor", "board_week")


def selected_dataset(st) -> str:
    name = st.session_state.get(DATASET_KEY, DEFAULT_DATASET)
    return name if name in DATASETS else DEFAULT_DATASET


def dataset_dir(name: str) -> str:
    return os.path.join(MOCK_DIR, name)


def read_file(dataset: str, filename: str):
    with open(os.path.join(dataset_dir(dataset), filename), encoding="utf-8") as f:
        return json.load(f)


def load_mock(st, filename: str):
    """Mock-mode AI functions: the file from the currently selected dataset."""
    return read_file(selected_dataset(st), filename)


def session_files(st) -> list[str]:
    return sorted(f for f in os.listdir(dataset_dir(selected_dataset(st)))
                  if f.startswith("session_") and f.endswith(".json"))


def load_demo_data(st, dataset: str | None = None) -> None:
    """Replace everything with one demo dataset. Clears all app state first, so
    nothing from another dataset or a half-finished real session is left over."""
    dataset = dataset if dataset in DATASETS else selected_dataset(st)
    for key in _APP_KEYS + _WIDGET_KEYS:
        st.session_state.pop(key, None)
    st.session_state[DATASET_KEY] = dataset
    st.session_state[DATA_SOURCE_KEY] = "demo"  # AI functions answer from this dataset, instantly
    ss = st.session_state
    plan = read_file(dataset, "plan.json")
    ss[K_DOC_TEXT] = "Mock course text."
    ss[K_TOPICS] = read_file(dataset, "topics.json")
    ss[K_PLAN] = plan
    ss[K_GOAL] = plan["goal"]
    ss[K_CONTENT] = {f[len("session_"):-len(".json")]: read_file(dataset, f) for f in session_files(st)}
    ss[K_SCHEDULE] = read_file(dataset, "schedule.json")
    ss[K_CALENDAR] = read_file(dataset, "calendar.json")
    ss[K_RESULTS] = {}
    ss[K_CURRENT] = plan["sessions"][0]["id"] if plan["sessions"] else "s1"
    ss[DEADLINES_KEY] = read_file(dataset, "deadlines.json")


def demo_picker(st, container, key: str) -> str:
    """The 'Demo data' selectbox. Its own widget key: Streamlit deletes widget state on
    pages that don't draw the widget, so the choice is copied to DATASET_KEY on load."""
    names = list(DATASETS)
    return container.selectbox("Demo data", names, index=names.index(selected_dataset(st)),
                               format_func=DATASETS.get, key=key)
