import streamlit as st
import json
import requests
import pandas as pd
import time
import threading
import os
import uuid
from datetime import datetime
from streamlit.runtime import get_instance

# Kendi modüllerimiz
from student_streamable import AIService, Config, FileHandler, StudentManager, Student, Grade

# ---------------------------------------------------------
# GLOBAL DEĞİŞKENLER
# ---------------------------------------------------------
if 'GLOBAL_LAST_STUDENT' not in globals():
    globals()['GLOBAL_LAST_STUDENT'] = None

manager = StudentManager()

# Sayfa Ayarları
st.set_page_config(
    page_title="UFT Analiz Sistemi",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------------------------------------------
# 1. WATCHDOG (OTOMATİK KAYITÇI)
# ---------------------------------------------------------
def browser_watcher():
    time.sleep(5)
    while True:
        try:
            runtime = get_instance()
            active_sessions = 1
            if runtime:
                if hasattr(runtime, "_client_mgr"):
                    active_sessions = len(runtime._client_mgr.list_active_sessions())
                elif hasattr(runtime, "_session_mgr"):
                    active_sessions = len(runtime._session_mgr.list_active_sessions())
                elif hasattr(runtime, "_session_manager"):
                    active_sessions = len(runtime._session_manager._session_info_by_id)

                if active_sessions == 0:
                    s_to_save = globals()['GLOBAL_LAST_STUDENT']
                    if s_to_save:
                        try:
                            manager.save_student(s_to_save)
                        except:
                            pass
                    os._exit(0)
        except:
            pass
        time.sleep(2)


# Thread Başlatma
if 'watcher_thread_started' not in st.session_state:
    t = threading.Thread(target=browser_watcher, daemon=True)
    t.start()
    st.session_state.watcher_thread_started = True

# ---------------------------------------------------------
# 2. SESSION STATE (HAFIZA) AYARLARI
# ---------------------------------------------------------
# Form verilerini tutan ana sözlük
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        "id": str(uuid.uuid4()),
        "name": "",
        "class_name": "",
        "notes": {},
        "behavior": [],
        "observation": "",
        "file_content": ""
    }

if 'course_list' not in st.session_state:
    st.session_state.course_list = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler"]


# ---------------------------------------------------------
# 3. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
def reset_form():
    """Formu temizler ve yeni bir ID oluşturur."""
    st.session_state.form_data = {
        "id": str(uuid.uuid4()),
        "name": "",
        "class_name": "",
        "notes": {},
        "behavior": [],
        "observation": "",
        "file_content": ""
    }


def load_student_to_form(student_obj):
    """Veritabanından gelen öğrenciyi forma yükler."""
    notes_dict = {g.subject: g.score for g in student_obj.grades}

    st.session_state.form_data = {
        "id": student_obj.id,
        "name": student_obj.name,
        "class_name": student_obj.class_name,
        "notes": notes_dict,
        "behavior": [],  # Davranış listesi basit tutuluyor
        "observation": "",  # Gözlem alanı (json'da yoksa boş)
        "file_content": student_obj.file_content
    }
    # Ders listesini öğrencinin derslerine göre güncelle
    if notes_dict:
        st.session_state.course_list = list(notes_dict.keys())


def save_current_form():
    """Formdaki veriyi Student nesnesine çevirip kaydeder."""
    data = st.session_state.form_data
    if not data["name"]:
        st.error("❌ Öğrenci adı girmediniz!")
        return False

    # Grade objelerini oluştur
    grade_objs = [Grade(subject=k, score=v) for k, v in data["notes"].items()]

    # Student nesnesi oluştur
    student = Student(
        id=data["id"],
        name=data["name"],
        class_name=data["class_name"],
        grades=grade_objs,
        file_content=data["file_content"]
    )

    # Diske kaydet
    manager.save_student(student)

    # Global değişkene yedekle (Watchdog için)
    globals()['GLOBAL_LAST_STUDENT'] = student

    return True


# ---------------------------------------------------------
# 4. SIDEBAR (YAN MENÜ)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Öğrenci İşlemleri")

    # A) YENİ ÖĞRENCİ BUTONU
    if st.button("➕ YENİ ÖĞRENCİ OLUŞTUR", type="primary", use_container_width=True):
        reset_form()
        st.rerun()

    st.markdown("---")

    # B) KAYITLI ÖĞRENCİ LİSTESİ
    st.subheader("📋 Kayıtlı Liste")

    # Klasördeki dosyaları kontrol et
    saved_students = manager.get_all_students()

    if not saved_students:
        st.info("Henüz kayıtlı öğrenci yok.")
    else:
        # İsim listesi oluştur
        student_names = [f"{s.name} ({s.class_name})" for s in saved_students]

        # Seçim kutusu
        selected_name = st.radio("Düzenlemek için seçin:", student_names, index=None)

        # Eğer bir seçim yapıldıysa ve formdaki ID ile uyuşmuyorsa yükle
        if selected_name:
            # Seçilen isme denk gelen objeyi bul
            target_student = next((s for s in saved_students if f"{s.name} ({s.class_name})" == selected_name), None)

            if target_student and st.session_state.form_data["id"] != target_student.id:
                load_student_to_form(target_student)
                st.rerun()

    st.markdown("---")
    st.caption("UFT v3.0 | Auto-Save Aktif")

# ---------------------------------------------------------
# 5. ANA EKRAN (FORM)
# ---------------------------------------------------------
st.title("🎓 Öğrenci Performans Sistemi")

