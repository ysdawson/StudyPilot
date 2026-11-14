"""Public AI-engine functions used by the StudyPilot application."""

import base64
import copy
import json
import fitz  # pymupdf
import streamlit as st

from core import contracts, demo
from core.llm import call_claude_json
from core.prompts import PLAN, REPLAN, SESSION, TIMETABLE, TOPICS

# The 8 Calculus lectures are ~69k chars and the chain rule (Lecture 9) is at the end.
MAX_DOC_CHARS = 150_000


class AIConfigError(RuntimeError):
    """The user's own files need the real AI, but no API key is configured."""


def _use_mock() -> bool:
    """Demo data (loaded with 'Load demo data') answers from mock_data instantly.
    Anything else is the user's own material and always goes to Claude; without a
    key that is an error, never silently demo data. MOCK_AI no longer decides this."""
    if st.session_state.get(demo.DATA_SOURCE_KEY) == "demo":
        return True
    from core.llm import api_key_configured
    if not api_key_configured():
        raise AIConfigError("AI is not configured: set ANTHROPIC_API_KEY in .streamlit/secrets.toml "
                            "(or the app's Secrets on Streamlit Cloud) to analyze your own files.")
    return False


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _valid_topics(value: object) -> list[dict]:
    topics = value if isinstance(value, list) else []
    valid = []
    for topic in topics:
        topic = _as_dict(topic)
        if topic.get("name"):
            valid.append(copy.deepcopy(topic))
    for index, topic in enumerate(valid, 1):
        if not topic.get("id"):
            topic["id"] = f"t{index}"
    return valid


def _valid_sessions(value: object, topic_ids: set[str]) -> list[dict]:
    sessions = value if isinstance(value, list) else []
    valid = []
    for session in sessions:
        session = _as_dict(session)
        if session.get("topic_id") not in topic_ids:
            continue
        session = copy.deepcopy(session)
        if not session.get("id"):
            session["id"] = f"s{len(valid) + 1}"
        try:
            minutes = int(session.get("minutes", 30))
        except (TypeError, ValueError):
            minutes = 30
        session["minutes"] = max(30, min(90, minutes))
        if session.get("kind") not in {"learn", "practice", "review"}:
            session["kind"] = "learn"
        valid.append(session)
    return valid


def _valid_questions(value: object, session_id: str, topic_id: str = "") -> list[dict]:
    questions = value if isinstance(value, list) else []
    valid = []
    for question in questions:
        question = _as_dict(question)
        if not question:
            continue
        question = copy.deepcopy(question)
        if question.get("type") == "mcq":
            options = question.get("options")
            if not isinstance(options, list) or question.get("answer") not in options:
                continue
        if not str(question.get("explanation", "")).strip():
            question["explanation"] = "See the study guide."
        if question.get("type") != "mcq":
            continue  # multiple choice only (4 options, exactly one correct)
        if len(question.get("options") or []) != 4 or question["options"].count(question.get("answer")) != 1:
            continue
        if not question.get("question") or not str(question.get("answer", "")).strip():
            continue
        question["id"] = f"{session_id}-q{len(valid) + 1}"
        question["session_id"] = session_id  # contract field, grade() relies on it
        if not question.get("topic_id") and topic_id:
            question["topic_id"] = topic_id
        valid.append(question)
    return valid


def _dumps(value: object) -> str:
    # ensure_ascii=False: math symbols in the PDFs (e.g. 𝑓, 𝑥) stay readable
    # instead of becoming 𝑓 escapes (+48% characters).
    return json.dumps(value, ensure_ascii=False)


def _valid_deadlines(value: object) -> list[dict]:
    """Keep only deadlines with a title and a real YYYY-MM-DD date."""
    from datetime import date
    valid = []
    for item in value if isinstance(value, list) else []:
        item = _as_dict(item)
        try:
            day = date.fromisoformat(str(item.get("date", "")))
        except ValueError:
            continue
        if item.get("title"):
            valid.append({"title": str(item["title"]), "date": day.isoformat()})
    return valid


def _guide(result: dict) -> dict:
    """Map the prompt's flat guide fields to the contract's nested Guide."""
    guide = _as_dict(result.get("guide")) or result
    points = guide.get("key_points")
    return {
        "key_points": [str(p) for p in points] if isinstance(points, list) else [],
        "explanation": str(guide.get("explanation", "")),
        "example": str(guide.get("example") or guide.get("worked_example") or ""),
        "source_hint": str(guide.get("source_hint", "")),
    }


