import streamlit as st
import google.generativeai as genai
import PyPDF2
import time
import json
import pandas as pd
from fpdf import FPDF

# --- UBAH LAYOUT JADI WIDE / FULL SCREEN ---
st.set_page_config(page_title="CV Matcher - Elabram", layout="wide")

# --- SETUP KONFIGURASI GEMINI ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- DATABASE TEMPLATE JOB DESCRIPTION ---
JD_TEMPLATES = {
    "Custom / Upload Manual": "",
    "Digital Marketing Specialist": "Mencari Digital Marketing Specialist. Syarat: Pengalaman minimal 2 tahun, menguasai Meta Ads, Google Ads, SEO, SEM, dan Google Analytics. Mampu membuat laporan performa campaign dan memiliki skill copywriting yang baik.",
    "Software Engineer (Python)": "Syarat Backend Engineer: Minimal pengalaman 3 tahun dengan Python (Django/FastAPI). Menguasai PostgreSQL, Git, Docker, dan pembuatan RESTful API. Memahami arsitektur microservices adalah nilai plus.",
    "Sales Executive / Manager": "Dibutuhkan Sales dengan pengalaman B2B minimal 4 tahun. Target-oriented, memiliki skill komunikasi & negosiasi tingkat tinggi, fasih berbahasa Inggris, dan mampu membangun hubungan dengan klien enterprise."
}

# --- INJEKSI CSS UNTUK TEMA NAVY-WHITE-BLACK BALANCED ---
st.markdown("""
<style>
/* 1. Paksa background utama web menjadi Navy Blue murni */
.stApp {
    background-color: #000080 !important;
}

/* 2. Paksa semua teks judul, subheader, dan label section menjadi putih terang */
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span, .stApp label, .navy-title {
    color: #FFFFFF !important;
}

/* 3. Ubah kotak input teks dan drop-down menjadi warna putih dengan teks hitam */
textarea, [data-baseweb="select"], [data-baseweb="select"] div, [data-testid="stHeaderBlock"], [data-baseweb="popover"] {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}
/* Memastikan text di dalam text area/input beneran hitam pekat */
textarea, [data-baseweb="select"] span {
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
}

/* 4. Paksa semua teks di dalam tombol (Button biasa & Button Upload) menjadi warna hitam */
button, p button, .stButton button, [data-testid="stFileUploaderDropzone"] button {
    color: #000000 !important;
    background-color: #FFFFFF !important;
    font-weight: bold !important;
}
/* Spesifik memaksa teks tombol aksi/roket dan teks di dalamnya menjadi hitam pekat */
.stButton button *, .stButton p, button div {
    color: #000000 !important;
    font-weight: bold !important;
}
/* Spesifik memaksa teks tombol upload dan tulisan "200MB per file" di dalam kotak upload menjadi hitam */
[data-testid="stFileUploaderDropzone"] button *, [data-testid="stFileUploaderDropzone"] div, [data-testid="stFileUploaderDropzone"] span {
    color: #000000 !important;
}

/* 5. Efek shadow tebal dan halus untuk kotak logo putih Elabram */
[data-testid="stImage"] img {
    border-radius: 12px;
    box-shadow: 0px 10px 25px rgba(0, 0, 0, 0.8);
    background-color: #FFFFFF;
    padding: 8px;
}

/* Styling khusus judul */
.navy-title {
    font-weight: 800;
    font-size: 3rem;
    margin-top: -15px;
}
</style>
""", unsafe_allow_html=True)

# --- TAMPILAN UTAMA WEB ---
col1, col2 = st.columns([1, 4]) # Kolom kiri buat logo, kanan buat judul

with col1:
    # Trik Anti-Error pemanggilan file lokal logo Elabram
    try:
        st.image("logo elabram.jpg", width=200)
    except:
        try:
            st.image("logo_elabram.jpg", width=200)
        except:
            st.error("File logo belum ter-upload di GitHub.")

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
    
    summary = clean_text(summary)
    missing_skills = clean_text(missing_skills)
    cleaned_cv = clean_text(cleaned_cv)
    candidate_name = clean_text(candidate_name)

    pdf = CVReportPDF()
    
    pdf.add_page()
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(62, 39, 35)
    pdf.cell(0, 15, f"Kandidat: {candidate_name}", 0, 1, 'L')
    
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(139, 90, 43)
    pdf.cell(0, 12, f"Tingkat Kecocokan: {score}%", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(62, 39, 35)
    pdf.cell(0, 8, "Summary Kecocokan:", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, summary)
    pdf.ln(3)

    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(200, 50, 50)
    pdf.cell(0, 8, "Requirement yang TIDAK Ditemukan di CV (Missing Skills):", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, missing_skills)
