import streamlit as st
import google.generativeai as genai
import PyPDF2
import json
import pandas as pd
from fpdf import FPDF

# --- CONFIG LAYOUT WIDE ---
st.set_page_config(page_title="CV Matcher - Elabram", layout="wide")

# --- SETUP API GEMINI ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- DATABASE TEMPLATE JOB DESCRIPTION ---
JD_TEMPLATES = {
    "Custom / Upload Manual": "",
    "Digital Marketing Specialist": "Mencari Digital Marketing Specialist. Syarat: Pengalaman minimal 2 tahun, menguasai Meta Ads, Google Ads, SEO, SEM, dan Google Analytics.",
    "Software Engineer (Python)": "Syarat Backend Engineer: Minimal pengalaman 3 tahun dengan Python (Django/FastAPI). Menguasai PostgreSQL, Git, Docker.",
    "Sales Executive / Manager": "Dibutuhkan Sales dengan pengalaman B2B minimal 4 tahun. Target-oriented, memiliki skill komunikasi & negosiasi tingkat tinggi."
}

# --- HEADER TAMPILAN UTAMA ---
col1, col2 = st.columns([1, 4])
with col1:
    try:
        st.image("logo elabram.jpg", width=180)
    except:
        try:
            st.image("logo_elabram.jpg", width=180)
        except:
            st.write("Logo Elabram")

with col2:
    st.title("CV Matcher")
    st.subheader("Sistem Cerdas Pengecekan Requirement & Screening CV")

st.divider()

# --- FUNGSI PARSING & GENERATOR PDF ---
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
    pdf.cell(0, 15, f"Kandidat: {candidate_name}", 0, 1, 'L')
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 12, f"Tingkat Kecocokan: {score}%", 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, "Summary Kecocokan:", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 6, summary)
    pdf.ln(3)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, "Requirement yang TIDAK Ditemukan di CV (Missing Skills):", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 6, missing_skills)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 12, "Profil CV Kandidat (Rapi & Detail)", 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, cleaned_cv)
    return pdf.output(dest='S').encode('latin1')

def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted: text += extracted
    return text

# --- CACHING PROSES AI ---
@st.cache_data(show_spinner=False)
def panggil_ai_gemini(jd, cv):
    prompt = f"Bandingkan JD dengan CV berikut. JD: {jd} \\n CV: {cv} \\n Berikan respons MURNI format JSON persis seperti struktur ini: {{\"score\": \"85\", \"summary\": \"alasan cocok\", \"missing_skills\": \"kekurangan di cv\", \"cleaned_cv\": \"isi cv rapi\"}}"
