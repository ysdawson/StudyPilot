"""OWNER: Member 2."""
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
from core.contracts import Event, K_SCHEDULE

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ROWS_KEY = "schedule_rows"
COLUMNS = ["day", "start", "end", "title", "type"]
TYPES = ["class", "busy"]  # Event.kind for the student's own week (busy = work, other commitments)
_CSV_TYPES = {"class": "class", "work": "busy"}  # other CSV types (Free, Suggested study) are skipped


def _events_to_rows(events: list[Event]) -> pd.DataFrame:
    rows = []
    for e in events:
        s = datetime.strptime(e["start"], "%Y-%m-%dT%H:%M")
        rows.append({"day": DAYS[s.weekday()], "start": e["start"][11:16], "end": e["end"][11:16],
                     "title": e["title"], "type": e.get("kind") if e.get("kind") in TYPES else "class"})
    return pd.DataFrame(rows, columns=COLUMNS)


def _valid_hm(x) -> bool:
    try:
        datetime.strptime(str(x).strip(), "%H:%M")
        return True
    except ValueError:
        return False


def _to_hm(value: str) -> str | None:
    """'6:00 PM' / '18:00' -> '18:00'; None if empty or unreadable."""
    value = str(value or "").strip().upper()
    for fmt in ("%I:%M %p", "%I:%M%p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def parse_timetable_csv(text: str) -> list[dict]:
    """Rows for the editor from a CSV with header Day,Date,Start,End,Activity,Type.
    Type "Class" -> class, "Work" -> busy. Other types (Free, Suggested study) and rows
    without a start/end time are skipped."""
    import csv, io
    rows = []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        r = {str(k).strip().lower(): (v or "").strip() for k, v in r.items() if k}
        kind = _CSV_TYPES.get(r.get("type", "").lower())
        if not kind:
            continue
        start, end = _to_hm(r.get("start")), _to_hm(r.get("end"))
        day = r.get("day", "")[:3].title()
        if day not in DAYS and r.get("date"):
            try:
                day = DAYS[date.fromisoformat(r["date"]).weekday()]
            except ValueError:
                pass
        if day in DAYS and start and end:
            rows.append({"day": day, "start": start, "end": end,
                         "title": r.get("activity") or kind.title(), "type": kind})
    return rows


def schedule_input_ui(week_start: str) -> list[Event]:
    monday = date.fromisoformat(week_start)
    if ROWS_KEY not in st.session_state:
        if st.session_state.get(K_SCHEDULE):
            st.session_state[ROWS_KEY] = _events_to_rows(st.session_state[K_SCHEDULE])
        else:
            st.session_state[ROWS_KEY] = pd.DataFrame([
                {"day": "Mon", "start": "09:00", "end": "11:00", "title": "Example class", "type": "class"},
                {"day": "Wed", "start": "13:00", "end": "15:00", "title": "Example lab", "type": "class"},
            ], columns=COLUMNS)

    csv_file = st.file_uploader("Optional: upload your timetable as CSV (Day,Date,Start,End,Activity,Type)",
                                type=["csv"])
    if csv_file is not None and st.button("Load my week from CSV"):
        try:
            rows = parse_timetable_csv(csv_file.getvalue().decode("utf-8-sig"))
            if rows:
                st.session_state[ROWS_KEY] = pd.DataFrame(rows, columns=COLUMNS)
                st.session_state.pop("schedule_editor", None)  # show the new rows, not old edits
                st.rerun()
            st.warning("No Class or Work rows with times found in that CSV.")
        except Exception as ex:
            st.error(f"Couldn't read the CSV: {ex}")

    img = st.file_uploader("Optional: upload a screenshot of your timetable", type=["png", "jpg", "jpeg"])
    if img is not None and st.button("Read my timetable with AI"):
        from core.ai_engine import parse_timetable_image
        try:
            with st.spinner("Reading your timetable..."):
                events = parse_timetable_image(img.getvalue(), img.type, week_start)
            st.session_state[ROWS_KEY] = _events_to_rows(events)
            st.session_state.pop("schedule_editor", None)
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
            "type": st.column_config.SelectboxColumn("Type", options=TYPES, default="class"),
        })

    events: list[Event] = []
    for i, r in enumerate(edited.to_dict("records"), 1):
        if r.get("day") not in DAYS or not _valid_hm(r.get("start")) or not _valid_hm(r.get("end")):
            continue
        d = monday + timedelta(days=DAYS.index(r["day"]))
        kind = r.get("type") if r.get("type") in TYPES else "class"
        events.append({"id": f"{kind}-{i}", "title": str(r.get("title") or kind.title()),
                       "start": f"{d.isoformat()}T{str(r['start']).strip()}",
                       "end": f"{d.isoformat()}T{str(r['end']).strip()}", "kind": kind})
    return events
