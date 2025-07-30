# app.py

import os
import streamlit as st
import pandas as pd

from gaap_audit.utils import (
    load_verified_memory,
    clean_df,
    generate_pdf,
    calculate_grade,
    save_verified_memory,
    load_vendor_memory,
)
from gaap_audit.ai import run_gaap_audit
from gaap_audit.ui import (
    handle_violation_checkboxes,
    show_vendor_mismatches,
    resolve_vendor_accounts
)

st.set_page_config(page_title="GAAP Compliance Checker", layout="wide", page_icon="📘")

# logo
if os.path.exists("ValiantLogWhite.png"):
    st.image("ValiantLogWhite.png", width=160)

# load memories
verified_memory = load_verified_memory()
vendor_memory = load_vendor_memory()

st.title("📘 GAAP Compliance Checker - Batch Mode")
st.caption("Audit files, review GAAP issues, verify false positives, and export clean summaries.")

# file uploader
files = st.file_uploader(
    "📤 Upload Financials",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
)

if files:
    for f in files:
        file_key = f.name
        st.subheader(f"📄 Preview: {file_key}")
        df = pd.read_excel(f)
        df_clean = clean_df(df)
        st.dataframe(df_clean, use_container_width=True)

        # update vendor memory if needed
        vendor_memory = resolve_vendor_accounts(df_clean, vendor_memory)
        show_vendor_mismatches(df_clean)

        audit_state_key = f"{file_key}_audit"
        if audit_state_key not in st.session_state:
            if st.button(f"🔍 Run GAAP Audit on {file_key}"):
                with st.spinner("Analyzing for GAAP compliance…"):
                    # call Gemini-based helper (two args)
                    audit_text, violations = run_gaap_audit(df_clean, "General Ledger")
                    st.session_state[audit_state_key] = {
                        "text": audit_text,
                        "violations": violations
                    }

        if audit_state_key in st.session_state:
            data = st.session_state[audit_state_key]
            audit_text = data["text"]
            violations = data["violations"]

            st.markdown("### 🧾 AI Audit Report (Detailed)")
            st.markdown(audit_text)

            st.markdown("### 🛠 GAAP Violations Checklist")
            handle_violation_checkboxes(file_key, violations, verified_memory)

            if st.button(f"✅ Update Checklist for {file_key}"):
                # compute unresolved
                unresolved = [v for idx, v in enumerate(violations)
                              if not st.session_state.get(f"verified::{file_key}::{idx}", False)]
                grade = calculate_grade(len(unresolved))
                st.session_state[f"{file_key}_grade"] = grade
                st.session_state[f"{file_key}_unresolved"] = unresolved

            if f"{file_key}_grade" in st.session_state:
                grade = st.session_state[f"{file_key}_grade"]
                unresolved = st.session_state.get(f"{file_key}_unresolved", [])
                st.markdown(f"### 📊 Updated GAAP Grade: `{grade}` ({len(unresolved)} unresolved issues)")

                if st.button(f"📥 Download Final PDF for {file_key}"):
                    summary = "\n".join([f"- {v.get('summary')}" for v in unresolved])
                    pdf_text = (
                        f"GAAP Audit Report: {file_key}\n\n"
                        f"Outstanding Violations:\n{summary}\n\n"
                        f"Final Grade: {grade}"
                    )
                    pdf_path = generate_pdf(f"{file_key} GAAP Audit", pdf_text)
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_file,
                            file_name=f"{file_key}_GAAP_Audit.pdf",
                            mime="application/pdf"
                        )
