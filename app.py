import streamlit as st
import json
import requests
import pandas as pd
import time
from datetime import datetime
from student_streamable import FileHandler
from student_streamable import AIService, Config

# ---------------------------------------------------------
# 1. SAYFA KONFİGÜRASYONU
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ollama Student Analyst",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS ile arayüzü makyajlayalım
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold;}
    .reportview-container .main .block-container{ padding-top: 2rem; }
    h1, h2, h3 { color: #4facfe; }
    .metric-card { background-color: #262730; padding: 15px; border-radius: 10px; border-left: 5px solid #4facfe; }
    /* Ders silme butonları için stil */
    .delete-btn { border: 1px solid #ff4b4b; color: #ff4b4b; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 2. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

def check_ollama_server():
    """Ollama sunucusunun çalışıp çalışmadığını kontrol eder."""
    try:
        response = requests.get("http://localhost:11434/")
        return response.status_code == 200
    except:
        return False


def get_ai_response(model, prompt, temperature):
    """Ollama API'sine istek atar (Streaming destekli)."""
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "stream": True
    }

    try:
        with requests.post(url, json=data, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    body = json.loads(line)
                    response_part = body.get("response", "")
                    yield response_part
                    if body.get("done", False):
                        break
    except Exception as e:
        yield f"⚠️ Hata: {str(e)}"


# ---------------------------------------------------------
# 3. SESSION STATE (Hafıza Yönetimi)
# ---------------------------------------------------------

# Öğrenci Verileri
if 'student_data' not in st.session_state:
    st.session_state.student_data = {
        'name': '',
        'class': '',
        'notes': {},
        'behavior': [],
        'observation': '',
        'file_content': ''
    }

# Ders Listesi (Varsayılanlar)
if 'course_list' not in st.session_state:
    st.session_state.course_list = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler"]

if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = ""

# ---------------------------------------------------------
# 4. SIDEBAR (YAN MENÜ)
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://ollama.com/public/ollama.png", width=50)
    st.title("Ayarlar")
    st.markdown("---")

    # Servis örneğini oluştur
    ai_service = AIService()

    # 1. Sunucu Kontrolü ve Model Listesi Alma
    if ai_service.check_connection():
        st.success("🟢 Ollama Bağlı")

        # Dinamik olarak modelleri çek
        available_models = ai_service.get_ollama_models()

        # Eğer liste boş gelirse (bir hata olduysa) varsayılan listeyi göster
        if not available_models:
            available_models = ["llama3.2", "mistral", "gemma:2b"]

        # Model Seçim Kutusu (Dinamik Liste)
        selected_model = st.selectbox(
            "Yapay Zeka Modeli",
            available_models,
            index=0
        )

        # Seçilen modeli servise bildir
        ai_service.configure(provider="Ollama", model=selected_model)

    else:
        st.error("🔴 Bağlantı Yok")
        st.warning("Ollama arka planda çalışmıyor.")
        st.info("Terminali açıp `ollama serve` yazın, sonra sayfayı yenileyin.")

        # Bağlantı yoksa varsayılan bir liste göster ki arayüz çökmesin
        selected_model = st.selectbox("Model (Çevrimdışı)", [Config.DEFAULT_MODEL], disabled=True)

    st.markdown("---")

    # Parametreler
    temperature = st.slider("Yaratıcılık (Temperature)", 0.0, 1.0, 0.7, 0.1)

    # Yenile Butonu (Yeni model indirilirse listeyi güncellemek için)
    if st.button("🔄 Model Listesini Yenile"):
        st.rerun()

    st.markdown("---")
    st.caption("v2.2.0 | Dinamik Model Algılama")

# ---------------------------------------------------------
# 5. ANA EKRAN
# ---------------------------------------------------------

col1, col2 = st.columns([3, 1])
with col1:
    st.title("🎓 Öğrenci Performans Analisti")
    st.markdown("Dinamik müfredat destekli pedagojik analiz sistemi.")
with col2:
    st.markdown(f"**Tarih:** {datetime.now().strftime('%d.%m.%Y')}")

st.markdown("---")

# Sekmeler
tab1, tab2, tab3 = st.tabs(["📝 Veri Girişi", "📊 Grafik & İstatistik", "🤖 AI Analizi"])

# --- TAB 1: VERİ GİRİŞİ ---
with tab1:
    # 1. Bölüm: Kimlik ve Davranış
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Kimlik Bilgileri")
        st.session_state.student_data['name'] = st.text_input("Adı Soyadı", value=st.session_state.student_data['name'],
                                                              placeholder="Örn: Ahmet Yılmaz")
        st.session_state.student_data['class'] = st.text_input("Sınıfı", value=st.session_state.student_data['class'],
                                                               placeholder="Örn: 8/A")

    with c2:
        st.subheader("Davranış Gözlemi")
        behaviors = ["Derse Katılım Yüksek", "Ödevlerini Düzenli Yapar", "Dikkat Dağınıklığı Var",
                     "Arkadaşlarıyla Uyumlu", "Liderlik Özelliği Var", "İçe Kapanık", "Sorumluluk Sahibi"]
        st.session_state.student_data['behavior'] = st.multiselect("Gözlemlenen Davranışlar", behaviors,
                                                                   default=st.session_state.student_data['behavior'])

    st.markdown("---")

    # 2. Bölüm: Ders Yönetimi ve Not Girişi
    st.subheader("📚 Akademik Notlar")

    st.markdown("---")
    st.subheader("📂 Öğrenci Ürün Dosyası (Ödev/Proje)")

    uploaded_file = st.file_uploader("Dosya Yükle (PDF, DOCX, TXT)", type=['pdf', 'docx', 'txt'])

    if uploaded_file is not None:
        with st.spinner("Dosya okunuyor..."):
            extracted_text = FileHandler.extract_text_from_file(uploaded_file)
            st.session_state.student_data['file_content'] = extracted_text
            st.success(f"Dosya başarıyla işlendi! ({len(extracted_text)} karakter)")

            with st.expander("Dosya İçeriğini Görüntüle"):
                st.text(extracted_text)

    # Ders Ekleme / Çıkarma Alanı (Expander içinde gizli)
    with st.expander("⚙️ Ders Listesini Düzenle (Ekle/Çıkar)", expanded=False):
        col_add, col_del = st.columns([2, 1])

        with col_add:
            new_course_name = st.text_input("Yeni Ders Adı", placeholder="Örn: Kodlama, Almanca...")
            if st.button("Ders Ekle"):
                if new_course_name and new_course_name not in st.session_state.course_list:
                    st.session_state.course_list.append(new_course_name)
                    st.success(f"{new_course_name} eklendi!")
                    time.sleep(0.5)
                    st.rerun()
                elif new_course_name in st.session_state.course_list:
                    st.warning("Bu ders zaten listede var.")

        with col_del:
            course_to_remove = st.selectbox("Silinecek Ders", st.session_state.course_list)
            if st.button("Ders Sil", type="primary"):
                if course_to_remove in st.session_state.course_list:
                    st.session_state.course_list.remove(course_to_remove)
                    # Eğer notu girildiyse veriden de silelim
                    if course_to_remove in st.session_state.student_data['notes']:
                        del st.session_state.student_data['notes'][course_to_remove]
                    st.rerun()

    # Dinamik Not Giriş Alanı (Grid Layout)
    if not st.session_state.course_list:
        st.info("Listenizde hiç ders yok. Lütfen yukarıdan ders ekleyiniz.")
    else:
        # Dersleri 4 kolonlu bir ızgarada gösterelim
        cols = st.columns(4)
        temp_notes = {}

        for i, course in enumerate(st.session_state.course_list):
            with cols[i % 4]:
                # Her ders için bir number_input oluşturuyoruz
                # key parametresi unique olmalı, bu yüzden ders adını kullanıyoruz
                val = st.number_input(
                    f"{course}",
                    min_value=0,
                    max_value=100,
                    step=5,
                    key=f"grade_{course}",
                    value=st.session_state.student_data['notes'].get(course, 0)  # Varsa eski değeri getir
                )
                temp_notes[course] = val

        # Güncel notları session state'e kaydet
        st.session_state.student_data['notes'] = temp_notes

    st.markdown("---")
    st.markdown("### 👁️ Öğretmen Özel Notu")
    st.session_state.student_data['observation'] = st.text_area("Eklemek istedikleriniz...", height=100,
                                                                placeholder="Öğrencinin son zamanlardaki durumu hakkında detaylı notlar...")

# --- TAB 2: GRAFİKLER ---
with tab2:
    if not any(st.session_state.student_data['notes'].values()):
        st.warning("Lütfen önce 'Veri Girişi' sekmesinden notları giriniz.")
    else:
        st.subheader(f"{st.session_state.student_data['name'] or 'Öğrenci'} - Akademik Başarı Grafiği")

        # Pandas DataFrame
        df = pd.DataFrame(list(st.session_state.student_data['notes'].items()), columns=["Ders", "Puan"])

        gc1, gc2 = st.columns([2, 1])

        with gc1:
            st.bar_chart(df.set_index("Ders"), color="#4facfe")

        with gc2:
            avg = df["Puan"].mean()
            st.metric(label="Genel Ortalama", value=f"{avg:.1f}")

            # En yüksek ve en düşük dersi bul
            max_course = df.loc[df['Puan'].idxmax()]
            min_course = df.loc[df['Puan'].idxmin()]

            st.info(f"🏆 En İyi: **{max_course['Ders']}** ({max_course['Puan']})")
            st.warning(f"📉 Destek: **{min_course['Ders']}** ({min_course['Puan']})")

            # Ham Veri Tablosu
            with st.expander("Detaylı Not Tablosu"):
                st.dataframe(df, hide_index=True, use_container_width=True)

# --- TAB 3: AI ANALİZİ ---
with tab3:
    st.subheader("🤖 Yapay Zeka Raporu")

    student = st.session_state.student_data

    # Prompt, dinamik ders listesine ve DOSYA İÇERİĞİNE göre otomatik şekillenecek
    prompt_text = f"""
        Sen uzman bir eğitim koçu ve pedagogsun. Aşağıdaki öğrenci verilerini ve öğrencinin hazırladığı ödev/proje dosyasını analiz et.

        ÖĞRENCİ: {student['name']} ({student['class']})

        DERSLER VE NOTLAR:
        {json.dumps(student['notes'], ensure_ascii=False)}

        DAVRANIŞLAR: {', '.join(student['behavior'])}
        ÖĞRETMEN GÖZLEMİ: {student['observation']}

        ---
        ÖĞRENCİ TARAFINDAN YÜKLENEN DOSYA İÇERİĞİ (Ödev/Kompozisyon/Proje):
        "{student.get('file_content', 'Dosya yüklenmedi.')}"
        ---

        GÖREV:
        1. Akademik durumu notlara göre yorumla.
        2. Yüklenen dosya içeriğini (varsa) dil bilgisi, ifade yeteneği ve konuya hakimiyet açısından değerlendir.
        3. Davranışsal analiz yap.
        4. Öğrencinin hem notlarına hem de yüklediği dosyadaki performansına dayanarak 3 adet gelişim tavsiyesi ver.
        5. Raporu samimi ama profesyonel bir dille yaz. Türkçe yanıt ver.
        """

    start_btn = st.button("Analizi Başlat", type="primary")

    if start_btn:
        if not check_ollama_server():
            st.error("Ollama sunucusu çalışmıyor! Lütfen terminalde 'ollama serve' yapın.")
        else:
            if not student['notes']:
                st.warning("Analiz için en az bir ders notu girmelisiniz.")
            else:
                response_container = st.empty()
                full_response = ""

                st.toast("Yapay Zeka raporu hazırlıyor...", icon="🧠")

                for chunk in get_ai_response(selected_model, prompt_text, temperature):
                    full_response += chunk
                    response_container.markdown(full_response + "▌")

                response_container.markdown(full_response)
                st.session_state.analysis_result = full_response

                st.download_button(
                    label="Raporu İndir (TXT)",
                    data=full_response,
                    file_name=f"{student['name']}_analiz.txt",
                    mime="text/plain"
                )