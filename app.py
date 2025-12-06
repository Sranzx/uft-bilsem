import streamlit as st
import pandas as pd
import time
from student_streamable import StudentManager, AIService, Student, Grade, BehaviorNote, AIInsight
from utils import create_pdf_report


def init_session():
    st.set_page_config(
        page_title="Öğrenci Zeka Sistemi",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    if 'manager' not in st.session_state:
        st.session_state.manager = StudentManager()
    if 'ai' not in st.session_state:
        st.session_state.ai = AIService()


def inject_custom_css():
    st.markdown("""
        <style>
        .main { background-color: #f8f9fa; }
        .stButton>button { width: 100%; border-radius: 6px; font-weight: bold; }
        div[data-testid="metric-container"] { background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        </style>
        """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.title("🎓 Öğrenci AI")
        st.markdown("---")

        st.subheader("⚙️ AI Ayarları")
        provider = st.selectbox("Sağlayıcı", ["Ollama", "OpenAI", "Anthropic", "Google"])

        api_key = None
        model_name = "llama3.2"

        if provider == "Ollama":
            model_name = st.text_input("Model Adı", value="llama3.2")
            is_connected = st.session_state.ai.check_connection()
            status_color = "green" if is_connected else "red"
            status_text = "Aktif" if is_connected else "Pasif"
            st.markdown(f"Durum: :{status_color}[{status_text}]")

        elif provider == "OpenAI":
            api_key = st.text_input("API Anahtarı", type="password")
            model_name = st.selectbox("Model", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])

        elif provider == "Anthropic":
            api_key = st.text_input("API Anahtarı", type="password")
            model_name = st.selectbox("Model", ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"])

        elif provider == "Google":
            api_key = st.text_input("API Anahtarı", type="password")
            model_name = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro"])

        st.session_state.ai.configure(provider, model_name, api_key)

        st.markdown("---")
        return st.radio("Navigasyon", ["Kontrol Paneli", "Yeni Öğrenci", "Veri Girişi", "AI Analiz"])


def render_dashboard():
    st.header("📊 Yönetim Paneli")
    students = st.session_state.manager.get_all_students()

    if not students:
        st.info("Sistemde kayıtlı öğrenci yok. Lütfen 'Yeni Öğrenci' menüsünden ekleme yapın.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Öğrenci", len(students))

    total_grades = sum(len(s.grades) for s in students)
    col2.metric("Toplam Veri Noktası", total_grades)

    all_scores = [g.score for s in students for g in s.grades]
    global_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    col3.metric("Genel Başarı Ortalaması", f"{global_avg:.1f}")

    st.subheader("Öğrenci Listesi")
    data = []
    for s in students:
        avg = sum(g.score for g in s.grades) / len(s.grades) if s.grades else 0
        last_analysis = s.ai_insights[-1].date if s.ai_insights else "-"
        data.append({
            "ID": s.id,
            "Ad Soyad": s.name,
            "Sınıf": s.class_name,
            "Ortalama": f"{avg:.1f}",
            "Son Analiz": last_analysis
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_new_student_form():
    st.header("👤 Yeni Öğrenci Kaydı")
    with st.form("new_student_form"):
        col1, col2 = st.columns(2)
        student_id = col1.text_input("Öğrenci Numarası (ID)")
        class_name = col2.text_input("Sınıf / Şube")
        full_name = st.text_input("Ad Soyad")

        if st.form_submit_button("Öğrenciyi Kaydet"):
            if not student_id or not full_name:
                st.error("Öğrenci ID ve İsim alanları zorunludur.")
                return

            if st.session_state.manager.load_student(student_id):
                st.error("Bu ID ile kayıtlı bir öğrenci zaten mevcut.")
                return

            new_student = Student(id=student_id, name=full_name, class_name=class_name)
            st.session_state.manager.save_student(new_student)
            st.success(f"{full_name} başarıyla sisteme eklendi.")
            time.sleep(1)
            st.rerun()


def render_data_entry():
    st.header("📝 Veri Giriş Portalı")
    students = st.session_state.manager.get_all_students()

    if not students:
        st.warning("Veri girilecek öğrenci bulunamadı.")
        return

    student_options = [f"{s.id} - {s.name}" for s in students]
    selected_option = st.selectbox("Öğrenci Seçin", student_options)
    student_id = selected_option.split(" - ")[0]
    student = st.session_state.manager.load_student(student_id)

    tab1, tab2 = st.tabs(["Not Ekle", "Davranış Notu Ekle"])

    with tab1:
        with st.form("grade_form"):
            subject = st.text_input("Ders Adı")
            score = st.number_input("Not", min_value=0, max_value=100, step=1)
            if st.form_submit_button("Notu Kaydet"):
                student.grades.append(Grade(subject=subject, score=score))
                st.session_state.manager.save_student(student)
                st.success("Not başarıyla eklendi.")

    with tab2:
        with st.form("behavior_form"):
            note = st.text_area("Gözlem Notu")
            note_type = st.selectbox("Tür", ["neutral", "positive", "negative"], format_func=lambda x:
            {"neutral": "Nötr", "positive": "Olumlu", "negative": "Olumsuz"}[x])
            if st.form_submit_button("Gözlemi Kaydet"):
                student.behavior_notes.append(BehaviorNote(note=note, type=note_type))
                st.session_state.manager.save_student(student)
                st.success("Davranış kaydı eklendi.")


def render_analysis():
    st.header(f"🤖 AI Analiz Motoru ({st.session_state.ai.provider})")
    students = st.session_state.manager.get_all_students()

    if not students:
        st.warning("Analiz edilecek öğrenci yok.")
        return

    student_options = [f"{s.id} - {s.name}" for s in students]
    selected_option = st.selectbox("Analiz İçin Öğrenci Seçin", student_options)
    student_id = selected_option.split(" - ")[0]
    student = st.session_state.manager.load_student(student_id)

    col1, col2 = st.columns([1, 3])

    with col1:
        st.info(f"**Kayıtlar:**\n\nNotlar: {len(student.grades)}\nGözlemler: {len(student.behavior_notes)}")
        start_analysis = st.button("Analizi Başlat ✨", type="primary")

    with col2:
        if start_analysis:
            if st.session_state.ai.provider != "Ollama" and not st.session_state.ai.api_key:
                st.error("Seçilen sağlayıcı için API Anahtarı gereklidir.")
                return

            prompt = st.session_state.ai.prepare_prompt(student)
            system_prompt = (
                "Sen uzman bir eğitim danışmanı ve pedagogsun. Sana verilen öğrenci verilerini analiz et. "
                "Yanıtını Markdown formatında şu başlıklarla yapılandır: "
                "1. Yönetici Özeti, 2. Akademik Analiz, 3. Davranışsal İçgörüler, 4. Öneriler. "
                "Dilin yapıcı, profesyonel ve motive edici olsun. Çıktı dili Türkçe olsun."
            )

            st.markdown("### Analiz Raporu")
            response_container = st.container(border=True)
            stream_generator = st.session_state.ai.generate_stream(prompt, system_prompt)
            full_response = response_container.write_stream(stream_generator)

            insight = AIInsight(analysis=str(full_response), model=st.session_state.ai.model)
            student.ai_insights.append(insight)
            st.session_state.manager.save_student(student)
            st.toast("Analiz öğrenci profiline kaydedildi.", icon="✅")

            # PDF İndirme Butonu (Analiz bittikten sonra görünür)
            pdf_data = create_pdf_report(student, str(full_response))
            st.download_button(
                label="📄 Raporu PDF Olarak İndir",
                data=pdf_data,
                file_name=f"Rapor_{student.name}_{student.id}.pdf",
                mime="application/pdf"
            )

        elif student.ai_insights:
            st.markdown("### Geçmiş Analizler")
            latest = student.ai_insights[-1]
            with st.container(border=True):
                st.caption(f"Tarih: {latest.date} | Model: {latest.model}")
                st.markdown(latest.analysis)

                # Geçmiş rapor için PDF butonu
                pdf_data = create_pdf_report(student, latest.analysis)
                st.download_button(
                    label="📄 Bu Raporu İndir",
                    data=pdf_data,
                    file_name=f"GecmisRapor_{student.name}.pdf",
                    mime="application/pdf",
                    key="history_pdf"
                )


def main():
    init_session()
    inject_custom_css()
    page = render_sidebar()

    if page == "Kontrol Paneli":
        render_dashboard()
    elif page == "Yeni Öğrenci":
        render_new_student_form()
    elif page == "Veri Girişi":
        render_data_entry()
    elif page == "AI Analiz":
        render_analysis()


if __name__ == "__main__":
    main()