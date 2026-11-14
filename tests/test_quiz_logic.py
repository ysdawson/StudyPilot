import os
from core.contracts import load_mock
from core.quiz_logic import grade

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _questions():
    os.chdir(ROOT)
    return load_mock("session_s1.json")["questions"]


def test_grade_matches_mock_result():
    qs = _questions()
    expected = load_mock("quiz_result_s1.json")
    answers = {r["question_id"]: r["user_answer"] for r in expected["results"]}
    self_marked = {"s1-q5": False, "s1-q6": True}
    res = grade(qs, answers, self_marked)
    assert res["session_id"] == "s1"
    assert [r["correct"] for r in res["results"]] == [r["correct"] for r in expected["results"]]
    assert res["score"] == expected["score"]
    assert res["topic_scores"] == expected["topic_scores"]


def test_mcq_case_insensitive_and_unanswered_is_wrong():
    qs = _questions()
    res = grade(qs, {"s1-q1": "  2 a "}, {})
    by_id = {r["question_id"]: r for r in res["results"]}
    assert by_id["s1-q1"]["correct"] is True
    assert by_id["s1-q2"]["correct"] is False and by_id["s1-q2"]["user_answer"] == ""
    assert abs(res["score"] - 1 / 6) < 1e-9


def test_topic_scores_per_topic():
    qs = _questions()
    qs[0] = {**qs[0], "topic_id": "t2"}
    res = grade(qs, {"s1-q1": "2 A"}, {})
    assert res["topic_scores"] == {"t2": 1.0, "t1": 0.0}


def test_empty_quiz():
    res = grade([], {}, {})
    assert res["score"] == 0.0 and res["results"] == [] and res["topic_scores"] == {}


def test_session_page_full_flow():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(ROOT, "pages", "3_Session.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    at.run()
    assert not at.exception
    at.radio(key="ans_s1-q1").set_value("2 A")
    at.radio(key="ans_s1-q2").set_value("12 W")
    at.text_area(key="ans_s1-q5").input("10 V")
    at.button[0].click()  # form submit: "Check my answers"
    at.run()
    assert not at.exception
    at.checkbox(key="self_s1-q5").check()
    next(b for b in at.button if b.label == "Save my results").click()
    at.run()
    assert not at.exception
    res = at.session_state["quiz_results"]["s1"]
    assert res["score"] == 3 / 6
    assert res["topic_scores"] == {"t1": 0.5}
