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
/* 1. Paksa background utama web menjadi Navy Blue murni */
.stApp { 
    background-color: #000080 !important; 
}

/* 2. Paksa SEMUA teks, paragraph, list item, label, expander header, dan teks di dalam bodi expander menjadi putih */
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span, .stApp label, .navy-title, .stApp li, [data-testid="stExpander"] div, [data-testid="stText"] { 
    color: #FFFFFF !important; 
}

/* 3. Ubah kotak input teks dan drop-down menjadi warna putih dengan teks hitam */
textarea, [data-baseweb="select"], [data-baseweb="select"] div, [data-testid="stHeaderBlock"], [data-baseweb="popover"] {
    background-color: #FFFFFF !important; 
    color: #000000 !important;
}
textarea, [data-baseweb="select"] span { 
    color: #000000 !important; 
    -webkit-text-fill-color: #000000 !important; 
}

/* 4. Paksa semua teks di dalam tombol (Button biasa, Button Upload, & Button Download/Export) menjadi warna hitam */
button, p button, .stButton button, [data-testid="stFileUploaderDropzone"] button, .stDownloadButton button {
    color: #000000 !important; 
    background-color: #FFFFFF !important; 
    font-weight: bold !important;
}
/* Memastikan teks di dalam tombol download / export beneran hitam pekat */
.stDownloadButton button *, .stButton button *, .stButton p, button div { 
    color: #000000 !important; 
    font-weight: bold !important; 
}

/* 5. Teks uploader */
[data-testid="stFileUploaderDropzone"] button *, [data-testid="stFileUploaderDropzone"] div, [data-testid="stFileUploaderDropzone"] span { 
    color: #000000 !important; 
}

/* 6. Efek shadow tebal dan halus untuk kotak logo putih Elabram */
[data-testid="stImage"] img { 
    border-radius: 12px; 
    box-shadow: 0px 10px 25px rgba(0, 0, 0, 0.8); 
    background-color: #FFFFFF; 
    padding: 8px; 
}

.navy-title { 
    font-weight: 800; 
    font-size: 3rem; 
    margin-top: -15px; 
}
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
    
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(62, 39, 35)
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

# --- CACHING AI ---
@st.cache_data(show_spinner=False)
def panggil_ai_gemini(jd, cv):
    prompt = f"""Anda adalah sistem ATS HRD yang ketat. Bandingkan JD dengan CV berikut.
    JOB DESCRIPTION: {jd}
    CV KANDIDAT: {cv}
    Berikan respons MURNI format JSON persis seperti struktur ini: 
    {{"score": "85", "summary": "alasan detail kenapa cocok", "missing_skills": "sebutkan requirement dari JD yang TIDAK ADA atau kurang di CV", "cleaned_cv": "isi cv kandidat rapi"}}
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        md_tick = chr(96) * 3 
        raw_text = response.text.strip().replace(f"{md_tick}json", "").replace(md_tick, "").strip()
        return json.loads(raw_text)
    except Exception as e:
        return {"score": "0", "summary": f"Error AI: {str(e)}", "missing_skills": "Gagal.", "cleaned_cv": "Gagal."}

# --- TAMPILAN INTERFACE ---
st.header("1. Job Description")
selected_template = st.selectbox("Pilih Template Posisi:", list(JD_TEMPLATES.keys()))
jd_default_text = JD_TEMPLATES[selected_template]

jd_file = st.file_uploader("Atau Upload dokumen Job Description (Format PDF)", type=["pdf"])
if jd_file is not None:
    jd_default_text = extract_text_from_pdf(jd_file)

# FIX: Di sini kemarin ada typo 'jd_' menggantung yang bikin error, sekarang sudah bersih total!
jd_text = st.text_area("Detail Job Description & Requirements:", value=jd_default_text, height=150)

st.header("2. Upload CV Kandidat")
uploaded_cvs = st.file_uploader("Pilih file-file CV (Format PDF
