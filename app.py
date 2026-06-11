import streamlit as st
import google.generativeai as genai
import PyPDF2
import time
import json
from fpdf import FPDF

# --- SETUP KONFIGURASI GEMINI ---
# Masukkan API Key Gemini gratisan lo di sini
# (Di versi production, ini bisa disimpan di Streamlit Secrets agar aman)
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- KLAS UNTUK GENERATE PDF ---
class CVReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(139, 90, 43) # Earth Tone Brown
        self.cell(0, 10, 'ATS Screening Report - Confidential', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

def create_pdf(candidate_name, score, summary, cleaned_cv):
    pdf = CVReportPDF()
    
    # Halaman 1: Skor & Summary
    pdf.add_page()
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(62, 39, 35) # Dark Brown
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
    
    # Halaman 2: CV Rapi & Detail
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(62, 39, 35)
    pdf.cell(0, 12, "Profil CV Kandidat (Rapi & Detail)", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, cleaned_cv)
    
    return pdf.output(dest='S').encode('latin1')

# --- FUNGSI EKSTRAKSI PDF ---
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# --- TAMPILAN UTAMA WEB ---
st.title("🗂️ EarthTone ATS - CV Matcher")
st.subheader("Cek kecocokan CV kandidat dengan Requirement posisi")
st.write("Aplikasi ini gratis dan bisa memproses hingga maksimal 30 CV sekaligus.")

st.markdown("---")

# Input 1: JD dan Requirement
st.header("1. Ketentuan Lowongan")
jd_text = st.text_area("Paste Job Description & Requirements di sini:", height=200, 
                      placeholder="Contoh: Dicari Social Media Specialist, Ahli CapCut, Pengalaman 2 tahun...")

# Input 2: Upload Banyak CV (Max 30)
st.header("2. Upload CV Kandidat")
uploaded_cvs = st.file_uploader("Pilih file-file CV (Format PDF, Maksimal 30 file)", 
                                type=["pdf"], accept_multiple_files=True)

# Validasi Jumlah CV
if uploaded_cvs and len(uploaded_cvs) > 30:
    st.error(f"🚨 Kebanyakan bos! Lo mengupload {len(uploaded_cvs)} CV. Maksimal cuma bisa 30 CV sekali cek.")
elif uploaded_cvs and jd_text:
    st.success(f"✅ {len(uploaded_cvs)} CV siap dianalisis.")
    
    if st.button("Mulai Proses Analisis 🚀"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Tempat menampung hasil
        results = []
        
        for index, cv_file in enumerate(uploaded_cvs):
            status_text.text(f"Sedang menganalisis ({index+1}/{len(uploaded_cvs)}): {cv_file.name}...")
            
            # 1. Baca teks CV
            cv_text = extract_text_from_pdf(cv_file)
            
            # 2. Setup Prompt AI dengan output wajib JSON agar tidak gagal parsing
            prompt = f"""
            Anda adalah sistem ATS profesional. Bandingkan Job Description (JD) dengan CV berikut.
            
            JOB DESCRIPTION:
            {jd_text}
            
            CV KANDIDAT:
            {cv_text}
            
            Berikan respons dalam format JSON mentah murni (tanpa markdown, tanpa ```json) dengan struktur persis seperti ini:
            {{
                "score": "masukkan angka persentase kecocokan saja tanpa simbol persen, contoh: 85",
                "summary": "jelaskan secara detail dalam bahasa Indonesia mengapa cocok/tidak cocok",
                "cleaned_cv": "susun ulang dan rapikan isi CV kandidat ini menjadi sangat terstruktur, rapi, clear, dan mendetail"
            }}
            """
            
            try:
                # 3. Panggil Gemini AI
                response = model.generate_content(prompt)
                res_json = json.loads(response.text.strip())
                
                # Simpan Hasil
                res_json['name'] = cv_file.name.replace(".pdf", "").replace(".PDF", "")
                results.append(res_json)
                
            except Exception as e:
                # Fallback aman jika AI lemot / error format
                results.append({
                    "name": cv_file.name,
                    "score": "0",
                    "summary": f"Gagal menganalisis secara otomatis. Error: {str(e)}",
                    "cleaned_cv": "Data tidak dapat dirapikan."
                })
            
            # Jeda 4 detik per CV biar tidak terkena limit kuota gratisan Gemini (Rate Limit)
            time.sleep(4)
            progress_bar.progress((index + 1) / len(uploaded_cvs))
            
        status_text.text("✅ Analisis Selesai!")
        
        # --- MENAMPILKAN HASIL DI LAYAR WEB ---
        st.markdown("---")
        st.header("📊 Hasil Pengecekan")
        
        for res in results:
            with st.expander(f"📋 {res['name']} - Kecocokan: {res['score']}%"):
                st.write(f"**Persentase:** {res['score']}%")
                st.write(f"**Alasan:** {res['summary']}")
                
                # Generate PDF secara instant untuk didownload
                pdf_data = create_pdf(res['name'], res['score'], res['summary'], res['cleaned_cv'])
                
                st.download_button(
                    label=f"📥 Download PDF Laporan {res['name']}",
                    data=pdf_data,
                    file_name=f"Laporan_ATS_{res['name']}.pdf",
                    mime="application/pdf"
                )
else:
    st.info("💡 Tolong isi Job Description dan upload minimal 1 CV dulu untuk memulai.")
