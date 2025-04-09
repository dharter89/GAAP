import streamlit as st
import pandas as pd
from openai import OpenAI
from fpdf import FPDF
import tempfile
import os
import json
from PIL import Image

# 🖼️ Set page config early
st.set_page_config(page_title="GAAP Compliance Checker", layout="wide", page_icon="📘")

# 🏢 Display logo
logo_path = "ValiantLogWhite.png"
if os.path.exists(logo_path):
    st.image(Image.open(logo_path), width=160)

# 🔑 OpenAI API
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 📂 Load verified memory
memory_file = "verified_issues.json"
if os.path.exists(memory_file):
    with open(memory_file, "r") as f:
        verified_memory = json.load(f)
else:
    verified_memory = {}

# 📉 Clean dataframe (ignore header/total/blank rows)
def clean_df(df):
    df = df.dropna(how='all')
    df = df.loc[~df.apply(lambda row: row.astype(str).str.lower().str.contains("total|header|subtotal").any(), axis=1)]
    df = df.loc[~df.iloc[:, 0].astype(str).str.strip().eq('')]
    return df

# ✂️ Limit rows to avoid token overflow
def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

# 🧠 AI audit logic
@st.cache_data(show_spinner=False)
def run_gaap_audit(df, file_type, file_key):
    df = truncate_df(clean_df(df))
    prompt = f"""
You are a GAAP expert CPA.

Review the uploaded {file_type} for:
- GAAP violations
- Classification errors
- Misplaced accounts
- Missing data
- Show exact line items and reasoning

Format:
Violation: [message]
Suggested Fix: [journal entry or classification]

Here is the data:
{df.to_string(index=False)}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1800
    )

    report = response.choices[0].message.content

    # Parse violations
    lines = report.split("\n")
    violations = [line for line in lines if line.strip().lower().startswith("violation:")]

    return report, violations

# 🧾 PDF Export
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

# 🚀 Streamlit App
st.title("📘 GAAP Compliance Checker - Batch Mode")
st.caption("Upload reports. Flag violations. Track memory.")

files = st.file_uploader("📤 Upload Financial Statements", type=["xlsx", "xls"], accept_multiple_files=True)

if files:
    for f in files:
        file_key = f.name
        st.subheader(f"📄 Preview: {file_key}")
        df = pd.read_excel(f)
        df_clean = clean_df(df)
        st.dataframe(df_clean, use_container_width=True)

        if st.button(f"🔍 Run GAAP Audit on {file_key}"):
            with st.spinner("Analyzing..."):
                audit_text, issues = run_gaap_audit(df_clean, "Financial Report", file_key)

                st.markdown("### ✅ Raw AI Audit Report")
                verified = verified_memory.get(file_key, [])

                outstanding = []
                updated_issues = []
                for i, issue in enumerate(issues):
                    key = f"{file_key}::{issue.strip()}"
                    checked = key in verified
                    if not checked:
                        outstanding.append(issue)
                    if st.checkbox(issue.strip(), key=key, value=checked):
                        updated_issues.append(key)

                verified_memory[file_key] = updated_issues
                with open(memory_file, "w") as f:
                    json.dump(verified_memory, f, indent=2)

                # Grade
                total = len(issues)
                unresolved = len(outstanding)
                if total == 0:
                    grade = "A"
                elif unresolved == 0:
                    grade = "A"
                elif unresolved <= 2:
                    grade = "B"
                elif unresolved <= 5:
                    grade = "C"
                elif unresolved <= 8:
                    grade = "D"
                else:
                    grade = "F"

                st.markdown(f"### 📊 Updated GAAP Grade: **{grade}** ({unresolved} outstanding issues)")

                pdf = generate_pdf(f"{file_key} GAAP Audit", audit_text)
                with open(pdf, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Download Updated PDF Report",
                        data=pdf_file,
                        file_name=f"{file_key}_GAAP_Audit.pdf",
                        mime="application/pdf"
                    )
else:
    st.info("Upload one or more financial reports to get started.")
