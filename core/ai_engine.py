"""OWNER: Member 1. STUB - mock mode already works so others can build; replace the real-mode parts."""
import copy
import streamlit as st
from core.contracts import (TopicsResult, Goal, Plan, Session, SessionContent, QuizResult,
                            Event, mock_mode, load_mock)

def extract_text(pdf_bytes: bytes) -> str:
    import fitz  # pymupdf
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "".join(f"\n[Page {i + 1}]\n" + page.get_text() for i, page in enumerate(doc))

def extract_topics(doc_text: str) -> TopicsResult:
    if mock_mode(st):
        return load_mock("topics.json")
    raise NotImplementedError("Member 1: real extract_topics")

def make_plan(topics: TopicsResult, goal: Goal) -> Plan:
    if mock_mode(st):
        plan = load_mock("plan.json"); plan["goal"] = goal; return plan
    raise NotImplementedError("Member 1: real make_plan")

def make_session(session: Session, topics: TopicsResult, doc_text: str) -> SessionContent:
    if mock_mode(st):
        c = load_mock("session_s1.json"); sid = session["id"]
        c["session_id"] = sid
        for i, q in enumerate(c["questions"], 1):
            q["id"], q["session_id"] = f"{sid}-q{i}", sid
        return c
    raise NotImplementedError("Member 1: real make_session")

def replan(plan: Plan, topics: TopicsResult, results: dict[str, QuizResult]) -> Plan:
    if mock_mode(st):
        new = copy.deepcopy(plan); n = len(new["sessions"]) + 1
        new["sessions"].append({"id": f"s{n}", "order": n, "topic_id": "t1", "title": "Review: weak topic",
                                "minutes": 30, "objective": "Fix the mistakes from the last quiz", "kind": "review"})
        return new
    raise NotImplementedError("Member 1: real replan")

def parse_timetable_image(image_bytes: bytes, media_type: str, week_start: str) -> list[Event]:
    if mock_mode(st):
        return load_mock("schedule.json")
    raise NotImplementedError("Member 1: real parse_timetable_image")
