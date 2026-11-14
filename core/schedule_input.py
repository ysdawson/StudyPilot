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
            # Start empty (headers only); rows come from the student, a CSV or an image.
            st.session_state[ROWS_KEY] = pd.DataFrame({c: pd.Series(dtype="object") for c in COLUMNS})

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
        st.session_state["data_source"] = "user"  # the user's own image: always the real AI
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


def parse_deadlines_csv(text: str) -> list[dict]:
    """Rows of Course,Title,Date,Weight,Source -> [{course, title, date, weight, source}].
    Rows without a title or a valid YYYY-MM-DD date are skipped."""
    import csv, io
    out = []
    for r in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        r = {str(k).strip().lower(): (v or "").strip() for k, v in r.items() if k}
        try:
            day = date.fromisoformat(r.get("date", ""))
        except ValueError:
            continue
        if r.get("title"):
            out.append({"course": r.get("course", ""), "title": r["title"], "date": day.isoformat(),
                        "weight": r.get("weight", ""), "source": r.get("source", "")})
    return sorted(out, key=lambda d: d["date"])


def deadlines_input_ui() -> list[dict]:
    """Optional upload of all courses' deadlines (Home, under the timetable).
    Stored in st.session_state[DEADLINES_KEY]; shown on the calendar as markers only."""
    from core.demo import DEADLINES_KEY
    st.subheader("Upcoming deadlines (optional)")
    up = st.file_uploader("Upcoming deadlines (CSV): Course,Title,Date,Weight,Source", type=["csv"],
                          key="deadlines_csv")
    if up is not None and st.button("Load deadlines from CSV"):
        try:
            rows = parse_deadlines_csv(up.getvalue().decode("utf-8-sig"))
            st.session_state[DEADLINES_KEY] = rows
            if not rows:
                st.warning("No rows with a title and a YYYY-MM-DD date found in that CSV.")
        except Exception as ex:
            st.error(f"Couldn't read the deadlines CSV: {ex}")
    rows = st.session_state.get(DEADLINES_KEY, [])
    if rows:
        st.dataframe(pd.DataFrame(rows)[["date", "course", "title", "weight", "source"]],
                     width="stretch", hide_index=True)
        st.caption("Dates marked as estimated in Source are not official. Deadlines are markers: "
                   "they never block study time.")
    return rows


def goal_options(topics: dict, course_deadlines: list[dict]) -> list[tuple[str, str, str | None]]:
    """Choices for "What are you studying for?": (label, target title, date or None).
    Dated items keep the date from the documents / deadlines CSV; assessments and
    topics found without a date have None (the student picks the date). Never invents one."""
    opts: list[tuple[str, str, str | None]] = []
    seen: set[str] = set()

    def add(label: str, title: str, day: str | None) -> None:
        if title and title.lower() not in seen:
            seen.add(title.lower())
            opts.append((label, title, day))

    for d in topics.get("deadlines", []):
        add(f"{d['title']} — {d['date']}", d["title"], d["date"])
    for d in course_deadlines:
        est = " (estimated)" if "estimat" in d.get("source", "").lower() else ""
        add(f"{d['course']}: {d['title']} — {d['date']}{est}" if d.get("course") else d["title"],
            d["title"], d["date"])
    for a in topics.get("assessments", []):
        add(f"{a} (no date in the documents)", str(a), None)
    for t in topics.get("topics", []):
        add(f"Topic: {t['name']}", t["name"], None)
    opts.append(("Other (type it)", "", None))
    return opts


STUDY_PREFS_KEY = "study_prefs"  # owned by Home: {"days": [0..6], "start": "HH:MM", "end": "HH:MM"}


DEFAULT_AVAILABILITY = {0: ("17:00", "22:00"), 1: ("17:00", "22:00"), 2: ("17:00", "22:00"),
                        3: ("17:00", "22:00"), 4: ("17:00", "22:00")}
_WEEKEND_DEFAULT = ("10:00", "18:00")


def availability_from_rows(rows: list[dict]) -> tuple[dict[int, tuple[str, str]], list[str]]:
    """Editor rows -> ({weekday: (from, to)} for checked valid days, warnings for skipped rows)."""
    avail, problems = {}, []
    for r in rows:
        if not r.get("study") or r.get("day") not in DAYS:
            continue
        f, t = str(r.get("from") or "").strip(), str(r.get("to") or "").strip()
        if not (_valid_hm(f) and _valid_hm(t)) or f.zfill(5) >= t.zfill(5):
            problems.append(f"{r['day']}: 'From' must be before 'To' (HH:MM) — skipped.")
            continue
        avail[DAYS.index(r["day"])] = (f.zfill(5), t.zfill(5))
    return avail, problems


def study_prefs_ui() -> dict:
    """Per-day study availability (Study? / From / To). Stored for Generate and 'Update plan'."""
    st.subheader("When can you study?")
    saved = (st.session_state.get(STUDY_PREFS_KEY) or {}).get("availability")
    base = {int(k): tuple(v) for k, v in saved.items()} if saved else DEFAULT_AVAILABILITY
    rows = pd.DataFrame([{"day": d, "study": i in base,
                          "from": base.get(i, DEFAULT_AVAILABILITY.get(i, _WEEKEND_DEFAULT))[0],
                          "to": base.get(i, DEFAULT_AVAILABILITY.get(i, _WEEKEND_DEFAULT))[1]}
                         for i, d in enumerate(DAYS)])
    edited = st.data_editor(rows, key="study_table", hide_index=True, num_rows="fixed", disabled=["day"],
                            column_config={
                                "day": st.column_config.TextColumn("Day"),
                                "study": st.column_config.CheckboxColumn("Study?"),
                                "from": st.column_config.TextColumn("From (HH:MM)"),
                                "to": st.column_config.TextColumn("To (HH:MM)")})
    avail, problems = availability_from_rows(edited.to_dict("records"))
    for p in problems:
        st.warning(p)
    return {"availability": avail}


def schedule_kwargs(prefs: dict | None) -> dict:
    """Extra schedule_sessions arguments for the saved study preferences (none = defaults)."""
    if not prefs or "availability" not in prefs:
        return {}
    return {"availability": {int(k): tuple(v) for k, v in prefs["availability"].items()}}
