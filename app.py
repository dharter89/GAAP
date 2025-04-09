import streamlit as st
import pandas as pd
from openai import OpenAI
from fpdf import FPDF
import tempfile
import os
import json
from PIL import Image

# ✅ Config
st.set_page_config(page_title="GAAP Checker", layout="wide", page_icon="📘")

# 🖼️ Logo
if os.path.exists("ValiantLogWhite.png"):
    st.image("ValiantLogWhite.png", width=160)

# 🔑 OpenAI Key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 💾 Persistent Verified Memory
MEMORY_FILE = "verified_issues.json"
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r") as f:
        verified_memory = json.load(f)
else:
    verified_memory = {}

# 🧹 Clean rows (ignore totals, headers, blanks)
def clean_df(df):
    df = df.dropna(how='all')
    df = df.loc[~df.apply(lambda r: r.astype(str).str.lower().str.contains("total|header|subtotal").any(), axis=1)]
    df = df.loc[~df.iloc[:, 0].astype(str).str.strip().eq('')]
    return df

# ✂️ Truncate for prompt size
def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

# 🧠 GAAP Audit Prompt
def run_gaap_audit(df, file_type, file_key):
    df = truncate_df(clean_df(df))
    prompt = f"""
You are an Ivy League-trained CPA and GAAP compliance expert.

Analyze the uploaded {file_type} for the following:
- GAAP violations
- Classification errors
- Missing or misclassified accounts
- Improper use of chart of accounts
- Missing required disclosures

For each issue:
- Start with `Violation: ...`
- Then include:
  - Reason: why this violates GAAP (include ASC reference if applicable)
  - Suggested Fix: write a correct journal entry
  - Example: sample correction
  - ASC Reference: cite the GAAP rule

At the bottom, assign a grade from A–F based on severity.

Here is the uploaded data:
{df.to_string(index=False)}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1800
    )
    full_text = response.choices[0].message.content
    violations = [line for line in full_text.splitlines() if line.strip().lower().startswith("violation:")]
    return full_text, violations

# 📝 PDF Generation
def generate_pdf(title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Arial", size=12)
    for line in content.split("\n"):
        pdf.multi_cell(0, 10, line)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp.name)
    return tmp.name

# 🎛️ App UI
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

        if st.button(f"🔍 Run GAAP Audit on {file_key}"):
            with st.spinner("Analyzing with GPT..."):
                audit_text, violations = run_gaap_audit(df_clean, "General Ledger", file_key)

                st.markdown("### 🧾 AI Audit Report (Detailed)")
                st.markdown(audit_text)

                st.markdown("### 🛠 GAAP Violations Checklist")
                session_key = f"verified::{file_key}"
                if session_key not in st.session_state:
                    st.session_state[session_key] = {}

                outstanding = []
                for v in violations:
                    v_key = f"{file_key}::{v}"
                    checked = v_key in verified_memory.get(file_key, [])
                    if not checked:
                        outstanding.append(v)
                    st.session_state[session_key][v] = st.checkbox(v, value=checked, key=v_key)

                # Update memory
                new_verified = [v for v, chk in st.session_state[session_key].items() if chk]
                verified_memory[file_key] = [f"{file_key}::{v}" for v in new_verified]
                with open(MEMORY_FILE, "w") as f:
                    json.dump(verified_memory, f, indent=2)

                # Grade logic
                unresolved = [v for v in violations if not st.session_state[session_key].get(v)]
                num_unresolved = len(unresolved)
                if num_unresolved == 0:
                    grade = "A"
                elif num_unresolved <= 2:
                    grade = "B"
                elif num_unresolved <= 5:
                    grade = "C"
                elif num_unresolved <= 8:
                    grade = "D"
                else:
                    grade = "F"

                st.markdown(f"### 📊 Updated GAAP Grade: `{grade}` ({num_unresolved} unresolved issues)")

                if st.button("📥 Download Final PDF"):
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
