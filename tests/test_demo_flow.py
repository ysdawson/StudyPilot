"""End-to-end demo flow in mock mode, following sample_data/calculus/README_Demo_Instructions.md:
Load demo data -> Plan -> open the chain-rule session -> get a chain-rule question wrong ->
save -> back to Plan -> Update plan -> the new review session targets the chain rule."""
import json
import os
from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mock(name):
    with open(os.path.join(ROOT, "mock_data", name), encoding="utf-8") as f:
        return json.load(f)


def _btn(at, label):
    return next(b for b in at.button if b.label == label)


def _run(at):
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_demo_flow_chain_rule_mistake_gets_a_chain_rule_review():
    os.chdir(ROOT)
    topics, plan = _mock("topics.json"), _mock("plan.json")
    chain = next(t["id"] for t in topics["topics"] if "chain" in t["name"].lower())
    sess = next(s for s in plan["sessions"] if s["topic_id"] == chain)

    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=30)
    at.secrets["MOCK_AI"] = "1"
    _run(at)
    _btn(at, "Load demo data").click(); _run(at)
    assert at.title[0].value == "Your study plan"
    assert at.session_state["schedule"] == _mock("schedule.json")

    at.button(key=f"open-{sess['id']}").click(); _run(at)
    content = at.session_state["session_content"][sess["id"]]
    assert {q["topic_id"] for q in content["questions"]} >= {chain}  # real chain-rule content
    qs = content["questions"]
    wrong = next(q for q in qs if q["type"] == "mcq" and q["topic_id"] == chain)
    at.radio(key=f"ans_{wrong['id']}").set_value(next(o for o in wrong["options"] if o != wrong["answer"]))
    others = [q for q in qs if q["type"] == "mcq" and q["topic_id"] != chain]  # other topics answered right
    for q in others:
        at.radio(key=f"ans_{q['id']}").set_value(q["answer"])
    _btn(at, "Check my answers").click(); _run(at)
    _btn(at, "Save my results").click(); _run(at)
    res = at.session_state["quiz_results"][sess["id"]]
    assert res["topic_scores"][chain] < 0.6

    _btn(at, "🗂️ Back to my plan").click(); _run(at)
    assert at.title[0].value == "Your study plan"
    n = len(at.session_state["plan"]["sessions"])
    _btn(at, "Update plan from my quiz results").click(); _run(at)
    ss = at.session_state
    assert len(ss["plan"]["sessions"]) == n + 1
    review = ss["plan"]["sessions"][-1]
    assert review["kind"] == "review" and review["topic_id"] == chain
    assert "chain" in review["title"].lower()
    # calendar rebuilt from the demo timetable: same classes, review scheduled
    assert sum(e["kind"] == "class" for e in ss["calendar"]) == sum(e["kind"] == "class" for e in _mock("calendar.json"))
    assert any(e.get("session_id") == review["id"] for e in ss["calendar"])

    at.button(key=f"open-{review['id']}").click(); _run(at)
    review_qs = at.session_state["session_content"][review["id"]]["questions"]
    assert review_qs and review_qs[0]["session_id"] == review["id"]
    assert {q["topic_id"] for q in review_qs} >= {chain}  # review shows chain-rule material
