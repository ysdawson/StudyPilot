"""OWNER: Member 3. Study session: guide + practice quiz, results saved to K_RESULTS."""
import html
import streamlit as st
from core.contracts import *
from core.demo import load_demo_data, demo_picker
from core.ai_engine import make_session
from core.quiz_logic import grade

st.set_page_config(page_title="StudyPilot | Study Session", page_icon="📚", layout="centered")

# Visual design from Member 3's redesign (badges, objective box, cards).
st.markdown("""
<style>
.session-badge {display:inline-block; padding:0.25rem 0.75rem; border-radius:999px; font-size:0.85rem;
                font-weight:600; background-color:#DBEAFE; color:#1E40AF; margin-right:0.5rem;}
.objective-box {background-color:#FFFFFF; color:#1F2937; border-left:4px solid #2563EB;
                padding:1rem 1.25rem; border-radius:0.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.06);
                margin-top:0.75rem; margin-bottom:1.5rem;}
</style>
""", unsafe_allow_html=True)

if K_PLAN not in st.session_state:
    st.info("No study plan yet. Generate one on the Home page, or load the demo.")
    c1, c2 = st.columns(2)
    if c1.button("Go to Home"):
        st.switch_page("app.py")
    choice = demo_picker(st, c2, key="demo_pick_session")
    if c2.button("Load demo data"):
        load_demo_data(st, choice)
        st.rerun()
    st.stop()

ss = st.session_state
ss.setdefault(K_CONTENT, {})
ss.setdefault(K_RESULTS, {})

sessions = sorted(ss[K_PLAN]["sessions"], key=lambda s: s["order"])
if not sessions:
    st.info("Your plan has no sessions yet."); st.stop()
topic_names = {t["id"]: t["name"] for t in ss.get(K_TOPICS, {}).get("topics", [])}

# ---- Pick the session (defaults to the one opened from the Plan page) ----
ids = [s["id"] for s in sessions]
if ss.get(K_CURRENT) not in ids:
    ss[K_CURRENT] = ids[0]
label = {s["id"]: f'{s["order"]}. {s["title"]}' + ("  ✅" if s["id"] in ss[K_RESULTS] else "") for s in sessions}
sid = st.sidebar.selectbox("Session", ids, index=ids.index(ss[K_CURRENT]), format_func=label.get)
ss[K_CURRENT] = sid
session = next(s for s in sessions if s["id"] == sid)

idx = ids.index(sid)
nav1, nav2 = st.columns([3, 1])
nav1.caption(f'📘 {ss[K_PLAN]["goal"]["course"]} • Session {idx + 1} of {len(ids)}')
if nav2.button("← Back to Plan", key="top-back", width="stretch"):
    st.switch_page("pages/1_Plan.py")
st.title(session["title"])
st.markdown(f'<span class="session-badge">{html.escape(session["kind"].capitalize())}</span>'
            f'<span class="session-badge">⏱️ {session["minutes"]} min</span>'
            f'<span class="session-badge">{html.escape(topic_names.get(session["topic_id"], session["topic_id"]))}</span>',
            unsafe_allow_html=True)
st.markdown(f'<div class="objective-box"><strong>🎯 Session Objective:</strong> '
            f'{html.escape(session["objective"])}</div>', unsafe_allow_html=True)

# ---- Get the content (AI call only if not generated yet) ----
if sid not in ss[K_CONTENT]:
    with st.spinner("Preparing your study guide and practice questions..."):
        try:
            ss[K_CONTENT][sid] = make_session(session, ss.get(K_TOPICS, {}), ss.get(K_DOC_TEXT, ""))
        except Exception as e:
            st.error(f"Could not generate this session: {e}")
            if st.button("Try again"):
                st.rerun()
            st.stop()
content = ss[K_CONTENT][sid]
guide, questions = content["guide"], content["questions"]

# ---- Study guide ----
tab_guide, tab_quiz = st.tabs(["📖 1. Study Guide", f"✍️ 2. Practice Quiz ({len(questions)} Questions)"])
with tab_guide:
    st.markdown("### Key Takeaways")
    with st.container(border=True):
        for p in guide["key_points"]:
            st.markdown(f"- {p}")
    st.markdown("### Core Concepts")
    with st.container(border=True):
        st.markdown(guide["explanation"])
    with st.expander("💡 View Worked Example", expanded=True):
        st.markdown(guide["example"])
    if guide.get("source_hint"):
        st.caption(f'📄 Grounded in: **{guide["source_hint"]}**')
    st.info("Ready to test yourself? Switch to the **Practice Quiz** tab above!")

