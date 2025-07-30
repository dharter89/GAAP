# gaap_audit/ai.py

import os
import re
import json
import tempfile

import streamlit as st
from google import genai
from gaap_audit.utils import clean_df, truncate_df


def run_gaap_audit(df, file_type):
    """
    Preprocesses the DataFrame, builds the auditing prompt, and sends it to Gemini 2.5 Pro.
    Returns the raw JSON/text, a compliance grade, and a list of violation dicts.
    """

    # ——————————————————————————————————————
    # 0) Load GCP creds from Streamlit secrets (cloud) or use local path (dev)
    if "GCP_CREDENTIALS" in st.secrets:
        creds = st.secrets["GCP_CREDENTIALS"]
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tf.write(json.dumps(creds).encode("utf-8"))
        tf.flush()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tf.name
    else:
        # fallback for local development—your existing service‐account JSON
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
            r"C:\Users\DavidHarter\OneDrive - Valiant Partners LLC"
            r"\VP Drive\7. Drive Templates\Python\GAAP\Credentials\Gemini"
            r"\gemini-demo-467504-ca7268cb4985.json"
        )
    # ——————————————————————————————————————

    # 1) Initialize the Vertex AI client
    client = genai.Client(
        vertexai=True,
        project="gemini-demo-467504",
        location="us-central1",
    )

    # 2) Clean and truncate the DataFrame, then convert to Markdown
    df_cleaned = clean_df(df)
    df_small   = truncate_df(df_cleaned)
    ledger_md  = df_small.to_markdown(index=False)

    # 3) Build a prompt that forces *all* violations to be listed + counted
    prompt = f"""
You are the world’s most meticulous CPA and GAAP auditor.

Below is a sample general ledger in Markdown table form:

{ledger_md}

--  
**Audit Instructions**  
1. Review **every** row for classification, disclosure, or GAAP deviations.  
2. For **each** violation you find, begin the line with **Violation:** and give a one-sentence summary.  
3. **Do not** omit or truncate any—list **all** violations, even if there are many.  
4. When you’re done, add a final line that reads exactly:  
   **Total violations found: X**  
   where **X** is the count of the violations you just listed.

Respond in JSON with this schema:

```json
{{
  "compliance_grade": "A|B|C|D|F",
  "total_violations": X,
  "violations": [
    {{
      "summary": "...",
      "location": "...",
      "suggested_correction": "..."
    }},
    …
  ]
}}
```"""

    # 4) Send to Gemini
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt
    )

    # 5) Parse the JSON (with robust stripping of fences)
    full_text = response.text
    raw = full_text

    # Strip any leading/trailing triple-backtick fences (``` or ```json)
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s*```$', '', raw)

    # Extract the first JSON object block
    match = re.search(r'(\{.*\})', raw, flags=re.DOTALL)
    if match:
        raw = match.group(1)

    try:
        payload    = json.loads(raw)
        grade      = payload.get("compliance_grade")
        violations = payload.get("violations", [])
    except json.JSONDecodeError:
        grade      = None
        violations = []

    # 6) Return the raw output, the extracted grade, and the violation list
    return full_text, grade, violations
