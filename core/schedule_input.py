"""OWNER: Member 2."""
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
from core.contracts import Event, K_SCHEDULE

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ROWS_KEY = "schedule_rows"


def _events_to_rows(events: list[Event]) -> pd.DataFrame:
    rows = []
    for e in events:
        s = datetime.strptime(e["start"], "%Y-%m-%dT%H:%M")
        rows.append({"day": DAYS[s.weekday()], "start": e["start"][11:16], "end": e["end"][11:16], "title": e["title"]})
    return pd.DataFrame(rows, columns=["day", "start", "end", "title"])


def _valid_hm(x) -> bool:
    try:
        datetime.strptime(str(x).strip(), "%H:%M")
        return True
    except ValueError:
        return False


def schedule_input_ui(week_start: str) -> list[Event]:
    monday = date.fromisoformat(week_start)
    if ROWS_KEY not in st.session_state:
        if st.session_state.get(K_SCHEDULE):
            st.session_state[ROWS_KEY] = _events_to_rows(st.session_state[K_SCHEDULE])
        else:
            st.session_state[ROWS_KEY] = pd.DataFrame([
                {"day": "Mon", "start": "09:00", "end": "11:00", "title": "Example class"},
                {"day": "Wed", "start": "13:00", "end": "15:00", "title": "Example lab"},
            ])

    img = st.file_uploader("Optional: upload a screenshot of your timetable", type=["png", "jpg", "jpeg"])
    if img is not None and st.button("Read my timetable with AI"):
        from core.ai_engine import parse_timetable_image
        try:
            with st.spinner("Reading your timetable..."):
                events = parse_timetable_image(img.getvalue(), img.type, week_start)
            st.session_state[ROWS_KEY] = _events_to_rows(events)
            st.rerun()
        except Exception as ex:
            st.error(f"Couldn't read the timetable: {ex}")

    edited = st.data_editor(
        st.session_state[ROWS_KEY], num_rows="dynamic", width="stretch", key="schedule_editor",
        column_config={
            "day": st.column_config.SelectboxColumn("Day", options=DAYS, required=True),
            "start": st.column_config.TextColumn("Start (HH:MM)", required=True),
            "end": st.column_config.TextColumn("End (HH:MM)", required=True),
            "title": st.column_config.TextColumn("Class / commitment", required=True),
        })

    events: list[Event] = []
    for i, r in enumerate(edited.to_dict("records"), 1):
        if r.get("day") not in DAYS or not _valid_hm(r.get("start")) or not _valid_hm(r.get("end")):
            continue
        d = monday + timedelta(days=DAYS.index(r["day"]))
        events.append({"id": f"class-{i}", "title": str(r.get("title") or "Class"),
                       "start": f"{d.isoformat()}T{str(r['start']).strip()}",
                       "end": f"{d.isoformat()}T{str(r['end']).strip()}", "kind": "class"})
    return events
