"""Run the StudyPilot AI pipeline against a real sample PDF."""

import json
from pathlib import Path
import traceback


def main() -> int:
    """Run the complete AI pipeline and print each result."""
    try:
        sample_pdfs = sorted(
            (Path(__file__).resolve().parent / "sample_data").glob("*.pdf")
        )
        if not sample_pdfs:
            print("Error: no sample PDF found in sample_data/.")
            return 1

        from core.ai_engine import extract_text, extract_topics, make_plan, make_session

        pdf_bytes = sample_pdfs[0].read_bytes()
        goal = {
            "target": "Midterm",
            "deadline": "2026-12-15",
            "start_date": "2026-11-14",
            "hours_per_week": 6,
            "target_grade": "B",
        }

        text = extract_text(pdf_bytes)
        print("=== EXTRACTED TEXT (first 500 chars) ===")
        print(text[:500])

        topics = extract_topics(text)
        print("=== TOPICS ===")
        print(json.dumps(topics, indent=2))

        plan = make_plan(topics, goal)
        print("=== PLAN ===")
        print(json.dumps(plan, indent=2))

        first_session = plan["sessions"][0]
        content = make_session(first_session, topics, text)
        print("=== SESSION CONTENT (session 1) ===")
        print(json.dumps(content, indent=2))

        print("✅ Engine test passed — chain ran end-to-end.")
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())