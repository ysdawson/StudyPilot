"""OWNER: Member 2. Pure helpers for the Calendar page's week board (no streamlit import)."""
import re
from datetime import date, datetime, timedelta

FMT = "%Y-%m-%dT%H:%M"
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TAGS = {"class": "Class", "busy": "Work", "study": "Study", "deadline": "Deadline"}

# Soft pastels: (background, border/accent). Classes get one per course.
COURSE_PALETTE = [("#DBEAFE", "#3B82F6"), ("#EDE9FE", "#8B5CF6"), ("#D1FAE5", "#10B981"),
                  ("#FFE4E6", "#F43F5E"), ("#CFFAFE", "#06B6D4"), ("#FEF9C3", "#CA8A04"),
                  ("#FCE7F3", "#DB2777"), ("#E0E7FF", "#6366F1")]
KIND_COLORS = {"busy": ("#FDE7CF", "#EA8A2E"), "study": ("#4F46E5", "#3730A3"),
               "deadline": ("#FEE2E2", "#DC2626")}
_SKIP_WORDS = {"lab", "labs", "general", "intro", "introduction", "to", "the", "of", "and", "i", "ii", "iii"}


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def course_key(title: str) -> str:
    """'Mechanics Lab' and 'Mechanics (Physics NYA)' -> 'mechanics';
    'General Chemistry' and 'Chemistry Lab' -> 'chemistry'."""
    text = re.sub(r"\(.*?\)", " ", title).split(" - ")[0].lower()
    words = [w for w in re.findall(r"[a-z]+", text) if w not in _SKIP_WORDS]
    return words[0] if words else title.lower()


def course_colors(events: list[dict]) -> dict[str, tuple[str, str]]:
    """Same course -> same colour. Assigned in sorted order so it is stable."""
    keys = sorted({course_key(e["title"]) for e in events if e.get("kind") == "class"})
    return {k: COURSE_PALETTE[i % len(COURSE_PALETTE)] for i, k in enumerate(keys)}


def event_colors(event: dict, courses: dict[str, tuple[str, str]]) -> tuple[str, str]:
    if event.get("kind") == "class":
        return courses.get(course_key(event["title"]), COURSE_PALETTE[0])
    return KIND_COLORS.get(event.get("kind"), COURSE_PALETTE[0])


def week_days(monday: date) -> list[date]:
    return [monday + timedelta(days=i) for i in range(7)]


def events_by_day(events: list[dict], monday: date) -> dict[date, list[dict]]:
    """The week's events per day, sorted by start time."""
    days = {d: [] for d in week_days(monday)}
    for e in events:
        d = date.fromisoformat(e["start"][:10])
        if d in days:
            days[d].append(e)
    return {d: sorted(evs, key=lambda e: (e["start"], e["end"])) for d, evs in days.items()}


def minutes(event: dict) -> int:
    return int((datetime.strptime(event["end"], FMT) - datetime.strptime(event["start"], FMT)).total_seconds() // 60)


def time_range(event: dict) -> str:
    return f"{event['start'][11:16]}–{event['end'][11:16]}"


def up_next(events: list[dict], done: set[str], n: int = 5) -> list[dict]:
    """The next n study sessions not done yet, in time order."""
    study = [e for e in events if e.get("kind") == "study" and e.get("session_id") not in done]
    return sorted(study, key=lambda e: e["start"])[:n]


def countdowns(events: list[dict], today: date) -> list[tuple[str, int]]:
    """(title, days left) for deadlines from today on."""
    out = []
    for e in sorted((e for e in events if e.get("kind") == "deadline"), key=lambda e: e["start"]):
        left = (date.fromisoformat(e["start"][:10]) - today).days
        if left >= 0:
            out.append((e["title"], left))
    return out


def week_progress(events: list[dict], monday: date, done: set[str]) -> tuple[int, int]:
    """(study minutes done, study minutes planned) for the week starting monday."""
    week = [e for evs in events_by_day(events, monday).values() for e in evs if e.get("kind") == "study"]
    planned = sum(minutes(e) for e in week)
    finished = sum(minutes(e) for e in week if e.get("session_id") in done)
    return finished, planned


def deadline_sources(course_deadlines: list[dict]) -> dict[str, str]:
    """Calendar deadline title ("<Course>: <Title>") -> Source text (e.g. "... day estimated")."""
    out = {}
    for d in course_deadlines:
        title = f"{d['course']}: {d['title']}" if d.get("course") else d["title"]
        out[title] = d.get("source", "")
    return out


def next_deadlines(events: list[dict], today: date, n: int = 3, skip_title: str = "") -> list[tuple[str, int]]:
    """The next n deadline markers (title, days left), skipping the goal's own marker."""
    return [(t, left) for t, left in countdowns(events, today) if t != skip_title][:n]
