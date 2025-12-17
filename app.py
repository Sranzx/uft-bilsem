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
# 1. WATCHDOG (OTOMATİK KAYITÇI)
# ---------------------------------------------------------
def browser_watcher():
    """Tarayıcı kapanırsa verileri otomatik kaydeder."""
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
                            print(f"✅ Otomatik kayıt: {s_to_save.name}")
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

# --- HATA DÜZELTME KISMI: GECİKMELİ GÜNCELLEME ---
# Eğer bir önceki işlemden gelen "Seçimi Güncelle" emri varsa,
# widget çizilmeden ÖNCE burada uyguluyoruz.
if "pending_student_selector" in st.session_state:
    st.session_state["student_selector"] = st.session_state.pop("pending_student_selector")


# ---------------------------------------------------------
# 3. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
def reset_form():
    """Formu temizler ve widget state'lerini sıfırlar."""
    st.session_state.form_data = {
        "id": str(uuid.uuid4()),
        "name": "",
        "class_name": "",
        "notes": {},
        "behavior": [],
        "observation": "",
        "file_content": ""
    }

    # Widget keylerini sıfırla
    for course in st.session_state.course_list:
        if f"grade_{course}" in st.session_state:
            st.session_state[f"grade_{course}"] = 0
        if f"check_{course}" in st.session_state:
            st.session_state[f"check_{course}"] = False

    # Seçimi temizle
    st.session_state["student_selector"] = None


def load_student_to_form(student_obj):
    """Veritabanından gelen öğrenciyi forma yükler."""
    notes_dict = {g.subject: g.score for g in student_obj.grades}

    st.session_state.form_data = {
        "id": student_obj.id,
        "name": student_obj.name,
        "class_name": student_obj.class_name,
        "notes": notes_dict,
        "behavior": [],
        "observation": "",
        "file_content": student_obj.file_content
    }

    if notes_dict:
        for subject in notes_dict.keys():
            if subject not in st.session_state.course_list:
                st.session_state.course_list.append(subject)

    # Widget'ları güncelle
    for course in st.session_state.course_list:
        if course in notes_dict:
            st.session_state[f"grade_{course}"] = notes_dict[course]
            st.session_state[f"check_{course}"] = True
        else:
            st.session_state[f"grade_{course}"] = 0
            st.session_state[f"check_{course}"] = False


def save_current_form(update_ui=False):
    """
    Formdaki veriyi kaydeder.
    update_ui=True ise sol menüdeki seçimi de günceller (Butona basınca).
    update_ui=False ise sadece arkada kaydeder (Yazı yazarken).
    """
    data = st.session_state.form_data
    if not data["name"]:
        # Otomatik kayıtta hata mesajı gösterme, sadece butonla basınca gösterilir
        if update_ui:
            st.error("❌ Öğrenci adı girmediniz!")
        return False

    grade_objs = [Grade(subject=k, score=v) for k, v in data["notes"].items()]

    student = Student(
        id=data["id"],
        name=data["name"],
        class_name=data["class_name"],
        grades=grade_objs,
        file_content=data["file_content"]
    )

    manager.save_student(student)
    globals()['GLOBAL_LAST_STUDENT'] = student

    if update_ui:
        # HATA ÇÖZÜMÜ: Seçimi hemen güncellemek yerine,
        # bir sonraki turda güncellenmesi için not bırakıyoruz.
        display_name = f"{student.name} ({student.class_name})"
        st.session_state["pending_student_selector"] = display_name

    return True


# ---------------------------------------------------------
# 4. SIDEBAR (YAN MENÜ)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Öğrenci İşlemleri")

    # YENİ ÖĞRENCİ BUTONU
    if st.button("➕ YENİ ÖĞRENCİ OLUŞTUR", type="primary", use_container_width=True):
        reset_form()
        st.rerun()

    st.markdown("---")
    st.subheader("📋 Kayıtlı Liste")

    saved_students = manager.get_all_students()

    if not saved_students:
        st.info("Henüz kayıtlı öğrenci yok.")
    else:
        student_names = [f"{s.name} ({s.class_name})" for s in saved_students]

        selected_name = st.radio(
            "Düzenlemek için seçin:",
            student_names,
            index=None,
            key="student_selector"
        )

        if selected_name:
            target = next((s for s in saved_students if f"{s.name} ({s.class_name})" == selected_name), None)
            if target and st.session_state.form_data["id"] != target.id:
                load_student_to_form(target)
                st.rerun()

    st.markdown("---")
    if st.button("🚪 KAYDET VE ÇIK", use_container_width=True):
        if st.session_state.form_data["name"]:
            # Burada UI güncellemeye gerek yok, çıkıyoruz zaten
            save_current_form(update_ui=False)
        st.success("Kapatılıyor...")
        time.sleep(1)
        os._exit(0)

# ---------------------------------------------------------
# 5. ANA EKRAN (FORM)
# ---------------------------------------------------------
st.title("🎓 Öğrenci Performans Sistemi")

