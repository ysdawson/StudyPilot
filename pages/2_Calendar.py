"""OWNER: Member 2. Calendar page: weekly board (default) + FullCalendar time grid."""
import html
from datetime import date, timedelta
import streamlit as st
from core.contracts import *
from core.demo import load_demo_data, demo_picker, DEADLINES_KEY
from core import board

st.set_page_config(page_title="StudyPilot | Calendar", layout="wide")

if K_PLAN not in st.session_state:
    st.info("No study plan yet. Generate one on the Home page, or load the demo.")
    c1, c2 = st.columns(2)
    if c1.button("Go to Home"):
        st.switch_page("app.py")
    choice = demo_picker(st, c2, key="demo_pick_calendar")
    if c2.button("Load demo data"):
        load_demo_data(st, choice)
        st.rerun()
    st.stop()

ss = st.session_state
plan = ss[K_PLAN]
events = ss.get(K_CALENDAR, [])
done = set(ss.get(K_RESULTS, {}))
sessions = {s["id"]: s for s in plan["sessions"]}
topic_name = {t["id"]: t["name"] for t in ss.get(K_TOPICS, {}).get("topics", [])}
courses = board.course_colors(events)
sources = board.deadline_sources(ss.get(DEADLINES_KEY, []))  # title -> "day estimated" etc.
goal = plan["goal"]
goal_marker = next((t for t, _ in board.countdowns(events, date.min)
                    if goal.get("target") and goal["target"].lower() in t.lower()), "")
today = date.today()
plan_week = board.monday_of(date.fromisoformat(plan["goal"]["start_date"]))
WEEK_KEY = "board_week"
ss.setdefault(WEEK_KEY, plan_week)


def _shift_week(days: int | None) -> None:
    ss[WEEK_KEY] = board.monday_of(today) if days is None else ss[WEEK_KEY] + timedelta(days=days)


def _open(session_id: str) -> None:
    ss[K_CURRENT] = session_id
    st.switch_page("pages/3_Session.py")


st.markdown("""
<style>
.sp-day {text-align:center; padding:6px 0 8px; border-radius:10px; margin-bottom:6px;
         font-weight:600; color:#374151; background:#F3F4F6;}
.sp-day small {display:block; font-weight:400; color:#6B7280;}
.sp-today {background:#4F46E5; color:#fff;}
.sp-today small {color:#E0E7FF;}
.sp-card {border-radius:12px; padding:8px 10px; margin:0 0 6px; border-left:4px solid;
          color:#1F2937; font-size:0.82rem; line-height:1.25; box-shadow:0 1px 2px rgba(0,0,0,.06);}
.sp-card b {display:block; margin:2px 0; font-size:0.86rem;}
.sp-time {color:#4B5563; font-size:0.75rem;}
.sp-tag {display:inline-block; margin-top:4px; padding:1px 8px; border-radius:999px;
         font-size:0.68rem; font-weight:600; background:rgba(255,255,255,.65); color:#374151;}
.sp-study {color:#fff; box-shadow:0 2px 6px rgba(79,70,229,.35);}
.sp-study .sp-time {color:#E0E7FF;}
.sp-study .sp-tag {background:rgba(255,255,255,.25); color:#fff;}
.sp-src {font-size:0.72rem; font-style:italic; color:#7F1D1D;}
.sp-empty {color:#9CA3AF; font-size:0.78rem; text-align:center; padding:8px 0;}
.sp-next {border-radius:10px; padding:6px 10px; background:#EEF2FF; margin-bottom:4px;
          font-size:0.82rem; color:#1F2937;}
.sp-count {border-radius:12px; padding:10px 12px; background:#FEE2E2; color:#991B1B;
           font-weight:600; margin-bottom:6px;}
div[data-testid="stButton"] button[kind="primary"] {background:#4F46E5; border-color:#4F46E5;}
div[data-testid="stButton"] button[kind="primary"]:hover {background:#4338CA; border-color:#4338CA;}
</style>""", unsafe_allow_html=True)


def card_html(e: dict) -> str:
    bg, accent = board.event_colors(e, courses)
    kind = e.get("kind", "class")
    title = e["title"]
    extra = ""
    if kind == "study":
        s = sessions.get(e.get("session_id"), {})
        title = s.get("title", title.removeprefix("Study: "))
        topic = topic_name.get(s.get("topic_id"), "")
        extra = f"<div>{html.escape(topic)} · {board.minutes(e)} min</div>"
        if e.get("session_id") in done:
            title = "✅ " + title
    elif kind == "deadline" and sources.get(e["title"]):
        extra = f'<div class="sp-src">{html.escape(sources[e["title"]])}</div>'
    time = "All day" if kind == "deadline" else board.time_range(e)
    cls = "sp-card sp-study" if kind == "study" else "sp-card"
    return (f'<div class="{cls}" style="background:{bg};border-left-color:{accent}">'
            f'<span class="sp-time">{time}</span><b>{html.escape(title)}</b>{extra}'
            f'<span class="sp-tag">{board.TAGS.get(kind, kind.title())}</span></div>')


