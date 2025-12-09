import streamlit as st
import json
import requests
import pandas as pd
import time
import threading
import os
from datetime import datetime
from streamlit.runtime import get_instance  # Oturum kontrolü için gerekli

# StudentManager ve diğer sınıfları import ediyoruz
from student_streamable import AIService, Config, FileHandler, StudentManager, Student, Grade
import uuid

# ---------------------------------------------------------
# GLOBAL DEĞİŞKENLER (OTOMATİK KAYIT İÇİN)
# ---------------------------------------------------------
# Bu değişken, Streamlit session'ı dışında veriyi tutmamızı sağlar.
# Böylece thread (bekçi) session kapansa bile veriye erişip kaydedebilir.
if 'GLOBAL_LAST_STUDENT' not in globals():
    globals()['GLOBAL_LAST_STUDENT'] = None

# Veritabanı yöneticisi (Global erişim için burada başlatıyoruz)
manager = StudentManager()


# ---------------------------------------------------------
# 1. BEKÇİ FONKSİYONU (WATCHDOG)
# ---------------------------------------------------------
def browser_watcher():
    """
    Arka planda çalışır. Tarayıcı bağlantısı koparsa (sekme kapanırsa),
    son veriyi kaydeder ve programı kapatır.
    """
    time.sleep(5)  # Programın açılması için süre ver
    print("👀 Tarayıcı izleyicisi aktif...")

    while True:
        try:
            # Aktif oturum sayısını kontrol et
            runtime = get_instance()
            if runtime:
                session_infos = runtime._session_manager._session_info_by_id
                active_sessions = len(session_infos)

                # Eğer bağlı kimse kalmadıysa (Tarayıcı kapandıysa)
                if active_sessions == 0:
                    print("🔻 Tarayıcı kapandı. Otomatik kayıt başlatılıyor...")

                    # Global değişkendeki son veriyi al ve kaydet
                    student_to_save = globals()['GLOBAL_LAST_STUDENT']
                    if student_to_save:
                        try:
                            manager.save_student(student_to_save)
                            print(f"✅ {student_to_save.name} verileri otomatik kaydedildi.")
                        except Exception as e:
                            print(f"❌ Otomatik kayıt hatası: {e}")

                    print("👋 Uygulama kapatılıyor...")
                    os._exit(0)  # Python sürecini tamamen öldür

        except Exception as e:
            # Hata olsa bile döngüyü kırma
            print(f"Watcher Hatası: {e}")

        time.sleep(2)  # 2 saniyede bir kontrol et


# İzleyici Thread'ini başlat (Sadece bir kez)
if 'watcher_thread_started' not in st.session_state:
    t = threading.Thread(target=browser_watcher, daemon=True)
    t.start()
    st.session_state.watcher_thread_started = True

