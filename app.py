import streamlit as st
import pandas as pd
from openai import OpenAI
from fpdf import FPDF
import tempfile
import os
import json

# ✅ Config
st.set_page_config(page_title="GAAP Checker", layout="wide", page_icon="📘")

# 🖼️ Logo
if os.path.exists("ValiantLogWhite.png"):
    st.image("ValiantLogWhite.png", width=160)

# 🔑 OpenAI Client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 💾 Verified Violations Memory
MEMORY_FILE = "verified_issues.json"

def load_verified_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_verified_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

# 🧹 Clean & Truncate DataFrame
def clean_df(df):
    df = df.dropna(how='all')
    df = df.loc[~df.apply(lambda r: r.astype(str).str.lower().str.contains("total|header|subtotal").any(), axis=1)]
    df = df.loc[~df.iloc[:, 0].astype(str).str.strip().eq('')]
    return df

def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

# 🤖 GAAP Audit
def run_gaap_audit(client, df, file_type):
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
    violations = [line.strip() for line in full_text.splitlines() if line.lower().startswith("violation:")]
    return full_text, violations

# 📄 PDF Generator
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

# 📋 Checkbox Management
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

    # Save updated memory
    verified_memory[file_key] = [v for v, chk in st.session_state[session_key].items() if chk]
    save_verified_memory(verified_memory)

    return outstanding

# 🧮 Grading
def calculate_grade(unresolved_count):
    if unresolved_count == 0:
        return "A"
    elif unresolved_count <= 2:
        return "B"
    elif unresolved_count <= 5:
        return "C"
    elif unresolved_count <= 8:
        return "D"
    return "F"

# 🚀 Streamlit App UI
st.title("📘 GAAP Compliance Checker - Batch Mode")
st.caption("Audit files, review GAAP issues, verify false positives, and export clean summaries.")

verified_memory = load_verified_memory()
files = st.file_uploader("📤 Upload Financials", type=["xlsx", "xls"], accept_multiple_files=True)

if files:
    for f in files:
        file_key = f.name
        st.subheader(f"📄 Preview: {file_key}")
        df = pd.read_excel(f)
        df_clean = clean_df(df)
        st.dataframe(df_clean, use_container_width=True)

        audit_state_key = f"{file_key}_audit"
        run_button_label = f"🔍 Run GAAP Audit on {file_key}"

        if audit_state_key not in st.session_state:
            if st.button(run_button_label):
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
            unresolved = handle_violation_checkboxes(file_key, violations, verified_memory)

            grade = calculate_grade(len(unresolved))
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
