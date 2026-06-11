import streamlit as st
import google.generativeai as genai
import PyPDF2
import time
import json
from fpdf import FPDF

# --- SETUP KONFIGURASI GEMINI ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

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

def create_pdf(candidate_name, score, summary, cleaned_cv):
    # Pembersih Karakter agar tidak Error saat cetak PDF
    def clean_text(text):
        if not isinstance(text, str): return ""
        reps = {'•': '-', '–': '-', '—': '-', '‘': "'", '’': "'", '“': '"', '”': '"', '\n': '\n'}
        for k, v in reps.items(): text = text.replace(k, v)
        return text.encode('latin-1', 'ignore').decode('latin-1')
    
    summary = clean_text(summary)
    cleaned_cv = clean_text(cleaned_cv)
    candidate_name = clean_text(candidate_name)

    pdf = CVReportPDF()
    
    # Halaman 1
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
    pdf.cell(0, 10, "Summary Penjelasan Kecocokan:", 0, 1, 'L')
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, summary)
    
    # Halaman 2
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(62, 39, 35)
    pdf.cell(0, 12, "Profil CV Kandidat (Rapi & Detail)", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, cleaned_cv)
    
    return pdf.output(dest='S').encode('latin1')

# --- FUNGSI BACA PDF ---
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# --- TAMPILAN UTAMA WEB ---
st.title("🗂️ EarthTone ATS - CV Matcher")
st.subheader("Cek kecocokan CV kandidat dengan Requirement posisi")
st.markdown("---")

st.header("1. Ketentuan Lowongan")
jd_text = st.text_area("Paste Job Description & Requirements di sini:", height=200)

st.header("2. Upload CV Kandidat")
uploaded_cvs = st.file_uploader("Pilih file-file CV (Format PDF, Maksimal 30 file)", type=["pdf"], accept_multiple_files=True)

# Memori Penyimpanan agar Data tidak hilang saat Refresh/Download
if 'proses_selesai' not in st.session_state:
    st.session_state.proses_selesai = False
    st.session_state.hasil_analisis = []

# --- LOGIKA PROSES AI ---
if uploaded_cvs and len(uploaded_cvs) > 30:
    st.error("🚨 Maksimal 30 CV sekali cek.")
elif uploaded_cvs and jd_text:
    if st.button("Mulai Proses Analisis 🚀"):
        st.session_state.hasil_analisis = [] # Kosongkan memori lama
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, cv_file in enumerate(uploaded_cvs):
            status_text.text(f"Sedang menganalisis ({index+1}/{len(uploaded_cvs)}): {cv_file.name}...")
            
            cv_text = extract_text_from_pdf(cv_file)
            prompt = f"""Anda adalah sistem ATS. Bandingkan JD dengan CV berikut.
            JOB DESCRIPTION: {jd_text}
            CV KANDIDAT: {cv_text}
            Berikan respons MURNI format JSON seperti ini: {{"score": "85", "summary": "alasan detail", "cleaned_cv": "isi cv rapi"}}
            """
            
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # Pembersihan Teks JSON
                raw_text = response.text.strip()
                if raw_text.startswith("
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1
http://googleusercontent.com/immersive_entry_chip/2

4. Klik tombol hijau **Commit changes...** dan simpan.

Tunggu *loading* 10 detik di web lo. Sekarang kodenya udah rapi struktur posisinya. Lo bisa langsung sikat masukin banyak CV sekaligus. Begitu semuanya selesai dibaca, hasilnya bakal berderet ke bawah dan bisa lo *download* satu-satu tanpa *error* dan tanpa hilang. 

Sekali lagi *sorry* banget bikin lo bolak-balik bos! Kalo udah jalan lancar, sikat buat ngerjain kerjaan HRD lo!
