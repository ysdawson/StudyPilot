"""OWNER: Member 2. Plan page."""
import streamlit as st
from core.contracts import *
from core.ai_engine import replan
from core.scheduler import schedule_sessions, build_calendar

if K_PLAN not in st.session_state:
    if mock_mode(st):
        load_mock_state(st)
    else:
        st.info("Start on the Home page"); st.stop()

ss = st.session_state
plan, topics = ss[K_PLAN], ss[K_TOPICS]
goal = plan["goal"]
results = ss.setdefault(K_RESULTS, {})
topic_name = {t["id"]: t["name"] for t in topics["topics"]}
when = {e.get("session_id"): e for e in ss.get(K_CALENDAR, []) if e["kind"] == "study"}

st.title("Your study plan")
st.write(f"**{goal['course']}**: {goal['target']} on **{goal['deadline']}** · "
         f"{goal['hours_per_week']:g} h/week · target {goal['target_grade']}")
done = sum(1 for s in plan["sessions"] if s["id"] in results)
st.progress(done / max(len(plan["sessions"]), 1), text=f"{done} of {len(plan['sessions'])} sessions done")

if st.button("Update plan from my quiz results", disabled=not results):
    try:
        with st.spinner("Adapting your plan..."):
            new = replan(plan, topics, results)
        ss[K_PLAN] = new
        todo = {**new, "sessions": [s for s in new["sessions"] if s["id"] not in results]}
        study = schedule_sessions(todo, ss.get(K_SCHEDULE, []))
        ss[K_CALENDAR] = build_calendar(ss.get(K_SCHEDULE, []), study, topics["deadlines"],
                                        goal["start_date"], goal["deadline"])
        st.rerun()
    except Exception as ex:
        st.error(f"Couldn't update the plan: {ex}")

BADGE = {"learn": "🟦 Learn", "practice": "🟧 Practice", "review": "🟪 Review"}
for s in sorted(plan["sessions"], key=lambda s: s["order"]):
    with st.container(border=True):
        c1, c2, c3 = st.columns([6, 3, 2])
        with c1:
            st.markdown(f"**{s['order']}. {s['title']}**")
            st.caption(f"{BADGE.get(s['kind'], s['kind'])} · {topic_name.get(s['topic_id'], s['topic_id'])} · {s['minutes']} min")
            st.write(s["objective"])
        with c2:
            ev = when.get(s["id"])
            st.write(f"📅 {ev['start'][:10]} {ev['start'][11:]}" if ev else "Not scheduled")
            if s["id"] in results:
                st.write(f"✅ Score {round(results[s['id']]['score'] * 100)}%")
        with c3:
            if st.button("Open", key=f"open-{s['id']}", type="primary" if s["id"] not in results else "secondary"):
                ss[K_CURRENT] = s["id"]
                st.switch_page("pages/3_Session.py")
