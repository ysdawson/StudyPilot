import json
from datetime import datetime
from core.scheduler import schedule_sessions, build_calendar, FMT

plan = json.load(open("mock_data/calculus/plan.json"))
busy = json.load(open("mock_data/calculus/schedule.json"))


def overlaps(a, b):
    return datetime.strptime(a["start"], FMT) < datetime.strptime(b["end"], FMT) and \
           datetime.strptime(b["start"], FMT) < datetime.strptime(a["end"], FMT)


def test_all_sessions_placed_before_deadline():
    ev = schedule_sessions(plan, busy)
    assert len(ev) == len(plan["sessions"])
    assert all(e["end"][:10] < plan["goal"]["deadline"] for e in ev)


def test_no_overlap_with_classes():
    ev = schedule_sessions(plan, busy)
    cal = build_calendar(busy, [], [], plan["goal"]["start_date"], plan["goal"]["deadline"])
    assert not any(overlaps(s, c) for s in ev for c in cal)


def test_daily_cap():
    ev = schedule_sessions(plan, busy, max_minutes_per_day=60)
    per_day = {}
    for e in ev:
        m = (datetime.strptime(e["end"], FMT) - datetime.strptime(e["start"], FMT)).seconds // 60
        per_day[e["start"][:10]] = per_day.get(e["start"][:10], 0) + m
    assert all(v <= 60 for v in per_day.values())


def test_calendar_has_deadline_and_study():
    ev = schedule_sessions(plan, busy)
    cal = build_calendar(busy, ev, [{"title": "Midterm", "date": "2026-11-27"}], "2026-11-16", "2026-11-27")
    assert any(e["kind"] == "deadline" for e in cal)
    assert sum(e["kind"] == "study" for e in cal) == len(ev)


def test_sessions_spread_until_deadline_not_crammed():
    ev = schedule_sessions(plan, busy)
    days = sorted({e["start"][:10] for e in ev})
    span = (datetime.fromisoformat(plan["goal"]["deadline"]) - datetime.fromisoformat(plan["goal"]["start_date"])).days
    # uses most of the available days instead of filling the first ones to the daily cap
    assert len(days) >= min(len(ev), span) * 0.8


def test_study_days_and_window_are_respected():
    days = {0, 2, 4}  # Mon, Wed, Fri
    ev = schedule_sessions(plan, busy, study_days=days, day_start="17:00", day_end="22:00")
    assert ev
    for e in ev:
        start, end = datetime.strptime(e["start"], FMT), datetime.strptime(e["end"], FMT)
        assert start.weekday() in days
        assert start.strftime("%H:%M") >= "17:00" and end.strftime("%H:%M") <= "22:00"


def test_default_study_days_unchanged():
    assert schedule_sessions(plan, busy) == schedule_sessions(plan, busy, study_days=None)


def test_per_day_availability_windows():
    avail = {0: ("17:00", "22:00"), 2: ("12:00", "15:00"), 5: ("09:00", "13:00")}  # Mon, Wed, Sat
    ev = schedule_sessions(plan, busy, max_minutes_per_day=60, availability=avail)
    assert ev
    cal = build_calendar(busy, [], [], plan["goal"]["start_date"], plan["goal"]["deadline"])
    per_day = {}
    for e in ev:
        s, en = datetime.strptime(e["start"], FMT), datetime.strptime(e["end"], FMT)
        assert s.weekday() in avail
        lo, hi = avail[s.weekday()]
        assert s.strftime("%H:%M") >= lo and en.strftime("%H:%M") <= hi
        per_day[e["start"][:10]] = per_day.get(e["start"][:10], 0) + (en - s).seconds // 60
    assert all(v <= 60 for v in per_day.values())
    from core.scheduler import BUFFER
    clash = [e for e in ev for c in cal if datetime.strptime(e["start"], FMT) < datetime.strptime(c["end"], FMT) + BUFFER
             and datetime.strptime(c["start"], FMT) - BUFFER < datetime.strptime(e["end"], FMT)]
    assert not clash


def test_availability_rows_validation():
    from core.schedule_input import availability_from_rows
    rows = [{"day": "Mon", "study": True, "from": "17:00", "to": "22:00"},
            {"day": "Tue", "study": True, "from": "20:00", "to": "18:00"},   # invalid: skipped
            {"day": "Wed", "study": False, "from": "10:00", "to": "12:00"},  # not studying
            {"day": "Sat", "study": True, "from": "9:00", "to": "13:00"}]
    avail, problems = availability_from_rows(rows)
    assert avail == {0: ("17:00", "22:00"), 5: ("09:00", "13:00")}
    assert len(problems) == 1 and problems[0].startswith("Tue")
