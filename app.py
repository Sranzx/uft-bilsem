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
from student_streamable import AIService, Config, FileHandler, StudentManager, Student, Grade, AIInsight, BehaviorNote

# ---------------------------------------------------------
# GLOBAL DEĞİŞKENLER
# ---------------------------------------------------------
if 'GLOBAL_LAST_STUDENT' not in globals():
    globals()['GLOBAL_LAST_STUDENT'] = None

manager = StudentManager()
ai_service = AIService()

# Sayfa Ayarları
st.set_page_config(
    page_title="UFT Analiz Sistemi",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS (kısaltılmış)
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold;}
</style>
""", unsafe_allow_html=True)


# Watchdog thread (varsa)
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
                            print(f"✅ Otomatik kayıt: {s_to_save.name}")
                        except:
                            pass
                    os._exit(0)
        except:
            pass
        time.sleep(2)


if 'watcher_thread_started' not in st.session_state:
    t = threading.Thread(target=browser_watcher, daemon=True)
    t.start()
    st.session_state.watcher_thread_started = True

# Session defaults
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


# Yardımcı fonksiyonlar
def reset_form():
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
    notes_dict = {g.subject: g.score for g in student_obj.grades}
    st.session_state.form_data = {
        "id": student_obj.id,
        "name": student_obj.name,
        "class_name": student_obj.class_name,
        "notes": notes_dict,
        "behavior": [b.note for b in student_obj.behavior_notes],
        "observation": "",
        "file_content": student_obj.file_content
    }
    if notes_dict:
        st.session_state.course_list = list(notes_dict.keys())


def save_current_form():
    data = st.session_state.form_data
    if not data["name"]:
        st.error("❌ Öğrenci adı girmediniz!")
        return False

    grade_objs = [Grade(subject=k, score=v) for k, v in data["notes"].items()]
    behavior_objs = [BehaviorNote(note=b) for b in data.get("behavior", [])]

    student = Student(
        id=data["id"],
        name=data["name"],
        class_name=data["class_name"],
        grades=grade_objs,
        file_content=data["file_content"],
        behavior_notes=behavior_objs
    )

    manager.save_student(student)
    globals()['GLOBAL_LAST_STUDENT'] = student
    return True


def render_diff_list(diffs):
    """UI için diffları okunabilir şekilde render et."""
    for d in diffs:
        fld = d.get("field")
        if fld == "grades":
            t = d.get("type")
            subject = d.get("subject")
            if t == "added":
                st.success(f"Yeni not eklendi — {subject}: {d.get('new')}")
            elif t == "removed":
                st.error(f"Not silindi — {subject}: {d.get('old')}")
            elif t == "updated":
                st.info(f"Not güncellendi — {subject}: {d.get('old')['score']} -> {d.get('new')['score']}")
        elif fld == "behavior_notes":
            t = d.get("type")
            note = d.get("note")
            if t == "added":
                st.success(f"Davranış eklendi: {note}")
            else:
                st.error(f"Davranış silindi: {note}")
        elif fld == "ai_insights_count":
            st.info(f"AI rapor sayısı: {d.get('old')} -> {d.get('new')}")
        else:
            # name, class_name, file_content_snippet vb.
            st.write(f"{fld}:")
            st.write(f"- Önce: {d.get('old')}")
            st.write(f"- Sonra: {d.get('new')}")


def display_student_details(student: Student):
    st.header(f"{student.name} ({student.class_name})")
    cols = st.columns([2, 1])
    with cols[0]:
        st.subheader("📚 Notlar")
        if student.grades:
            df = pd.DataFrame([{"Ders": g.subject, "Not": g.score, "Tarih": g.date} for g in student.grades])
            st.dataframe(df, use_container_width=True)
            avg = sum([g.score for g in student.grades]) / len(student.grades)
            st.info(f"Ortalama Not: {avg:.2f}")
        else:
            st.info("Not bilgisi yok.")

        st.subheader("📝 Ödev / Dosya İçeriği (Önizleme)")
        if student.file_content:
            st.text_area("Dosya İçeriği (ilk 3000 karakter)", value=student.file_content[:3000], height=200)
        else:
            st.info("Yüklenmiş dosya içeriği yok.")

    with cols[1]:
        st.subheader("🧾 Davranışlar")
        if getattr(student, "behavior_notes", None):
            for b in student.behavior_notes:
                st.write(f"- {b.date} — {b.note} ({b.type})")
        else:
            st.info("Davranış notu yok.")

        st.markdown("---")
        st.subheader("🤖 Yapay Zeka Raporları")
        if getattr(student, "ai_insights", None) and len(student.ai_insights) > 0:
            for i, insight in enumerate(reversed(student.ai_insights)):
                with st.expander(f"{insight.date} — Model: {insight.model}"):
                    st.write(insight.analysis)
                    st.download_button(
                        label="Raporu İndir (.txt)",
                        data=insight.analysis,
                        file_name=f"{student.name.replace(' ','_')}_ai_report_{i}.txt",
                        mime="text/plain"
                    )
        else:
            st.info("Henüz oluşturulmuş yapay zeka raporu yok.")

        st.markdown("---")
        st.subheader("🛠️ Rapor İşlemleri")
        if not ai_service.check_connection():
            st.warning("🔴 Ollama kapalı. Terminalde 'ollama serve' yazın.")
        else:
            if st.button("🔁 Yapay Zeka Raporu Oluştur ve Kaydet"):
                with st.spinner("Analiz yapılıyor..."):
                    prompt = f"ÖĞRENCİ: {student.name}\nSINIF: {student.class_name}\nİÇERİK:\n{student.file_content[:15000]}\n\nAnaliz et ve 3 öğretici öneri ver."
                    full_text = ""
                    box = st.empty()
                    for chunk in ai_service.generate_stream(prompt, "Eğitim koçusun."):
                        full_text += chunk
                        box.markdown(full_text + "▌")
                    box.markdown(full_text)
                    try:
                        s = manager.load_student(student.id)
                        if not s:
                            s = student
                        s.ai_insights.append(AIInsight(analysis=full_text, model=ai_service.model))
                        manager.save_student(s)
                        st.success("✅ Rapor kaydedildi.")
                    except Exception as e:
                        st.error(f"Rapor kaydedilemedi: {e}")

        st.markdown("---")
        # Changelog & fark gösterme
        st.subheader("📜 Değişiklik Geçmişi (Changelog)")
        changelog = manager.get_changelog(student.id)
        if not changelog:
            st.info("Bu öğrenci için değişiklik geçmişi bulunmamaktadır.")
        else:
            # Show entries in reverse chronological order with index mapping
            choices = []
            for i, entry in enumerate(reversed(changelog)):
                idx = len(changelog) - 1 - i  # gerçek index
                ts = entry.get("timestamp", "")
                summary = f"{ts} — {len(entry.get('diffs', []))} değişiklik"
                choices.append((summary, idx))

            labels = [c[0] for c in choices]
            selected_label = st.selectbox("Gösterilecek değişikliği seçin:", labels)
            sel_idx = dict(choices)[selected_label]

            entry = changelog[sel_idx]
            st.markdown(f"**Zaman:** {entry.get('timestamp')}")
            st.markdown("**Değişiklikler:**")
            render_diff_list(entry.get("diffs", []))

            st.markdown("---")
            if st.button("🔄 Bu versiyona geri yükle"):
                if manager.restore_from_changelog(student.id, sel_idx):
                    st.success("✅ Geri yükleme başarılı. Sayfa yenileniyor...")
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("❌ Geri yükleme başarısız.")


# Sidebar
with st.sidebar:
    st.header("📂 Öğrenci İşlemleri")
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
        selected_name = st.radio("Düzenlemek için seçin:", student_names, index=None)
        if selected_name:
            target = next((s for s in saved_students if f"{s.name} ({s.class_name})" == selected_name), None)
            if target and st.session_state.form_data["id"] != target.id:
                load_student_to_form(target)
                st.rerun()

    st.markdown("---")
    if st.button("🚪 KAYDET VE ÇIK", use_container_width=True):
        if st.session_state.form_data["name"]:
            save_current_form()
        st.success("Kapatılıyor...")
        time.sleep(1)
        os._exit(0)

# Main UI
st.title("🎓 Öğrenci Performans Sistemi")

col_save, col_info = st.columns([1, 3])
with col_save:
    if st.button("💾 VERİLERİ KAYDET", type="primary", use_container_width=True):
        if save_current_form():
            st.toast(f"✅ {st.session_state.form_data['name']} kaydedildi!", icon="🎉")
            time.sleep(1)
            st.rerun()

with col_info:
    if st.session_state.form_data["name"]:
        st.info(f"Düzenlenen: **{st.session_state.form_data['name']}**")
    else:
        st.warning("Yeni Öğrenci Girişi")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📝 KİMLİK & NOTLAR", "📄 ÖDEV DOSYASI", "🤖 YAPAY ZEKA", "📚 KAYITLI ÖĞRENCİLER"])

# Tab1: data entry
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.form_data["name"] = st.text_input("Adı Soyadı", value=st.session_state.form_data["name"])
    with col2:
        st.session_state.form_data["class_name"] = st.text_input("Sınıfı", value=st.session_state.form_data["class_name"])

    st.subheader("📚 Ders Notları")
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
                st.session_state.form_data["notes"].pop(del_c, None)
                st.rerun()

    cols = st.columns(3)
    for i, course in enumerate(st.session_state.course_list):
        with cols[i % 3]:
            score = st.session_state.form_data["notes"].get(course, 0)
            new_score = st.number_input(f"{course}", 0, 100, value=score, key=f"grade_{course}")
            st.session_state.form_data["notes"][course] = new_score

    st.subheader("🧠 Davranış Gözlemi")
    opts = ["Derse Katılım Yüksek", "Ödev Eksikliği Var", "Arkadaşlarıyla Uyumlu", "Dikkat Dağınıklığı",
            "Sorumluluk Sahibi"]
    st.session_state.form_data["behavior"] = st.multiselect("Gözlemlenen Davranışlar", opts,
                                                            default=st.session_state.form_data["behavior"])

# Tab2: file upload
with tab2:
    st.subheader("📂 Dosya Yükle")
    uploaded = st.file_uploader("PDF / DOCX / TXT", type=['pdf', 'docx', 'txt'])
    if uploaded:
        with st.spinner("Okunuyor..."):
            text = FileHandler.extract_text_from_file(uploaded)
            st.session_state.form_data["file_content"] = text
            st.success("Aktarıldı.")
    if st.session_state.form_data["file_content"]:
        st.markdown("**Dosya Önizlemesi**")
        st.write(st.session_state.form_data["file_content"][:5000])

# Tab3: AI
with tab3:
    st.subheader("🤖 Yapay Zeka Analizi")
    if ai_service.check_connection():
        st.info(f"Ollama bağlantısı: ✅ Model: {ai_service.model}")
        if st.session_state.form_data["file_content"] and st.button("Analiz Başlat"):
            prompt = f"ÖDEV: {st.session_state.form_data['file_content'][:2000]}\nGÖREV: Analiz et ve 3 öneri ver."
            box = st.empty()
            full_text = ""
            for chunk in ai_service.generate_stream(prompt, "Eğitim koçusun."):
                full_text += chunk
                box.markdown(full_text + "▌")
            box.markdown(full_text)
            try:
                s = manager.load_student(st.session_state.form_data["id"])
                if not s:
                    grade_objs = [Grade(subject=k, score=v) for k, v in st.session_state.form_data["notes"].items()]
                    behavior_objs = [BehaviorNote(note=b) for b in st.session_state.form_data.get("behavior", [])]
                    s = Student(
                        id=st.session_state.form_data["id"],
                        name=st.session_state.form_data["name"] or "İsimsiz Öğrenci",
                        class_name=st.session_state.form_data["class_name"],
                        grades=grade_objs,
                        file_content=st.session_state.form_data["file_content"],
                        behavior_notes=behavior_objs
                    )
                s.ai_insights.append(AIInsight(analysis=full_text, model=ai_service.model))
                manager.save_student(s)
                globals()['GLOBAL_LAST_STUDENT'] = s
                st.success("✅ Yapay zeka analizi kaydedildi.")
            except Exception as e:
                st.error(f"Kaydetme hatası: {e}")
    else:
        st.error("🔴 Ollama kapalı. Terminalde 'ollama serve' yazın.")

# Tab4: show all students with details
with tab4:
    st.subheader("📚 Kayıtlı Öğrenciler ve Raporlar")
    all_students = manager.get_all_students()
    if not all_students:
        st.info("Henüz kayıtlı öğrenci yok.")
    else:
        for s in all_students:
            with st.expander(f"{s.name} ({s.class_name})"):
                display_student_details(s)

# Otomatik kaydetme (opsiyonel)
if st.session_state.form_data["name"]:
    # Hafif bir anlık-kaydetme: burada sıklık kontrolü eklenebilir
    save_current_form()