col_save, col_info = st.columns([1, 3])
with col_save:
    if st.button("💾 VERİLERİ KAYDET", type="primary", use_container_width=True):
        # Butonla basınca UI güncellemesi istiyoruz (True)
        if save_current_form(update_ui=True):
            st.toast(f"✅ {st.session_state.form_data['name']} kaydedildi!", icon="🎉")
            time.sleep(0.5)
            st.rerun()

with col_info:
    if st.session_state.form_data["name"]:
        st.info(f"Düzenlenen: **{st.session_state.form_data['name']}**")
    else:
        st.warning("Yeni Öğrenci Girişi")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📝 KİMLİK & NOTLAR", "📄 ÖDEV DOSYASI", "🤖 YAPAY ZEKA"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.form_data["name"] = st.text_input("Adı Soyadı", value=st.session_state.form_data["name"])
    with col2:
        st.session_state.form_data["class_name"] = st.text_input("Sınıfı",
                                                                 value=st.session_state.form_data["class_name"])

    st.subheader("📚 Ders Notları")
    st.caption("Not girmek istediğiniz dersin kutucuğunu işaretleyin.")

    with st.expander("Ders Listesini Düzenle"):
        c_add, c_del = st.columns(2)
        new_c = c_add.text_input("Ders Ekle")
        if c_add.button("Ekle"):
            if new_c and new_c not in st.session_state.course_list:
                st.session_state.course_list.append(new_c)
                st.session_state[f"check_{new_c}"] = False
                st.session_state[f"grade_{new_c}"] = 0
                st.rerun()

        del_c = c_del.selectbox("Silinecek Ders", st.session_state.course_list)
        if c_del.button("Dersi Sil"):
            if del_c in st.session_state.course_list:
                st.session_state.course_list.remove(del_c)
                st.session_state.form_data["notes"].pop(del_c, None)
                st.rerun()

    # --- NOT GİRİŞ SİSTEMİ ---
    cols = st.columns(3)
    for i, course in enumerate(st.session_state.course_list):
        with cols[i % 3]:
            check_key = f"check_{course}"
            widget_key = f"grade_{course}"

            if check_key not in st.session_state:
                st.session_state[check_key] = (course in st.session_state.form_data["notes"])

            is_active = st.checkbox(f"{course}", key=check_key)

            if is_active:
                if widget_key not in st.session_state:
                    st.session_state[widget_key] = st.session_state.form_data["notes"].get(course, 0)

                new_score = st.number_input(f"Notu Gir", 0, 100, key=widget_key, label_visibility="collapsed")
                st.session_state.form_data["notes"][course] = new_score
            else:
                if course in st.session_state.form_data["notes"]:
                    del st.session_state.form_data["notes"][course]

    st.subheader("🧠 Davranış Gözlemi")
    opts = ["Derse Katılım Yüksek", "Ödev Eksikliği Var", "Arkadaşlarıyla Uyumlu", "Dikkat Dağınıklığı",
            "Sorumluluk Sahibi"]
    st.session_state.form_data["behavior"] = st.multiselect("Gözlemlenen Davranışlar", opts,
                                                            default=st.session_state.form_data["behavior"])

with tab2:
    st.subheader("📂 Dosya Yükle")
    uploaded = st.file_uploader("PDF / DOCX / TXT", type=['pdf', 'docx', 'txt'])
    if uploaded:
        with st.spinner("Okunuyor..."):
            text = FileHandler.extract_text_from_file(uploaded)
            st.session_state.form_data["file_content"] = text
            st.success("Aktarıldı.")

    if st.session_state.form_data["file_content"]:
        st.text_area("İçerik", value=st.session_state.form_data["file_content"][:2000] + "...", height=200,
                     disabled=True)

with tab3:
    st.subheader("🤖 Ollama Analizi")
    ai_service = AIService()

    if ai_service.check_connection():
        st.success("🟢 Bağlı")
        models = ai_service.get_ollama_models()
        model = st.selectbox("Model", models or ["llama3.2"])
        ai_service.configure("Ollama", model)

        if st.button("Analizi Başlat", type="primary"):
            if not st.session_state.form_data["name"]:
                st.error("İsim giriniz.")
            else:
                data = st.session_state.form_data
                prompt = f"""
                ÖĞRENCİ: {data['name']} ({data['class_name']})
                NOTLAR: {json.dumps(data['notes'], ensure_ascii=False)}
                DAVRANIŞLAR: {', '.join(data['behavior'])}
                ÖDEV: {data['file_content'][:2000]}
                GÖREV: Analiz et ve 3 öneri ver.
                """
                box = st.empty()
                full_text = ""
                for chunk in ai_service.generate_stream(prompt, "Eğitim koçusun."):
                    full_text += chunk
                    box.markdown(full_text + "▌")
                box.markdown(full_text)
    else:
        st.error("🔴 Ollama kapalı. Terminalde 'ollama serve' yazın.")

# Anlık Veri Yedekleme (Arka planda sessiz çalışır)
# update_ui=False olduğu için sol menüyü güncellemeye çalışmaz ve hata vermez.
if st.session_state.form_data["name"]:
    save_current_form(update_ui=False)