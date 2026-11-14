"""End-to-end demo flow in mock mode: Home -> Plan -> Session -> save quiz -> Plan -> replan."""
import json
import os
from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _btn(at, label):
    return next(b for b in at.button if b.label == label)


def _run(at):
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_demo_flow_plan_session_replan():
    os.chdir(ROOT)
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    _run(at)
    _btn(at, "Load demo data").click(); _run(at)
    assert at.title[0].value == "Your study plan"
    mock_schedule = json.load(open(os.path.join(ROOT, "mock_data", "schedule.json")))
    assert at.session_state["schedule"] == mock_schedule

    at.button(key="open-s1").click(); _run(at)
    at.radio(key="ans_s1-q1").set_value("2 A")
    _btn(at, "Check my answers").click(); _run(at)
    _btn(at, "Save my results").click(); _run(at)
    assert at.session_state["quiz_results"]["s1"]["score"] == 1 / 6

    _btn(at, "🗂️ Back to my plan").click(); _run(at)
    assert at.title[0].value == "Your study plan"
    n = len(at.session_state["plan"]["sessions"])
    _btn(at, "Update plan from my quiz results").click(); _run(at)
    ss = at.session_state
    assert len(ss["plan"]["sessions"]) == n + 1
    # calendar rebuilt from the demo timetable: 8 weekly classes over 2 weeks
    assert sum(e["kind"] == "class" for e in ss["calendar"]) == 16
    new_id = ss["plan"]["sessions"][-1]["id"]
    assert any(e.get("session_id") == new_id for e in ss["calendar"])

    at.button(key=f"open-{new_id}").click(); _run(at)
    assert new_id in at.session_state["session_content"]
