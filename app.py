"""OWNER: Member 2. PLACEHOLDER Home page."""
import streamlit as st
from core.contracts import load_mock_state, mock_mode

st.set_page_config(page_title="StudyPilot", layout="wide")
st.title("StudyPilot")
st.write("Upload your course material and schedule. Get a tailored study plan with guides and practice questions.")
st.caption(f"Mock mode: {'ON (no API spend)' if mock_mode(st) else 'OFF (real Claude API)'}")
if st.sidebar.button("Load demo data"):
    load_mock_state(st)
    st.switch_page("pages/1_Plan.py")
