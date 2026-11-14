"""grade() and the Session page, driven by whatever is in mock_data/ (no hard-coded answers)."""
import os
from core.contracts import load_mock
from core.quiz_logic import grade

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
    qs = _questions()
    s = _first(qs, "short")[0]
    assert grade(qs, {s["id"]: "anything"}, {s["id"]: True})["results"][qs.index(s)]["correct"] is True
    assert grade(qs, {s["id"]: s["answer"]}, {})["results"][qs.index(s)]["correct"] is False


def test_empty_quiz():
    res = grade([], {}, {})
    assert res["score"] == 0.0 and res["results"] == [] and res["topic_scores"] == {}


def test_session_page_full_flow():
    from streamlit.testing.v1 import AppTest
    qs = _questions()
    m1, m2 = _first(qs, "mcq")[:2]
    s1 = _first(qs, "short")[0]
    at = AppTest.from_file(os.path.join(ROOT, "pages", "3_Session.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    at.run()
    assert not at.exception
    next(b for b in at.button if b.label == "Load demo data").click()  # no auto-load any more
    at.run()
    assert not at.exception
    at.radio(key=f"ans_{m1['id']}").set_value(m1["answer"])
    at.radio(key=f"ans_{m2['id']}").set_value(m2["answer"])
    at.text_area(key=f"ans_{s1['id']}").input(s1["answer"])
    at.button[0].click()  # form submit: "Check my answers"
    at.run()
    assert not at.exception
    at.checkbox(key=f"self_{s1['id']}").check()
    next(b for b in at.button if b.label == "Save my results").click()
    at.run()
    assert not at.exception
    res = at.session_state["quiz_results"]["s1"]
    assert res["score"] == 3 / len(qs)
