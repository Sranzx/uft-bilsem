import streamlit as st
import pandas as pd
import json
import time

# !!! DİKKAT: Dosya ismi değiştiği için import da güncellendi !!!
from student_streamable import StudentManager, AIService, Student, Grade, BehaviorNote, Config

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Öğrenci Analiz AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STİL ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'manager' not in st.session_state:
    st.session_state.manager = StudentManager()
if 'ai' not in st.session_state:
    st.session_state.ai = AIService()


# --- YARDIMCI FONKSİYON ---
def get_ai_stream(prompt, system_prompt):
    """Backend'den gelen veri akışını Streamlit'e iletir"""
    return st.session_state.ai.generate_streaming_response(prompt, system_prompt)


# --- YAN MENÜ (AYARLAR) ---
with st.sidebar:
    st.title("🎓 Analiz AI")
    st.markdown("---")

    # 1. SAĞLAYICI SEÇİMİ
    st.subheader("⚙️ AI Motoru")
    provider = st.selectbox(
        "Sağlayıcı Seçin",
        ["Ollama", "OpenAI", "Anthropic", "Google"],
        index=0
    )

    api_key = None
    model_name = "llama3.2"  # Varsayılan

    # Seçime göre detay ayarlar
    if provider == "Ollama":
        model_name = st.text_input("Model Adı", value="llama3.2")
        st.caption("Yerel çalışır. Ücretsizdir.")
        status_icon = "🟢" if st.session_state.ai.check_connection() else "🔴"
        st.markdown(f"Durum: {status_icon}")

    elif provider == "OpenAI":
        api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        model_name = st.selectbox("Model", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])

    elif provider == "Anthropic":
        api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
        model_name = st.selectbox("Model", ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"])

    elif provider == "Google":
        api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
        model_name = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro"])

    # Ayarları kaydet
    st.session_state.ai.set_provider_config(provider, model_name, api_key)

    st.markdown("---")

    # 2. NAVİGASYON
    menu = st.radio(
        "Menü",
        ["📊 Dashboard", "➕ Yeni Öğrenci", "📝 Veri Girişi", "🤖 AI Analiz"]
    )

# --- SAYFA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Genel Bakış")
    students = st.session_state.manager.get_all_students()

    if not students:
        st.info("Kayıtlı öğrenci yok. 'Yeni Öğrenci' menüsünden ekleyin.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Öğrenci Sayısı", len(students))
        total_grades = sum(len(s.grades) for s in students)
        col2.metric("Toplam Not", total_grades)

        # Tablo
        data = []
        for s in students:
            avg = sum(g.score for g in s.grades) / len(s.grades) if s.grades else 0
            last_ai = s.ai_insights[-1].date if s.ai_insights else "-"
            data.append({
                "ID": s.id,
                "Ad": s.name,
                "Sınıf": s.class_name,
                "Ortalama": f"{avg:.1f}",
                "Son Analiz": last_ai
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

# --- SAYFA: YENİ ÖĞRENCİ ---
elif menu == "➕ Yeni Öğrenci":
    st.header("Yeni Öğrenci Kaydı")
    with st.form("add_student"):
        c1, c2 = st.columns(2)
        sid = c1.text_input("Öğrenci ID")
        cls = c2.text_input("Sınıf")
        name = st.text_input("Ad Soyad")

        if st.form_submit_button("Kaydet"):
            if st.session_state.manager.load_student(sid):
                st.error("Bu ID zaten kayıtlı!")
            elif sid and name:
                new_s = Student(id=sid, name=name, class_name=cls)
                st.session_state.manager.save_student(new_s)
                st.success("Kaydedildi!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("Alanları doldurun.")

# --- SAYFA: VERİ GİRİŞİ ---
elif menu == "📝 Veri Girişi":
    st.header("Veri Girişi")
    students = st.session_state.manager.get_all_students()

    if students:
        s_names = [f"{s.id} - {s.name}" for s in students]
        sel = st.selectbox("Öğrenci Seç", s_names)
        curr_id = sel.split(" - ")[0]
        student = st.session_state.manager.load_student(curr_id)

        tab1, tab2 = st.tabs(["Not Ekle", "Davranış Ekle"])

        with tab1:
            with st.form("grade"):
                sub = st.text_input("Ders")
                sc = st.number_input("Not", 0, 100)
                if st.form_submit_button("Not Ekle"):
                    student.grades.append(Grade(subject=sub, score=sc))
                    st.session_state.manager.save_student(student)
                    st.success("Eklendi")

        with tab2:
            with st.form("beh"):
                note = st.text_area("Not")
                typ = st.selectbox("Tür", ["neutral", "positive", "negative"])
                if st.form_submit_button("Kaydet"):
                    student.behavior_notes.append(BehaviorNote(note=note, type=typ))
                    st.session_state.manager.save_student(student)
                    st.success("Eklendi")
    else:
        st.warning("Önce öğrenci ekleyin.")

# --- SAYFA: AI ANALİZ ---
elif menu == "🤖 AI Analiz":
    st.header(f"AI Analiz ({st.session_state.ai.provider})")

    students = st.session_state.manager.get_all_students()
    if students:
        s_names = [f"{s.id} - {s.name}" for s in students]
        sel = st.selectbox("Analiz Edilecek Öğrenci", s_names)
        curr_id = sel.split(" - ")[0]
        student = st.session_state.manager.load_student(curr_id)

        if st.button("Analizi Başlat ✨", type="primary"):
            # Kontroller
            if st.session_state.ai.provider != "Ollama" and not st.session_state.ai.api_key:
                st.error(f"{st.session_state.ai.provider} için API Key girmelisiniz (Sol Menü).")
            else:
                prompt_data = st.session_state.ai.prepare_student_prompt(student)
                system = "Sen uzman bir eğitim koçu ve pedagogsun. Öğrenci verilerini analiz et, Markdown formatında, motive edici ve yapıcı bir rapor sun."

                st.markdown("### 🧠 AI Raporu")
                container = st.container(border=True)

                # Streaming Başlat
                stream = get_ai_stream(prompt_data, system)
                full_resp = container.write_stream(stream)

                # Kaydet
                from student_streamable import AIInsight

                student.ai_insights.append(AIInsight(analysis=str(full_resp), model=st.session_state.ai.model))
                st.session_state.manager.save_student(student)
                st.toast("Rapor kaydedildi!", icon="✅")

        # Geçmiş
        if student.ai_insights:
            with st.expander("Geçmiş Analizler"):
                for insight in reversed(student.ai_insights):
                    st.caption(f"{insight.date} - {insight.model}")
                    st.markdown(insight.analysis)
                    st.divider()

    else:
        st.warning("Öğrenci yok.")