# ---------------------------------------------------------
# 2. SAYFA KONFİGÜRASYONU
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ollama Student Analyst",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold;}
    h1, h2, h3 { color: #4facfe; }
    .metric-card { background-color: #262730; padding: 15px; border-radius: 10px; border-left: 5px solid #4facfe; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 3. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

def sync_global_data():
    """
    Session state'deki veriyi anlık olarak Global değişkene kopyalar.
    Böylece sayfa kapandığında elimizde en güncel veri olur.
    """
    if st.session_state.get('student_data') and st.session_state.get('current_student_id'):
        s_data = st.session_state.student_data

        # Notları Grade objelerine çevir
        grade_objects = [Grade(subject=k, score=v) for k, v in s_data['notes'].items()]

        # Student Nesnesi Oluştur
        current_student = Student(
            id=s_data['id'],
            name=s_data['name'],
            class_name=s_data['class'],
            grades=grade_objects,
            file_content=s_data['file_content']
        )

        # Global değişkene at (Watcher buradan okuyacak)
        globals()['GLOBAL_LAST_STUDENT'] = current_student


def check_ollama_server():
    try:
        response = requests.get("http://localhost:11434/")
        return response.status_code == 200
    except:
        return False


def get_ai_response(model, prompt, temperature):
    url = "http://localhost:11434/api/generate"
    data = {"model": model, "prompt": prompt, "temperature": temperature, "stream": True}
    try:
        with requests.post(url, json=data, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    body = json.loads(line)
                    response_part = body.get("response", "")
                    yield response_part
                    if body.get("done", False): break
    except Exception as e:
        yield f"⚠️ Hata: {str(e)}"


# ---------------------------------------------------------
# 4. SESSION STATE BAŞLATMA
# ---------------------------------------------------------
if 'current_student_id' not in st.session_state:
    st.session_state.current_student_id = None

if 'student_data' not in st.session_state:
    st.session_state.student_data = {
        'id': str(uuid.uuid4()),
        'name': '',
        'class': '',
        'notes': {},
        'behavior': [],
        'observation': '',
        'file_content': ''
    }
if 'course_list' not in st.session_state:
    st.session_state.course_list = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler"]

if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = ""

# ---------------------------------------------------------
# 5. SIDEBAR (YAN MENÜ)
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://ollama.com/public/ollama.png", width=50)

    # --- VERİTABANI SEÇİM ALANI ---
    st.title("📂 Kayıtlı Öğrenciler")
    saved_students = manager.get_all_students()
    student_options = ["➕ Yeni Öğrenci Ekle"] + [f"{s.name} ({s.class_name})" for s in saved_students]
    selected_option = st.selectbox("Öğrenci Seçin", student_options)

    if selected_option == "➕ Yeni Öğrenci Ekle":
        if st.session_state.current_student_id is not None:
            st.session_state.student_data = {
                'id': str(uuid.uuid4()),
                'name': '', 'class': '', 'notes': {},
                'behavior': [], 'observation': '', 'file_content': ''
            }
            st.session_state.current_student_id = None
            globals()['GLOBAL_LAST_STUDENT'] = None  # Global veriyi sıfırla
            st.rerun()
    else:
        selected_name = selected_option.split(" (")[0]
        found_student = next((s for s in saved_students if s.name == selected_name), None)

        if found_student and st.session_state.current_student_id != found_student.id:
            notes_dict = {g.subject: g.score for g in found_student.grades}
            st.session_state.student_data = {
                'id': found_student.id,
                'name': found_student.name,
                'class': found_student.class_name,
                'notes': notes_dict,
                'behavior': [],
                'observation': '',
                'file_content': found_student.file_content
            }
            st.session_state.course_list = list(notes_dict.keys()) if notes_dict else ["Matematik", "Türkçe"]
            st.session_state.current_student_id = found_student.id
            st.rerun()

    st.markdown("---")
    # AI AYARLARI
    ai_service = AIService()
    if ai_service.check_connection():
        st.success("🟢 Ollama Bağlı")
        available_models = ai_service.get_ollama_models() or ["llama3.2"]
        selected_model = st.selectbox("Yapay Zeka Modeli", available_models, index=0)
        ai_service.configure(provider="Ollama", model=selected_model)
    else:
        st.error("🔴 Bağlantı Yok")
        selected_model = st.selectbox("Model", [Config.DEFAULT_MODEL], disabled=True)

    temperature = st.slider("Yaratıcılık", 0.0, 1.0, 0.7, 0.1)
    if st.button("🔄 Modelleri Yenile"): st.rerun()

    st.markdown("---")
    # GÜVENLİ ÇIKIŞ BUTONU
    if st.button("🚪 KAYDET VE ÇIK", type="primary"):
        sync_global_data()
        student_to_save = globals()['GLOBAL_LAST_STUDENT']
        if student_to_save:
            manager.save_student(student_to_save)
        st.success("Veriler kaydedildi, uygulama kapatılıyor...")
        time.sleep(1)
        os._exit(0)

# ---------------------------------------------------------
# 6. ANA EKRAN
# ---------------------------------------------------------
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🎓 Öğrenci Performans Analisti")
with col2:
    st.markdown(f"**Tarih:** {datetime.now().strftime('%d.%m.%Y')}")

st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📝 Veri Girişi", "📊 Grafik & İstatistik", "🤖 AI Analizi"])

# --- TAB 1: VERİ GİRİŞİ ---
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.student_data['name'] = st.text_input("Adı Soyadı", value=st.session_state.student_data['name'])
        st.session_state.student_data['class'] = st.text_input("Sınıfı", value=st.session_state.student_data['class'])
    with c2:
        behaviors = ["Derse Katılım Yüksek", "Ödevlerini Düzenli Yapar", "Dikkat Dağınıklığı Var",
                     "Arkadaşlarıyla Uyumlu", "Liderlik Özelliği Var", "İçe Kapanık"]
        st.session_state.student_data['behavior'] = st.multiselect("Davranışlar", behaviors,
                                                                   default=st.session_state.student_data['behavior'])

    st.subheader("📚 Akademik Notlar")
    # Ders Ekleme/Çıkarma
    with st.expander("⚙️ Ders Listesini Düzenle"):
        ca, cd = st.columns([2, 1])
        with ca:
            new_c = st.text_input("Yeni Ders")
            if st.button("Ekle") and new_c:
                st.session_state.course_list.append(new_c)
                st.rerun()
        with cd:
            del_c = st.selectbox("Silinecek", st.session_state.course_list)
            if st.button("Sil"):
                st.session_state.course_list.remove(del_c)
                if del_c in st.session_state.student_data['notes']:
                    del st.session_state.student_data['notes'][del_c]
                st.rerun()

    # Not Girişleri
    cols = st.columns(4)
    temp_notes = {}
    for i, course in enumerate(st.session_state.course_list):
        with cols[i % 4]:
            val = st.number_input(f"{course}", 0, 100, step=5, key=f"grade_{course}",
                                  value=st.session_state.student_data['notes'].get(course, 0))
            temp_notes[course] = val
    st.session_state.student_data['notes'] = temp_notes

    # Dosya Yükleme
    st.markdown("---")
    st.subheader("📂 Öğrenci Ürün Dosyası")
    uploaded_file = st.file_uploader("Ödev/Proje Yükle (PDF, DOCX, TXT)", type=['pdf', 'docx', 'txt'])
    if uploaded_file is not None:
        with st.spinner("Dosya okunuyor..."):
            extracted_text = FileHandler.extract_text_from_file(uploaded_file)
            st.session_state.student_data['file_content'] = extracted_text
            st.success("Dosya işlendi!")

    # Not Alanı
    st.session_state.student_data['observation'] = st.text_area("Öğretmen Notu",
                                                                value=st.session_state.student_data['observation'])

    # HER İŞLEM SONUNDA GLOBAL VERİYİ GÜNCELLE (AUTO-SYNC)
    # Bu, kullanıcı herhangi bir şeye tıkladığında çalışır.
    sync_global_data()

    # Manuel Kaydet Butonu (Hala orada olsun, güven verir)
    if st.button("💾 ŞİMDİ KAYDET", type="primary"):
        sync_global_data()
        s_to_save = globals()['GLOBAL_LAST_STUDENT']
        if s_to_save and s_to_save.name:
            manager.save_student(s_to_save)
            st.success("Kaydedildi!")
        else:
            st.error("İsim giriniz.")

# --- TAB 2: GRAFİK ---
with tab2:
    if st.session_state.student_data['notes']:
        df = pd.DataFrame(list(st.session_state.student_data['notes'].items()), columns=["Ders", "Puan"])
        st.bar_chart(df.set_index("Ders"))
    else:
        st.info("Not verisi yok.")

# --- TAB 3: AI ---
with tab3:
    st.subheader("🤖 Yapay Zeka Raporu")
    student_dict = st.session_state.student_data
    if st.button("Analizi Başlat", type="primary"):
        prompt_text = f"""
        ÖĞRENCİ: {student_dict['name']} ({student_dict['class']})
        NOTLAR: {json.dumps(student_dict['notes'], ensure_ascii=False)}
        DAVRANIŞLAR: {', '.join(student_dict['behavior'])}
        DOSYA İÇERİĞİ: {student_dict.get('file_content', '')[:1000]}...
        GÖREV: Öğrenciyi akademik, davranışsal ve yüklenen ödeve göre değerlendir. 3 gelişim önerisi ver.
        """
        container = st.empty()
        full_res = ""
        for chunk in get_ai_response(selected_model, prompt_text, temperature):
            full_res += chunk
            container.markdown(full_res + "▌")
        container.markdown(full_res)