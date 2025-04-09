import streamlit as st
import pandas as pd
from openai import OpenAI
from fpdf import FPDF
import tempfile

# Load OpenAI key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Truncate dataframe to avoid token overflow
def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

# Auto-detect header row or fallback to QuickBooks default row
DEFAULT_HEADER_ROW = 6

# Tries to detect the first valid header row
def detect_header_row(df):
    for i, row in df.iterrows():
        if row.notnull().sum() >= 3:
            return i
    return DEFAULT_HEADER_ROW

# Load Excel file with QB-aware fallback and data cleanup
def load_excel(file, sheet_name=None):
    try:
        preview = pd.read_excel(file, sheet_name=sheet_name, header=None)
        if isinstance(preview, dict):
            sheet_name = list(preview.keys())[0]
            preview = preview[sheet_name]
        header_row = detect_header_row(preview)
        df = pd.read_excel(file, sheet_name=sheet_name, skiprows=header_row)
        df.columns = df.columns.astype(str).str.strip()
        df = df.dropna(axis=1, how='all')
        df = df.dropna(axis=0, how='all')
        for col in df.select_dtypes(include='object').columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").str.strip(), errors='ignore')
        return df
    except Exception as e:
        st.error(f"❌ Failed to load Excel file: {e}")
        raise

# Generate AI analysis
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

# Generate PDF from AI content
def generate_pdf_report(title, content):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("ValiantLogWhite.png", x=10, y=8, w=33)
    except:
        pass
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.multi_cell(0, 10, line)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# Streamlit UI
st.set_page_config(page_title="GAAP Compliance Checker - Valiant Partners", layout="wide")
st.image("logo.png", width=160)
st.markdown("""
    <style>
    .main {
        background-color: #f9f9f9;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .stApp {
        font-family: 'Helvetica Neue', sans-serif;
        color: #111;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #003366;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💼 GAAP Compliance Checker – Valiant Partners")
st.caption("Precision-grade audits with institutional clarity. Upload one or more Excel-based financial statements for an AI-driven GAAP compliance assessment.")

uploaded_files = st.file_uploader("📤 Upload Financial Statements (.xlsx, .xls)", type=["xlsx", "xls"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        try:
            df = load_excel(uploaded_file)
            file_type = file_name.split("_")[1].replace(".xlsx", "").replace(".xls", "") if "_" in file_name else "Unknown"
            st.subheader(f"📄 Preview: {file_name}")
            st.dataframe(df, use_container_width=True)

            if st.button(f"🔍 Run GAAP AI Audit on {file_name}", key=file_name):
                with st.spinner("Analyzing with AI..."):
                    audit_report = run_single_statement_analysis(df, file_type)
                    st.markdown("### ✅ AI Audit Report")
                    st.markdown(audit_report)

                    pdf_path = generate_pdf_report(f"{file_name} GAAP AI Audit", audit_report)
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📄 Download PDF Report",
                            data=f,
                            file_name=f"{file_name.replace(' ', '_')}_GAAP_Audit.pdf",
                            mime="application/pdf"
                        )

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
else:
    st.info("👆 Please upload one or more financial statements to begin.")