# StudyPilot (hackathon starter)

AI study planner: upload course docs + schedule, get a tailored plan with study guides and practice questions, placed in your week.

## Run (2 minutes)
    pip install -r requirements.txt
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # already done in the zip; add the real key
    streamlit run app.py

With `MOCK_AI = "1"` every page works on the data in `mock_data/` and the API is never called.

## Who owns what (only edit your own files)
| Member | Files |
|---|---|
| 1 - AI engine | core/llm.py, core/prompts.py, core/ai_engine.py, test_engine.py |
| 2 - App + integration | app.py, pages/1_Plan.py, pages/2_Calendar.py, core/scheduler.py, core/schedule_input.py, tests/ |
| 3 - Session + quiz | pages/3_Session.py, core/quiz_logic.py, .streamlit/config.toml |
| 4 - Data + demo | mock_data/, sample_data/, check_mocks.py, slides |

`core/contracts.py` is FROZEN: it defines every data shape and session_state key. Don't change it without telling everyone.

Already working: contracts, mock data (Circuit Analysis 1 demo), mock mode in ai_engine.py, page placeholders.
Stubs to replace: llm.py and the real-mode parts of ai_engine.py (M1), scheduler.py + schedule_input.py (M2), quiz_logic.py (M3).

## Timeline
0:00-0:20 kickoff, repo, API key test | 0:20-2:30 build on mocks | 2:30 checkpoint | 2:30-3:30 integrate |
3:30 FEATURE FREEZE | 3:30-4:15 test + fix | 4:15 record backup demo video | 4:30-5:00 rehearse

## Budget ($50 key)
Mock mode for everyone except member 1. Haiku while building, Sonnet for the demo. AI results are cached in cache/:
run the full demo once at ~4:00 and don't delete cache/ before presenting.
