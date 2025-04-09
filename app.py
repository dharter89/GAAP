# ⚙️ Must be first Streamlit call
import streamlit as st
st.set_page_config(
    page_title="GAAP Compliance Checker (Batch)",
    layout="wide",
    page_icon="📘"
)

import pandas as pd
from openai import OpenAI
from fpdf import FPDF
import tempfile
from PIL import Image
import os
import json

# 🏢 Display Logo
logo_path = "ValiantLogWhite.png"
if os.path.exists(logo_path):
    st.image(Image.open(logo_path), width=160)
else:
    st.warning("⚠️ Company logo not found. Make sure 'ValiantLogWhite.png' is in your repo.")

# Load OpenAI key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 📚 Load memory (if any)
MEMORY_FILE = "violation_memory.json"
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r") as f:
        violation_memory = json.load(f)
else:
    violation_memory = {}

# Truncate dataframe to avoid token overflow
def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

# Header detection
DEFAULT_HEADER_ROW = 6
def detect_header_row(df):
    for i, row in df.iterrows():
        if row.notnull().sum() >= 3:
            return i
    return DEFAULT_HEADER_ROW

# Load Excel cleanly
def load_excel(file, sheet_name=None):
    try:
        preview = pd.read_excel(file, sheet_name=sheet_name, header=None)
        if isinstance(preview, dict):
            sheet_name = list(preview.keys())[0]
            preview = preview[sheet_name]
        header_row = detect_header_row(preview)
        df = pd.read_excel(file, sheet_name=sheet_name, skiprows=header_row)
        df.columns = df.columns.astype(str).str.strip()
        df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
        for col in df.select_dtypes(include='object').columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").str.strip(), errors='ignore')
        return df
    except Exception as e:
        st.error(f"❌ Failed to load Excel file: {e}")
        raise

# Analyze single statement
@st.cache_data(show_spinner=False)
def run_single_statement_analysis(df, file_type):
    df = truncate_df(df)
    prompt = f"""
You are an Ivy League-trained CPA and GAAP compliance expert.

Analyze the uploaded {file_type} for:
- GAAP violations
- Common accounting errors
- Needed Adjusting Journal Entries (AJEs)
- References to ASC (GAAP) standards
- For each issue, include a suggested journal entry (debit/credit, account name, amount)
- Include an appendix summarizing the raw data rows tied to each issue
- Itemize **every** infraction found (not just a few examples)

At the top of your response, assign a GAAP Compliance Grade from A to F:
- A: Fully compliant, no material issues
- B: Minor issues or suggestions
- C: Moderate GAAP issues, requires adjustments
- D: Significant errors or recurring issues
- F: Critical violations, potential misstatements

Return your response in clean markdown. Use headers and bullet points.

Here is the uploaded data:
{df.to_string(index=False)}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1800
    )
    return response.choices[0].message.content

# Extract only violations
def extract_violations(md_text):
    return [line.strip("- ").strip() for line in md_text.splitlines() if line.strip().startswith("- Violation:")]

# Grade recalculation logic
def recalculate_grade(num_unverified):
    if num_unverified == 0:
        return "A"
    elif num_unverified <= 2:
        return "B"
    elif num_unverified <= 4:
        return "C"
    elif num_unverified <= 6:
        return "D"
    else:
        return "F"

# PDF generation
def generate_pdf_report(title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.multi_cell(0, 10, line)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# Streamlit UI
st.title("📘 GAAP Compliance Checker - Batch Mode")
st.caption("Upload and audit financials with AI. Verify false positives to refine your GAAP score.")

uploaded_files = st.file_uploader("📤 Upload Financial Statements (.xlsx, .xls)", type=["xlsx", "xls"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        st.subheader(f"📄 Preview: {file_name}")
        try:
            df = load_excel(uploaded_file)
            file_type = file_name.split("_")[1] if "_" in file_name else "Unknown"
            st.dataframe(df, use_container_width=True)

            if st.button(f"🔍 Run GAAP AI Audit on {file_name}", key=file_name):
                with st.spinner("Analyzing with AI..."):
                    audit_report = run_single_statement_analysis(df, file_type)
                    violations = extract_violations(audit_report)

                    st.markdown("### ✅ Raw AI Audit Report")
                    session_key = f"verified_{file_name}"
                    if session_key not in st.session_state:
                        st.session_state[session_key] = {}

                    for i, v in enumerate(violations):
                        v_id = f"{file_name}::{v}"
                        default_check = violation_memory.get(v_id, False)
                        checked = st.checkbox(f"{v}", key=f"{session_key}_{i}", value=default_check)
                        if checked:
                            st.session_state[session_key][v] = True
                            violation_memory[v_id] = True
                        else:
                            st.session_state[session_key][v] = False

                    unverified = [v for v in violations if not st.session_state[session_key].get(v)]
                    updated_grade = recalculate_grade(len(unverified))
                    st.markdown(f"### 📊 Updated GAAP Grade: `{updated_grade}` ({len(unverified)} outstanding issues)")

                    if st.button("📥 Download Updated PDF Report"):
                        cleaned_report = "\n".join(f"- {v}" for v in unverified)
                        content = f"GAAP Audit Report for {file_name}\n\nVerified Issues Removed.\n\nOutstanding Violations:\n{cleaned_report}\n\nFinal Grade: {updated_grade}"
                        pdf_path = generate_pdf_report(f"{file_name} GAAP AI Audit", content)
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="📄 Download PDF",
                                data=f,
                                file_name=f"{file_name}_Filtered_GAAP_Audit.pdf",
                                mime="application/pdf"
                            )

                    # Save memory
                    with open(MEMORY_FILE, "w") as f:
                        json.dump(violation_memory, f, indent=2)

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
else:
    st.info("👆 Please upload one or more financial statements to begin.")
