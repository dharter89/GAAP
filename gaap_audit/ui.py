# gaap_audit/ui.py

import sys, os, json
import streamlit as st
import pandas
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

def handle_violation_checkboxes(file_key: str,
                                violations: list[dict],
                                verified_memory: dict) -> dict:
    """
    Render a checkbox for each violation, track selections in session_state,
    and update verified_memory[file_key] accordingly.
    Returns the updated verified_memory[file_key] dict.
    """
    for idx, v in enumerate(violations):
        key = f"verified::{file_key}::{idx}"
        default = False
        if file_key in verified_memory:
            default = verified_memory[file_key].get(idx, False)

        checked = st.checkbox(
            f"{v.get('location','N/A')} – {v.get('summary','(no summary)')}",
            key=key,
            value=default,
        )

        # persist choice back into memory
        verified_memory.setdefault(file_key, {})[idx] = checked

    return verified_memory[file_key]


def show_vendor_mismatches(vendor_memory: dict,
                           violations: list[dict]) -> None:
    """
    Compare each violation’s suggested_correction against any prior
    mapping in vendor_memory, and display a warning if they differ.
    """
    st.subheader("🔄 Vendor Mismatch Warnings")
    found_mismatch = False

    for v in violations:
        vendor    = v.get("vendor_name") or v.get("location", "")
        new_sugg  = v.get("suggested_correction", "")
        prev_sugg = vendor_memory.get(vendor)

        if prev_sugg and prev_sugg != new_sugg:
            st.warning(
                f"Vendor **{vendor}** was previously classified as **{prev_sugg}**,\n"
                f"but now suggested: **{new_sugg}**."
            )
            found_mismatch = True

    if not found_mismatch:
        st.info("No vendor-mismatch issues detected.")


def resolve_vendor_accounts(vendor_memory: dict,
                            df_clean: pd.DataFrame) -> dict:
    """
    Placeholder for vendor-memory resolution logic.
    E.g. you might present a selectbox per unique vendor
    and update vendor_memory accordingly.
    For now, simply return vendor_memory unmodified.
    """
    # TODO: implement interactive resolution
    return vendor_memory