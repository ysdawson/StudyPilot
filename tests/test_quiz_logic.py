"""grade() and the Session page, driven by whatever is in mock_data/ (no hard-coded answers)."""
import os
from core.demo import read_file
from core.quiz_logic import grade


def load_mock(name):
    return read_file("calculus", name)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _questions():
    os.chdir(ROOT)
    return load_mock("session_s1.json")["questions"]


def _first(qs, kind):
    return [q for q in qs if q["type"] == kind]


def test_grade_matches_mock_result():
    qs = _questions()
    expected = load_mock("quiz_result_s1.json")
    answers = {r["question_id"]: r["user_answer"] for r in expected["results"]}
    short_ids = {q["id"] for q in _first(qs, "short")}
    self_marked = {r["question_id"]: r["correct"] for r in expected["results"] if r["question_id"] in short_ids}
    res = grade(qs, answers, self_marked)
    assert res["session_id"] == "s1"
    assert [r["correct"] for r in res["results"]] == [r["correct"] for r in expected["results"]]
    assert res["score"] == expected["score"]
    assert res["topic_scores"] == expected["topic_scores"]


def test_mcq_case_insensitive_and_unanswered_is_wrong():
    qs = _questions()
    q1, q2 = _first(qs, "mcq")[:2]
    res = grade(qs, {q1["id"]: "  " + q1["answer"].upper() + " "}, {})
    by_id = {r["question_id"]: r for r in res["results"]}
    assert by_id[q1["id"]]["correct"] is True
    assert by_id[q2["id"]]["correct"] is False and by_id[q2["id"]]["user_answer"] == ""
    assert abs(res["score"] - 1 / len(qs)) < 1e-9


def test_topic_scores_per_topic():
    qs = _questions()
    i = qs.index(_first(qs, "mcq")[0])
    qs[i] = {**qs[i], "topic_id": "t-other"}
    res = grade(qs, {qs[i]["id"]: qs[i]["answer"]}, {})
    assert res["topic_scores"]["t-other"] == 1.0
    assert all(v == 0.0 for t, v in res["topic_scores"].items() if t != "t-other")


def test_short_answers_use_self_marking():
    qs = _questions() + [{"id": "s1-qx", "session_id": "s1", "topic_id": "t1", "type": "short",
                          "question": "Explain.", "options": [], "answer": "Because.", "explanation": "e"}]
    s = qs[-1]
    assert grade(qs, {s["id"]: "anything"}, {s["id"]: True})["results"][qs.index(s)]["correct"] is True
    assert grade(qs, {s["id"]: s["answer"]}, {})["results"][qs.index(s)]["correct"] is False


def test_empty_quiz():
    res = grade([], {}, {})
    assert res["score"] == 0.0 and res["results"] == [] and res["topic_scores"] == {}


def test_session_page_full_flow():
    from streamlit.testing.v1 import AppTest
    qs = _questions()
    m1, m2, m3 = _first(qs, "mcq")[:3]
    at = AppTest.from_file(os.path.join(ROOT, "pages", "3_Session.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    at.run()
    assert not at.exception
    at.selectbox(key="demo_pick_session").set_value("calculus")
    next(b for b in at.button if b.label == "Load demo data").click()  # no auto-load any more
    at.run()
    assert not at.exception
    at.radio(key=f"ans_{m1['id']}").set_value(m1["answer"])
    at.radio(key=f"ans_{m2['id']}").set_value(m2["answer"])
    at.radio(key=f"ans_{m3['id']}").set_value(m3["answer"])
    next(b for b in at.button if b.label == "Check my answers").click()
    at.run()
    assert not at.exception
    next(b for b in at.button if b.label == "Save my results").click()
    at.run()
    assert not at.exception
    res = at.session_state["quiz_results"]["s1"]
    assert res["score"] == 3 / len(qs)


def _session_app(dataset, fake_ai=None, key_ok=False):
    from streamlit.testing.v1 import AppTest
    import core.llm
    core.llm.api_key_configured = lambda: key_ok
    if fake_ai:
        import core.ai_engine
        core.ai_engine.call_claude_json = fake_ai
    at = AppTest.from_file(os.path.join(ROOT, "pages", "3_Session.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    at.run()
    at.selectbox(key="demo_pick_session").set_value(dataset)
    next(b for b in at.button if b.label == "Load demo data").click()
    at.run()
    assert not at.exception
    return at


def test_switching_session_in_the_dropdown_switches_the_content(monkeypatch):
    import core.llm
    monkeypatch.setattr(core.llm, "api_key_configured", core.llm.api_key_configured)
    at = _session_app("yassine")
    first_q = at.session_state["session_content"]["s1"]["questions"][0]["question"]
    at.sidebar.selectbox[0].set_value("s13")
    at.run()
    assert not at.exception
    content = at.session_state["session_content"]["s13"]
    assert content["questions"][0]["question"] != first_q
    assert all(q["id"].startswith("s13-") for q in content["questions"])
    shown = " ".join(m.value for m in at.markdown)
    assert content["questions"][0]["question"] in shown and first_q not in shown


def test_demo_session_without_saved_content_is_generated_when_key(monkeypatch):
    import core.llm, core.ai_engine
    monkeypatch.setattr(core.llm, "api_key_configured", core.llm.api_key_configured)
    calls = []

    def fake(system, content, max_tokens=4000):
        calls.append(content)
        return {"key_points": ["a", "b", "c"], "explanation": "Own guide", "worked_example": "w",
                "source_hint": "Outline week 9", "questions": [
                    {"type": "mcq", "question": "Own question?", "options": ["1", "2", "3", "4"],
                     "answer": "2", "explanation": "e"}]}
    monkeypatch.setattr(core.ai_engine, "call_claude_json", fake)
    at = _session_app("yassine", key_ok=True)
    at.sidebar.selectbox[0].set_value("s5")  # topic t4: no saved session on that topic
    at.run()
    assert not at.exception and len(calls) == 2  # 1 question < 80% of 8: one retry
    assert at.session_state["session_content"]["s5"]["guide"]["explanation"] == "Own guide"


def test_question_count_scales_with_session_minutes():
    from core.ai_engine import question_count
    assert [question_count(m) for m in (15, 30, 37, 40, 45, 50, 60, 65, 75, 90)] == [8, 8, 8, 10, 10, 10, 12, 12, 15, 15]


def test_make_session_asks_for_the_target_and_retries_when_short(monkeypatch):
    import json as _json
    import core.ai_engine as ae
    monkeypatch.setattr(ae, "_use_mock", lambda: False)
    calls = []

    def fake(system, content, max_tokens=4000):
        calls.append((_json.loads(content), max_tokens))
        n = 5 if len(calls) == 1 else 15  # first answer too short (< 80% of 15)
        return {"key_points": ["a"], "explanation": "e", "worked_example": "w", "source_hint": "s",
                "questions": [{"type": "mcq", "question": f"Q{i}", "options": ["a", "b", "c", "d"],
                               "answer": "a", "explanation": "x"} for i in range(n)]}
    monkeypatch.setattr(ae, "call_claude_json", fake)
    out = ae.make_session({"id": "s9", "topic_id": "t1", "minutes": 90}, {"topics": []}, "doc")
    assert [c[0]["target_questions"] for c in calls] == [15, 15] and calls[0][1] >= 12000
    assert len(out["questions"]) == 15 and out["questions"][-1]["id"] == "s9-q15"
