"""OWNER: Member 3. Study session: guide + practice quiz, results saved to K_RESULTS."""
import streamlit as st
from core.contracts import *
from core.ai_engine import make_session
from core.quiz_logic import grade

if K_PLAN not in st.session_state:
    if mock_mode(st):
        load_mock_state(st)
    else:
        st.info("Start on the Home page"); st.stop()

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

st.title(session["title"])
st.caption(f'{session["kind"].capitalize()} · {session["minutes"]} min · '
           f'Topic: {topic_names.get(session["topic_id"], session["topic_id"])}')
st.markdown(f'**Goal of this session:** {session["objective"]}')

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
tab_guide, tab_quiz = st.tabs(["📖 Study guide", "📝 Practice quiz"])
with tab_guide:
    st.subheader("Key points")
    for p in guide["key_points"]:
        st.markdown(f"- {p}")
    st.subheader("Explanation")
    st.markdown(guide["explanation"])
    with st.expander("Worked example", expanded=True):
        st.markdown(guide["example"])
    st.caption(f'📍 Where to look: {guide["source_hint"]}')
    st.info("When you are done reading, open the **Practice quiz** tab.")

# ---- Quiz ----
submitted_key = f"quiz_submitted_{sid}"
with tab_quiz:
    if sid in ss[K_RESULTS]:
        st.success(f'Last saved score: {ss[K_RESULTS][sid]["score"]:.0%}. You can retake the quiz below.')

    with st.form(f"quiz_{sid}"):
        for i, q in enumerate(questions, 1):
            st.markdown(f"**Q{i}. {q['question']}**")
            if q["type"] == "mcq":
                st.radio("Your answer", q["options"], index=None, key=f"ans_{q['id']}",
                         label_visibility="collapsed")
            else:
                st.text_area("Your answer", key=f"ans_{q['id']}", height=80,
                             label_visibility="collapsed")
        if st.form_submit_button("Check my answers", type="primary"):
            ss[submitted_key] = True

    if ss.get(submitted_key):
        st.divider()
        st.subheader("Answers")
        answers = {q["id"]: ss.get(f"ans_{q['id']}") or "" for q in questions}
        self_marked: dict[str, bool] = {}
        for i, q in enumerate(questions, 1):
            ua = answers[q["id"]]
            st.markdown(f"**Q{i}. {q['question']}**")
            if q["type"] == "mcq":
                ok = ua.strip().lower() == q["answer"].strip().lower()
                (st.success if ok else st.error)(
                    f'{"✅ Correct" if ok else "❌ Not quite"}. Your answer: {ua or "(none)"} · '
                    f'Correct answer: {q["answer"]}')
            else:
                st.markdown(f"Your answer: {ua or '_(none)_'}")
                st.info(f'Model answer: {q["answer"]}')
                self_marked[q["id"]] = st.checkbox("My answer matches the model answer",
                                                   key=f"self_{q['id']}")
            st.caption(q["explanation"])

        if st.button("Save my results", type="primary"):
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
        st.metric("Score", f'{res["score"]:.0%}')
        weak = [t for t, v in res["topic_scores"].items() if v < 0.6]
        if weak:
            st.warning("Needs review: " + ", ".join(topic_names.get(t, t) for t in weak) +
                       ". Go to the Plan page and click **Update plan from my quiz results**.")
        else:
            st.success("Nice work! This topic looks solid.")

st.divider()
c1, c2 = st.columns(2)
idx = ids.index(sid)
if idx + 1 < len(ids) and c1.button("Next session →"):
    ss[K_CURRENT] = ids[idx + 1]
    st.rerun()
if c2.button("🗂️ Back to my plan"):
    st.switch_page("pages/1_Plan.py")
