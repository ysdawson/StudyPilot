"""Public AI-engine functions used by the StudyPilot application."""

import base64
import copy
import json
import fitz  # pymupdf
import streamlit as st

from core import contracts
from core.llm import call_claude_json
from core.prompts import PLAN, REPLAN, SESSION, TIMETABLE, TOPICS


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


def _valid_questions(value: object, session_id: str) -> list[dict]:
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
        question["id"] = f"{session_id}-q{len(valid) + 1}"
        valid.append(question)
    return valid


def _valid_events(value: object) -> list[dict]:
    events = value if isinstance(value, list) else []
    valid = []
    for event in events:
        event = _as_dict(event)
        if not all(event.get(key) for key in ("title", "start", "end")):
            continue
        event = copy.deepcopy(event)
        event["kind"] = "class"
        event["id"] = f"class-{len(valid) + 1}"
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
    if contracts.mock_mode(st):
        return contracts.load_mock("topics.json")

    result = _as_dict(call_claude_json(TOPICS, doc_text[:60000]))
    topics = _valid_topics(result.get("topics"))
    deadlines = result.get("deadlines")
    return {
        "course": result.get("course", ""),
        "topics": topics,
        "deadlines": deadlines if isinstance(deadlines, list) else [],
    }


def make_plan(topics: dict, goal: dict) -> dict:
    """Create and normalize an ordered study plan."""
    topics = _as_dict(topics)
    goal = _as_dict(goal)
    if contracts.mock_mode(st):
        plan = _as_dict(contracts.load_mock("plan.json"))
        plan["goal"] = goal
        return plan

    content = json.dumps({"topics": topics, "goal": goal})
    result = _as_dict(call_claude_json(PLAN, content))
    topic_ids = {
        topic.get("id")
        for topic in _valid_topics(topics.get("topics"))
        if topic.get("id")
    }
    return {
        "goal": result.get("goal", goal),
        "sessions": _valid_sessions(result.get("sessions"), topic_ids),
    }


def make_session(session: dict, topics: dict, doc_text: str) -> dict:
    """Create and normalize a guide and questions for one study session."""
    session = _as_dict(session)
    topics = _as_dict(topics)
    session_id = str(session.get("id", "s1"))
    if contracts.mock_mode(st):
        content = _as_dict(contracts.load_mock("session_s1.json"))
        content["session_id"] = session_id
        content["questions"] = _valid_questions(content.get("questions"), session_id)
        return content

    prompt_content = json.dumps(
        {"session": session, "topics": topics, "doc_text": doc_text[:60000]}
    )
    result = _as_dict(call_claude_json(SESSION, prompt_content))
    result["session_id"] = session_id
    result["questions"] = _valid_questions(result.get("questions"), session_id)
    return result


def replan(plan: dict, topics: dict, results: dict) -> dict:
    """Append targeted review sessions based on quiz performance."""
    plan = _as_dict(plan)
    topics = _as_dict(topics)
    if contracts.mock_mode(st):
        updated = copy.deepcopy(plan)
        sessions = updated.get("sessions")
        if not isinstance(sessions, list):
            sessions = []
            updated["sessions"] = sessions
        topic_scores: dict[str, list[float]] = {}
        for result in results.values() if isinstance(results, dict) else []:
            if not isinstance(result, dict):
                continue
            topic_id = result.get("topic_id")
            score = result.get("score")
            if topic_id is not None:
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
        sessions.append({
            "id": new_id,
            "order": len(sessions) + 1,
            "topic_id": topic_id,
            "title": "Review: weak topic",
            "minutes": 30,
            "objective": "Fix mistakes from the latest quiz.",
            "kind": "review",
        })
        return updated

    content = json.dumps({"plan": plan, "topics": topics, "results": results})
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
    return {"goal": result.get("goal", plan.get("goal", {})), "sessions": normalized}


def parse_timetable_image(
    image_bytes: bytes, media_type: str, week_start: str
) -> list:
    """Extract and normalize class events from a timetable image."""
    if contracts.mock_mode(st):
        return contracts.load_mock("schedule.json")

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