# --- KAYDET BUTONU (EN ÜSTTE VE BELİRGİN) ---
col_save, col_info = st.columns([1, 3])
with col_save:
    if st.button("💾 VERİLERİ KAYDET", type="primary", use_container_width=True):
        if save_current_form():
            st.toast(f"✅ {st.session_state.form_data['name']} başarıyla kaydedildi!", icon="🎉")
            time.sleep(1)  # Kullanıcı mesajı görsün
            st.rerun()  # Listeyi güncellemek için yenile

with col_info:
    if st.session_state.form_data["name"]:
        st.info(f"Şu an düzenleniyor: **{st.session_state.form_data['name']}**")
    else:
        st.warning("Yeni Öğrenci Girişi Yapılıyor...")

st.markdown("---")

# SEKME YAPISI
tab1, tab2, tab3 = st.tabs(["📝 KİMLİK & NOTLAR", "📄 ÖDEV DOSYASI", "🤖 YAPAY ZEKA"])

# TAB 1: TEMEL BİLGİLER
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.form_data["name"] = st.text_input("Öğrenci Adı Soyadı",
                                                           value=st.session_state.form_data["name"])
    with col2:
        st.session_state.form_data["class_name"] = st.text_input("Sınıfı / Şubesi",
                                                                 value=st.session_state.form_data["class_name"])

    st.subheader("📚 Ders Notları")

    # Ders Ekleme
    with st.expander("Ders Listesini Düzenle"):
        c_add, c_del = st.columns(2)
        new_c = c_add.text_input("Ders Ekle")
        if c_add.button("Ekle"):
            if new_c and new_c not in st.session_state.course_list:
                st.session_state.course_list.append(new_c)
                st.rerun()

        del_c = c_del.selectbox("Silinecek Ders", st.session_state.course_list)
        if c_del.button("Dersi Sil"):
            if del_c in st.session_state.course_list:
                st.session_state.course_list.remove(del_c)
                # Varsa notunu da sil
                st.session_state.form_data["notes"].pop(del_c, None)
                st.rerun()

    # Not Giriş Kutuları
    cols = st.columns(3)
    for i, course in enumerate(st.session_state.course_list):
        with cols[i % 3]:
            # Mevcut notu çek
            current_score = st.session_state.form_data["notes"].get(course, 0)
            # Input oluştur
            new_score = st.number_input(f"{course}", min_value=0, max_value=100, value=current_score,
                                        key=f"grade_{course}")
            # Veriyi güncelle
            st.session_state.form_data["notes"][course] = new_score

    # Davranışlar
    st.subheader("🧠 Davranış Gözlemi")
    opts = ["Derse Katılım Yüksek", "Ödev Eksikliği Var", "Arkadaşlarıyla Uyumlu", "Dikkat Dağınıklığı",
            "Sorumluluk Sahibi"]
    st.session_state.form_data["behavior"] = st.multiselect("Gözlemlenen Davranışlar", opts,
                                                            default=st.session_state.form_data["behavior"])

# TAB 2: DOSYA YÜKLEME
with tab2:
    st.subheader("📂 Öğrenci Ödevi / Projesi Yükle")
    st.caption("PDF, Word veya TXT formatındaki dosyalar yapay zeka tarafından okunur.")

    uploaded = st.file_uploader("Dosya Seçiniz", type=['pdf', 'docx', 'txt'])

    if uploaded:
        with st.spinner("Dosya okunuyor..."):
            text = FileHandler.extract_text_from_file(uploaded)
            st.session_state.form_data["file_content"] = text
            st.success("✅ Dosya içeriği sisteme aktarıldı.")

    if st.session_state.form_data["file_content"]:
        with st.expander("Mevcut Dosya İçeriğini Gör"):
            st.text_area("İçerik", value=st.session_state.form_data["file_content"], height=200, disabled=True)

# TAB 3: AI ANALİZ
with tab3:
    st.subheader("🤖 Ollama Analizi")

    ai_service = AIService()
    if ai_service.check_connection():
        st.success(f"Bağlı: {Config.OLLAMA_URL}")
        models = ai_service.get_ollama_models()
        selected_model = st.selectbox("Model Seçin", models or ["llama3.2"])
        ai_service.configure("Ollama", selected_model)

        if st.button("Analizi Başlat", type="primary"):
            if not st.session_state.form_data["name"]:
                st.error("Önce öğrenci adını giriniz.")
            else:
                data = st.session_state.form_data
                prompt = f"""
                ÖĞRENCİ: {data['name']} ({data['class_name']})
                NOTLAR: {json.dumps(data['notes'], ensure_ascii=False)}
                DAVRANIŞLAR: {', '.join(data['behavior'])}
                YÜKLENEN ÖDEV İÇERİĞİ:
                {data['file_content'][:2000]}

                GÖREV: Bu öğrenciyi akademik, davranışsal ve ödev performansına göre analiz et. 
                Türkçe, samimi ve yapıcı bir dille 3 maddelik gelişim önerisi yaz.
                """

                box = st.empty()
                full_text = ""
                for chunk in ai_service.generate_stream(prompt, "Sen uzman bir eğitim koçusun."):
                    full_text += chunk
                    box.markdown(full_text + "▌")
                box.markdown(full_text)

    else:
        st.error("⚠️ Ollama bulunamadı. Lütfen terminalden 'ollama serve' komutunu çalıştırın.")

# Sayfa her etkileşimde global veriyi günceller (Watchdog için)
# Ancak kaydetme işlemi sadece butona basınca diske yazar.
# Bu fonksiyon sadece "anlık kapanma" durumları için veri tutar.
if st.session_state.form_data["name"]:
    save_current_form()  # Session'daki veriyi globale at (Diske yazmaz, sadece memory)