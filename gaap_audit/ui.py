# gaap_audit/ui.py

import sys, os, json
import streamlit as st
import pandas as pd

# make sure the gaap_audit package is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gaap_audit.utils import (
    clean_df,
    truncate_df,
    save_verified_memory,
    load_vendor_memory,
)
from gaap_audit.ai import run_gaap_audit

st.set_page_config(page_title="GAAP Compliance Checker", layout="wide")

# logo at the top center
logo_path = os.path.join(os.path.dirname(__file__), "..", "LogoBlack.png")
if os.path.exists(logo_path):
    st.image(logo_path, use_container_width=False, width=300)

st.title("GAAP Compliance Checker")

# load any previously saved memory
vendor_mem = load_vendor_memory()

# 1) file uploader
uploaded_docs = st.file_uploader(
    "Upload your General Ledger Excel files:",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
)

if uploaded_docs:
    # read & concat
    dfs = [pd.read_excel(doc) for doc in uploaded_docs]
    combined_df = pd.concat(dfs, ignore_index=True)

    # 2) run the audit when the button is pressed
    if st.button("Run GAAP Audit"):
        with st.spinner("Lets see what you did…"):
            full_text, grade, violations = run_gaap_audit(
                combined_df, file_type="excel"
            )

        # 3) show the grade
        st.subheader("Compliance Grade")
        if grade:
            st.metric(label="", value=grade)
        else:
            st.warning("❗ No grade returned from AI")

        # 4) raw AI response in a collapsible expander
        with st.expander("🔍 View raw AI response"):
            try:
                parsed = json.loads(full_text)
                st.json(parsed)
            except Exception:
                st.text(full_text)

        # 5) nicely formatted violations (nested bullets)
        st.subheader("Detected Violations")
        if violations:
            for v in violations:
                # summary as top-level bullet
                st.markdown(f"- **{v.get('summary','(no summary)')}**")
                # indented sub-bullets
                st.markdown(f"    - 📍 Location: {v.get('location','N/A')}")
                st.markdown(f"    - 🛠️ Correction: {v.get('suggested_correction','N/A')}")
                # blank line between violations
                st.markdown("")
        else:
            st.success("✅ No violations detected.")

        # 6) persist memory if you like
        save_verified_memory(vendor_mem)

def handle_violation_checkboxes(file_key, violations, verified_memory):
    """
    Render a checkbox for each violation, track selections in session_state.
    """
    for idx, v in enumerate(violations):
        key = f"verified::{file_key}::{idx}"
        default = False
        if file_key in verified_memory:
            default = verified_memory[file_key].get(idx, False)
        checked = st.checkbox(f"{v.get('location','')} - {v.get('summary','')}", key=key, value=default)
        # store the user choice
        st.session_state.setdefault('verified', {}).setdefault(file_key, {})[idx] = checked
    return st.session_state.get('verified', {}).get(file_key, {})
def show_vendor_mismatches(df_clean):
    """
    Placeholder for vendor mismatch display.  Customize as needed.
    """
    st.info("Vendor mismatch checking is not yet implemented.")


def resolve_vendor_accounts(df_clean, vendor_memory):
    """
    Placeholder for resolving vendor accounts into memory. Returns passed memory.
    """
    return vendor_memory
