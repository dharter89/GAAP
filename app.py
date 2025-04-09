import streamlit as st
import pandas as pd
from openai import OpenAI

# Load OpenAI key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Utility: Truncate dataframe to avoid token overflow
def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

# Load Excel file with sheet logic
def load_excel(file, sheet_name=None):
    result = pd.read_excel(file, sheet_name=sheet_name)
    
    # If a dict is returned (multiple sheets), select the first one unless specified
    if isinstance(result, dict):
        if sheet_name:
            result = result.get(sheet_name)
        else:
            # Default to the first sheet if no sheet_name is passed
            result = next(iter(result.values()))
    
    return result


# Dynamic prompt builder
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
- Return your response in clean markdown.

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

# Streamlit UI
st.set_page_config(page_title="GAAP Compliance Checker (Per File)", layout="wide")
st.title("📘 GAAP Compliance Checker")
st.caption("Upload and audit one statement at a time for GAAP compliance.")

file_type = st.selectbox("Select the Financial Statement Type", [
    "Balance Sheet", "Profit and Loss", "Cash Flow", "General Ledger"])

uploaded_file = st.file_uploader(f"📤 Upload {file_type} (.xlsx)", type="xlsx")

if uploaded_file:
    try:
        df = load_excel(uploaded_file)
        st.success("✅ File loaded successfully")
        st.subheader(f"📑 Preview: {file_type}")
        st.dataframe(df, use_container_width=True)

        if st.button("🔍 Run GAAP AI Audit"):
            with st.spinner("Analyzing with AI..."):
                audit_report = run_single_statement_analysis(df, file_type)
                st.markdown("### ✅ AI Audit Report")
                st.markdown(audit_report)
                st.download_button(
                    label="📄 Export AI Report",
                    data=audit_report.encode("utf-8"),
                    file_name=f"{file_type.replace(' ', '_')}_GAAP_Audit.md",
                    mime="text/markdown"
                )

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
else:
    st.info("👆 Please upload a financial statement to begin.")