# ---- Quiz ----
submitted_key = f"quiz_submitted_{sid}"
with tab_quiz:
    if sid in ss[K_RESULTS]:
        st.success(f'Last saved score: {ss[K_RESULTS][sid]["score"]:.0%}. You can retake the quiz below.')

    with st.form(f"quiz_{sid}"):
        for i, q in enumerate(questions, 1):
            with st.container(border=True):
                st.markdown(f"**Question {i} of {len(questions)}**")
                st.markdown(q["question"])
                if q["type"] == "mcq":
                    st.radio("Choose the best answer:", q["options"], index=None, key=f"ans_{q['id']}",
                             label_visibility="collapsed")
                else:
                    st.text_area("Write your response:", key=f"ans_{q['id']}", height=80,
                                 placeholder="Type your answer here before checking the model solution...",
                                 label_visibility="collapsed")
        if st.form_submit_button("Check my answers", type="primary", width="stretch"):
            ss[submitted_key] = True

    if ss.get(submitted_key):
        st.divider()
        st.markdown("### Detailed Answer Review")
        answers = {q["id"]: ss.get(f"ans_{q['id']}") or "" for q in questions}
        self_marked: dict[str, bool] = {}
        for i, q in enumerate(questions, 1):
            ua = answers[q["id"]]
            with st.container(border=True):
                if q["type"] == "mcq":
                    ok = ua.strip().lower() == q["answer"].strip().lower()
                    st.markdown(f"{'✅' if ok else '❌'} **Question {i} — {'Correct' if ok else 'Needs Review'}**")
                    st.markdown(f"*{q['question']}*")
                    st.markdown(f"**Your Answer:** {ua or '_No selection_'}")  # Markdown, so LaTeX renders
                    st.markdown(f"**Correct Answer:** {q['answer']}")
                else:
                    st.markdown(f"✍️ **Question {i} — Compare with the model answer**")
                    st.markdown(f"*{q['question']}*")
                    st.markdown(f"**Your Response:** {ua or '*Blank*'}")
                    st.markdown(f"**Model Answer:** {q['answer']}")
                    self_marked[q["id"]] = st.checkbox("I got this right (count toward my score)",
                                                       key=f"self_{q['id']}")
                st.info(f"**Explanation:** {q['explanation']}")

        if st.button("Save my results", type="primary", width="stretch"):
            try:
                ss[K_RESULTS][sid] = grade(questions, answers, self_marked)
                ss[submitted_key] = False
                st.rerun()
            except Exception as e:
                st.error(f"Could not save results: {e}")

    # ---- Saved result summary ----
    if sid in ss[K_RESULTS] and not ss.get(submitted_key):
        res = ss[K_RESULTS][sid]
        st.divider()
        st.subheader("📊 Session Performance")
        m1, m2 = st.columns([1, 2])
        m1.metric("Overall Quiz Score", f'{res["score"]:.0%}')
        with m2:
            for t, v in res["topic_scores"].items():
                st.progress(v, text=f"{topic_names.get(t, t)}: {v:.0%}")
        weak = [t for t, v in res["topic_scores"].items() if v < 0.6]
        if weak:
            st.warning("⚠️ **Adaptive Review Triggered:** you scored under 60% on "
                       f"**{', '.join(topic_names.get(t, t) for t in weak)}**. Go back to your Plan and click "
                       "**Update plan from my quiz results** to add an extra review session.")
        else:
            st.success("🎉 Great job! You're on track across all topics in this session.")

st.divider()
c1, c2 = st.columns(2)
if c1.button("🗂️ Back to my plan", width="stretch"):
    st.switch_page("pages/1_Plan.py")
if idx + 1 < len(ids):
    if c2.button(f"Next: {sessions[idx + 1]['title']} →", type="primary", width="stretch"):
        ss[K_CURRENT] = ids[idx + 1]
        st.rerun()
elif c2.button("📅 View Weekly Calendar →", type="primary", width="stretch"):
    st.switch_page("pages/2_Calendar.py")
