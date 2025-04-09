import os
import json
import tempfile
from fpdf import FPDF
import pandas as pd

GAAP_DIR = "GAAP"
MEMORY_FILE = os.path.join(GAAP_DIR, "verified_issues.json")

def load_verified_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_verified_memory(memory):
    if not os.path.exists(GAAP_DIR):
        os.makedirs(GAAP_DIR)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def clean_df(df):
    df = df.dropna(how='all')
    df = df.loc[~df.apply(lambda r: r.astype(str).str.lower().str.contains("total|header|subtotal").any(), axis=1)]
    df = df.loc[~df.iloc[:, 0].astype(str).str.strip().eq('')]
    return df

def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

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

def calculate_grade(unresolved_count):
    if unresolved_count == 0:
        return "A"
    elif unresolved_count <= 2:
        return "B"
    elif unresolved_count <= 5:
        return "C"
    elif unresolved_count <= 8:
        return "D"
    return "F"
