import json
from datetime import datetime
from core.scheduler import schedule_sessions, build_calendar, FMT

plan = json.load(open("mock_data/plan.json"))
busy = json.load(open("mock_data/schedule.json"))


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
