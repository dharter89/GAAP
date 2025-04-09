import streamlit as st
import pandas as pd
import openai

# Securely load API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

def load_excel(file, sheet_name):
    result = pd.read_excel(file, sheet_name=sheet_name)
    if isinstance(result, dict):
        result = result[sheet_name]
    return result


def run_gaap_ai_advisor(bs_df, pl_df, cf_df, gl_df):
    prompt = f"""
You are an Ivy League-trained CPA and GAAP compliance expert.

Analyze the following financial data and create a full audit-style report with:
1. Executive Summary
2. Section-by-section GAAP findings
3. Adjusting Journal Entries (AJEs)
4. GAAP references (ASC codes)
5. Markdown structure

---

Balance Sheet:
{bs_df.to_string(index=False)}

Profit and Loss:
{pl_df.to_string(index=False)}

Cash Flow Statement:
{cf_df.to_string(index=False)}

General Ledger:
{gl_df.to_string(index=False)}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1800
    )
    return response.choices[0].message["content"]

# ------------------- Streamlit UI -------------------
st.set_page_config(page_title="GAAP Compliance Checker AI", layout="wide")
st.title("📘 GAAP Compliance Checker")
st.caption("Upload Balance Sheet, P&L, Cash Flow, and General Ledger for full GAAP analysis.")

bs_file = st.file_uploader("📊 Upload Balance Sheet (.xlsx)", type="xlsx")
pl_file = st.file_uploader("📈 Upload Profit & Loss (.xlsx)", type="xlsx")
cf_file = st.file_uploader("💧 Upload Cash Flow Statement (.xlsx)", type="xlsx")
gl_file = st.file_uploader("📜 Upload General Ledger (.xlsx)", type="xlsx")

if all([bs_file, pl_file, cf_file, gl_file]):
    try:
        bs_df = load_excel(bs_file, sheet_name="Balance Sheet")
        pl_df = load_excel(pl_file, sheet_name="Profit and Loss")
        cf_df = load_excel(cf_file, sheet_name="Statement of Cash Flows")
        gl_df = load_excel(gl_file, sheet_name="General Ledger")


        st.success("✅ All financial statements uploaded successfully.")

        # Preview uploaded data
        with st.expander("📂 Preview Uploaded Financial Statements"):
            tabs = st.tabs(["Balance Sheet", "Profit & Loss", "Cash Flow", "General Ledger"])
            with tabs[0]:
                st.write("### 📊 Balance Sheet")
                st.dataframe(bs_df)
            with tabs[1]:
                st.write("### 📈 Profit & Loss")
                st.dataframe(pl_df)
            with tabs[2]:
                st.write("### 💧 Cash Flow Statement")
                st.dataframe(cf_df)
            with tabs[3]:
                st.write("### 📜 General Ledger")
                st.dataframe(gl_df)

        if st.button("🔍 Run AI GAAP Audit Analysis"):
            with st.spinner("Analyzing with GPT-4..."):
                report_text = run_gaap_ai_advisor(bs_df, pl_df, cf_df, gl_df)
                st.markdown("### ✅ AI GAAP Audit Report")
                st.markdown(report_text)

                # Export full report
                st.download_button(
                    label="📄 Export Full AI Report",
                    data=report_text.encode('utf-8'),
                    file_name="GAAP_AI_Audit_Report.md",
                    mime="text/markdown"
                )

    except Exception as e:
        st.error(f"❌ Error processing files: {e}")
else:
    st.info("👆 Upload all 4 required Excel files to begin.")