"""OWNER: Member 3. PLACEHOLDER."""
import streamlit as st
from core.contracts import *

if K_PLAN not in st.session_state:
    if mock_mode(st):
        load_mock_state(st)
    else:
        st.info("Start on the Home page"); st.stop()

st.title("Study session")
st.json(st.session_state[K_CONTENT].get(st.session_state[K_CURRENT], {}))
