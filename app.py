import os
import streamlit as st
import pandas as pd
from openai import OpenAI

from gaap_audit.utils import (
    load_verified_memory, clean_df, generate_pdf,
    calculate_grade, save_verified_memory
)
from gaap_audit.ai import run_gaap_audit
from gaap_audit.ui import handle_violation_checkboxes

st.set_page_config(page_title="GAAP Checker", layout="wide", page_icon="📘")

if os.path.exists("ValiantLogWhite.png"):
    st.image("ValiantLogWhite.png", width=160)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
verified_memory = load_verified_memory()

st.title("📘 GAAP Compliance Checker - Batch Mode")
st.caption("Audit files, review GAAP issues, verify false positives, and export clean summaries.")

files = st.file_uploader("📤 Upload Financials", type=["xlsx", "xls"], accept_multiple_files=True)

if files:
    for f in files:
        file_key = f.name
        st.subheader(f"📄 Preview: {file_key}")
        df = pd.read_excel(f)
        df_clean = clean_df(df)
        st.dataframe(df_clean, use_container_width=True)

        audit_state_key = f"{file_key}_audit"

        if audit_state_key not in st.session_state:
            if st.button(f"🔍 Run GAAP Audit on {file_key}"):
                with st.spinner("Analyzing with GPT..."):
                    audit_text, violations = run_gaap_audit(client, df_clean, "General Ledger")
                    st.session_state[audit_state_key] = {
                        "text": audit_text,
                        "violations": violations
                    }

        if audit_state_key in st.session_state:
            audit_data = st.session_state[audit_state_key]
            audit_text = audit_data["text"]
            violations = audit_data["violations"]

            st.markdown("### 🧾 AI Audit Report (Detailed)")
            st.markdown(audit_text)

            st.markdown("### 🛠 GAAP Violations Checklist")
            handle_violation_checkboxes(file_key, violations, verified_memory)

            if st.button(f"✅ Update Checklist for {file_key}"):
                unresolved = [
                    v for v in violations
                    if not st.session_state.get(f"verified::{file_key}", {}).get(v, False)
                ]
                grade = calculate_grade(len(unresolved))
                st.session_state[f"{file_key}_grade"] = grade
                st.session_state[f"{file_key}_unresolved"] = unresolved

            if f"{file_key}_grade" in st.session_state:
                grade = st.session_state[f"{file_key}_grade"]
                unresolved = st.session_state.get(f"{file_key}_unresolved", [])
                st.markdown(f"### 📊 Updated GAAP Grade: `{grade}` ({len(unresolved)} unresolved issues)")

                if st.button(f"📥 Download Final PDF for {file_key}"):
                    report_summary = "\n".join([f"- {v}" for v in unresolved])
                    pdf_text = f"GAAP Audit Report: {file_key}\n\nOutstanding Violations:\n{report_summary}\n\nFinal Grade: {grade}"
                    pdf_path = generate_pdf(f"{file_key} GAAP Audit", pdf_text)
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📄 Download PDF",
                            data=f,
                            file_name=f"{file_key}_GAAP_Audit.pdf",
                            mime="application/pdf"
                        )
