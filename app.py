import streamlit as st
import google.generativeai as genai
import PyPDF2
import time
import json
import pandas as pd
from fpdf import FPDF

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
    
    # Halaman 1: Summary & Kelemahan
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
    pdf.set_text_color(200, 50, 50) # Warna kemerahan untuk bagian missing skills
    pdf.cell(0, 8, "Requirement yang TIDAK Ditemukan di CV (Missing Skills):", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, missing_skills)
    
    # Halaman 2: Cleaned CV
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

# --- TAMPILAN UTAMA WEB ---
col1, col2 = st.columns([1, 8]) # Membagi layar jadi 2 kolom (kiri kecil, kanan lebar)

with col1:
    # Sementara gue pakai logo inisial "E" yang warnanya udah dicocokin sama tema Navy-Gold.
    # Kalau lo mau pakai logo asli Elabram, tinggal ganti URL di bawah ini sama link gambar logonya.
    # Atau upload file logo aslinya ke GitHub lo, lalu ganti jadi: st.image("logo_elabram.png", width=70)
    st.image("https://ui-avatars.com/api/?name=Elabram&background=FBBF24&color=0F172A&size=128&bold=true", width=70)

with col2:
    # CSS ini biar posisi judulnya sejajar rapi dengan tengah-tengah logo
    st.markdown("<h1 style='margin-top: -15px;'>CV Matcher</h1>", unsafe_allow_html=True)

st.subheader("Sistem Cerdas Pengecekan Requirement & Screening CV")
st.markdown("---")

# 1. JOB DESCRIPTION SECTION
st.header("1. Job Description")

# Fitur Template
selected_template = st.selectbox("Pilih Template Posisi (Atau pilih Custom untuk isi sendiri):", list(JD_TEMPLATES.keys()))
jd_default_text = JD_TEMPLATES[selected_template]

# Fitur Upload JD
jd_file = st.file_uploader("Atau Upload dokumen Job Description (Opsional, Format PDF)", type=["pdf"])
if jd_file is not None:
    jd_default_text = extract_text_from_pdf(jd_file)
    st.success("Teks Job Description berhasil diekstrak! Silakan cek/edit di kotak bawah.")

# Kotak Teks Akhir
jd_text = st.text_area("Detail Job Description & Requirements:", value=jd_default_text, height=150, 
                       placeholder="Ketik manual atau upload dokumen PDF di atas...")

# 2. CV UPLOAD SECTION
st.header("2. Upload CV Kandidat")
uploaded_cvs = st.file_uploader("Pilih file-file CV (Format PDF, Maksimal 30 file)", type=["pdf"], accept_multiple_files=True)

if 'proses_selesai' not in st.session_state:
    st.session_state.proses_selesai = False
    st.session_state.hasil_analisis = []

# --- LOGIKA PROSES AI ---
if uploaded_cvs and len(uploaded_cvs) > 30:
    st.error("🚨 Maksimal 30 CV sekali cek.")
