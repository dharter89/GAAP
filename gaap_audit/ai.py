from gaap_audit.utils import clean_df, truncate_df

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
