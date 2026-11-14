"""Session and Quiz Page — Enhanced UI/UX."""
import streamlit as st
from core.contracts import (
    K_CURRENT, K_PLAN, K_CONTENT, K_TOPICS, K_DOC_TEXT, K_RESULTS,
    load_mock_state, mock_mode
)
from core.quiz_logic import grade

st.set_page_config(page_title="StudyPilot | Study Session", page_icon="📚", layout="centered")

# --- Custom Styling for Cards & Badges ---
st.markdown("""
<style>
    .session-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
        background-color: #DBEAFE;
        color: #1E40AF;
        margin-right: 0.5rem;
    }
    .objective-box {
        background-color: #FFFFFF;
        border-left: 4px solid #2563EB;
        padding: 1rem 1.25rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        margin-top: 0.75rem;
        margin-bottom: 1.5rem;
    }
    .guide-card {
        background-color: #FFFFFF;
        padding: 1.25rem 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. Missing-State Safety Check ---
if K_PLAN not in st.session_state:
    if mock_mode(st):
        load_mock_state(st)
    else:
        st.info("Start on the Home page to upload your syllabus and generate a plan.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        st.stop()

# --- 2. Resolve Current Session ---
plan = st.session_state[K_PLAN]
sessions = plan["sessions"]
sid = st.session_state.get(K_CURRENT)

if not sid or not any(s["id"] == sid for s in sessions):
    sid = sessions[0]["id"]
    st.session_state[K_CURRENT] = sid

current_idx = next((i for i, s in enumerate(sessions) if s["id"] == sid), 0)
current_session = sessions[current_idx]

# --- 3. Top Navigation & Session Header ---
nav_col1, nav_col2 = st.columns([3, 1])
with nav_col1:
    st.caption(f"📘 {plan['goal']['course']} • Session {current_idx + 1} of {len(sessions)}")
with nav_col2:
    if st.button("← Back to Plan", use_container_width=True):
        st.switch_page("pages/1_Plan.py")

st.title(current_session["title"])

kind_label = current_session["kind"].capitalize()
st.markdown(
    f'<span class="session-badge">{kind_label}</span>'
    f'<span class="session-badge">⏱️ {current_session["minutes"]} min</span>',
    unsafe_allow_html=True
)

st.markdown(
    f'<div class="objective-box"><strong>🎯 Session Objective:</strong> {current_session["objective"]}</div>',
    unsafe_allow_html=True
)

# --- 4. Load or Generate Session Content ---
if K_CONTENT not in st.session_state:
    st.session_state[K_CONTENT] = {}

if sid not in st.session_state[K_CONTENT]:
    with st.spinner("Building your tailored study guide and practice quiz..."):
        try:
            from core.ai_engine import make_session
            content = make_session(
                current_session,
                st.session_state[K_TOPICS],
                st.session_state[K_DOC_TEXT]
            )
            st.session_state[K_CONTENT][sid] = content
        except Exception as e:
            st.error(f"Could not generate session content: {e}")
            if st.button("🔄 Try Again"):
                st.rerun()
            st.stop()

session_data = st.session_state[K_CONTENT][sid]
guide = session_data["guide"]
questions = session_data["questions"]

# --- 5. Main Experience Tabs ---
tab_guide, tab_quiz = st.tabs(["📖 1. Study Guide", f"✍️ 2. Practice Quiz ({len(questions)} Questions)"])

# === TAB 1: STUDY GUIDE ===
with tab_guide:
    st.markdown("### Key Takeaways")
    with st.container(border=True):
        for point in guide["key_points"]:
            st.markdown(f"- {point}")

    st.markdown("### Core Concepts")
    with st.container(border=True):
        st.markdown(guide["explanation"])

    with st.expander("💡 View Worked Example", expanded=True):
        st.markdown(guide["example"])

    if guide.get("source_hint"):
        st.caption(f"📄 Grounded in: **{guide['source_hint']}**")

    st.info("Ready to test yourself? Switch to the **Practice Quiz** tab above!")

# === TAB 2: PRACTICE QUIZ ===
with tab_quiz:
    ans_key = f"answers_{sid}"
    marked_key = f"marked_{sid}"
    submitted_key = f"submitted_{sid}"

    st.session_state.setdefault(ans_key, {})
    st.session_state.setdefault(marked_key, {})
    st.session_state.setdefault(submitted_key, False)

    with st.form(key=f"quiz_form_{sid}"):
        user_answers = {}
        self_marked = {}

        for i, q in enumerate(questions, 1):
            qid = q["id"]
            with st.container(border=True):
                st.markdown(f"**Question {i} of {len(questions)}**")
                st.markdown(q["question"])

                if q["type"] == "mcq":
                    options = q["options"]
                    prev_ans = st.session_state[ans_key].get(qid)
                    default_idx = options.index(prev_ans) if prev_ans in options else None

                    choice = st.radio(
                        "Choose the best answer:",
                        options=options,
                        index=default_idx,
                        key=f"radio_{sid}_{qid}",
                        label_visibility="collapsed"
                    )
                    user_answers[qid] = choice if choice is not None else ""

                elif q["type"] == "short":
                    prev_txt = st.session_state[ans_key].get(qid, "")
                    txt = st.text_area(
                        "Write your response:",
                        value=prev_txt,
                        placeholder="Type your answer here before checking the model solution...",
                        key=f"text_{sid}_{qid}"
                    )
                    user_answers[qid] = txt

                    if st.session_state[submitted_key]:
                        st.markdown(f"**Model Answer:** {q['answer']}")
                        checked = st.checkbox(
                            "I got this right (count toward my score)",
                            value=st.session_state[marked_key].get(qid, False),
                            key=f"self_{sid}_{qid}"
                        )
                        self_marked[qid] = checked
                    else:
                        self_marked[qid] = False

        btn_label = "Update Score" if st.session_state[submitted_key] else "Submit & Grade Quiz"
        submitted = st.form_submit_button(btn_label, type="primary", use_container_width=True)

    if submitted:
        st.session_state[ans_key] = user_answers
        st.session_state[marked_key] = self_marked
        st.session_state[submitted_key] = True

        result = grade(questions, user_answers, self_marked)
        st.session_state.setdefault(K_RESULTS, {})[sid] = result
        st.rerun()

    # --- Results & Feedback Breakdown ---
    if st.session_state[submitted_key] and sid in st.session_state.get(K_RESULTS, {}):
        res_data = st.session_state[K_RESULTS][sid]
        st.divider()
        st.subheader("📊 Session Performance")

        score_pct = int(round(res_data["score"] * 100))
        m_col1, m_col2 = st.columns([1, 2])

        with m_col1:
            st.metric("Overall Quiz Score", f"{score_pct}%")

        with m_col2:
            topics_lookup = {t["id"]: t["name"] for t in st.session_state[K_TOPICS]["topics"]}
            weak_topics = []
            for tid, t_score in res_data["topic_scores"].items():
                t_name = topics_lookup.get(tid, tid)
                st.progress(t_score, text=f"{t_name}: {int(round(t_score * 100))}%")
                if t_score < 0.6:
                    weak_topics.append(t_name)

        if weak_topics:
            st.warning(
                f"⚠️ **Adaptive Review Triggered:** You scored under 60% on **{', '.join(weak_topics)}**. "
                "Go back to your Plan and click **Update plan from my results** to add an extra review session."
            )
        else:
            st.success("🎉 Great job! You're on track across all topics in this session.")

        if any(q["type"] == "short" for q in questions):
            st.caption("💡 *Tip: For short-answer questions, compare your response to the model answer above, check the box if you got it right, and click **Update Score**.*")

        st.markdown("### Detailed Answer Review")
        result_map = {r["question_id"]: r for r in res_data["results"]}

        for i, q in enumerate(questions, 1):
            qid = q["id"]
            r_item = result_map.get(qid, {})
            is_correct = r_item.get("correct", False)

            with st.container(border=True):
                if is_correct:
                    st.markdown(f"✅ **Question {i} — Correct**")
                else:
                    st.markdown(f"❌ **Question {i} — Needs Review**")

                st.markdown(f"*{q['question']}*")
                if q["type"] == "mcq":
                    st.markdown(f"**Your Answer:** `{r_item.get('user_answer') or 'No selection'}`")
                    st.markdown(f"**Correct Answer:** `{q['answer']}`")
                else:
                    st.markdown(f"**Your Response:** {st.session_state[ans_key].get(qid) or '*Blank*'}")
                    st.markdown(f"**Model Answer:** {q['answer']}")

                st.info(f"**Explanation:** {q['explanation']}")

# --- 6. Bottom Session Switcher ---
st.divider()
foot_col1, foot_col2 = st.columns(2)
with foot_col1:
    if st.button("📋 Return to Study Plan", use_container_width=True):
        st.switch_page("pages/1_Plan.py")

with foot_col2:
    if current_idx < len(sessions) - 1:
        next_sess = sessions[current_idx + 1]
        if st.button(f"Next: {next_sess['title']} →", type="primary", use_container_width=True):
            st.session_state[K_CURRENT] = next_sess["id"]
            st.rerun()
    else:
        if st.button("📅 View Weekly Calendar →", type="primary", use_container_width=True):
            st.switch_page("pages/2_Calendar.py")