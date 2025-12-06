import streamlit as st
import pandas as pd
import json
import time
from student_ai_v2 import StudentManager, AIService, Student, Grade, BehaviorNote

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Ollama Student AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS İLE MODERN GÖRÜNÜM ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE (Önbellek) ---
if 'manager' not in st.session_state:
    st.session_state.manager = StudentManager()
if 'ai' not in st.session_state:
    st.session_state.ai = AIService()


# --- YARDIMCI FONKSİYONLAR ---
def get_ai_stream(prompt, system_prompt):
    """Ollama yanıtını Streamlit için generator'a dönüştürür"""
    import requests
    from student_ai_v2 import Config

    payload = {
        "model": st.session_state.ai.model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": True,
        "options": {"temperature": 0.3}
    }

    try:
        with requests.post(f"{Config.OLLAMA_URL}/api/generate", json=payload, stream=True, timeout=120) as r:
            for line in r.iter_lines():
                if line:
                    body = json.loads(line)
                    token = body.get('response', '')
                    yield token
    except Exception as e:
        yield f"Hata: {str(e)}"


# --- YAN MENÜ ---
with st.sidebar:
    st.image("https://ollama.com/public/ollama.png", width=50)
    st.title("Öğrenci Analiz")
    st.markdown("---")

    menu = st.radio(
        "Menü",
        ["📊 Dashboard", "➕ Yeni Öğrenci", "📝 Veri Girişi", "🤖 AI Analiz"]
    )

    st.markdown("---")

    # Bağlantı Durumu
    if st.session_state.ai.is_connected:
        st.success(f"🟢 Ollama Aktif\nModel: {st.session_state.ai.model}")
    else:
        st.error("🔴 Ollama Kapalı")
        if st.button("Tekrar Dene"):
            st.rerun()

