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
            
            sukses = False
            # Sistem Antre (Retry) maksimal 3 kali jika kena limit Google
            for attempt in range(3):
                try:
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    
                    # Pembersihan Teks JSON yang kebal error copy-paste
                    md_tick = chr(96) * 3  # Menghasilkan simbol backtick
                    raw_text = response.text.strip()
                    raw_text = raw_text.replace(f"{md_tick}json", "").replace(md_tick, "").strip()
                    
                    res_json = json.loads(raw_text)
                    res_json['name'] = cv_file.name.replace(".pdf", "").replace(".PDF", "")
                    
                    # Simpan ke Memori
                    st.session_state.hasil_analisis.append(res_json)
                    sukses = True
                    break # Berhasil, keluar dari loop antrean
                    
                except Exception as e:
                    error_msg = str(e)
                    # Jika error karena Limit (429) dari versi gratisan Google
                    if "429" in error_msg or "quota" in error_msg.lower():
                        status_text.text(f"⏳ Ups, server Google membatasi versi gratis. Otomatis istirahat 60 detik sebelum lanjut (CV {index+1})...")
                        time.sleep(60) # Tunggu 1 menit lalu coba loop lagi
                    else:
                        st.session_state.hasil_analisis.append({
                            "name": cv_file.name,
                            "score": "0",
                            "summary": f"Error memproses AI: {error_msg}",
                            "cleaned_cv": "Gagal dirapikan."
                        })
                        sukses = True # Error di luar limit, anggap selesai biar lanjut ke CV lain
                        break
            
            if not sukses:
                st.session_state.hasil_analisis.append({
                    "name": cv_file.name,
                    "score": "0",
                    "summary": "Gagal diproses karena limit API Google terlalu sering (Versi Free).",
                    "cleaned_cv": "Gagal dirapikan."
                })

            time.sleep(6) # Jeda kita naikkan jadi 6 detik per CV biar makin aman dari tilang Google
            progress_bar.progress((index + 1) / len(uploaded_cvs))
            
        status_text.text("✅ Analisis Semua CV Selesai!")
        st.session_state.proses_selesai = True

# --- LOGIKA TAMPILAN HASIL (Di luar Loop Proses) ---
if st.session_state.proses_selesai:
    st.markdown("---")
    st.header("📊 Hasil Pengecekan")
    
    for i, res in enumerate(st.session_state.hasil_analisis):
        with st.expander(f"📋 {res['name']} - Kecocokan: {res['score']}%"):
            st.write(f"**Persentase:** {res['score']}%")
            st.write(f"**Alasan:** {res['summary']}")
            
            pdf_data = create_pdf(str(res['name']), str(res['score']), str(res['summary']), str(res['cleaned_cv']))
            
            st.download_button(
                label=f"📥 Download PDF Laporan {res['name']}",
                data=pdf_data,
                file_name=f"Laporan_{res['name']}.pdf",
                mime="application/pdf",
                key=f"dl_btn_{i}"
            )
