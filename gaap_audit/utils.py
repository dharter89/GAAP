import os
import json
import tempfile
from fpdf import FPDF
import pandas as pd

# === File Paths ===
GAAP_DIR = "GAAP"
MEMORY_FILE = os.path.join(GAAP_DIR, "verified_issues.json")
VENDOR_FILE = os.path.join(GAAP_DIR, "vendor_accounts.json")

# === Verified Issues Memory ===
def load_verified_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_verified_memory(memory):
    os.makedirs(GAAP_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

# === Vendor Memory ===
def load_vendor_memory():
    if os.path.exists(VENDOR_FILE):
        with open(VENDOR_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_vendor_memory(memory):
    os.makedirs(GAAP_DIR, exist_ok=True)
    with open(VENDOR_FILE, "w") as f:
        json.dump(memory, f, indent=2)

# === Data Cleaning ===
def clean_df(df):
    df = df.dropna(how='all')
    df = df.loc[~df.apply(lambda r: r.astype(str).str.lower().str.contains("total|header|subtotal").any(), axis=1)]
    df = df.loc[~df.iloc[:, 0].astype(str).str.strip().eq('')]
    return df

def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

# === PDF Report ===
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

# === GAAP Grade Logic ===
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
import os
import json
import tempfile
from fpdf import FPDF
import pandas as pd

# === File Paths ===
GAAP_DIR = "GAAP"
MEMORY_FILE = os.path.join(GAAP_DIR, "verified_issues.json")
VENDOR_FILE = os.path.join(GAAP_DIR, "vendor_accounts.json")

# === Verified Issues Memory ===
def load_verified_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_verified_memory(memory):
    os.makedirs(GAAP_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

# === Vendor Memory ===
def load_vendor_memory():
    if os.path.exists(VENDOR_FILE):
        with open(VENDOR_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_vendor_memory(memory):
    os.makedirs(GAAP_DIR, exist_ok=True)
    with open(VENDOR_FILE, "w") as f:
        json.dump(memory, f, indent=2)

# === Data Cleaning ===
def clean_df(df):
    df = df.dropna(how='all')
    df = df.loc[~df.apply(lambda r: r.astype(str).str.lower().str.contains("total|header|subtotal").any(), axis=1)]
    df = df.loc[~df.iloc[:, 0].astype(str).str.strip().eq('')]
    return df

def truncate_df(df, max_rows=50):
    return df.head(max_rows) if df.shape[0] > max_rows else df

# === PDF Report ===
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

# === GAAP Grade Logic ===
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
