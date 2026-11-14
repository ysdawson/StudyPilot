"""CSV timetable import, Home 'Generate' with no deadlines, mock replan targeting."""
import datetime
import json
import os
import pandas as pd
from streamlit.testing.v1 import AppTest

from core.schedule_input import parse_timetable_csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_parse_calculus_timetable_csv_keeps_only_classes():
    with open(os.path.join(ROOT, "sample_data", "calculus", "Weekly_Timetable.csv"), encoding="utf-8") as f:
        rows = parse_timetable_csv(f.read())  # file starts with a BOM; also handles it
    assert rows == [
        {"day": "Tue", "start": "18:00", "end": "21:00", "title": "Calculus I class", "type": "class"},
        {"day": "Thu", "start": "18:00", "end": "21:00", "title": "Calculus I class", "type": "class"},
    ]


def test_parse_csv_bom_12h_times_and_bad_rows():
    text = ("﻿Day,Date,Start,End,Activity,Type\n"
            ",2026-11-16,12:30 PM,1:15 PM,Lab,class\n"      # day from date, lower-case type
            "Friday,,9:00 AM,,Broken,Class\n"               # no end time: skipped
            "Saturday,,10:00 AM,11:00 AM,Gym,Busy\n")       # not a class
    assert parse_timetable_csv(text) == [{"day": "Mon", "start": "12:30", "end": "13:15", "title": "Lab", "type": "class"}]


def test_parse_full_timetable_work_rows_become_busy():
    with open(os.path.join(ROOT, "sample_data", "calculus", "Weekly_Timetable_Full.csv"), encoding="utf-8") as f:
        rows = parse_timetable_csv(f.read())
    assert sum(r["type"] == "class" for r in rows) == 13
    assert [r for r in rows if r["type"] == "busy"] == [
        {"day": "Wed", "start": "16:00", "end": "20:00", "title": "Part-time job", "type": "busy"},
        {"day": "Sat", "start": "10:00", "end": "16:00", "title": "Part-time job", "type": "busy"},
    ]
    assert not any(r["day"] == "Sun" for r in rows)  # the Free row (no times) is skipped


def test_mock_schedule_keeps_busy_events_and_study_avoids_them():
    from datetime import datetime
    from core.demo import read_file
    load_mock = lambda n: read_file("calculus", n)
    from core.scheduler import BUFFER, FMT
    os.chdir(ROOT)
    schedule, cal = load_mock("schedule.json"), load_mock("calendar.json")
    assert {e["kind"] for e in schedule} == {"class", "busy"}
    dt = lambda s: datetime.strptime(s, FMT)
    blocked = [e for e in cal if e["kind"] in ("class", "busy")]
    study = [e for e in cal if e["kind"] == "study"]
    assert len(study) == len(load_mock("plan.json")["sessions"])
    assert not [(s["id"], b["id"]) for s in study for b in blocked
                if dt(s["start"]) < dt(b["end"]) + BUFFER and dt(b["start"]) - BUFFER < dt(s["end"])]


def _app():
    os.chdir(ROOT)
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    return at


def test_home_generate_with_no_deadlines_uses_other_and_manual_date():
    at = _app()
    topics = json.load(open(os.path.join(ROOT, "mock_data", "calculus", "topics.json"), encoding="utf-8"))
    topics["deadlines"] = []
    at.session_state["topics"] = topics
    at.session_state["data_source"] = "demo"  # mock plan; a user's own topics would use the real AI
    at.session_state["schedule_rows"] = pd.DataFrame(parse_timetable_csv(
        open(os.path.join(ROOT, "sample_data", "calculus", "Weekly_Timetable.csv"), encoding="utf-8").read()))
    at.run()
    assert not at.exception
    assert at.selectbox[0].options == ["Other"]
    next(t for t in at.text_input if t.label.startswith("If other")).input("Test 1")
    day = datetime.date.today() + datetime.timedelta(days=17)
    at.date_input[0].set_value(day)
    next(b for b in at.button if "Generate" in b.label).click()
    at.run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    ss = at.session_state
    assert ss["goal"]["target"] == "Test 1" and ss["goal"]["deadline"] == day.isoformat()
    deadlines = [e for e in ss["calendar"] if e["kind"] == "deadline"]
    assert [(d["title"], d["start"][:10]) for d in deadlines] == [("Test 1 (your target date)", day.isoformat())]
    # CSV classes (Tue/Thu 18:00) are in the calendar; study never overlaps them
    classes = [e for e in ss["calendar"] if e["kind"] == "class"]
    assert classes and all(e["start"][11:] == "18:00" for e in classes)


def test_mock_replan_reviews_the_weakest_topic():
    at = AppTest.from_string(
        "import streamlit as st\n"
        "st.session_state['data_source'] = 'demo'\n"
        "from core.demo import read_file\n"
        "load_mock = lambda n: read_file('calculus', n)\n"
        "from core.ai_engine import replan\n"
        "plan, topics = load_mock('plan.json'), load_mock('topics.json')\n"
        "ids = [t['id'] for t in topics['topics']]\n"
        "res = {'s1': {'session_id': 's1', 'results': [], 'score': 0.5,\n"
        "              'topic_scores': {ids[0]: 0.9, ids[-1]: 0.2}}}\n"
        "st.session_state['out'] = (replan(plan, topics, res)['sessions'][-1], ids[-1])\n",
        default_timeout=30)
    os.chdir(ROOT)
    at.secrets["MOCK_AI"] = "1"
    at.run()
    assert not at.exception
    new, weakest = at.session_state["out"]
    assert new["kind"] == "review" and new["topic_id"] == weakest
