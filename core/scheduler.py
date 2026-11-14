"""OWNER: Member 2. STUB - pure Python, no streamlit import."""
from core.contracts import Plan, Event, Deadline

def schedule_sessions(plan: Plan, busy: list[Event], max_minutes_per_day: int = 120,
                      day_start: str = "08:00", day_end: str = "22:00") -> list[Event]:
    raise NotImplementedError("Member 2: implement schedule_sessions")

def build_calendar(busy: list[Event], study: list[Event], deadlines: list[Deadline],
                   start_date: str, end_date: str) -> list[Event]:
    raise NotImplementedError("Member 2: implement build_calendar")
