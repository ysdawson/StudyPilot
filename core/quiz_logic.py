"""OWNER: Member 3. Pure Python, no streamlit import (so it is easy to test)."""
from core.contracts import Question, QuestionResult, QuizResult


def _norm(text: str) -> str:
    """Compare answers ignoring case and extra spaces."""
    return " ".join(str(text).strip().lower().split())


def grade(questions: list[Question], answers: dict[str, str], self_marked: dict[str, bool]) -> QuizResult:
    """Grade one session's quiz.

    - mcq: correct when the chosen option matches q["answer"].
    - short: the student reads the model answer and marks themselves (self_marked[qid]).
    Unanswered questions count as wrong.
    """
    results: list[QuestionResult] = []
    per_topic: dict[str, list[bool]] = {}

    for q in questions:
        qid = q["id"]
        user_answer = answers.get(qid) or ""
        if q["type"] == "mcq":
            correct = bool(user_answer) and _norm(user_answer) == _norm(q["answer"])
        else:
            correct = bool(self_marked.get(qid, False))
        results.append({"question_id": qid, "topic_id": q["topic_id"],
                        "correct": correct, "user_answer": user_answer})
        per_topic.setdefault(q["topic_id"], []).append(correct)

    score = sum(r["correct"] for r in results) / len(results) if results else 0.0
    topic_scores = {t: sum(v) / len(v) for t, v in per_topic.items()}
    session_id = questions[0]["session_id"] if questions else ""
    return {"session_id": session_id, "results": results,
            "score": score, "topic_scores": topic_scores}
