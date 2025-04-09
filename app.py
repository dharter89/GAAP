import streamlit as st
import pandas as pd

# ---------- Helpers ----------
def parse_numeric(val):
    if isinstance(val, str):
        val = val.replace(')', '').replace('(', '-').replace(',', '')
    try:
        return float(val)
    except:
        return None

def load_excel(file, sheet_name, header_row=3):
    df = pd.read_excel(file, sheet_name=sheet_name)
    df.columns = df.iloc[header_row]
    df = df.iloc[header_row + 1:].reset_index(drop=True)
    df.columns = ["Account", "Balance"]
    df["Account"] = df["Account"].str.strip()
    df["Balance"] = df["Balance"].apply(parse_numeric)
    return df

def check_gaap_issues(bs_df, pl_df, mode="summary"):
    issues = []
    ajes = []

    def explain(entry, note):
        return f"{entry}\n_Explanation: {note}_"

    # Negative cash balance
    cash_accounts = bs_df[bs_df["Account"].str.contains("Checking|Bank|United", case=False, na=False)]
    for _, row in cash_accounts.iterrows():
        if row["Balance"] < 0:
            issues.append(
                explain(
                    f"🔴 Negative cash in `{row['Account']}`",
                    "Per ASC 305-10-45, overdrafts should be reclassified as liabilities unless legally offset."
                )
            )
            ajes.append({
                "Debit": "Overdraft Liability",
                "Credit": row["Account"],
                "Amount": abs(row["Balance"]),
                "Memo": "Reclassify overdraft to liability (ASC 305)"
            })

    # Opening Balance Equity
    obe = bs_df[bs_df["Account"] == "Opening Balance Equity"]
    if not obe.empty and abs(obe.iloc[0]["Balance"]) > 1:
        issues.append(
            explain(
                "🟡 Opening Balance Equity not closed",
                "OBE should be cleared to retained earnings or owner equity before year-end."
            )
        )
        ajes.append({
            "Debit": "Owner Equity",
            "Credit": "Opening Balance Equity",
            "Amount": abs(obe.iloc[0]["Balance"]),
            "Memo": "Clear OBE to permanent equity"
        })

    # Clearing Account
    clearing = bs_df[bs_df["Account"] == "1009 Clearing Account"]
    if not clearing.empty and abs(clearing.iloc[0]["Balance"]) > 1:
        issues.append(
            explain(
                "🟡 Clearing Account not zero",
                "Clearing accounts should be reconciled monthly and zeroed out. Open balance may indicate incomplete transactions."
            )
        )
        ajes.append({
            "Debit": "Suspense Account",
            "Credit": "1009 Clearing Account",
            "Amount": abs(clearing.iloc[0]["Balance"]),
            "Memo": "Investigate and clear clearing account"
        })

    # Missing expected accruals
    accrual_flags = ["Payroll", "Depreciation", "Insurance", "Office"]
    for flag in accrual_flags:
        if not pl_df["Account"].str.contains(flag, case=False, na=False).any():
            issues.append(
                explain(
                    f"⚠️ Missing expected expense: `{flag}`",
                    f"Under the matching principle (ASC 450), {flag.lower()} expenses must be accrued if incurred but unpaid."
                )
            )
            if mode == "detailed":
                ajes.append({
                    "Debit": f"{flag} Expense",
                    "Credit": f"Accrued {flag}",
                    "Amount": 10000,
                    "Memo": f"Estimate accrual for {flag.lower()}"
                })

    return issues, pd.DataFrame(ajes)

# ---------- Streamlit UI ----------
st.set_page_config(page_title="GAAP Compliance Checker", layout="centered")
st.title("📊 GAAP Compliance Checker")
st.caption("Upload your Balance Sheet and P&L Excel files to analyze GAAP compliance.")

# Upload controls
bs_file = st.file_uploader("📥 Upload Balance Sheet (.xlsx)", type="xlsx")
pl_file = st.file_uploader("📥 Upload Profit & Loss (.xlsx)", type="xlsx")

mode = st.radio("View Mode", ["Summary Mode", "Detailed Mode"])

# File handling
if bs_file and pl_file:
    try:
        bs_df = load_excel(bs_file, sheet_name="Balance Sheet")
        pl_df = load_excel(pl_file, sheet_name="Profit and Loss")

        st.success("✅ Files loaded successfully.")

        issues, ajes_df = check_gaap_issues(bs_df, pl_df, mode="detailed" if mode == "Detailed Mode" else "summary")

        st.subheader("⚠️ GAAP Issues Detected")
        if issues:
            for issue in issues:
                st.markdown(f"- {issue}")
        else:
            st.success("No GAAP violations identified.")

        st.subheader("🧾 Suggested Adjusting Journal Entries")
        if not ajes_df.empty:
            st.dataframe(ajes_df)

            csv = ajes_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download AJEs as CSV",
                data=csv,
                file_name="adjusting_journal_entries.csv",
                mime="text/csv"
            )
        else:
            st.info("No AJEs required for this upload.")

    except Exception as e:
        st.error(f"❌ Error loading files: {e}")
else:
    st.info("Upload both Balance Sheet and P&L files to begin.")