elif uploaded_cvs and jd_text:
    if st.button("Mulai Pengecekan 🚀"):
        st.session_state.hasil_analisis = [] 
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, cv_file in enumerate(uploaded_cvs):
            status_text.text(f"Menganalisis ({index+1}/{len(uploaded_cvs)}): {cv_file.name}...")
            
            cv_text = extract_text_from_pdf(cv_file)
            # PROMPT DIUPDATE dengan tambahan "missing_skills"
            prompt = f"""Anda adalah sistem ATS HRD yang ketat. Bandingkan JD dengan CV berikut.
            JOB DESCRIPTION: {jd_text}
            CV KANDIDAT: {cv_text}
            Berikan respons MURNI format JSON persis seperti struktur ini: 
            {{"score": "85", "summary": "alasan detail kenapa cocok", "missing_skills": "sebutkan requirement dari JD yang TIDAK ADA atau kurang di CV kandidat ini", "cleaned_cv": "isi cv kandidat yang disusun ulang sangat rapi dan lengkap"}}
            """
            
            sukses = False
            for attempt in range(5):
                try:
                    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                    md_tick = chr(96) * 3 
                    raw_text = response.text.strip()
                    raw_text = raw_text.replace(f"{md_tick}json", "").replace(md_tick, "").strip()
                    
                    res_json = json.loads(raw_text)
                    res_json['name'] = cv_file.name.replace(".pdf", "").replace(".PDF", "")
                    
                    st.session_state.hasil_analisis.append(res_json)
                    sukses = True
                    break 
                    
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "quota" in error_msg.lower():
                        status_text.text(f"⏳ Jeda santai... Google minta istirahat 60 detik (Percobaan {attempt+1}/5)...")
                        time.sleep(60) 
                    else:
                        st.session_state.hasil_analisis.append({
                            "name": cv_file.name,
                            "score": "0",
                            "summary": f"Error memproses AI: {error_msg}",
                            "missing_skills": "Tidak dapat dianalisa.",
                            "cleaned_cv": "Gagal dirapikan."
                        })
                        sukses = True 
                        break
            
            if not sukses:
                st.session_state.hasil_analisis.append({
                    "name": cv_file.name,
                    "score": "0",
                    "summary": "Gagal diproses karena limit harian API Google (Versi Free) habis.",
                    "missing_skills": "Tidak dapat dianalisa.",
                    "cleaned_cv": "Gagal dirapikan."
                })

            time.sleep(15) 
            progress_bar.progress((index + 1) / len(uploaded_cvs))
            
        status_text.text("✅ Proses Semua CV Selesai!")
        st.session_state.proses_selesai = True

# --- TAMPILAN HASIL ---
if st.session_state.proses_selesai:
    st.markdown("---")
    st.header("📊 Rekap Hasil Matcher")
    
    # Auto-Sorting dari Skor Tertinggi
    st.session_state.hasil_analisis.sort(key=lambda x: int(x.get('score', 0)) if str(x.get('score', '0')).isdigit() else 0, reverse=True)
    
    # FITUR 1: DOWNLOAD EXCEL / CSV REKAPAN
    df_rekap = pd.DataFrame([{
        "Nama Kandidat": res.get('name', ''),
        "Skor Kecocokan (%)": res.get('score', '0'),
        "Summary Kecocokan": res.get('summary', ''),
        "Missing Skills (Kekurangan)": res.get('missing_skills', 'Tidak ada data')
    } for res in st.session_state.hasil_analisis])
    
    csv_data = df_rekap.to_csv(index=False).encode('utf-8')
    
    st.success("Tabel rekapitulasi semua kandidat siap didownload!")
    st.download_button(
        label="📊 Download Tabel Rekap (CSV/Excel)",
        data=csv_data,
        file_name="Rekap_ATS_CV_Matcher.csv",
        mime="text/csv",
    )
    
    st.markdown("### Detail Tiap Kandidat")
    
    for i, res in enumerate(st.session_state.hasil_analisis):
        with st.expander(f"📋 {res['name']} - Skor: {res['score']}%"):
            st.write(f"**Persentase Kecocokan:** {res['score']}%")
            st.write(f"**Ringkasan AI:** {res['summary']}")
            st.write(f"**Kekurangan (Missing Skills):** {res.get('missing_skills', 'Aman / Tidak terdeteksi')}")
            
            pdf_data = create_pdf(
                str(res.get('name', '')), 
                str(res.get('score', '0')), 
                str(res.get('summary', '')), 
                str(res.get('missing_skills', '-')),
                str(res.get('cleaned_cv', ''))
            )
            
            st.download_button(
                label=f"📥 Download Report PDF {res['name']}",
                data=pdf_data,
                file_name=f"Report_CV_Matcher_{res['name']}.pdf",
                mime="application/pdf",
                key=f"dl_btn_{i}"
            )