# --- SAYFA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("🎓 Genel Bakış")

    students = st.session_state.manager.get_all_students()

    if not students:
        st.info("Henüz sisteme kayıtlı öğrenci yok. Yan menüden ekleyebilirsiniz.")
    else:
        # İstatistik Kartları
        col1, col2, col3 = st.columns(3)

        total_students = len(students)
        total_grades = sum([len(s.grades) for s in students])

        # Basit bir ortalama hesaplama
        all_scores = [g.score for s in students for g in s.grades]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

        col1.metric("Toplam Öğrenci", total_students)
        col2.metric("Toplam Girilen Not", total_grades)
        col3.metric("Genel Not Ortalaması", f"{avg_score:.1f}")

        st.markdown("### 📋 Öğrenci Listesi")

        # Veriyi Tablo İçin Hazırla
        data = []
        for s in students:
            s_avg = sum([g.score for g in s.grades]) / len(s.grades) if s.grades else 0
            last_analysis = s.ai_insights[-1].date if s.ai_insights else "Yok"
            data.append({
                "ID": s.id,
                "İsim": s.name,
                "Sınıf": s.class_name,
                "Ortalama": f"{s_avg:.1f}",
                "Not Sayısı": len(s.grades),
                "Son Analiz": last_analysis
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- SAYFA: YENİ ÖĞRENCİ ---
elif menu == "➕ Yeni Öğrenci":
    st.title("👤 Yeni Öğrenci Ekle")

    with st.form("new_student_form"):
        col1, col2 = st.columns(2)
        sid = col1.text_input("Öğrenci Numarası (ID)")
        cls_name = col2.text_input("Sınıf")
        name = st.text_input("Ad Soyad")

        submit = st.form_submit_button("Kaydet")

        if submit:
            if not sid or not name or not cls_name:
                st.warning("Lütfen tüm alanları doldurun!")
            elif st.session_state.manager.load_student(sid):
                st.error("Bu ID ile kayıtlı bir öğrenci zaten var!")
            else:
                new_s = Student(id=sid, name=name, class_name=cls_name)
                st.session_state.manager.save_student(new_s)
                st.success(f"{name} başarıyla sisteme eklendi!")
                time.sleep(1)
                st.rerun()

# --- SAYFA: VERİ GİRİŞİ ---
elif menu == "📝 Veri Girişi":
    st.title("📝 Not ve Davranış Girişi")

    students = st.session_state.manager.get_all_students()
    student_names = [f"{s.id} - {s.name}" for s in students]

    if not students:
        st.warning("Önce öğrenci eklemelisiniz.")
    else:
        selected_s_str = st.selectbox("Öğrenci Seçin", student_names)
        selected_id = selected_s_str.split(" - ")[0]
        student = st.session_state.manager.load_student(selected_id)

        tab1, tab2 = st.tabs(["📚 Not Ekle", "🧠 Davranış Ekle"])

        with tab1:
            with st.form("grade_form"):
                subject = st.text_input("Ders Adı (Örn: Matematik)")
                score = st.number_input("Not", min_value=0, max_value=100, step=1)
                if st.form_submit_button("Notu Kaydet"):
                    student.grades.append(Grade(subject=subject, score=score))
                    st.session_state.manager.save_student(student)
                    st.success("Not eklendi!")

        with tab2:
            with st.form("behavior_form"):
                note = st.text_area("Gözlem Notu")
                b_type = st.selectbox("Tür", ["neutral", "positive", "negative"])
                if st.form_submit_button("Gözlem Kaydet"):
                    from student_ai_v2 import BehaviorNote  # Tekrar import gerekebilir scope için

                    student.behavior_notes.append(BehaviorNote(note=note, type=b_type))
                    st.session_state.manager.save_student(student)
                    st.success("Davranış notu eklendi!")

# --- SAYFA: AI ANALİZ ---
elif menu == "🤖 AI Analiz":
    st.title("🤖 Yapay Zeka Analizi")

    students = st.session_state.manager.get_all_students()
    student_names = [f"{s.id} - {s.name}" for s in students]

    if not students:
        st.warning("Listelenecek öğrenci yok.")
    else:
        col1, col2 = st.columns([1, 3])

        with col1:
            selected_s_str = st.radio("Öğrenci Seç", student_names)
            selected_id = selected_s_str.split(" - ")[0]
            student = st.session_state.manager.load_student(selected_id)

            st.info(f"**{student.name}**\n\nNot Sayısı: {len(student.grades)}\nGözlem: {len(student.behavior_notes)}")

            analyze_btn = st.button("Analizi Başlat ✨", type="primary")

        with col2:
            if analyze_btn:
                if not st.session_state.ai.is_connected:
                    st.error("Ollama bağlantısı yok! Lütfen 'ollama serve' komutunu çalıştırın.")
                else:
                    # Prompt Hazırlama
                    student_data = st.session_state.ai.prepare_student_prompt(student)
                    system_prompt = "Sen uzman bir pedagogsun. Öğrenci verilerini analiz et, Markdown formatında, yapıcı bir dille rapor sun."
                    full_prompt = f"Veriler:\n{student_data}"

                    # Streaming Alanı
                    st.markdown("### 🧠 AI Raporu")
                    report_container = st.container(border=True)

                    # Streamlit'in kendi streaming fonksiyonu
                    stream = get_ai_stream(full_prompt, system_prompt)
                    response_text = report_container.write_stream(stream)

                    # Kaydetme
                    from student_ai_v2 import AIInsight

                    student.ai_insights.append(AIInsight(analysis=response_text, model=st.session_state.ai.model))
                    st.session_state.manager.save_student(student)
                    st.toast("Analiz kaydedildi!", icon="✅")

            # Eski raporları göster
            elif student.ai_insights:
                st.markdown("### 🕒 Son Analiz")
                last_insight = student.ai_insights[-1]
                with st.container(border=True):
                    st.markdown(f"_{last_insight.date} - Model: {last_insight.model}_")
                    st.markdown(last_insight.analysis)
            else:
                st.markdown("Analysis başlatmak için butona tıklayın.")