def _valid_events(value: object) -> list[dict]:
    events = value if isinstance(value, list) else []
    valid = []
    for event in events:
        event = _as_dict(event)
        if not all(event.get(key) for key in ("title", "start", "end")):
            continue
        event = copy.deepcopy(event)
        event["kind"] = event.get("kind") if event.get("kind") in {"class", "busy"} else "class"
        event["id"] = f"{event['kind']}-{len(valid) + 1}"
        valid.append(event)
    return valid


def _next_session_id(sessions: list[dict]) -> str:
    numbers = []
    for session in sessions:
        value = str(session.get("id", ""))
        if value.startswith("s") and value[1:].isdigit():
            numbers.append(int(value[1:]))
    return f"s{max(numbers, default=0) + 1}"


def extract_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF and preserve one-based page markers."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "".join(
        f"\n[Page {index}]\n{page.get_text()}"
        for index, page in enumerate(doc, 1)
    )


def extract_topics(doc_text: str) -> dict:
    """Extract and defensively normalize course topics and deadlines."""
    if _use_mock():
        return demo.load_mock(st, "topics.json")

    result = _as_dict(call_claude_json(TOPICS, doc_text[:MAX_DOC_CHARS]))
    topics = _valid_topics(result.get("topics"))
    for topic in topics:  # contract: Topic has id, name, weight, summary
        try:
            topic["weight"] = float(topic.get("weight", 0))
        except (TypeError, ValueError):
            topic["weight"] = 0.0
        topic["summary"] = str(topic.get("summary", ""))
    return {
        "course": str(result.get("course", "") or "My course"),
        "topics": topics,
        "deadlines": _valid_deadlines(result.get("deadlines")),
        # extra optional key (titles only, no dates) for Home's "What are you studying for?"
        "assessments": [str(a) for a in (result.get("assessments") or []) if str(a).strip()][:20],
    }


def make_plan(topics: dict, goal: dict) -> dict:
    """Create and normalize an ordered study plan."""
    topics = _as_dict(topics)
    goal = _as_dict(goal)
    if _use_mock():
        plan = _as_dict(demo.load_mock(st, "plan.json"))
        plan["goal"] = goal
        return plan

    content = _dumps({"topics": topics, "goal": goal})
    result = _as_dict(call_claude_json(PLAN, content))
    topic_ids = {
        topic.get("id")
        for topic in _valid_topics(topics.get("topics"))
        if topic.get("id")
    }
    sessions = _valid_sessions(result.get("sessions"), topic_ids)
    sessions.sort(key=lambda s: s.get("order", 0))
    for index, item in enumerate(sessions, 1):  # unique ids/orders, as the contract says
        item["id"], item["order"] = f"s{index}", index
    # Keep the student's goal: the prompt's goal shape has no "course".
    return {"goal": goal, "sessions": sessions}


def _mock_session_file(session: dict) -> str | None:
    """Demo content for this session: session_<id>.json if saved, else a saved
    session on the same topic (e.g. a chain-rule review), else None."""
    files = demo.session_files(st)
    own = f"session_{session.get('id')}.json"
    if own in files:
        return own
    for name in files:
        questions = _as_dict(demo.load_mock(st, name)).get("questions") or []
        topic_ids = [q.get("topic_id") for q in questions if isinstance(q, dict)]
        if topic_ids and max(set(topic_ids), key=topic_ids.count) == session.get("topic_id"):
            return name
    return None


def question_count(minutes: int) -> int:
    """Quiz length for a session: 30 min -> 8, 45 -> 10, 60 -> 12, 75+ -> 15 (nearest band)."""
    bands = [(30, 8), (45, 10), (60, 12), (75, 15)]
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        m = 30
    if m >= 75:
        return 15
    return min(bands, key=lambda b: (abs(b[0] - m), b[0]))[1]


