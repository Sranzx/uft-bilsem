import streamlit as st
import json
import time
import uuid
import threading
import os
from datetime import datetime
from typing import Optional
from streamlit.runtime import get_instance

from core.models import (
    Student, Grade, Homework, Project, Exam, AIInsight,
    HOMEWORK_STATUSES, PROJECT_STATUSES, EXAM_TYPES, DEFAULT_SUBJECTS
)
from core.storage import StudentRepository
from core.file_handler import FileHandler
from core.ai_service import AIService
from core.exporter import CSVExporter, PDFExporter, get_homework_alerts

repo = StudentRepository()

st.set_page_config(
    page_title="Öğrenci Takip Sistemi",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    h1, h2, h3 { color: #4facfe; }
    .metric-card { background-color: #262730; padding: 15px; border-radius: 10px; border-left: 5px solid #4facfe; margin: 10px 0; }
    .status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
    .homework-item { background-color: #1e1e2e; padding: 15px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #4facfe; }
    .project-item { background-color: #1e1e2e; padding: 15px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #ff6b6b; }
    .exam-item { background-color: #1e1e2e; padding: 15px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #51cf66; }
    div[data-testid="stExpander"] div[data-testid="stExpanderContent"] { background-color: #1a1a2e; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
def init_session():
    defaults = {
        "current_student_id": None,
        "subjects": DEFAULT_SUBJECTS.copy(),
        "active_tab": "dashboard",
        "last_ai_response": "",
        "last_ai_model": "",
        "editing_homework_id": None,
        "editing_project_id": None,
        "editing_exam_id": None,
        "nav_mode": "student",
        "export_class_filter": "Tümü",
        "export_subject_filter": "Tümü",
        "new_homework": {"title": "", "description": "", "subject": "", "due_date": "", "status": "pending"},
        "new_project": {"title": "", "description": "", "subject": "", "due_date": "", "status": "not_started"},
        "new_exam": {"title": "", "subject": "", "date": "", "score": 0.0, "max_score": 100.0, "exam_type": "exam", "notes": ""},
        "grade_inputs": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def get_student() -> Optional[Student]:
    sid = st.session_state.current_student_id
    if not sid:
        return None
    return repo.load(sid)


def save_student(student: Student):
    repo.save(student)
    st.toast(f"✅ {student.name} kaydedildi!", icon="🎉")


def new_student():
    student = Student(
        id=str(uuid.uuid4()),
        name="",
        class_name=""
    )
    repo.save(student)
    st.session_state.current_student_id = student.id
    st.session_state.grade_inputs = {}
    st.rerun()


def select_student(student_id: str):
    st.session_state.current_student_id = student_id
    st.session_state.grade_inputs = {}
    st.session_state.editing_homework_id = None
    st.session_state.editing_project_id = None
    st.session_state.editing_exam_id = None
    st.rerun()


def delete_current_student():
    sid = st.session_state.current_student_id
    if sid:
        repo.delete(sid)
        st.session_state.current_student_id = None
        st.rerun()


def refresh_grade_inputs(student: Student):
    inputs = {}
    for g in student.grades:
        inputs[g.subject] = g.score
    for s in st.session_state.subjects:
        if s not in inputs:
            inputs[s] = 0
    st.session_state.grade_inputs = inputs


def save_grades(student: Student):
    grades = []
    for subject, score in st.session_state.grade_inputs.items():
        if score and score > 0:
            existing = next((g for g in student.grades if g.subject == subject), None)
            if existing:
                existing.score = score
                grades.append(existing)
            else:
                grades.append(Grade(subject=subject, score=score))
    student.grades = grades
    save_student(student)


# ---------------------------------------------------------------------------
# BROWSER WATCHDOG (auto-save on tab close)
# ---------------------------------------------------------------------------
def _save_before_exit():
    sid = st.session_state.get("current_student_id")
    if not sid:
        return
    student = repo.load(sid)
    if student and student.name:
        repo.save(student)


def browser_watcher():
    time.sleep(3)
    while True:
        try:
            runtime = get_instance()
            if runtime:
                active = 1
                for attr in ["_session_mgr", "_session_manager", "_client_mgr"]:
                    mgr = getattr(runtime, attr, None)
                    if mgr and hasattr(mgr, "list_active_sessions"):
                        active = len(mgr.list_active_sessions())
                        break

                if active == 0:
                    _save_before_exit()
                    os._exit(0)
        except Exception:
            pass
        time.sleep(2)


if not st.session_state.get("_watcher_started"):
    t = threading.Thread(target=browser_watcher, daemon=True)
    t.start()
    st.session_state._watcher_started = True


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📚 Öğrenci Takip")

    if st.button("➕ YENİ ÖĞRENCİ", type="primary", use_container_width=True):
        new_student()

    st.divider()
    st.subheader("📋 Öğrenci Listesi")

    if not all_students:
        st.info("Henüz kayıtlı öğrenci yok.")
    else:
        search = st.text_input("🔍 Ara...", placeholder="İsim veya sınıf", label_visibility="collapsed")
        if search:
            filtered = [s for s in all_students if search.lower() in s.name.lower() or search.lower() in s.class_name.lower()]
        else:
            filtered = all_students

        for s in filtered:
            label = f"{s.name} ({s.class_name})" if s.class_name else s.name
            active = s.id == st.session_state.current_student_id
            if st.button(
                f"{'👉 ' if active else ''}{label}",
                key=f"sel_{s.id}",
                use_container_width=True,
                type="secondary" if not active else "primary"
            ):
                select_student(s.id)

    st.divider()
    if st.button("🚪 Çıkış", use_container_width=True):
        st.stop()


# ---------------------------------------------------------------------------
# MAIN CONTENT
# ---------------------------------------------------------------------------
all_students = repo.get_all()

nav_mode = st.radio(
    "Görünüm",
    ["student", "overview", "export"],
    format_func=lambda m: {"student": "👤 Öğrenci", "overview": "🏫 Sınıf", "export": "📥 Dışa Aktar"}[m],
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state.nav_mode = nav_mode

if nav_mode == "student":
    current = get_student()

    if not current:
        st.title("🎓 Öğrenci Takip Sistemi")
        st.markdown("""
        <div class="metric-card">
        Sol menüden bir öğrenci seçin veya yeni bir öğrenci oluşturun.
        <br><br>
        <b>Özellikler:</b>
        <br>📝 Not takibi &nbsp;|&nbsp; 📋 Ödev yönetimi &nbsp;|&nbsp; 📁 Proje takibi &nbsp;|&nbsp; 📊 Sınav kaydı &nbsp;|&nbsp; 🤖 Yapay Zeka Analizi &nbsp;|&nbsp; 🏫 Sınıf görünümü
        </div>
        """, unsafe_allow_html=True)

        total = len(all_students)
        classes = set(s.class_name for s in all_students if s.class_name)
        if total > 0:
            col1, col2, col3 = st.columns(3)
            col1.metric("Toplam Öğrenci", total)
            col2.metric("Sınıf Sayısı", len(classes))
            pending_hw = sum(1 for s in all_students for hw in s.homeworks if hw.status in ("pending", "late"))
            col3.metric("Bekleyen Ödev", pending_hw)

        st.divider()
        st.subheader("📬 Yaklaşan Ödev Hatırlatmaları")
        alerts = get_homework_alerts(all_students)
        if alerts:
            for a in alerts[:10]:
                urgency_colors = {"OVERDUE": "#ff6b6b", "TODAY": "#ff922b", "SOON": "#ffd43b"}
                color = urgency_colors.get(a["urgency"], "#4facfe")
                days_str = "⚠️ Gecikmiş!" if a["days_left"] < 0 else f"⏰ {abs(a['days_left'])} gün kaldı" if a["days_left"] > 0 else "📣 Bugün teslim!"
                st.markdown(f"""
                <div class="homework-item" style="border-left-color: {color};">
                    <b>{a['student'].name}</b> ({a['student'].class_name}) &nbsp;|&nbsp;
                    <b>{a['homework'].title}</b> - {a['homework'].subject}
                    <br><small>{days_str}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("Yaklaşan ödev yok!")
        st.stop()

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"### ✏️ {current.name}")
        if current.class_name:
            st.caption(f"Sınıf: {current.class_name}")
    with col2:
        st.metric("Ders Notu", f"{len(current.grades)} ders")
    with col3:
        st.metric("Ödev", f"{len(current.homeworks)}")
    with col4:
        st.metric("Sınav", f"{len(current.exams)}")

    tabs = st.tabs(["📊 Genel", "📝 Bilgiler & Notlar", "📋 Ödevler", "📁 Projeler", "📝 Sınavlar", "🤖 Yapay Zeka"])

# ===================================================================
# TAB 0: DASHBOARD
# ===================================================================
with tabs[0]:
    st.subheader("📊 Genel Durum")

    col1, col2, col3, col4 = st.columns(4)
    avg_grade = sum(g.score for g in current.grades) / len(current.grades) if current.grades else 0
    col1.metric("Not Ortalaması", f"{avg_grade:.1f}" if avg_grade else "-")
    pending_hw = sum(1 for h in current.homeworks if h.status == "pending")
    col2.metric("Bekleyen Ödev", pending_hw)
    late_hw = sum(1 for h in current.homeworks if h.status == "late")
    col3.metric("Geciken Ödev", late_hw)
    graded_hw = sum(1 for h in current.homeworks if h.status == "graded")
    col4.metric("Notlanan Ödev", graded_hw)

    if current.grades:
        st.subheader("📈 Ders Notları")
        cols = st.columns(len(current.grades))
        for i, g in enumerate(current.grades):
            with cols[i]:
                color = "#51cf66" if g.score >= 70 else "#ffd43b" if g.score >= 50 else "#ff6b6b"
                st.markdown(f"""
                <div class="metric-card" style="border-left-color: {color}; text-align: center;">
                    <div style="font-size: 0.9em;">{g.subject}</div>
                    <div style="font-size: 1.8em; font-weight: bold; color: {color};">{g.score:.0f}</div>
                </div>
                """, unsafe_allow_html=True)

    if current.homeworks:
        st.subheader("📋 Son Ödevler")
        for hw in sorted(current.homeworks, key=lambda h: h.due_date or "", reverse=True)[:5]:
            status_label = HOMEWORK_STATUSES.get(hw.status, hw.status)
            st.markdown(f"""
            <div class="homework-item">
                <b>{hw.title}</b> - {hw.subject} &nbsp;|&nbsp; {status_label}
                <br><small>Son Teslim: {hw.due_date or 'Belirtilmemiş'}</small>
            </div>
            """, unsafe_allow_html=True)

    if current.exams:
        st.subheader("📝 Son Sınavlar")
        for exam in sorted(current.exams, key=lambda e: e.date or "", reverse=True)[:5]:
            pct = (exam.score / exam.max_score * 100) if exam.max_score else 0
            st.markdown(f"""
            <div class="exam-item">
                <b>{exam.title}</b> - {exam.subject} &nbsp;|&nbsp; {exam.score}/{exam.max_score} ({pct:.0f}%)
            </div>
            """, unsafe_allow_html=True)

# ===================================================================
# TAB 1: STUDENT INFO & GRADES
# ===================================================================
with tabs[1]:
    st.subheader("👤 Öğrenci Bilgileri")

    name = st.text_input("Adı Soyadı", value=current.name, key="edit_name")
    class_name = st.text_input("Sınıfı", value=current.class_name, key="edit_class")

    if name != current.name or class_name != current.class_name:
        current.name = name
        current.class_name = class_name
        save_student(current)

    st.divider()
    st.subheader("📚 Ders Notları")

    with st.expander("📌 Ders Listesini Düzenle"):
        c1, c2 = st.columns(2)
        new_subj = c1.text_input("Yeni ders adı", key="new_subj")
        if c1.button("➕ Ekle") and new_subj and new_subj not in st.session_state.subjects:
            st.session_state.subjects.append(new_subj)
            st.session_state.grade_inputs[new_subj] = 0
            st.rerun()

        del_subj = c2.selectbox("Silinecek ders", st.session_state.subjects, key="del_subj")
        if c2.button("🗑️ Sil") and del_subj:
            st.session_state.subjects.remove(del_subj)
            st.session_state.grade_inputs.pop(del_subj, None)
            current.grades = [g for g in current.grades if g.subject != del_subj]
            save_student(current)
            st.rerun()

    if not st.session_state.grade_inputs:
        refresh_grade_inputs(current)

    cols = st.columns(3)
    changed = False
    for i, subject in enumerate(st.session_state.subjects):
        with cols[i % 3]:
            if subject not in st.session_state.grade_inputs:
                st.session_state.grade_inputs[subject] = 0
            val = st.number_input(
                subject, 0, 100,
                value=int(st.session_state.grade_inputs.get(subject, 0)),
                key=f"g_{subject}",
                label_visibility="visible"
            )
            if val != st.session_state.grade_inputs.get(subject):
                st.session_state.grade_inputs[subject] = val
                changed = True

    if changed:
        save_grades(current)

    st.divider()
    st.subheader("🧠 Davranış Notları")
    behavior_opts = ["Derse Katılım Yüksek", "Ödev Eksikliği Var", "Arkadaşlarıyla Uyumlu",
                     "Dikkat Dağınıklığı", "Sorumluluk Sahibi", "Grup Çalışmasına Yatkın",
                     "Liderlik Özelliği Var", "Özgüven Eksikliği"]
    selected_behaviors = st.multiselect(
        "Gözlemlenen Davranışlar",
        behavior_opts,
        default=[b for b in current.behavior_notes if b in behavior_opts],
        key="behavior_input"
    )
    custom_behavior = st.text_input(
        "Özel davranış notu ekle",
        placeholder="Davranış notunu yazın...",
        key="custom_behavior"
    )
    if st.button("Davranış Notlarını Kaydet", key="save_behavior"):
        current.behavior_notes = selected_behaviors[:]
        if custom_behavior.strip():
            current.behavior_notes.append(custom_behavior.strip())
        save_student(current)
        st.success("Davranış notları kaydedildi!")

    st.divider()
    st.subheader("👁️ Gözlem")
    observation = st.text_area(
        "Öğrenci gözlemi",
        value=current.observation,
        height=150,
        key="observation_input"
    )
    if observation != current.observation:
        current.observation = observation
        save_student(current)

# ===================================================================
# TAB 2: HOMEWORK (MOST IMPORTANT)
# ===================================================================
with tabs[2]:
    st.subheader("📋 Ödev Yönetimi")

    # Add/Edit homework form
    with st.expander("➕ Yeni Ödev Ekle / Düzenle", expanded=st.session_state.editing_homework_id is not None):
        editing_hw = None
        if st.session_state.editing_homework_id:
            editing_hw = next((h for h in current.homeworks if h.id == st.session_state.editing_homework_id), None)

        prefix = "hw_edit_" if editing_hw else "hw_new_"

        title = st.text_input("Ödev Başlığı",
            value=editing_hw.title if editing_hw else st.session_state.new_homework["title"],
            key=f"{prefix}title")
        c1, c2 = st.columns(2)
        subject = c1.selectbox("Ders",
            st.session_state.subjects,
            index=st.session_state.subjects.index(editing_hw.subject) if editing_hw and editing_hw.subject in st.session_state.subjects else 0,
            key=f"{prefix}subject")
        status = c2.selectbox("Durum",
            list(HOMEWORK_STATUSES.keys()),
            format_func=lambda k: HOMEWORK_STATUSES[k],
            index=list(HOMEWORK_STATUSES.keys()).index(editing_hw.status) if editing_hw else 0,
            key=f"{prefix}status")
        c3, c4 = st.columns(2)
        assigned_date = c3.date_input("Veriliş Tarihi",
            value=datetime.strptime(editing_hw.assigned_date[:10], "%Y-%m-%d") if editing_hw and editing_hw.assigned_date else datetime.now(),
            key=f"{prefix}assigned")
        due_date = c4.date_input("Teslim Tarihi",
            value=datetime.strptime(editing_hw.due_date[:10], "%Y-%m-%d") if editing_hw and editing_hw.due_date else datetime.now(),
            key=f"{prefix}due")

        description = st.text_area("Açıklama",
            value=editing_hw.description if editing_hw else st.session_state.new_homework["description"],
            height=100,
            key=f"{prefix}desc")

        uploaded_file = st.file_uploader("Ödev Dosyası (PDF/DOCX/TXT)", type=['pdf', 'docx', 'txt'],
            key=f"{prefix}file")
        file_content = editing_hw.file_content if editing_hw else ""

        if uploaded_file:
            with st.spinner("Dosya okunuyor..."):
                file_content = FileHandler.extract_text(uploaded_file)
                st.success("Dosya yüklendi!")

        if file_content:
            with st.expander("📄 Yüklenen Dosya İçeriği"):
                st.text(file_content[:2000] + ("..." if len(file_content) > 2000 else ""))

        if editing_hw:
            st.subheader("Notlandırma")
            c5, c6 = st.columns(2)
            hw_grade = c5.number_input("Not", 0.0, editing_hw.max_grade,
                value=editing_hw.grade if editing_hw.grade is not None else 0.0,
                key=f"{prefix}grade")
            max_grade = c6.number_input("Maksimum Not", 1.0, 1000.0,
                value=editing_hw.max_grade,
                key=f"{prefix}max_grade")
            feedback = st.text_area("Geri Bildirim",
                value=editing_hw.feedback,
                height=100,
                key=f"{prefix}feedback")

        save_col, cancel_col = st.columns([1, 1])
        with save_col:
            if st.button("💾 Kaydet", key=f"{prefix}save", type="primary"):
                if not title.strip():
                    st.error("Ödev başlığı gerekli!")
                else:
                    hw_data = {
                        "title": title.strip(),
                        "description": description,
                        "subject": subject,
                        "assigned_date": assigned_date.strftime("%Y-%m-%d"),
                        "due_date": due_date.strftime("%Y-%m-%d"),
                        "status": status,
                        "file_content": file_content,
                    }
                    if editing_hw:
                        hw_data["grade"] = hw_grade if status == "graded" else None
                        hw_data["max_grade"] = max_grade
                        hw_data["feedback"] = feedback
                        hw_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        for k, v in hw_data.items():
                            setattr(editing_hw, k, v)
                        st.session_state.editing_homework_id = None
                    else:
                        hw = Homework(**hw_data)
                        current.homeworks.append(hw)
                        st.session_state.new_homework = {"title": "", "description": "", "subject": "", "due_date": "", "status": "pending"}

                    save_student(current)
                    st.rerun()

        with cancel_col:
            if st.button("İptal", key=f"{prefix}cancel"):
                st.session_state.editing_homework_id = None
                st.rerun()

    st.divider()

    # Homework list
    if not current.homeworks:
        st.info("Henüz ödev eklenmemiş. Yukarıdan yeni ödev ekleyin.")
    else:
        # Filters
        fcol1, fcol2 = st.columns(2)
        status_filter = fcol1.selectbox(
            "Durum Filtresi",
            ["Tümü"] + list(HOMEWORK_STATUSES.keys()),
            format_func=lambda k: "Tümü" if k == "Tümü" else HOMEWORK_STATUSES[k],
            key="hw_filter_status"
        )
        subject_filter = fcol2.selectbox(
            "Ders Filtresi",
            ["Tümü"] + st.session_state.subjects,
            key="hw_filter_subject"
        )

        filtered_hw = current.homeworks
        if status_filter != "Tümü":
            filtered_hw = [h for h in filtered_hw if h.status == status_filter]
        if subject_filter != "Tümü":
            filtered_hw = [h for h in filtered_hw if h.subject == subject_filter]

        filtered_hw.sort(key=lambda h: h.due_date or "")

        if not filtered_hw:
            st.info("Filtrelere uygun ödev bulunamadı.")
        else:
            for hw in filtered_hw:
                status_label = HOMEWORK_STATUSES.get(hw.status, hw.status)
                late = hw.due_date and hw.due_date < datetime.now().strftime("%Y-%m-%d") and hw.status in ("pending",)
                border_color = "#ff6b6b" if late else "#4facfe"

                with st.container():
                    st.markdown(f"""
                    <div class="homework-item" style="border-left-color: {border_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <b>{hw.title}</b>
                                <span style="margin-left: 10px; font-size: 0.85em; color: #888;">{hw.subject}</span>
                            </div>
                            <span class="status-badge" style="background: {'#ff6b6b' if hw.status == 'late' else '#ffd43b' if hw.status == 'pending' else '#51cf66' if hw.status == 'graded' else '#4facfe'}; color: #000;">
                                {status_label}
                            </span>
                        </div>
                        <div style="margin-top: 8px; font-size: 0.9em;">
                            {hw.description[:150]}{'...' if len(hw.description) > 150 else ''}
                        </div>
                        <div style="margin-top: 5px; font-size: 0.8em; color: #888;">
                            Veriliş: {hw.assigned_date} &nbsp;|&nbsp; Teslim: {hw.due_date or 'Belirtilmemiş'}
                            {f' &nbsp;|&nbsp; Not: {hw.grade:.0f}/{hw.max_grade:.0f}' if hw.grade is not None else ''}
                            {f' &nbsp;|&nbsp; ⚠️ Gecikmiş!' if late else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    col_a, col_b, col_c = st.columns([1, 1, 4])
                    if col_a.button("✏️ Düzenle", key=f"hw_edit_{hw.id}"):
                        st.session_state.editing_homework_id = hw.id
                        st.rerun()
                    if col_b.button("🗑️ Sil", key=f"hw_del_{hw.id}"):
                        current.homeworks = [h for h in current.homeworks if h.id != hw.id]
                        save_student(current)
                        st.rerun()

                    if hw.file_content:
                        with st.expander("📄 Ödev Dosyası İçeriği", key=f"hw_content_{hw.id}"):
                            st.text(hw.file_content[:3000] + ("..." if len(hw.file_content) > 3000 else ""))

                    st.divider()

# ===================================================================
# TAB 3: PROJECTS
# ===================================================================
with tabs[3]:
    st.subheader("📁 Proje Yönetimi")

    with st.expander("➕ Yeni Proje Ekle / Düzenle", expanded=st.session_state.editing_project_id is not None):
        editing_pr = None
        if st.session_state.editing_project_id:
            editing_pr = next((p for p in current.projects if p.id == st.session_state.editing_project_id), None)

        pp = "pr_edit_" if editing_pr else "pr_new_"

        title = st.text_input("Proje Başlığı",
            value=editing_pr.title if editing_pr else st.session_state.new_project["title"],
            key=f"{pp}title")
        c1, c2 = st.columns(2)
        subject = c1.selectbox("Ders",
            st.session_state.subjects,
            index=st.session_state.subjects.index(editing_pr.subject) if editing_pr and editing_pr.subject in st.session_state.subjects else 0,
            key=f"{pp}subject")
        status = c2.selectbox("Durum",
            list(PROJECT_STATUSES.keys()),
            format_func=lambda k: PROJECT_STATUSES[k],
            index=list(PROJECT_STATUSES.keys()).index(editing_pr.status) if editing_pr else 0,
            key=f"{pp}status")
        c3, c4 = st.columns(2)
        start_date = c3.date_input("Başlangıç Tarihi",
            value=datetime.strptime(editing_pr.start_date[:10], "%Y-%m-%d") if editing_pr and editing_pr.start_date else datetime.now(),
            key=f"{pp}start")
        due_date = c4.date_input("Teslim Tarihi",
            value=datetime.strptime(editing_pr.due_date[:10], "%Y-%m-%d") if editing_pr and editing_pr.due_date else datetime.now(),
            key=f"{pp}due")

        description = st.text_area("Açıklama",
            value=editing_pr.description if editing_pr else st.session_state.new_project["description"],
            height=100,
            key=f"{pp}desc")

        uploaded_file = st.file_uploader("Proje Dosyası (PDF/DOCX/TXT)", type=['pdf', 'docx', 'txt'],
            key=f"{pp}file")
        file_content = editing_pr.file_content if editing_pr else ""
        if uploaded_file:
            with st.spinner("Dosya okunuyor..."):
                file_content = FileHandler.extract_text(uploaded_file)
                st.success("Dosya yüklendi!")

        if file_content:
            with st.expander("📄 Yüklenen Dosya İçeriği"):
                st.text(file_content[:2000] + ("..." if len(file_content) > 2000 else ""))

        if editing_pr:
            st.subheader("Notlandırma")
            c5, c6 = st.columns(2)
            pr_grade = c5.number_input("Not", 0.0, editing_pr.max_grade,
                value=editing_pr.grade if editing_pr.grade is not None else 0.0,
                key=f"{pp}grade")
            max_grade = c6.number_input("Maksimum Not", 1.0, 1000.0,
                value=editing_pr.max_grade,
                key=f"{pp}max_grade")
            feedback = st.text_area("Geri Bildirim",
                value=editing_pr.feedback,
                height=100,
                key=f"{pp}feedback")

        save_col, cancel_col = st.columns([1, 1])
        with save_col:
            if st.button("💾 Kaydet", key=f"{pp}save", type="primary"):
                if not title.strip():
                    st.error("Proje başlığı gerekli!")
                else:
                    pr_data = {
                        "title": title.strip(),
                        "description": description,
                        "subject": subject,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "due_date": due_date.strftime("%Y-%m-%d"),
                        "status": status,
                        "file_content": file_content,
                    }
                    if editing_pr:
                        pr_data["grade"] = pr_grade if status == "graded" else None
                        pr_data["max_grade"] = max_grade
                        pr_data["feedback"] = feedback
                        pr_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        for k, v in pr_data.items():
                            setattr(editing_pr, k, v)
                        st.session_state.editing_project_id = None
                    else:
                        pr = Project(**pr_data)
                        current.projects.append(pr)
                        st.session_state.new_project = {"title": "", "description": "", "subject": "", "due_date": "", "status": "not_started"}

                    save_student(current)
                    st.rerun()

        with cancel_col:
            if st.button("İptal", key=f"{pp}cancel"):
                st.session_state.editing_project_id = None
                st.rerun()

    st.divider()

    if not current.projects:
        st.info("Henüz proje eklenmemiş.")
    else:
        fcol1, fcol2 = st.columns(2)
        p_status_filter = fcol1.selectbox(
            "Durum Filtresi",
            ["Tümü"] + list(PROJECT_STATUSES.keys()),
            format_func=lambda k: "Tümü" if k == "Tümü" else PROJECT_STATUSES[k],
            key="pr_filter_status"
        )
        p_subject_filter = fcol2.selectbox(
            "Ders Filtresi",
            ["Tümü"] + st.session_state.subjects,
            key="pr_filter_subject"
        )

        filtered_pr = current.projects
        if p_status_filter != "Tümü":
            filtered_pr = [p for p in filtered_pr if p.status == p_status_filter]
        if p_subject_filter != "Tümü":
            filtered_pr = [p for p in filtered_pr if p.subject == p_subject_filter]

        filtered_pr.sort(key=lambda p: p.due_date or "")

        for pr in filtered_pr:
            status_label = PROJECT_STATUSES.get(pr.status, pr.status)
            with st.container():
                st.markdown(f"""
                <div class="project-item">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <b>{pr.title}</b>
                            <span style="margin-left: 10px; font-size: 0.85em; color: #888;">{pr.subject}</span>
                        </div>
                        <span class="status-badge" style="background: {'#ffd43b' if pr.status in ('not_started',) else '#4facfe' if pr.status == 'in_progress' else '#51cf66' if pr.status == 'graded' else '#868e96'}; color: #000;">
                            {status_label}
                        </span>
                    </div>
                    <div style="margin-top: 8px; font-size: 0.9em;">
                        {pr.description[:150]}{'...' if len(pr.description) > 150 else ''}
                    </div>
                    <div style="margin-top: 5px; font-size: 0.8em; color: #888;">
                        Başlangıç: {pr.start_date} &nbsp;|&nbsp; Teslim: {pr.due_date or 'Belirtilmemiş'}
                        {f' &nbsp;|&nbsp; Not: {pr.grade:.0f}/{pr.max_grade:.0f}' if pr.grade is not None else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_a, col_b, col_c = st.columns([1, 1, 4])
                if col_a.button("✏️ Düzenle", key=f"pr_edit_{pr.id}"):
                    st.session_state.editing_project_id = pr.id
                    st.rerun()
                if col_b.button("🗑️ Sil", key=f"pr_del_{pr.id}"):
                    current.projects = [p for p in current.projects if p.id != pr.id]
                    save_student(current)
                    st.rerun()

                if pr.file_content:
                    with st.expander("📄 Proje Dosyası İçeriği", key=f"pr_content_{pr.id}"):
                        st.text(pr.file_content[:3000] + ("..." if len(pr.file_content) > 3000 else ""))

                st.divider()

# ===================================================================
# TAB 4: EXAMS
# ===================================================================
with tabs[4]:
    st.subheader("📝 Sınav / Test Yönetimi")

    with st.expander("➕ Yeni Sınav Ekle / Düzenle", expanded=st.session_state.editing_exam_id is not None):
        editing_ex = None
        if st.session_state.editing_exam_id:
            editing_ex = next((e for e in current.exams if e.id == st.session_state.editing_exam_id), None)

        ep = "ex_edit_" if editing_ex else "ex_new_"

        title = st.text_input("Sınav Adı",
            value=editing_ex.title if editing_ex else st.session_state.new_exam["title"],
            key=f"{ep}title")
        c1, c2, c3 = st.columns(3)
        subject = c1.selectbox("Ders",
            st.session_state.subjects,
            index=st.session_state.subjects.index(editing_ex.subject) if editing_ex and editing_ex.subject in st.session_state.subjects else 0,
            key=f"{ep}subject")
        exam_type = c2.selectbox("Türü",
            list(EXAM_TYPES.keys()),
            format_func=lambda k: EXAM_TYPES[k],
            index=list(EXAM_TYPES.keys()).index(editing_ex.exam_type) if editing_ex else 0,
            key=f"{ep}type")
        exam_date = c3.date_input("Tarih",
            value=datetime.strptime(editing_ex.date[:10], "%Y-%m-%d") if editing_ex and editing_ex.date else datetime.now(),
            key=f"{ep}date")

        c4, c5 = st.columns(2)
        score = c4.number_input("Alınan Not", 0.0, 1000.0,
            value=float(editing_ex.score) if editing_ex else st.session_state.new_exam["score"],
            key=f"{ep}score")
        max_score = c5.number_input("Maksimum Not", 1.0, 1000.0,
            value=float(editing_ex.max_score) if editing_ex else st.session_state.new_exam["max_score"],
            key=f"{ep}max")

        notes = st.text_area("Notlar",
            value=editing_ex.notes if editing_ex else st.session_state.new_exam["notes"],
            height=80,
            key=f"{ep}notes")

        save_col, cancel_col = st.columns([1, 1])
        with save_col:
            if st.button("💾 Kaydet", key=f"{ep}save", type="primary"):
                if not title.strip():
                    st.error("Sınav adı gerekli!")
                elif score > max_score:
                    st.error("Alınan not, maksimum nottan büyük olamaz!")
                else:
                    exam_data = {
                        "title": title.strip(),
                        "subject": subject,
                        "exam_type": exam_type,
                        "date": exam_date.strftime("%Y-%m-%d"),
                        "score": score,
                        "max_score": max_score,
                        "notes": notes,
                    }
                    if editing_ex:
                        exam_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        for k, v in exam_data.items():
                            setattr(editing_ex, k, v)
                        st.session_state.editing_exam_id = None
                    else:
                        exam = Exam(**exam_data)
                        current.exams.append(exam)
                        st.session_state.new_exam = {"title": "", "subject": "", "date": "", "score": 0.0, "max_score": 100.0, "exam_type": "exam", "notes": ""}

                    save_student(current)
                    st.rerun()

        with cancel_col:
            if st.button("İptal", key=f"{ep}cancel"):
                st.session_state.editing_exam_id = None
                st.rerun()

    st.divider()

    if not current.exams:
        st.info("Henüz sınav kaydı eklenmemiş.")
    else:
        fcol1, fcol2 = st.columns(2)
        ex_subject_filter = fcol1.selectbox(
            "Ders Filtresi",
            ["Tümü"] + st.session_state.subjects,
            key="ex_filter_subject"
        )
        ex_type_filter = fcol2.selectbox(
            "Sınav Türü",
            ["Tümü"] + list(EXAM_TYPES.keys()),
            format_func=lambda k: "Tümü" if k == "Tümü" else EXAM_TYPES[k],
            key="ex_filter_type"
        )

        filtered_ex = current.exams
        if ex_subject_filter != "Tümü":
            filtered_ex = [e for e in filtered_ex if e.subject == ex_subject_filter]
        if ex_type_filter != "Tümü":
            filtered_ex = [e for e in filtered_ex if e.exam_type == ex_type_filter]

        filtered_ex.sort(key=lambda e: e.date or "", reverse=True)

        for exam in filtered_ex:
            pct = (exam.score / exam.max_score * 100) if exam.max_score else 0
            color = "#51cf66" if pct >= 70 else "#ffd43b" if pct >= 50 else "#ff6b6b"

            with st.container():
                st.markdown(f"""
                <div class="exam-item">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <b>{exam.title}</b>
                            <span style="margin-left: 10px; font-size: 0.85em; color: #888;">{exam.subject}</span>
                            <span style="margin-left: 8px; font-size: 0.8em; color: #666;">{EXAM_TYPES.get(exam.exam_type, exam.exam_type)}</span>
                        </div>
                        <span style="font-size: 1.2em; font-weight: bold; color: {color};">{exam.score:.0f}/{exam.max_score:.0f} ({pct:.0f}%)</span>
                    </div>
                    <div style="margin-top: 5px; font-size: 0.8em; color: #888;">
                        Tarih: {exam.date}
                    </div>
                    {f'<div style="margin-top: 5px; font-size: 0.9em;">{exam.notes[:200]}</div>' if exam.notes else ''}
                </div>
                """, unsafe_allow_html=True)

                col_a, col_b = st.columns([1, 1])
                if col_a.button("✏️ Düzenle", key=f"ex_edit_{exam.id}"):
                    st.session_state.editing_exam_id = exam.id
                    st.rerun()
                if col_b.button("🗑️ Sil", key=f"ex_del_{exam.id}"):
                    current.exams = [e for e in current.exams if e.id != exam.id]
                    save_student(current)
                    st.rerun()

                st.divider()

# ===================================================================
# TAB 5: AI ANALYSIS
# ===================================================================
with tabs[5]:
    st.subheader("🤖 Yapay Zeka Analizi (Ollama)")

    ai_service = AIService()

    if current.ai_insights:
        with st.expander(f"📚 Geçmiş Analizler ({len(current.ai_insights)})"):
            for insight in reversed(current.ai_insights):
                st.caption(f"📅 {insight.date} | 🤖 {insight.model}")
                st.info(insight.analysis)
                st.divider()

    if ai_service.check_connection():
        st.success("🟢 Ollama bağlantısı hazır")
        models = ai_service.get_available_models()
        model = st.selectbox("Model Seçin", models or ["llama3.2"], key="ai_model")

        if st.button("✨ Analizi Başlat", type="primary", key="ai_start"):
            if not current.name:
                st.error("Öğrenci adı gerekli!")
            else:
                prompt = f"""
ÖĞRENCİ: {current.name} ({current.class_name})
NOTLAR: {json.dumps({g.subject: g.score for g in current.grades}, ensure_ascii=False)}
DAVRANIŞLAR: {', '.join(current.behavior_notes)}
GÖZLEM: {current.observation}
DOSYA İÇERİĞİ: {current.file_content[:2000] if current.file_content else 'Yok'}
ÖDEV SAYISI: {len(current.homeworks)} (Teslim edilen: {sum(1 for h in current.homeworks if h.status in ('submitted', 'graded'))})
PROJE SAYISI: {len(current.projects)}
SINAV SAYISI: {len(current.exams)}

GÖREV: Öğrencinin akademik durumunu detaylı analiz et. Güçlü yönleri, gelişim alanları ve önerilerini belirt.
"""

                ai_service.configure("Ollama", model)
                box = st.empty()
                full_text = ""
                for chunk in ai_service.generate_stream(prompt, "Sen deneyimli bir eğitim koçusun."):
                    full_text += chunk
                    box.markdown(full_text + "▌")
                box.markdown(full_text)
                st.session_state.last_ai_response = full_text
                st.session_state.last_ai_model = model

        if st.session_state.last_ai_response:
            st.divider()
            st.caption("Son analiz henüz kaydedilmedi.")
            if st.button("💾 Analizi Kaydet", type="primary", key="ai_save"):
                insight = AIInsight(
                    analysis=st.session_state.last_ai_response,
                    model=st.session_state.last_ai_model,
                    date=datetime.now().strftime("%Y-%m-%d %H:%M")
                )
                current.ai_insights.append(insight)
                save_student(current)
                st.session_state.last_ai_response = ""
                st.success("Analiz kaydedildi!")
                time.sleep(1)
                st.rerun()
    else:
        st.error("🔴 Ollama servisi kapalı. Terminalde 'ollama serve' çalıştırın.")
        st.info("Kurulum için: https://ollama.ai")


# ===================================================================
# NAV MODE: CLASS OVERVIEW
# ===================================================================
if nav_mode == "overview":
    st.title("🏫 Sınıf Geneli Görünüm")

    if not all_students:
        st.info("Henüz kayıtlı öğrenci yok.")
        st.stop()

    classes = sorted(set(s.class_name for s in all_students if s.class_name))
    selected_class = st.selectbox("Sınıf Seçin", ["Tümü"] + classes)

    if selected_class == "Tümü":
        filtered = all_students
    else:
        filtered = [s for s in all_students if s.class_name == selected_class]

    st.markdown(f"**{len(filtered)} öğrenci**")
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    total_hw = sum(len(s.homeworks) for s in filtered)
    pending_hw = sum(1 for s in filtered for h in s.homeworks if h.status == "pending")
    late_hw = sum(1 for s in filtered for h in s.homeworks if h.status == "late")
    graded_hw = sum(1 for s in filtered for h in s.homeworks if h.status == "graded")
    avg_all = []
    for s in filtered:
        if s.grades:
            avg_all.extend([g.score for g in s.grades])
    overall_avg = sum(avg_all) / len(avg_all) if avg_all else 0

    c1.metric("Ders Not Ort.", f"{overall_avg:.1f}")
    c2.metric("Toplam Ödev", total_hw)
    c3.metric("Bekleyen", pending_hw)
    c4.metric("Geciken", late_hw)

    st.divider()
    st.subheader("📬 Ödev Hatırlatmaları & Durumu")

    alerts = get_homework_alerts(filtered)
    if alerts:
        for a in alerts[:20]:
            urgency_styles = {
                "OVERDUE": ("#ff6b6b", "⚠️ Gecikmiş!"),
                "TODAY": ("#ff922b", "📣 Bugün teslim!"),
                "SOON": ("#ffd43b", f"⏰ {abs(a['days_left'])} gün kaldı"),
            }
            color, label = urgency_styles.get(a["urgency"], ("#4facfe", f"{a['days_left']} gün"))
            st.markdown(f"""
            <div class="homework-item" style="border-left-color: {color};">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <b>{a['student'].name}</b> &nbsp;|&nbsp; {a['homework'].title}
                        <span style="margin-left: 10px; font-size: 0.85em; color: #888;">{a['homework'].subject}</span>
                    </div>
                    <span class="status-badge" style="background: {color}; color: #000;">{label}</span>
                </div>
                <div style="font-size: 0.8em; color: #888; margin-top: 4px;">
                    Teslim: {a['homework'].due_date or 'Belirtilmemiş'} | Durum: {HOMEWORK_STATUSES.get(a['homework'].status, a['homework'].status)}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("Yaklaşan ödev yok, her şey güncel!")

    st.divider()
    st.subheader("📊 Ders Bazlı Not Ortalamaları")

    subject_stats = {}
    for s in filtered:
        for g in s.grades:
            if g.subject not in subject_stats:
                subject_stats[g.subject] = []
            subject_stats[g.subject].append(g.score)

    if subject_stats:
        sub_cols = st.columns(min(len(subject_stats), 4))
        for i, (subj, scores) in enumerate(sorted(subject_stats.items())):
            avg_s = sum(scores) / len(scores)
            color_s = "#51cf66" if avg_s >= 70 else "#ffd43b" if avg_s >= 50 else "#ff6b6b"
            with sub_cols[i % 4]:
                st.markdown(f"""
                <div class="metric-card" style="border-left-color: {color_s}; text-align: center;">
                    <div style="font-size: 0.85em;">{subj}</div>
                    <div style="font-size: 1.6em; font-weight: bold; color: {color_s};">{avg_s:.1f}</div>
                    <div style="font-size: 0.75em; color: #888;">{len(scores)} not</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Henüz ders notu girilmemiş.")

    st.divider()
    st.subheader("📋 Öğrenci Listesi")

    for s in filtered:
        avg_s = sum(g.score for g in s.grades) / len(s.grades) if s.grades else 0
        pending_s = sum(1 for h in s.homeworks if h.status == "pending")
        late_s = sum(1 for h in s.homeworks if h.status == "late")

        with st.expander(f"{s.name} ({s.class_name}) — Ort: {avg_s:.1f if avg_s else '-'} | Bekleyen: {pending_s} | Geciken: {late_s}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Ders Notları:**")
                for g in s.grades:
                    st.write(f"  {g.subject}: {g.score:.0f}")

            with col2:
                st.write("**Ödev Durumu:**")
                for h in s.homeworks:
                    status_icon = {"pending": "📋", "submitted": "📤", "graded": "✅", "late": "⏰"}.get(h.status, "•")
                    st.write(f"  {status_icon} {h.title} - {h.subject} ({h.due_date or 'no date'})")

            st.write("**Sınavlar:**")
            for e in s.exams:
                pct_e = (e.score / e.max_score * 100) if e.max_score else 0
                st.write(f"  📝 {e.title} - {e.subject}: {e.score:.0f}/{e.max_score:.0f} ({pct_e:.0f}%)")


# ===================================================================
# NAV MODE: EXPORT
# ===================================================================
elif nav_mode == "export":
    st.title("📥 Veri Dışa Aktarma")

    if not all_students:
        st.info("Henüz kayıtlı öğrenci yok.")
        st.stop()

    classes = sorted(set(s.class_name for s in all_students if s.class_name))
    col_f, col_s, col_t = st.columns(3)

    with col_f:
        export_type = st.radio("Dışa Aktarma Türü", ["Tüm Öğrenciler", "Sınıf", "Tek Öğrenci"])

    with col_s:
        if export_type == "Sınıf":
            target_class = st.selectbox("Sınıf Seç", ["Tümü"] + classes)
        elif export_type == "Tek Öğrenci":
            student_names = [f"{s.name} ({s.class_name})" for s in all_students]
            selected_name = st.selectbox("Öğrenci Seç", student_names)
            target_student = next((s for s in all_students if f"{s.name} ({s.class_name})" == selected_name), None)
        else:
            target_class = "Tümü"

    with col_t:
        export_format = st.radio("Format", ["CSV", "PDF"])

    st.divider()

    if export_type == "Tek Öğrenci" and target_student:
        col_csv, col_pdf = st.columns(2)
        with col_csv:
            csv_data = CSVExporter.student_to_csv(target_student)
            st.download_button("📊 CSV İndir", csv_data.encode("utf-8"),
                file_name=f"{target_student.name}_{target_student.class_name}.csv",
                mime="text/csv", use_container_width=True)

        with col_pdf:
            pdf_data = PDFExporter.student_to_pdf(target_student)
            is_csv_fallback = len(pdf_data) > 50000 and b"Ad Soyad" in pdf_data
            if is_csv_fallback:
                st.download_button("📄 PDF İndir", pdf_data,
                    file_name=f"{target_student.name}_{target_student.class_name}_report.csv",
                    mime="text/csv", use_container_width=True)
                st.caption("PDF kütüphanesi yüklenmedi, CSV olarak indirildi.")
            else:
                st.download_button("📄 PDF İndir", pdf_data,
                    file_name=f"{target_student.name}_{target_student.class_name}.pdf",
                    mime="application/pdf", use_container_width=True)

        st.divider()
        st.subheader(f"📋 {target_student.name} Özet")
        c1, c2, c3, c4 = st.columns(4)
        avg_e = sum(g.score for g in target_student.grades) / len(target_student.grades) if target_student.grades else 0
        c1.metric("Not Ort.", f"{avg_e:.1f}")
        c2.metric("Ödev", len(target_student.homeworks))
        c3.metric("Proje", len(target_student.projects))
        c4.metric("Sınav", len(target_student.exams))

        st.subheader("📋 Tüm Ödevler")
        for h in target_student.homeworks:
            st.markdown(f"**{h.title}** — {h.subject} | {HOMEWORK_STATUSES.get(h.status, h.status)} | Teslim: {h.due_date or '-'}")

    else:
        if export_type == "Sınıf" and target_class != "Tümü":
            target_students = [s for s in all_students if s.class_name == target_class]
        else:
            target_students = all_students

        st.write(f"**{len(target_students)} öğrenci** seçildi.")

        tab_list, tab_summary, tab_hw = st.tabs(["Liste", "Özet", "Ödev Raporu"])

        with tab_list:
            csv_all = CSVExporter.all_students_csv(target_students)
            st.download_button("📊 Tüm Liste CSV", csv_all.encode("utf-8"),
                file_name=f"ogrenci_liste_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", use_container_width=True)
            st.dataframe([{"Ad": s.name, "Sınıf": s.class_name, "Ders": len(s.grades),
                          "Ödev": len(s.homeworks), "Proje": len(s.projects), "Sınav": len(s.exams)}
                         for s in target_students], use_container_width=True)

        with tab_summary:
            csv_summary = CSVExporter.all_students_csv(target_students)
            st.download_button("📊 Özet CSV", csv_summary.encode("utf-8"),
                file_name=f"ogrenci_ozet_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", use_container_width=True)

            data_rows = []
            for s in target_students:
                avg = sum(g.score for g in s.grades) / len(s.grades) if s.grades else 0
                pending = sum(1 for h in s.homeworks if h.status == "pending")
                late = sum(1 for h in s.homeworks if h.status == "late")
                graded = sum(1 for h in s.homeworks if h.status == "graded")
                data_rows.append({
                    "Ad": s.name,
                    "Sınıf": s.class_name,
                    "Not Ort.": f"{avg:.1f}",
                    "Ders": len(s.grades),
                    "Toplam Ödev": len(s.homeworks),
                    "Bekleyen": pending,
                    "Geciken": late,
                    "Notlanan": graded,
                })

            st.dataframe(data_rows, use_container_width=True, hide_index=True)

        with tab_hw:
            csv_hw = CSVExporter.homework_overview_csv(target_students)
            st.download_button("📋 Ödev Raporu CSV", csv_hw.encode("utf-8"),
                file_name=f"odev_raporu_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", use_container_width=True)

            hw_rows = []
            for s in target_students:
                for h in s.homeworks:
                    days_left = ""
                    if h.due_date:
                        try:
                            due = datetime.strptime(h.due_date, "%Y-%m-%d")
                            diff = (due - datetime.now()).days
                            days_left = str(diff)
                        except Exception:
                            days_left = ""
                    pct = f"{(h.grade/h.max_grade*100):.0f}%" if h.grade is not None else "-"
                    hw_rows.append({
                        "Öğrenci": s.name,
                        "Sınıf": s.class_name,
                        "Ödev": h.title,
                        "Ders": h.subject,
                        "Teslim": h.due_date or "-",
                        "Durum": HOMEWORK_STATUSES.get(h.status, h.status),
                        "Not": f"{h.grade:.0f}" if h.grade is not None else "-",
                        "Gün": days_left,
                    })
            st.dataframe(hw_rows, use_container_width=True, hide_index=True)
