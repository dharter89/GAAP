# gaap_audit/ui.py
import streamlit as st
from gaap_audit.utils import save_verified_memory

def handle_violation_checkboxes(file_key, violations, verified_memory):
    session_key = f"verified::{file_key}"
    if session_key not in st.session_state:
        st.session_state[session_key] = {}

    if file_key not in verified_memory:
        verified_memory[file_key] = []

    outstanding = []
    for v in violations:
        checkbox_key = f"{session_key}::{v}"
        checked = v in verified_memory[file_key]
        state = st.checkbox(v, value=checked, key=checkbox_key)
        st.session_state[session_key][v] = state
        if not state:
            outstanding.append(v)

    verified_memory[file_key] = [v for v, chk in st.session_state[session_key].items() if chk]
    save_verified_memory(verified_memory)