def make_session(session: dict, topics: dict, doc_text: str) -> dict:
    """Create and normalize a guide and questions for one study session."""
    session = _as_dict(session)
    topics = _as_dict(topics)
    session_id = str(session.get("id", "s1"))
    if _use_mock():
        name = _mock_session_file(session)
        from core.llm import api_key_configured
        if name or not api_key_configured():
            content = _as_dict(demo.load_mock(st, name or "session_s1.json"))
            content["session_id"] = session_id
            content["questions"] = _valid_questions(content.get("questions"), session_id)
            return content
        # Demo session with no saved content on its topic: generate it for real, so each
        # session shows its own guide and quiz (demo data has no documents: use the topics).
        topic = next((t for t in topics.get("topics", []) if t.get("id") == session.get("topic_id")), {})
        doc_text = (f"(Demo data: no course documents loaded. Explain from standard knowledge of the "
                    f"course topic '{topic.get('name', session.get('title', ''))}': {topic.get('summary', '')})")

    target = question_count(session.get("minutes", 30))
    payload = {"session": session, "topics": topics, "target_questions": target,
               "doc_text": doc_text[:MAX_DOC_CHARS]}
    tokens = 4000 + 600 * target  # room for a 15-question quiz plus the guide
    result = _as_dict(call_claude_json(SESSION, _dumps(payload), max_tokens=tokens))
    questions = _valid_questions(result.get("questions"), session_id, str(session.get("topic_id", "")))
    if len(questions) < 0.8 * target:  # too few valid questions: retry once
        payload["retry_note"] = f"Return exactly {target} valid multiple-choice questions."
        retry = _as_dict(call_claude_json(SESSION, _dumps(payload), max_tokens=tokens))
        retry_qs = _valid_questions(retry.get("questions"), session_id, str(session.get("topic_id", "")))
        if len(retry_qs) > len(questions):
            result, questions = retry, retry_qs
    return {"session_id": session_id, "guide": _guide(result), "questions": questions}


def replan(plan: dict, topics: dict, results: dict) -> dict:
    """Append targeted review sessions based on quiz performance."""
    plan = _as_dict(plan)
    topics = _as_dict(topics)
    if _use_mock():
        updated = copy.deepcopy(plan)
        sessions = updated.get("sessions")
        if not isinstance(sessions, list):
            sessions = []
            updated["sessions"] = sessions
        # QuizResult has topic_scores {topic_id: 0..1}, not a top-level topic_id.
        topic_scores: dict[str, list[float]] = {}
        for result in results.values() if isinstance(results, dict) else []:
            for topic_id, score in _as_dict(_as_dict(result).get("topic_scores")).items():
                try:
                    topic_scores.setdefault(topic_id, []).append(float(score))
                except (TypeError, ValueError):
                    continue
        topic_id = min(
            topic_scores,
            key=lambda key: sum(topic_scores[key]) / len(topic_scores[key]),
            default=None,
        )
        if topic_id is None:
            available = _valid_topics(topics.get("topics"))
            topic_id = available[0].get("id") if available else "t1"
        new_id = _next_session_id(sessions)
        names = {t.get("id"): t.get("name") for t in _valid_topics(topics.get("topics"))}
        sessions.append({
            "id": new_id,
            "order": len(sessions) + 1,
            "topic_id": topic_id,
            "title": f"Review: {names.get(topic_id) or 'weak topic'}",
            "minutes": 30,
            "objective": "Fix mistakes from the latest quiz.",
            "kind": "review",
        })
        return updated

    content = _dumps({"plan": plan, "topics": topics, "results": results})
    result = _as_dict(call_claude_json(REPLAN, content))
    existing = plan.get("sessions") if isinstance(plan.get("sessions"), list) else []
    existing_ids = {item.get("id") for item in existing if isinstance(item, dict)}
    topic_ids = {
        topic.get("id")
        for topic in _valid_topics(topics.get("topics"))
        if topic.get("id")
    }
    new_sessions = [
        item for item in result.get("sessions", [])
        if (
            isinstance(item, dict)
            and item.get("id") not in existing_ids
            and item.get("topic_id") in topic_ids
        )
    ]
    normalized = copy.deepcopy(existing)
    for item in new_sessions:
        if item.get("kind") != "review":
            continue
        item = copy.deepcopy(item)
        item["id"] = _next_session_id(normalized)
        item["order"] = len(normalized) + 1
        try:
            item["minutes"] = max(30, min(45, int(item.get("minutes", 30))))
        except (TypeError, ValueError):
            item["minutes"] = 30
        normalized.append(item)
    return {"goal": plan.get("goal", {}), "sessions": normalized}


def parse_timetable_image(
    image_bytes: bytes, media_type: str, week_start: str
) -> list:
    """Extract and normalize class events from a timetable image."""
    if _use_mock():
        return demo.load_mock(st, "schedule.json")

    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(image_bytes).decode(),
            },
        },
        {"type": "text", "text": f"week_start = {week_start}"},
    ]
    return _valid_events(call_claude_json(TIMETABLE, content))
