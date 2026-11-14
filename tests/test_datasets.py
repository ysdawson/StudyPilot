"""Two demo datasets (yassine default, calculus), course deadlines, mock AI per dataset."""
import os
import pytest
from streamlit.testing.v1 import AppTest

from core.demo import read_file, DATASETS, DEFAULT_DATASET
from core.schedule_input import parse_deadlines_csv
from core.scheduler import all_deadlines

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED = {"yassine": ("Network Applications I (243-5E3)", 10, 10),   # course, timetable rows, deadlines
            "calculus": ("Calculus I", 15, 0)}


def _home():
    os.chdir(ROOT)
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    at.run()
    return at


def _load(at, dataset):
    at.selectbox(key="demo_pick_home").set_value(dataset)
    next(b for b in at.button if b.label == "Load demo data").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_default_is_yassine_and_files_are_complete():
    assert DEFAULT_DATASET == "yassine" and set(DATASETS) == {"yassine", "calculus"}
    for ds in DATASETS:
        for f in ("topics.json", "plan.json", "session_s1.json", "schedule.json", "calendar.json", "deadlines.json"):
            assert read_file(ds, f) is not None
    at = _home()
    assert at.selectbox(key="demo_pick_home").value == "yassine"


@pytest.mark.parametrize("first,second", [("yassine", "calculus"), ("calculus", "yassine")])
def test_loading_a_dataset_replaces_the_other(first, second):
    at = _home()
    _load(at, first)
    at.switch_page("app.py"); at.run(); at._page_hash = ""
    _load(at, second)
    ss = at.session_state
    course, n_sched, n_dl = EXPECTED[second]
    assert ss["demo_dataset"] == second
    assert ss["goal"]["course"] == course
    assert ss["schedule"] == read_file(second, "schedule.json") and len(ss["schedule"]) == n_sched
    assert ss["course_deadlines"] == read_file(second, "deadlines.json") and len(ss["course_deadlines"]) == n_dl
    assert ss["calendar"] == read_file(second, "calendar.json")
    other_ids = {s["id"] + s["title"] for s in read_file(first, "plan.json")["sessions"]}
    assert not other_ids & {s["id"] + s["title"] for s in ss["plan"]["sessions"]}
    assert set(ss["session_content"]) <= {f[8:-5] for f in os.listdir(os.path.join(ROOT, "mock_data", second))
                                          if f.startswith("session_")}


def test_deadlines_csv_import():
    with open(os.path.join(ROOT, "sample_data", "yassine", "Deadlines_Fall2026.csv"), encoding="utf-8") as f:
        rows = parse_deadlines_csv(f.read())
    assert len(rows) == 10 and rows == sorted(rows, key=lambda d: d["date"])
    assert set(rows[0]) == {"course", "title", "date", "weight", "source"}
    assert all("estimated" in r["source"] or "unknown" in r["source"] for r in rows)
    bad = "Course,Title,Date,Weight,Source\nX,No date,,1%,s\nY,Bad date,26-11-2026,1%,s\nZ,Ok,2026-11-20,5%,official\n"
    assert parse_deadlines_csv(bad) == [{"course": "Z", "title": "Ok", "date": "2026-11-20",
                                         "weight": "5%", "source": "official"}]


def test_course_deadlines_on_calendar_without_duplicating_the_goal():
    goal = read_file("yassine", "plan.json")["goal"]
    merged = all_deadlines([], read_file("yassine", "deadlines.json"), goal)
    assert len(merged) == 10  # "Class Test 4" is already a course deadline: not added twice
    assert "Network Applications I (243-5E3): Class Test 4" in {d["title"] for d in merged}
    cal = read_file("yassine", "calendar.json")
    dl = [e for e in cal if e["kind"] == "deadline"]
    assert len(dl) == 10 and all(": " in e["title"] for e in dl)
    study = [e for e in cal if e["kind"] == "study"]
    assert len(study) == len(read_file("yassine", "plan.json")["sessions"])
    assert all(e["end"][:10] < goal["deadline"] for e in study)


def test_board_shows_deadlines_with_their_source():
    at = _home()
    _load(at, "yassine")
    at.switch_page("pages/2_Calendar.py"); at.run(); at._page_hash = ""
    assert not at.exception
    md = [m.value for m in at.markdown]
    cards = [m for m in md if 'class="sp-card' in m and ">Deadline<" in m]
    assert any("Homework 3: Web recon" in c and "day estimated" in c for c in cards)  # Thu Nov 19
    side = " ".join(md)
    assert "Class Test 4 in" in side                                  # goal countdown
    assert "#### Next deadlines" in side and side.count("sp-src") >= 3  # next 3 deadlines with source


@pytest.mark.parametrize("dataset", ["yassine", "calculus"])
def test_mock_ai_functions_follow_the_selected_dataset(dataset):
    at = AppTest.from_string(
        "import streamlit as st\n"
        "from core import ai_engine as ae\n"
        f"st.session_state['demo_dataset'] = '{dataset}'\n"
        "t = ae.extract_topics('x')\n"
        "p = ae.make_plan(t, {'course': 'c', 'target': 'x', 'deadline': '2026-12-01', 'start_date': '2026-11-16',"
        " 'hours_per_week': 4.0, 'target_grade': 'A'})\n"
        "s = ae.make_session(p['sessions'][0], t, '')\n"
        "ev = ae.parse_timetable_image(b'', 'image/png', '2026-11-16')\n"
        "st.session_state['out'] = (t['course'], len(p['sessions']), s['questions'][0]['session_id'], len(ev))\n",
        default_timeout=30)
    os.chdir(ROOT)
    at.secrets["MOCK_AI"] = "1"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    course, n_sessions, qsid, n_events = at.session_state["out"]
    assert course == read_file(dataset, "topics.json")["course"]
    assert n_sessions == len(read_file(dataset, "plan.json")["sessions"])
    assert qsid == read_file(dataset, "plan.json")["sessions"][0]["id"]
    assert n_events == len(read_file(dataset, "schedule.json"))
