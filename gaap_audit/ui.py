import streamlit as st
from gaap_audit.utils import save_verified_memory, load_vendor_memory, save_vendor_memory

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

    verified_memory[file_key] = [v for v, chk in st.session_state[session_key].items() if chk]
    save_verified_memory(verified_memory)

def show_vendor_mismatches(df):
    vendor_memory = load_vendor_memory()
    vendor_col = "Vendor"
    account_col = "Account"

    if vendor_col not in df.columns or account_col not in df.columns:
        st.info("No vendor classification check available (missing 'Vendor' or 'Account' columns).")
        return

    mismatches = []
    for _, row in df[[vendor_col, account_col]].dropna().iterrows():
        vendor = row[vendor_col]
        account = row[account_col]
        if vendor in vendor_memory and account != vendor_memory[vendor]:
            mismatches.append((vendor, account, vendor_memory[vendor]))

    if mismatches:
        st.markdown("### 🚨 Misclassified Vendors (Based on Master Vendor List)")
        for vendor, used, correct in mismatches:
            st.markdown(f"- **{vendor}** was booked to `{used}` but should be `{correct}`")
    else:
        st.markdown("✅ No vendor misclassifications detected.")

def resolve_vendor_accounts(df, vendor_memory):
    st.markdown("### 🧾 Vendor Classification Review")
    vendor_col = "Vendor"
    account_col = "Account"

    if vendor_col not in df.columns or account_col not in df.columns:
        st.warning("Missing 'Vendor' or 'Account' columns.")
        return vendor_memory

    for vendor in df[vendor_col].dropna().unique():
        entries = df[df[vendor_col] == vendor]
        accounts_used = entries[account_col].dropna().unique().tolist()

        if len(accounts_used) > 1:
            st.markdown(f"⚠️ `{vendor}` used multiple accounts: {accounts_used}")
            selected = st.selectbox(
                f"Select correct account for '{vendor}'", options=accounts_used, key=f"correct::{vendor}"
            )
            vendor_memory[vendor] = selected
        elif len(accounts_used) == 1:
            vendor_memory[vendor] = accounts_used[0]

    save_vendor_memory(vendor_memory)
    return vendor_memory

