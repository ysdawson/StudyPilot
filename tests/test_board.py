"""Calendar week board: helpers, cards for the demo week, and Open -> Session."""
import os
from datetime import date
from streamlit.testing.v1 import AppTest

from core import board
from core.demo import read_file


def load_mock(name):
    return read_file("calculus", name)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _demo():
    os.chdir(ROOT)
    return load_mock("calendar.json"), load_mock("plan.json")


def test_same_course_same_colour():
    assert board.course_key("Mechanics Lab") == board.course_key("Mechanics (Physics NYA)") == "mechanics"
    assert board.course_key("General Chemistry") == board.course_key("Chemistry Lab") == "chemistry"
    assert board.course_key("Calculus I (201-NYA-05)") == "calculus"
    cal, _ = _demo()
    colours = board.course_colors(cal)
    by_title = {e["title"]: board.event_colors(e, colours) for e in cal if e["kind"] == "class"}
    assert by_title["Mechanics Lab"] == by_title["Mechanics (Physics NYA)"]
    assert by_title["English 603 - Literary Genres"] != by_title["Calculus I (201-NYA-05)"]


def test_demo_week_helpers():
    cal, plan = _demo()
    monday = board.monday_of(date.fromisoformat(plan["goal"]["start_date"]))
    days = board.events_by_day(cal, monday)
    assert len(days) == 7
    for evs in days.values():
        assert [e["start"] for e in evs] == sorted(e["start"] for e in evs)
    week = [e for evs in days.values() for e in evs]
    assert {e["kind"] for e in week} == {"class", "busy", "study"}
    nxt = board.up_next(cal, done={"s1"})
    assert len(nxt) == 5 and "s1" not in {e["session_id"] for e in nxt}
    assert [e["start"] for e in nxt] == sorted(e["start"] for e in nxt)
    assert board.countdowns(cal, date(2026, 11, 14)) == [("Test 1 (your target date)", 19)]
    done_min, planned = board.week_progress(cal, monday, done={"s1"})
    assert planned == sum(board.minutes(e) for e in week if e["kind"] == "study") and done_min == 30


def _calendar_with_demo():
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    at.run()
    at.switch_page("pages/2_Calendar.py")
    at.run()
    at._page_hash = ""  # AppTest otherwise keeps forcing the page chosen by switch_page()
    at.selectbox(key="demo_pick_calendar").set_value("calculus")
    next(b for b in at.button if b.label == "Load demo data").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_board_renders_cards_for_the_demo_week():
    cal, plan = _demo()
    at = _calendar_with_demo()
    assert [t.value for t in at.title] == ["Your week"]
    cards = [m.value for m in at.markdown if 'class="sp-card' in m.value]
    monday = board.monday_of(date.fromisoformat(plan["goal"]["start_date"]))
    week = [e for evs in board.events_by_day(cal, monday).values() for e in evs]
    assert len(cards) == len(week)
    assert sum('>Study<' in c for c in cards) == sum(e["kind"] == "study" for e in week)
    assert sum('>Work<' in c for c in cards) == sum(e["kind"] == "busy" for e in week) == 2
    assert any("Part-time job" in c for c in cards)
    side = " ".join(m.value for m in at.markdown)
    assert "Test 1 in 19 days" in side or ("Test 1 in" in side and "days" in side)
    assert "your target date" in side  # the goal is labelled as the student's own date
    # week navigation
    next(b for b in at.button if b.key == "week-next").click()
    at.run()
    assert at.session_state["board_week"] == date(2026, 11, 23)


def test_study_card_open_goes_to_session():
    at = _calendar_with_demo()
    open_btn = next(b for b in at.button if (b.key or "").startswith("board-open-study-"))
    sid = open_btn.key.removeprefix("board-open-study-")
    open_btn.click()
    at.run()
    assert not at.exception
    assert at.session_state["current_session_id"] == sid
    plan_titles = {s["id"]: s["title"] for s in at.session_state["plan"]["sessions"]}
    assert [t.value for t in at.title] == [plan_titles[sid]]  # Session page title


def test_time_grid_view_renders_the_calendar_component():
    at = _calendar_with_demo()
    at.radio(key="cal_view").set_value("🕒 Time grid")
    at.run()
    assert not at.exception
    assert not [m for m in at.markdown if 'class="sp-card' in m.value]  # board not drawn
    assert any(getattr(c, "type", "") == "component_instance" or "component" in type(c).__name__.lower()
               for c in at.main)


def _add_task(at, title, day, start, end, blocks=True):
    form_inputs = [t for t in at.text_input]
    next(t for t in form_inputs if t.label == "Title").input(title)
    next(t for t in form_inputs if t.label == "From (HH:MM)").input(start)
    next(t for t in form_inputs if t.label == "To (HH:MM)").input(end)
    next(d for d in at.date_input if d.label == "Date").set_value(day)
    cb = next(c for c in at.checkbox if c.label == "Blocks study time?")
    cb.check() if blocks else cb.uncheck()
    next(b for b in at.button if b.label == "Add task").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_own_task_shows_on_board_and_can_be_removed():
    at = _calendar_with_demo()
    _add_task(at, "Dentist", date(2026, 11, 18), "15:00", "16:00", blocks=False)
    tasks = at.session_state["custom_tasks"]
    assert tasks == [{"id": "task-1", "title": "Dentist", "date": "2026-11-18", "start": "15:00",
                      "end": "16:00", "blocks": False}]
    cards = [m.value for m in at.markdown if 'class="sp-card' in m.value and "Dentist" in m.value]
    assert len(cards) == 1 and ">Task<" in cards[0]
    next(b for b in at.button if b.key == "rm-task-1").click()
    at.run()
    assert at.session_state["custom_tasks"] == []
    assert not [m for m in at.markdown if "Dentist" in m.value]


def test_invalid_task_times_are_rejected():
    at = _calendar_with_demo()
    _add_task(at, "Bad", date(2026, 11, 18), "16:00", "15:00")
    assert at.session_state["custom_tasks"] == []
    assert any("before" in w.value for w in at.warning)


def test_blocking_task_is_avoided_by_replanning():
    from datetime import datetime, timedelta
    from core.scheduler import BUFFER, FMT
    at = _calendar_with_demo()
    ss = at.session_state
    target = next(e for e in ss["calendar"] if e.get("session_id") == "s3")  # a session not done yet
    s = datetime.strptime(target["start"], FMT)
    _add_task(at, "Shift swap", s.date(), (s - timedelta(minutes=30)).strftime("%H:%M"),
              (s + timedelta(hours=3)).strftime("%H:%M"), blocks=True)
    task = ss["custom_tasks"][0]
    ts, te = datetime.strptime(f"{task['date']}T{task['start']}", FMT), datetime.strptime(f"{task['date']}T{task['end']}", FMT)
    ss["quiz_results"] = {"s1": {"session_id": "s1", "results": [], "score": 0.2, "topic_scores": {"t1": 0.2}}}
    at.switch_page("pages/1_Plan.py"); at.run(); at._page_hash = ""
    next(b for b in at.button if b.label == "Update plan from my quiz results").click()
    at.run()
    assert not at.exception
    study = [e for e in at.session_state["calendar"] if e["kind"] == "study"]
    assert study and not [e for e in study if datetime.strptime(e["start"], FMT) < te + BUFFER
                          and ts - BUFFER < datetime.strptime(e["end"], FMT)]
    assert not [e for e in at.session_state["calendar"] if e["id"].startswith("task-")]  # drawn, not stored
