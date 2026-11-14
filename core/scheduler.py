"""OWNER: Member 2. Pure Python, no streamlit import."""
from datetime import date, datetime, timedelta
from core.contracts import Plan, Event, Deadline

FMT = "%Y-%m-%dT%H:%M"
BUFFER = timedelta(minutes=15)


def _dt(s: str) -> datetime:
    return datetime.strptime(s, FMT)


def _hm(day: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime(day.year, day.month, day.day, h, m)


def _busy_on(day: date, busy: list[Event]) -> list[tuple[datetime, datetime]]:
    """Weekly schedule: an event repeats on the same weekday every week."""
    out = []
    for e in busy:
        s, en = _dt(e["start"]), _dt(e["end"])
        if s.weekday() == day.weekday():
            out.append((_hm(day, s.strftime("%H:%M")), _hm(day, en.strftime("%H:%M"))))
    return sorted(out)


def _free_windows(day: date, busy: list[Event], day_start: str, day_end: str):
    cursor, end = _hm(day, day_start), _hm(day, day_end)
    windows = []
    for s, e in _busy_on(day, busy):
        s, e = s - BUFFER, e + BUFFER
        if s > cursor:
            windows.append((cursor, min(s, end)))
        cursor = max(cursor, e)
    if cursor < end:
        windows.append((cursor, end))
    return [w for w in windows if w[1] > w[0]]


def schedule_sessions(plan: Plan, busy: list[Event], max_minutes_per_day: int = 120,
                      day_start: str = "08:00", day_end: str = "22:00") -> list[Event]:
    goal = plan["goal"]
    day = date.fromisoformat(goal["start_date"])
    last = date.fromisoformat(goal["deadline"]) - timedelta(days=1)
    queue = sorted(plan["sessions"], key=lambda s: s["order"])
    events: list[Event] = []
    while queue and day <= last:
        used = 0
        # Spread the work evenly up to the deadline instead of cramming the
        # first days: today's share = remaining minutes / remaining days.
        days_left = (last - day).days + 1
        share = -(-sum(s["minutes"] for s in queue) // days_left)  # ceil
        windows = _free_windows(day, busy, day_start, day_end)
        while queue and windows:
            sess = queue[0]
            need = timedelta(minutes=sess["minutes"])
            if used + sess["minutes"] > max_minutes_per_day:
                break
            if used and used + sess["minutes"] > share:
                break
            placed = False
            for i, (ws, we) in enumerate(windows):
                if we - ws >= need:
                    events.append({"id": f"study-{sess['id']}", "title": f"Study: {sess['title']}",
                                   "start": ws.strftime(FMT), "end": (ws + need).strftime(FMT),
                                   "kind": "study", "session_id": sess["id"]})
                    windows[i] = (ws + need + BUFFER, we)
                    used += sess["minutes"]
                    queue.pop(0)
                    placed = True
                    break
            if not placed:
                break
        day += timedelta(days=1)
    return events


def build_calendar(busy: list[Event], study: list[Event], deadlines: list[Deadline],
                   start_date: str, end_date: str) -> list[Event]:
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    cal: list[Event] = []
    day = start
    while day <= end:
        for e in busy:
            s, en = _dt(e["start"]), _dt(e["end"])
            if s.weekday() == day.weekday():
                cal.append({"id": f"{e['id']}-{day.isoformat()}", "title": e["title"],
                            "start": _hm(day, s.strftime("%H:%M")).strftime(FMT),
                            "end": _hm(day, en.strftime("%H:%M")).strftime(FMT), "kind": e["kind"]})
        day += timedelta(days=1)
    cal.extend(study)
    for i, d in enumerate(deadlines, 1):
        if start_date <= d["date"] <= end_date:
            cal.append({"id": f"deadline-{i}", "title": d["title"], "start": f"{d['date']}T08:00",
                        "end": f"{d['date']}T09:00", "kind": "deadline"})
    return cal


def with_goal_deadline(deadlines: list[Deadline], goal: dict) -> list[Deadline]:
    """Course deadlines plus the student's own goal deadline (when the material
    gives no date, e.g. "Other" + a date typed on the Home page)."""
    target = str(goal.get("target") or "").lower()
    if not goal.get("deadline") or any(
            d.get("date") == goal["deadline"] and (not target or target in d.get("title", "").lower())
            for d in deadlines):
        return list(deadlines)
    title = f"{goal.get('target') or 'Deadline'} (your target date)"  # not from the material
    return list(deadlines) + [{"title": title, "date": goal["deadline"]}]


def course_deadline_title(d: dict) -> str:
    return f"{d['course']}: {d['title']}" if d.get("course") else d["title"]


def all_deadlines(topic_deadlines: list[Deadline], course_deadlines: list[dict], goal: dict) -> list[Deadline]:
    """Deadlines for build_calendar: from the material, from the deadlines CSV
    ("<Course>: <Title>"), plus the student's goal unless one of them already is it."""
    merged = list(topic_deadlines) + [{"title": course_deadline_title(d), "date": d["date"]}
                                      for d in course_deadlines]
    return with_goal_deadline(merged, goal)


def calendar_end(goal: dict, deadlines: list[Deadline]) -> str:
    """Show the calendar up to the goal or the last deadline, whichever is later."""
    return max([goal["deadline"]] + [d["date"] for d in deadlines])
