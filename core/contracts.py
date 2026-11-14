"""Shared data contracts. FROZEN: do not edit without telling the whole team."""
import json, os
from typing import TypedDict, Literal, NotRequired

class Topic(TypedDict):
    id: str              # "t1", "t2", ...
    name: str            # "Thevenin equivalents"
    weight: float        # importance 0..1, all topics sum to about 1
    summary: str         # one sentence

class Deadline(TypedDict):
    title: str           # "Midterm"
    date: str            # "YYYY-MM-DD"

class TopicsResult(TypedDict):
    course: str
    topics: list[Topic]
    deadlines: list[Deadline]

class Goal(TypedDict):
    course: str
    target: str          # what we study for: "Midterm", "Lab report 3"
    deadline: str        # "YYYY-MM-DD"
    start_date: str      # "YYYY-MM-DD", usually today
    hours_per_week: float
    target_grade: str    # "Pass" | "B" | "A"

class Session(TypedDict):
    id: str              # "s1", "s2", ... unique in the plan
    order: int           # 1..n, study order
    topic_id: str        # must match a Topic.id
    title: str
    minutes: int         # 30..90
    objective: str       # one sentence
    kind: Literal["learn", "practice", "review"]

class Plan(TypedDict):
    goal: Goal
    sessions: list[Session]

class Guide(TypedDict):
    key_points: list[str]   # 3..6 bullets
    explanation: str        # short markdown
    example: str            # worked example, markdown
    source_hint: str        # where in the material, e.g. "Slides p.12-15"

class Question(TypedDict):
    id: str                 # "s1-q1"
    session_id: str
    topic_id: str
    type: Literal["mcq", "short"]
    question: str
    options: list[str]      # exactly 4 for mcq, [] for short
    answer: str             # mcq: exact text of the correct option; short: model answer
    explanation: str

class SessionContent(TypedDict):
    session_id: str
    guide: Guide
    questions: list[Question]   # 5..8

class Event(TypedDict):
    id: str                 # unique: "class-1", "study-s1", "deadline-1"
    title: str
    start: str              # "YYYY-MM-DDTHH:MM" local time
    end: str                # "YYYY-MM-DDTHH:MM"
    kind: Literal["class", "busy", "study", "deadline"]
    session_id: NotRequired[str]   # only when kind == "study"

class QuestionResult(TypedDict):
    question_id: str
    topic_id: str
    correct: bool
    user_answer: str

class QuizResult(TypedDict):
    session_id: str
    results: list[QuestionResult]
    score: float                    # 0..1
    topic_scores: dict[str, float]  # topic_id -> 0..1

# st.session_state keys (always use these constants, never raw strings)
K_DOC_TEXT = "doc_text"           # str: all uploaded PDF text joined
K_TOPICS = "topics"               # TopicsResult
K_GOAL = "goal"                   # Goal
K_PLAN = "plan"                   # Plan
K_CONTENT = "session_content"     # dict[str, SessionContent] keyed by session id
K_SCHEDULE = "schedule"           # list[Event]: classes/busy for ONE week, repeats weekly
K_CALENDAR = "calendar"           # list[Event]: classes for every week + study + deadlines
K_RESULTS = "quiz_results"        # dict[str, QuizResult] keyed by session id
K_CURRENT = "current_session_id"  # str

MOCK_DIR = "mock_data"

def mock_mode(st) -> bool:
    return str(st.secrets.get("MOCK_AI", "1")) == "1"

def load_mock(name: str):
    with open(os.path.join(MOCK_DIR, name), encoding="utf-8") as f:
        return json.load(f)

def load_mock_state(st) -> None:
    """Fill missing session_state keys from mock_data/ so any page works on its own."""
    ss = st.session_state
    ss.setdefault(K_DOC_TEXT, "Mock course text.")
    ss.setdefault(K_TOPICS, load_mock("topics.json"))
    ss.setdefault(K_PLAN, load_mock("plan.json"))
    ss.setdefault(K_GOAL, ss[K_PLAN]["goal"])
    ss.setdefault(K_CONTENT, {"s1": load_mock("session_s1.json"), "s2": load_mock("session_s2.json")})
    ss.setdefault(K_SCHEDULE, load_mock("schedule.json"))
    ss.setdefault(K_CALENDAR, load_mock("calendar.json"))
    ss.setdefault(K_RESULTS, {})
    ss.setdefault(K_CURRENT, "s1")
