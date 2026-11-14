"""Calendar week board: helpers, cards for the demo week, and Open -> Session."""
import os
from datetime import date
from streamlit.testing.v1 import AppTest

from core import board
from core.contracts import load_mock

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
    assert "Test 1 (your target date)" in side and "days" in side
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
