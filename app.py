# -*- coding: utf-8 -*-
import streamlit as st
import json
import requests
import pandas as pd
import time
import threading
import os
import uuid
import hashlib
from datetime import datetime
from streamlit.runtime import get_instance

# Kendi modüllerimiz
from student_streamable import AIService, Config, FileHandler, StudentManager, Student, Grade, AIInsight, BehaviorNote

# ---------------------------------------------------------
# SAYFA AYARLARI ve GÜVENLİ RERUN HANDLER
# ---------------------------------------------------------
st.set_page_config(
    page_title="UFT Analiz Sistemi",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Güvenli rerun helper
def safe_rerun():
    """
    Try multiple methods to request a rerun, to be compatible with various Streamlit versions.
    1) st.experimental_rerun() if present
    2) raise internal RerunException
    3) fallback: set needs_rerun True and stop
    """
    # 1) public API if available
    try:
        if hasattr(st, "experimental_rerun"):
            try:
                st.experimental_rerun()
                return
            except Exception:
                # fallthrough to internal method
                pass
    except Exception:
        pass

    # 2) internal API fallback
    try:
        from streamlit.runtime.scriptrunner.script_runner import RerunException
        raise RerunException()
    except Exception:
        # 3) final fallback
        st.session_state['needs_rerun'] = True
        st.stop()

# Güvenli "rerun" kontrolü: handler'lar sadece bir talep bırakır, ana akış burada güvenle rerun yapar.
if 'needs_rerun' not in st.session_state:
    st.session_state['needs_rerun'] = False

# Eğer önceki run bir rerun talebi bırakmışsa, ana bağlamda güvenli şekilde rerun et.
if st.session_state.pop('needs_rerun', False):
    safe_rerun()

# ---------------------------------------------------------
# GLOBAL DEĞİŞKENLER
# ---------------------------------------------------------
if 'GLOBAL_LAST_STUDENT' not in globals():
    globals()['GLOBAL_LAST_STUDENT'] = None

manager = StudentManager()
ai_service = AIService()

# Ollama bağlantı durumu (module-level global; UI bu değişkenden okur)
OLLAMA_STATUS = {"connected": False, "last_checked": None}

# ---------------------------------------------------------
# BACKGROUND THREADS
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


def ollama_poller(poll_interval: int = 5):
    """Arka planda periyodik olarak Ollama bağlantısını kontrol eder."""
    while True:
        try:
            connected = ai_service.check_connection()
            OLLAMA_STATUS["connected"] = bool(connected)
            OLLAMA_STATUS["last_checked"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            OLLAMA_STATUS["connected"] = False
            OLLAMA_STATUS["last_checked"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        time.sleep(poll_interval)


if 'watcher_thread_started' not in st.session_state:
    t = threading.Thread(target=browser_watcher, daemon=True)
    t.start()
    st.session_state.watcher_thread_started = True

if 'ollama_poller_started' not in st.session_state:
    tp = threading.Thread(target=ollama_poller, args=(5,), daemon=True)
    tp.start()
    st.session_state.ollama_poller_started = True

# ---------------------------------------------------------
# SESSION STATE (HAFIZA) AYARLARI & WIDGET KEYS
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

def init_widget_keys():
    if 'form_name' not in st.session_state:
        st.session_state.form_name = st.session_state.form_data.get("name", "")
    if 'form_class' not in st.session_state:
        st.session_state.form_class = st.session_state.form_data.get("class_name", "")
    if 'form_file_content' not in st.session_state:
        st.session_state.form_file_content = st.session_state.form_data.get("file_content", "")
    if 'behavior' not in st.session_state:
        st.session_state.behavior = st.session_state.form_data.get("behavior", [])
    if 'grade_keys' not in st.session_state:
        st.session_state.grade_keys = {}
    if 'auto_save' not in st.session_state:
        st.session_state.auto_save = False
    if 'last_saved_form_hash' not in st.session_state:
        st.session_state.last_saved_form_hash = None
    if 'last_auto_save_time' not in st.session_state:
        st.session_state.last_auto_save_time = 0.0
    if 'auto_save_interval' not in st.session_state:
        st.session_state.auto_save_interval = 10  # seconds debounce

init_widget_keys()

if 'course_list' not in st.session_state:
    st.session_state.course_list = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler"]

# ---------------------------------------------------------
# NORMALIZATION, SYNC & HELPERS
# ---------------------------------------------------------
def normalize_name(name: str) -> str:
    if not name:
        return ""
    cleaned = " ".join(name.strip().split())
    return cleaned.title()

def normalize_class_name(cname: str) -> str:
    if not cname:
        return ""
    c = cname.strip().upper()
    c = c.replace(" ", "").replace("-", "")
    return c

def normalize_grades(notes: dict) -> dict:
    normalized = {}
    for subj, val in notes.items():
        try:
            num = int(float(str(val).replace(",", ".")))
            num = max(0, min(100, num))
        except Exception:
            num = 0
        normalized[subj] = num
    return normalized

def normalize_behavior(behavior_list: list) -> list:
    seen = set()
    cleaned = []
    for b in behavior_list:
        if not isinstance(b, str): continue
        t = " ".join(b.strip().split())
        if not t: continue
        if t not in seen:
            seen.add(t)
            cleaned.append(t)
    return cleaned

def normalize_file_content(text: str, limit: int = 15000) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) > limit:
        return t[:limit] + "\n\n...[truncated]"
    return t

def normalize_form_data():
    fd = st.session_state.form_data
    fd["name"] = normalize_name(fd.get("name", ""))
    fd["class_name"] = normalize_class_name(fd.get("class_name", ""))
    fd["notes"] = normalize_grades(fd.get("notes", {}))
    fd["behavior"] = normalize_behavior(fd.get("behavior", []))
    fd["file_content"] = normalize_file_content(fd.get("file_content", ""))
    fd["observation"] = (fd.get("observation") or "").strip()
    st.session_state.form_data = fd
    apply_form_to_widget_keys()
    return fd

def form_hash(fd: dict) -> str:
    j = json.dumps(fd, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(j.encode('utf-8')).hexdigest()

def apply_form_to_widget_keys():
    fd = st.session_state.form_data
    st.session_state.form_name = fd.get("name", "")
    st.session_state.form_class = fd.get("class_name", "")
    st.session_state.form_file_content = fd.get("file_content", "")
    st.session_state.behavior = fd.get("behavior", [])

    st.session_state.grade_keys = st.session_state.get('grade_keys', {})
    for subj, score in fd.get("notes", {}).items():
        key = f"grade_{subj}"
        st.session_state.grade_keys[subj] = key
        st.session_state.setdefault(key, score)
        st.session_state[key] = score

    for subj in fd.get("notes", {}).keys():
        if subj not in st.session_state.course_list:
            st.session_state.course_list.append(subj)

def sync_widgets_to_form():
    fd = st.session_state.form_data
    fd["name"] = st.session_state.get("form_name", fd.get("name", ""))
    fd["class_name"] = st.session_state.get("form_class", fd.get("class_name", ""))
    fd["file_content"] = st.session_state.get("form_file_content", fd.get("file_content", ""))
    fd["behavior"] = st.session_state.get("behavior", fd.get("behavior", []))
    notes = {}
    for subj, key in st.session_state.get("grade_keys", {}).items():
        notes[subj] = st.session_state.get(key, 0)
    fd["notes"] = notes
    st.session_state.form_data = fd

# ---------------------------------------------------------
# PERSISTENCE (NORMALIZE BEFORE SAVE)
# ---------------------------------------------------------
def save_current_form():
    sync_widgets_to_form()
    normalize_form_data()
    data = st.session_state.form_data
    if not data["name"]:
        st.error("❌ Öğrenci adı girmediniz!")
        return False

    grade_objs = [Grade(subject=k, score=v) for k, v in data["notes"].items()]
    behavior_objs = [BehaviorNote(note=b) for b in data.get("behavior", [])]

    student = Student(
        id=data.get("id") or str(uuid.uuid4()),
        name=data["name"],
        class_name=data["class_name"],
        grades=grade_objs,
        file_content=data["file_content"],
        behavior_notes=behavior_objs
    )

    manager.save_student(student)
    globals()['GLOBAL_LAST_STUDENT'] = student
    st.session_state.form_data = student.to_dict()
    apply_form_to_widget_keys()
    st.session_state.last_saved_form_hash = form_hash(st.session_state.form_data)
    st.session_state.last_auto_save_time = time.time()
    return True

# ---------------------------------------------------------
# UI HELPERS (diff rendering, details)
# ---------------------------------------------------------
def render_diff_list(diffs):
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
                try:
                    st.info(f"Not güncellendi — {subject}: {d.get('old')['score']} -> {d.get('new')['score']}")
                except Exception:
                    st.info(f"Not güncellendi — {subject}")
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
            st.dataframe(df, width='stretch')
        else:
            st.info("Not bilgisi yok.")

        st.subheader("📝 Ödev / Dosya İçeriği (Önizleme)")
        st.text_area("Dosya İçeriği (ilk 3000 karakter)", value=st.session_state.get("form_file_content", student.file_content[:3000]), height=200, key="form_file_content")

    with cols[1]:
        st.subheader("🧾 Davranışlar")
        st.multiselect("Gözlemlenen Davranışlar",
                       ["Derse Katılım Yüksek", "Ödev Eksikliği Var", "Arkadaşlarıyla Uyumlu", "Dikkat Dağınıklığı", "Sorumluluk Sahibi"],
                       default=st.session_state.get("behavior", []),
                       key="behavior")

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
                        mime="text/plain",
                        width='stretch'
                    )
        else:
            st.info("Henüz oluşturulmuş yapay zeka raporu yok.")

        st.markdown("---")
        st.subheader("🛠️ Rapor İşlemleri")
        st.markdown("**Ollama Bağlantısı**")
        status_col, btn_col = st.columns([3, 1])
        with status_col:
            connected = OLLAMA_STATUS.get("connected", False)
            last = OLLAMA_STATUS.get("last_checked")
            if connected:
                st.success(f"✅ Ollama bağlı (Son kontrol: {last})")
            else:
                st.error(f"🔴 Ollama bağlantısı yok (Son kontrol: {last})")
        with btn_col:
            if st.button("🔄 Yenile", width='stretch'):
                # Manuel yenileme: talep bırak ve akışı sonlandır (güvenli rerun pattern)
                conn = ai_service.check_connection()
                OLLAMA_STATUS["connected"] = bool(conn)
                OLLAMA_STATUS["last_checked"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state['needs_rerun'] = True
                st.stop()

        if not OLLAMA_STATUS.get("connected", False):
            st.warning("Ollama kapalıysa terminalde `ollama serve` çalıştırın veya modelin hazır olduğundan emin olun.")
        else:
            if st.button("🔁 Yapay Zeka Raporu Oluştur ve Kaydet", width='stretch'):
                with st.spinner("Analiz yapılıyor..."):
                    prompt = f"ÖĞRENCİ: {student.name}\nSINIF: {student.class_name}\nİÇERİK:\n{st.session_state.get('form_file_content', student.file_content)[:15000]}\n\nAnaliz et ve 3 öğretici öneri ver."
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
                        st.session_state.form_data = s.to_dict()
                        apply_form_to_widget_keys()
                        # güvenli yeniden çizim talebi
                        st.session_state['needs_rerun'] = True
                        st.stop()
                    except Exception as e:
                        st.error(f"Rapor kaydedilemedi: {e}")

        st.markdown("---")
        st.subheader("📜 Değişiklik Geçmişi (Changelog)")
        changelog = manager.get_changelog(student.id)
        if not changelog:
            st.info("Bu öğrenci için değişiklik geçmişi bulunmamaktadır.")
        else:
            choices = []
            for i, entry in enumerate(reversed(changelog)):
                idx = len(changelog) - 1 - i
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
            if st.button("🔄 Bu versiyona geri yükle", width='stretch'):
                ok = manager.restore_from_changelog(student.id, sel_idx)
                if ok:
                    st.success("✅ Geri yükleme başarılı. Sayfa yenileniyor...")
                    st.session_state['needs_rerun'] = True
                    st.stop()
                else:
                    st.error("❌ Geri yükleme başarısız.")

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Öğrenci İşlemleri")
    if st.button("➕ YENİ ÖĞRENCİ OLUŞTUR", type="primary", width='stretch'):
        reset_id = str(uuid.uuid4())
        st.session_state.form_data = {
            "id": reset_id,
            "name": "",
            "class_name": "",
            "notes": {},
            "behavior": [],
            "observation": "",
            "file_content": ""
        }
        apply_form_to_widget_keys()
        st.session_state['needs_rerun'] = True
        st.stop()

    st.markdown("---")
    st.subheader("📋 Kayıtlı Liste")
    saved_students = manager.get_all_students()
    if not saved_students:
        st.info("Henüz kayıtlı öğrenci yok.")
    else:
        student_names = [f"{s.name} ({s.class_name})" for s in saved_students]
        selected_name = st.radio("Düzenlemek için seçin:", student_names, index=None, key="saved_student_select")
        if selected_name:
            target = next((s for s in saved_students if f"{s.name} ({s.class_name})" == selected_name), None)
            if target and st.session_state.form_data.get("id") != target.id:
                st.session_state.form_data = target.to_dict()
                apply_form_to_widget_keys()
                st.session_state['needs_rerun'] = True
                st.stop()

    st.markdown("---")
    st.session_state.auto_save = st.checkbox("Otomatik Kaydet (Düzenlemeleri otomatik kaydeder)", value=st.session_state.auto_save)
    st.session_state.auto_save_interval = st.number_input("Otomatik kaydet aralığı (s)", min_value=2, max_value=300, value=int(st.session_state.auto_save_interval), step=1)
    if st.button("🚪 KAYDET VE ÇIK", width='stretch'):
        if save_current_form():
            st.success("Kapatılıyor...")
            time.sleep(1)
            os._exit(0)

# ---------------------------------------------------------
# MAIN FORM UI
# ---------------------------------------------------------
st.title("🎓 Öğrenci Performans Sistemi")

col_save, col_info = st.columns([1, 3])
with col_save:
    if st.button("💾 KALICI KAYDET", type="primary", width='stretch'):
        if save_current_form():
            st.toast(f"✅ {st.session_state.form_data['name']} kaydedildi!", icon="🎉")
            st.session_state['needs_rerun'] = True
            st.stop()
with col_info:
    st.text(f"Düzenlenen: {st.session_state.form_data.get('name','(yok)')}  —  ID: {st.session_state.form_data.get('id')}")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📝 KİMLİK & NOTLAR", "📄 ÖDEV DOSYASI", "🤖 YAPAY ZEKA", "📚 KAYITLI ÖĞRENCİLER"]) 

# (remaining UI unchanged...)
