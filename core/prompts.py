TOPICS = """
Read the provided course text. The text may contain page markers such as
[Page 1], [Page 2], and so on. Identify the course name, the major study
topics, and any deadlines explicitly supported by the text.

Return exactly this JSON shape:
{
  "course": "Circuit Analysis",
  "topics": [
    {"id": "t1", "name": "Ohm's law", "weight": 0.4,
     "summary": "Relating voltage, current and resistance in a resistor."},
    {"id": "t2", "name": "Kirchhoff's laws", "weight": 0.6,
     "summary": "Current and voltage laws for analysing whole circuits."}
  ],
  "deadlines": [],
  "assessments": ["Midterm", "Lab report 3"]
}

Hard rules:
- Use topic ids t1, t2, ... tn, in the order the material teaches them.
- Aim for about one topic per lecture or major section (6 to 12 topics).
  Do not merge rules or methods that are taught in separate lectures into one
  topic: a student must be able to be weak in one and strong in the other.
- Each weight must be a float between 0 and 1, with weights roughly summing to
  1.0.
- Each summary is one sentence.
- Deadlines: only include a deadline when the text states its full calendar
  date explicitly (day, month and year). Write it as {"title": "...",
  "date": "YYYY-MM-DD"}. If no such date is written in the text, return
  "deadlines": []. Never invent, guess or estimate a date, and never infer one
  from lecture numbers, weeks or the current date.
- assessments: the names of tests, exams, quizzes, projects and reports the text
  mentions (e.g. "Class Test 4", "Final exam"), with or without a date. Names
  only, never a date. Empty list if none.
- Topics are subject matter only. Ignore course administration: grading,
  penalties, attendance, policies, contact details, office hours, textbooks.
- If the text is a course outline (a week-by-week schedule rather than lecture
  notes), take the topics from the scheduled weeks and name the week(s) in each
  summary, e.g. "Outline weeks 13-14: ...".
- If the text starts with a "Focus:" note from the student, only return topics
  from the weeks or subjects it names.
- Never invent facts that the provided text does not support.

Return only the JSON. No prose. No markdown fences.
"""

PLAN = """
Given the provided topics and study goal, create an ordered study plan.
Schedule sessions between the goal's start date and deadline, emphasizing
important topics and following a progression from learning to practice to
review.

Return exactly this JSON shape:
{
  "goal": {
    "target": "Midterm",
    "deadline": "2026-03-20",
    "hours_per_week": 6,
    "target_grade": "A",
    "start_date": "2026-03-01"
  },
  "sessions": [
    {
      "id": "s1",
      "order": 1,
      "topic_id": "t1",
      "title": "Learn Ohm's law",
      "minutes": 60,
      "objective": "Apply Ohm's law to basic circuits.",
      "kind": "learn"
    }
  ]
}

Hard rules:
- Use session ids s1, s2, ... sn, and session order values 1, 2, ... n.
- Every session.topic_id must exist in the provided topics list.
- Every session must be 30 to 90 minutes.
- Total study minutes should be approximately
  goal.hours_per_week * the number of weeks between goal.start_date and
  goal.deadline.
- Follow the topic order t1, t2, ... (prerequisites first, as the course
  teaches them). Within a topic, learn comes before practice. Put any review
  sessions at the end.
- Higher-weight topics should receive more sessions.
- A target_grade of "A" means include more practice sessions.
- Every session.kind must be exactly "learn", "practice", or "review".

Return only the JSON. No prose. No markdown fences.
"""

