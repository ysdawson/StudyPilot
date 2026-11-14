"""Demo data loads only from a "Load demo data" button, never on startup (also in mock mode)."""
import os
import pytest
from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_KEYS = ("plan", "calendar", "schedule", "topics", "goal", "session_content", "quiz_results")
PAGES = ["pages/1_Plan.py", "pages/2_Calendar.py", "pages/3_Session.py"]


def _app(path, mock="1"):
    os.chdir(ROOT)
    at = AppTest.from_file(os.path.join(ROOT, path), default_timeout=30)
    at.secrets["MOCK_AI"] = mock
    return at


def _data_keys(at):
    return [k for k in DATA_KEYS if k in at.session_state]


@pytest.mark.parametrize("mock", ["1", "0"])
@pytest.mark.parametrize("page", PAGES)
def test_page_with_empty_session_shows_no_data(page, mock):
    at = _app(page, mock)
    at.run()
    assert not at.exception
    assert [i.value for i in at.info] == ["No study plan yet. Generate one on the Home page, or load the demo."]
    assert {b.label for b in at.button} == {"Go to Home", "Load demo data"}
    assert not at.title  # page content (plan, calendar, session) is not rendered
    assert _data_keys(at) == []


def test_home_startup_creates_no_schedule_plan_or_calendar():
    at = _app("app.py")
    at.run()
    assert not at.exception
    rows = at.session_state["schedule_rows"]
    assert len(rows) == 0 and list(rows.columns) == ["day", "start", "end", "title", "type"]  # empty editor
    assert _data_keys(at) == []


@pytest.mark.parametrize("page", PAGES)
def test_load_demo_button_fills_the_page(page):
    at = _app(page)
    at.run()
    next(b for b in at.button if b.label == "Load demo data").click()
    at.run()
    assert not at.exception
    assert not any(i.value.startswith("No study plan yet") for i in at.info)
    assert at.title  # the page now renders its content
    assert set(_data_keys(at)) >= {"plan", "calendar", "schedule", "topics"}


def test_load_demo_replaces_half_finished_real_data():
    at = _app("pages/2_Calendar.py")
    at.session_state["topics"] = {"course": "Other course", "topics": [], "deadlines": []}
    at.session_state["schedule_rows"] = "stale editor rows"
    at.run()
    next(b for b in at.button if b.label == "Load demo data").click()
    at.run()
    assert at.session_state["topics"]["course"] != "Other course"
    assert "schedule_rows" not in at.session_state


def test_go_to_home_button():
    at = _app("app.py")
    at.run()
    at.switch_page("pages/2_Calendar.py")
    at.run()
    at._page_hash = ""  # AppTest otherwise keeps forcing the page chosen by switch_page()
    next(b for b in at.button if b.label == "Go to Home").click()
    at.run()
    assert not at.exception
    assert [t.value for t in at.title] == ["StudyPilot"]


def test_generate_with_an_empty_timetable():
    import datetime, json
    at = _app("app.py")
    with open(os.path.join(ROOT, "mock_data", "calculus", "topics.json"), encoding="utf-8") as f:
        at.session_state["topics"] = json.load(f)
    at.session_state["data_source"] = "demo"
    at.run()
    assert len(at.session_state["schedule_rows"]) == 0
    at.selectbox(key="goal_choice").set_value("Other (type it)")
    at.run()
    at.text_input(key="goal_other").input("Test 1")
    at.date_input[0].set_value(datetime.date.today() + datetime.timedelta(days=14))
    next(b for b in at.button if "Generate" in b.label).click()
    at.run()
    assert not at.exception and not at.error
    ss = at.session_state
    assert ss["schedule"] == [] and not [e for e in ss["calendar"] if e["kind"] in ("class", "busy")]
    assert len([e for e in ss["calendar"] if e["kind"] == "study"]) == len(ss["plan"]["sessions"])
