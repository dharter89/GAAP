import pandas as pd
from gaap_audit.ai import run_gaap_audit

# Dummy DataFrame
df = pd.DataFrame([
    {"Account": "1000", "Description": "Cash",     "Amount": 5000},
    {"Account": "4000", "Description": "Revenue",  "Amount": 7000},
    {"Account": "5000", "Description": "Expenses", "Amount": -2000},
])

full_text, violations = run_gaap_audit(df, file_type="dummy")

print("=== LLM Response ===")
print(full_text)
print("\n=== Parsed Violations ===")
for v in violations:
    print("-", v)
