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
    resolve_vendor_accounts,
)

# ─── Streamlit page config & logo ─────────────────────────────────────────────
st.set_page_config(page_title="GAAP Compliance Checker", layout="wide", page_icon="📘")

if os.path.exists("ValiantLogWhite.png"):
    st.image("ValiantLogWhite.png", width=160)

# ─── Load persisted memory ─────────────────────────────────────────────────────
verified_memory = load_verified_memory()
vendor_memory   = load_vendor_memory()

# ─── Page title & uploader ────────────────────────────────────────────────────
st.title("📘 GAAP Compliance Checker - Batch Mode")
st.caption("Upload files, run the audit, review issues, verify, and export a summary.")

files = st.file_uploader(
    "📤 Upload your General Ledger Excel files",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
)

# ─── Main loop over each uploaded file ────────────────────────────────────────
if files:
    for f in files:
        file_key = f.name
        st.subheader(f"📄 Preview: {file_key}")
        
        # 1) Read & clean
        df = pd.read_excel(f)
        df_clean = clean_df(df)
        st.dataframe(df_clean, use_container_width=True)

        # 2) Vendor mismatch UI
        #    (your helper should display & let you adjust vendor_memory)
        vendor_memory = resolve_vendor_accounts(vendor_memory, df_clean)
        show_vendor_mismatches(vendor_memory, df_clean)

        # 3) Run the GAAP audit via Gemini
        state_key = f"{file_key}_audit"
        if state_key not in st.session_state:
            if st.button(f"🔍 Run GAAP Audit on {file_key}"):
                with st.spinner("Analyzing for GAAP compliance…"):
                    ai_text, grade, violations = run_gaap_audit(
                        df_clean,
                        "General Ledger",
                    )
                    # store results in session
                    st.session_state[state_key] = {
                        "text":       ai_text,
                        "grade":      grade,
                        "violations": violations,
                    }

        # 4) If we have audit results, display them
        if state_key in st.session_state:
            result = st.session_state[state_key]
            ai_text    = result["text"]
            grade      = result.get("grade")
            violations = result["violations"]

            # 4a) Raw AI JSON
            st.markdown("### 🧾 AI Audit Report (Detailed)")
            st.markdown(ai_text)

            # 4b) Compliance grade metric
            st.markdown("### 📊 Compliance Grade")
            if grade is not None:
                st.metric(label="", value=grade)
            else:
                st.warning("❗ No grade returned from AI")

            # 4c) Violations checklist
            st.markdown("### 🛠 GAAP Violations Checklist")
            handle_violation_checkboxes(file_key, violations, verified_memory)

            # 4d) “Update Checklist” button to recalc grade
            if st.button(f"✅ Update Checklist for {file_key}"):
                # collect any that remain unchecked
                unresolved = [
                    v for v in violations
                    if not st.session_state.get(f"verified::{file_key}", {}).get(v, False)
                ]
                new_grade = calculate_grade(len(unresolved))
                st.session_state[f"{file_key}_grade"]      = new_grade
                st.session_state[f"{file_key}_unresolved"] = unresolved

            # 4e) Show updated grade + PDF export
            if f"{file_key}_grade" in st.session_state:
                ug = st.session_state[f"{file_key}_grade"]
                ur = st.session_state.get(f"{file_key}_unresolved", [])
                st.markdown(f"### 📈 Updated Grade: `{ug}` ({len(ur)} unresolved)")

                if st.button(f"📥 Download Final PDF for {file_key}"):
                    summary = "\n".join(f"- {v}" for v in ur)
                    pdf_text = (
                        f"GAAP Audit Report: {file_key}\n\n"
                        f"Outstanding Violations:\n{summary}\n\n"
                        f"Final Grade: {ug}"
                    )
                    pdf_path = generate_pdf(f"{file_key} GAAP Audit", pdf_text)
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_file,
                            file_name=f"{file_key}_GAAP_Audit.pdf",
                            mime="application/pdf",
                        )

    # ─── After looping all files, persist any updated memory ─────────────────
    save_verified_memory(verified_memory)
    save_verified_memory(vendor_memory)
