import streamlit as st
import google.generativeai as genai
import PyPDF2
import json
import pandas as pd
from fpdf import FPDF

# --- CONFIG LAYOUT ---
st.set_page_config(page_title="CV Matcher - Elabram", layout="wide")

# --- SETUP API GEMINI ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- TEMPLATE JD ---
JD_TEMPLATES = {
    "Custom / Upload Manual": "",
    "Digital Marketing Specialist": "Mencari Digital Marketing Specialist. Syarat: Pengalaman minimal 2 tahun, menguasai Meta Ads, Google Ads, SEO, SEM, dan Google Analytics.",
    "Software Engineer (Python)": "Syarat Backend Engineer: Minimal pengalaman 3 tahun dengan Python (Django/FastAPI). Menguasai PostgreSQL, Git, Docker.",
    "Sales Executive / Manager": "Dibutuhkan Sales dengan pengalaman B2B minimal 4 tahun. Target-oriented, memiliki skill komunikasi & negosiasi tingkat tinggi."
}

# --- INJEKSI CSS ---
st.markdown("""
<style>
.stApp { background-color: #000080 !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span, .stApp label, .navy-title, .stApp li, [data-testid="stExpander"] div, [data-testid="stText"] { 
    color: #FFFFFF !important; 
}
textarea, [data-baseweb="select"], [data-baseweb="select"] div, [data-testid="stHeaderBlock"], [data-baseweb="popover"] {
    background-color: #FFFFFF !important; color: #000000 !important;
}
textarea, [data-baseweb="select"] span { color: #000000 !important; -webkit-text-fill-color: #000000 !important; }
button, p button, .stButton button, [data-testid="stFileUploaderDropzone"] button, .stDownloadButton button {
    color: #000000 !important; background-color: #FFFFFF !important; font-weight: bold !important;
}
.stDownloadButton button *, .stButton button *, .stButton p, button div { color: #000000 !important; font-weight: bold !important; }
[data-testid="stFileUploaderDropzone"] button *, [data-testid="stFileUploaderDropzone"] div, [data-testid="stFileUploaderDropzone"] span { color: #000000 !important; }
[data-testid="stImage"] img { border-radius: 12px; box-shadow: 0px 10px 25px rgba(0, 0, 0, 0.8); background-color: #FFFFFF; padding: 8px; }
.navy-title { font-weight: 800; font-size: 3rem; margin-top: -15px; }
</style>
""", unsafe_allow_html=True)

# --- HEADER APP ---
col1, col2 = st.columns([1, 4])
with col1:
    try: st.image("logo elabram.jpg", width=200)
    except:
        try: st.image("logo_elabram.jpg", width=200)
        except: st.error("Logo tidak ditemukan.")
with col2:
    st.markdown("<h1 class='navy-title'>CV Matcher</h1>", unsafe_allow_html=True)
    st.subheader("Sistem Cerdas Pengecekan Requirement & Screening CV")

st.divider()

# --- KLAS UNTUK GENERATE PDF ---
class CVReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(139, 90, 43)
        self.cell(0, 10, 'ATS Screening Report - Confidential', 0, 1, 'R')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

def create_pdf(candidate_name, score, summary, missing_skills, cleaned_cv):
    def clean_text(text):
        if not isinstance(text, str): return ""
        reps = {'•': '-', '–': '-', '—': '-', '‘': "'", '’': "'", '“': '"', '”': '"', '\n': '\n'}
        for k, v in reps.items(): text = text.replace(k, v)
        return text.encode('latin-1', 'ignore').decode('latin-1')
    
    summary, missing_skills, cleaned_cv, candidate_name = clean_text(summary), clean_text(missing_skills), clean_text(cleaned_cv), clean_text(candidate_name)
    pdf = CVReportPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(62, 39, 35)
    pdf.cell(0, 15, f"Kandidat: {candidate_name}", 0, 1, 'L')
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(139, 90, 43)