SESSION = """
Given one study session, the topic list, and the full course document text,
create a study guide and practice questions grounded in that document. Use
[Page N] markers in the document when identifying source material.

Return exactly this JSON shape:
{
  "session_id": "s1",
  "key_points": ["Use V = IR", "Check units before calculating"],
  "explanation": "Ohm's law relates voltage, current, and resistance. Use it when two of these quantities are known.",
  "worked_example": "For V = 12 V and R = 4 ohms, I = V/R = 3 A.",
  "source_hint": "[Page 2]",
  "questions": [
    {
      "id": "s1-q1",
      "type": "mcq",
      "question": "What is the current when V=12 V and R=4 ohms?",
      "options": ["2 A", "3 A", "4 A", "8 A"],
      "answer": "3 A",
      "explanation": "Using I = V/R gives 12/4 = 3 A.",
      "topic_id": "t1"
    }
  ]
}

Hard rules:
- Include 3 to 6 key_points.
- The explanation must be short and 2 to 4 sentences.
- Include exactly one worked_example.
- source_hint must reference [Page N] markers from the provided document text.
  The text may contain several files, each starting with "=== <file name> ===",
  and page numbers restart in every file, so always cite the file too, e.g.
  "Lecture9.pdf p.14-16". Cite sources the same way in question explanations.
- Include 5 to 8 questions, mixing type="mcq" and type="short".
- Every mcq question must have exactly 4 options.
- For mcq questions, answer must exactly equal one of the options.
- Every question must have a non-empty explanation.
- Use question ids <session_id>-q1, <session_id>-q2, and so on.
- Every question.topic_id must exist in the provided topics list.
- Ground every part of the response in the provided document text and do not
  contradict it.
- If the text is only a course outline (a week-by-week schedule, no lecture
  notes), you may explain the session's topic from standard, well-established
  knowledge of the subject, but source_hint and the explanations must cite the
  outline week instead of pages, e.g. "Outline week 13: VoIP Fundamentals".
  Never cite slides or pages that are not in the text.
- The document text was extracted from slides, so exponents and brackets may
  be flattened (e.g. "x2 + 1" means x^2 + 1). Interpret them mathematically.
- Work out every answer step by step before writing it, and make sure the
  answer and explanation are mathematically correct and agree with each other.
- Write math in plain text that reads well in Markdown, e.g. x^2, sqrt(x),
  (x^2 + 1)^3, sin(x)/x, lim_(x->0). Do not use LaTeX.

Return only the JSON. No prose. No markdown fences.
"""

REPLAN = """
Given the current study plan, the topics, and quiz results, return an updated
study plan. Preserve the existing plan and add targeted review sessions for
topics where the average quiz score is below 0.6.

Return exactly this JSON shape:
{
  "goal": {
    "target": "Midterm",
    "deadline": "2026-03-20",
    "hours_per_week": 6,
    "target_grade": "B",
    "start_date": "2026-03-01"
  },
  "sessions": [
    {
      "id": "s1",
      "order": 1,
      "topic_id": "t1",
      "title": "Learn Ohm's law",
      "minutes": 60,
      "objective": "Apply Ohm's law to basic circuits.",
      "kind": "learn"
    },
    {
      "id": "s8",
      "order": 8,
      "topic_id": "t1",
      "title": "Review Ohm's law",
      "minutes": 40,
      "objective": "Correct mistakes from the Ohm's law quiz.",
      "kind": "review"
    }
  ]
}

Hard rules:
- Keep ALL existing sessions unchanged.
- For each topic whose average score is below 0.6, append exactly one
  kind="review" session.
- Continue session ids from the existing numbering; if the plan ends at s7,
  reviews start at s8.
- Review sessions must be 30 to 45 minutes.
- New sessions must have sequential order values after the existing sessions.
- Every new session.topic_id must exist in the provided topics list.

Return only the JSON. No prose. No markdown fences.
"""

TIMETABLE = """
Read the provided timetable image and use the supplied Monday date of the
target week to extract every class and every other fixed commitment (work
shifts, appointments). Return one event for each occurrence that falls in the
Monday-through-Sunday week.

Return exactly this JSON shape:
[
  {
    "title": "Circuit Analysis",
    "start": "2026-03-02T09:00",
    "end": "2026-03-02T10:30",
    "kind": "class",
    "id": "class-1"
  }
]

Hard rules:
- start and end must use ISO format YYYY-MM-DDTHH:MM.
- event.kind is "class" for courses, labs and lectures, and "busy" for work
  shifts or any other non-class commitment.
- Use event ids <kind>-1, <kind>-2, ... numbered in output order.
- Times are 24-hour HH:MM: convert "4:00 PM" to "16:00".
- Every date must fall within the Monday-Sunday week beginning at week_start.
- If a class occurs multiple times, create one event for each occurrence.
- Use the event title exactly as written in the image.
- Do not invent classes or times that are not supported by the image.

Return only the JSON. No prose. No markdown fences.
"""