st.title("Your week")
# A view switch instead of st.tabs: the time grid (FullCalendar) drawn inside a hidden
# tab gets zero width and stays blank, so only the chosen view is drawn.
VIEWS = ["🗂️ Week board", "🕒 Time grid"]
view = st.radio("View", VIEWS, horizontal=True, key="cal_view", label_visibility="collapsed")

if view == VIEWS[0]:
    week = ss[WEEK_KEY]
    nav = st.columns([1, 1, 1.4, 5])
    nav[0].button("←", key="week-prev", on_click=_shift_week, args=(-7,), help="Previous week")
    nav[1].button("→", key="week-next", on_click=_shift_week, args=(7,), help="Next week")
    nav[2].button("This week", key="week-now", on_click=_shift_week, args=(None,))
    nav[3].markdown(f"**{week:%b %d} – {week + timedelta(days=6):%b %d, %Y}**")

    main, side = st.columns([4.2, 1.3], gap="medium")
    with main:
        cols = st.columns(7, gap="small")
        for col, (day, day_events) in zip(cols, board.events_by_day(events, week).items()):
            with col:
                head = "sp-day sp-today" if day == today else "sp-day"
                st.markdown(f'<div class="{head}">{board.DAY_NAMES[day.weekday()]}'
                            f'<small>{day:%b %d}</small></div>', unsafe_allow_html=True)
                if not day_events:
                    st.markdown('<div class="sp-empty">Free</div>', unsafe_allow_html=True)
                for e in day_events:
                    st.markdown(card_html(e), unsafe_allow_html=True)
                    sid = e.get("session_id")
                    if e.get("kind") == "study" and sid in sessions:
                        if st.button("Open", key=f"board-open-{e['id']}", width="stretch",
                                     type="secondary" if sid in done else "primary"):
                            _open(sid)

    with side:
        st.markdown("#### Up next")
        nxt = board.up_next(events, done)
        if not nxt:
            st.caption("All planned sessions are done 🎉")
        for e in nxt:
            s = sessions.get(e.get("session_id"), {})
            st.markdown(f'<div class="sp-next"><b>{html.escape(s.get("title", e["title"]))}</b><br>'
                        f'{date.fromisoformat(e["start"][:10]):%a %b %d} · {board.time_range(e)}</div>',
                        unsafe_allow_html=True)
            if s and st.button("Open", key=f"next-open-{e['id']}", width="stretch"):
                _open(s["id"])
        st.markdown("#### Countdown")

        def _when(left: int) -> str:
            return "today" if left == 0 else "tomorrow" if left == 1 else f"in {left} days"

        goal_left = (date.fromisoformat(goal["deadline"]) - today).days
        if goal_left >= 0:
            src = sources.get(goal_marker, "your target date")
            st.markdown(f'<div class="sp-count">🎯 {html.escape(goal["target"])} {_when(goal_left)}'
                        f'<div class="sp-src">{html.escape(src)}</div></div>', unsafe_allow_html=True)
        others = board.next_deadlines(events, today, 3, skip_title=goal_marker)
        if others:
            st.markdown("#### Next deadlines")
        elif goal_left < 0:
            st.caption("No upcoming deadlines.")
        for title, left in others:
            src = sources.get(title, "")
            st.markdown(f'<div class="sp-next"><b>{html.escape(title)}</b><br>{_when(left)}'
                        + (f'<div class="sp-src">{html.escape(src)}</div>' if src else "") + '</div>',
                        unsafe_allow_html=True)
        st.markdown("#### This week")
        finished, planned = board.week_progress(events, week, done)
        st.progress(finished / planned if planned else 0.0,
                    text=f"{finished} of {planned} study minutes done")

else:
    grid = [{"title": e["title"] + (f" ({sources[e['title']]})" if e.get("kind") == "deadline"
                                    and sources.get(e["title"]) else ""),
             "start": e["start"], "end": e["end"], "id": e["id"],
             "backgroundColor": board.event_colors(e, courses)[0],
             "borderColor": board.event_colors(e, courses)[1],
             "textColor": "#FFFFFF" if e.get("kind") == "study" else "#1F2937",
             "extendedProps": {"session_id": e.get("session_id", "")}} for e in events]
    try:
        from streamlit_calendar import calendar
        state = calendar(events=grid, options={
            "initialView": "timeGridWeek", "initialDate": plan["goal"]["start_date"],
            "slotMinTime": "08:00:00", "slotMaxTime": "22:00:00", "allDaySlot": False, "height": 700,
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "timeGridWeek,dayGridMonth"},
        }, callbacks=["eventClick"], key="cal")
        clicked = (state or {}).get("eventClick", {}).get("event", {})
        sid = (clicked.get("extendedProps") or {}).get("session_id") or ""
        if sid in sessions and ss.get("grid_click_handled") != clicked.get("id"):
            ss["grid_click_handled"] = clicked.get("id")  # the component keeps its last click
            _open(sid)
        st.caption("Click a study session (indigo) to open it.")
    except ImportError:
        st.warning("Install streamlit-calendar for the time grid. Showing a list instead.")
        st.dataframe(grid, width="stretch")
    st.caption("Classes: one colour per course · Orange: work · Indigo: study sessions · Red: deadlines")
