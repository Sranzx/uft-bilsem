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
# GLOBAL DEĞİŞKENLER VE BAŞLANGIÇ AYARLARI
# ---------------------------------------------------------
if 'GLOBAL_LAST_STUDENT' not in globals():
    globals()['GLOBAL_LAST_STUDENT'] = None

manager = StudentManager()

# Sayfa Ayarları
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
# 1. BEKÇİ FONKSİYONU (WATCHDOG)
# ---------------------------------------------------------
def browser_watcher():
    """Tarayıcı kapanırsa verileri otomatik kaydeder."""
    time.sleep(5)
    print("👀 Watchdog aktif...")
    
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
                    print("🔻 Oturum kapandı. Kayıt yapılıyor...")
                    s_to_save = globals()['GLOBAL_LAST_STUDENT']
                    if s_to_save:
                        try:
                            manager.save_student(s_to_save)
                            print(f"✅ {s_to_save.name} kaydedildi.")
                        except:
                            pass
                    os._exit(0)
        except:
            pass
        time.sleep(2)

# ---------------------------------------------------------
# 2. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
def get_ai_response(model, prompt, temperature):
    url = "http://localhost:11434/api/generate"
    data = {"model": model, "prompt": prompt, "temperature": temperature, "stream": True}
    try:
        with requests.post(url, json=data, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    body = json.loads(line)
                    yield body.get("response", "")
                    if body.get("done", False): break
    except Exception as e:
        yield f"⚠️ Hata: {str(e)}"

def create_student_object_from_session():
    """Session State'deki verileri Student nesnesine çevirir."""
    s_data = st.session_state.student_data
    grade_objects = [Grade(subject=k, score=v) for k, v in s_data['notes'].items()]
    
    return Student(
        id=s_data['id'],
        name=s_data['name'],
        class_name=s_data['class'],
        grades=grade_objects,
        behavior_notes=[], # Basitleştirilmiş
        file_content=s_data['file_content']
    )

def sync_global_data():
    """Veriyi global değişkene yedekler."""
    if st.session_state.get('student_data'):
        current = create_student_object_from_session()
        # Davranışları behavior_notes değil string listesi olarak tutuyoruz şimdilik
        # Kaydederken Student sınıfı behavior_notes bekler ama biz string listesini 
        # prompt'ta kullanıyoruz. Veritabanı için behavior'ları Student nesnesine eklemek gerekebilir.
        # Basitlik için şu anlık sadece ana verileri senkronize ediyoruz.
        globals()['GLOBAL_LAST_STUDENT'] = current

# Watchdog Başlat
if 'watcher_thread_started' not in st.session_state:
    t = threading.Thread(target=browser_watcher, daemon=True)
    t.start()
    st.session_state.watcher_thread_started = True

# ---------------------------------------------------------
# 3. SESSION STATE (HAFIZA) BAŞLATMA
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

# ---------------------------------------------------------
# 4. SIDEBAR (YAN MENÜ) - KRİTİK DÜZELTME
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://ollama.com/public/ollama.png", width=50)
    st.title("📂 Kayıtlı Öğrenciler")

    # 1. Veritabanındaki öğrencileri çek
    saved_students = manager.get_all_students()
    
    # 2. İsimleri ve Nesneleri Eşleştiren Bir Sözlük Yap (Hata Önleyici)
    # Format: "Ahmet Yılmaz (5-A)" -> Student Nesnesi
    student_map = {f"{s.name} ({s.class_name})": s for s in saved_students}
    
    # 3. Listeyi Hazırla
    options = ["➕ Yeni Öğrenci Ekle"] + list(student_map.keys())
    
    # 4. Seçim Kutusu
    # Eğer şu an seçili bir öğrenci varsa, index'i korumaya çalış
    index = 0
    if st.session_state.current_student_id:
        # Şu anki ID'ye sahip öğrencinin adını bul
        current_obj = next((s for s in saved_students if s.id == st.session_state.current_student_id), None)
        if current_obj:
            key = f"{current_obj.name} ({current_obj.class_name})"
            if key in options:
                index = options.index(key)

    selected_option = st.selectbox("Öğrenci Seçin", options, index=index)

    # 5. SEÇİM MANTIĞI
    if selected_option == "➕ Yeni Öğrenci Ekle":
        # Eğer daha önce bir öğrenci seçiliyse ve şimdi "Yeni" dendi ise formu temizle
        if st.session_state.current_student_id is not None:
            st.session_state.student_data = {
                'id': str(uuid.uuid4()),
                'name': '', 'class': '', 'notes': {},
                'behavior': [], 'observation': '', 'file_content': ''
            }
            st.session_state.current_student_id = None
            st.rerun() # Sayfayı yenile ki form boşalsın
            
    else:
        # Mevcut bir öğrenci seçildi
        student_obj = student_map[selected_option]
        
        # Eğer seçilen öğrenci zaten ekranda değilse yükle
        if st.session_state.current_student_id != student_obj.id:
            notes_dict = {g.subject: g.score for g in student_obj.grades}
            
            st.session_state.student_data = {
                'id': student_obj.id,
                'name': student_obj.name,
                'class': student_obj.class_name,
                'notes': notes_dict,
                'behavior': [], # Davranış listesini veritabanından çekmek istersen burayı güncelle
                'observation': '',
                'file_content': student_obj.file_content
            }
            # Ders listesini güncelle
            if notes_dict:
                st.session_state.course_list = list(notes_dict.keys())
                
            st.session_state.current_student_id = student_obj.id
            st.rerun() # Sayfayı yenile ki veriler forma dolsun

    st.markdown("---")
    
    # AI Servis Ayarları
    ai_service = AIService()
    if ai_service.check_connection():
        st.success("🟢 Ollama Bağlı")
        models = ai_service.get_ollama_models() or ["llama3.2"]
        model = st.selectbox("Model", models)
        ai_service.configure("Ollama", model)
    else:
        st.error("🔴 Bağlantı Yok")
        model = st.selectbox("Model", ["Local"], disabled=True)
        
    temp = st.slider("Yaratıcılık", 0.0, 1.0, 0.7)
    if st.button("🔄 Yenile"): st.rerun()
    
    st.markdown("---")
    if st.button("🚪 KAYDET VE ÇIK", type="primary"):
        sync_global_data()
        s = globals()['GLOBAL_LAST_STUDENT']
        if s: manager.save_student(s)
        st.success("Kapatılıyor...")
        time.sleep(1)
        os._exit(0)

# ---------------------------------------------------------
# 5. ANA EKRAN
# ---------------------------------------------------------
col1, col2 = st.columns([3, 1])
with col1: st.title("🎓 Öğrenci Performans Analisti")
with col2: st.markdown(f"**Tarih:** {datetime.now().strftime('%d.%m.%Y')}")

st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📝 Veri Girişi", "📊 Grafik", "🤖 AI Analizi"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.student_data['name'] = st.text_input("Adı Soyadı", value=st.session_state.student_data['name'])
        st.session_state.student_data['class'] = st.text_input("Sınıfı", value=st.session_state.student_data['class'])
    with c2:
        beh_opts = ["Derse Katılım Yüksek", "Ödevlerini Düzenli Yapar", "Dikkat Dağınıklığı", "Arkadaşlarıyla Uyumlu"]
        st.session_state.student_data['behavior'] = st.multiselect("Davranışlar", beh_opts, default=st.session_state.student_data['behavior'])

    st.subheader("📚 Notlar")
    # Ders Yönetimi
    with st.expander("⚙️ Ders Ekle/Çıkar"):
        ca, cd = st.columns(2)
        new_c = ca.text_input("Ders Ekle")
        if ca.button("Ekle") and new_c:
            st.session_state.course_list.append(new_c)
            st.rerun()
        
        del_c = cd.selectbox("Ders Sil", st.session_state.course_list)
        if cd.button("Sil"):
            st.session_state.course_list.remove(del_c)
            st.session_state.student_data['notes'].pop(del_c, None)
            st.rerun()

    # Not Inputları
    cols = st.columns(4)
    temp_notes = {}
    for i, course in enumerate(st.session_state.course_list):
        with cols[i % 4]:
            val = st.number_input(f"{course}", 0, 100, step=5, key=f"g_{course}", 
                                  value=st.session_state.student_data['notes'].get(course, 0))
            temp_notes[course] = val
    st.session_state.student_data['notes'] = temp_notes

    # Dosya
    st.markdown("---")
    st.subheader("📂 Ürün Dosyası")
    uploaded = st.file_uploader("Dosya Yükle", type=['pdf', 'docx', 'txt'])
    if uploaded:
        with st.spinner("Okunuyor..."):
            text = FileHandler.extract_text_from_file(uploaded)
            st.session_state.student_data['file_content'] = text
            st.success("Yüklendi!")

    st.session_state.student_data['observation'] = st.text_area("Öğretmen Notu", value=st.session_state.student_data['observation'])
    
    sync_global_data()
    
    # KAYDET BUTONU - DÜZELTİLMİŞ
    if st.button("💾 VERİLERİ KAYDET", type="primary"):
        if not st.session_state.student_data['name']:
            st.error("İsim girmelisiniz!")
        else:
            # 1. Nesneyi oluştur
            s_obj = create_student_object_from_session()
            
            # 2. Davranışları string listesinden alıp (basitçe) ekleyelim ki kaybolmasın
            # İdeal dünyada behavior_notes sınıfını kullanmalıyız ama hızlı çözüm için:
            # (Davranışları notlara eklemiyoruz, sadece prompt için session state'de tutuyoruz,
            # veritabanına kaydetmek için Student sınıfına behavior_list diye alan eklemek en doğrusu olurdu.
            # Şimdilik ana veriler kaydediliyor.)
            
            # 3. Diske Yaz
            manager.save_student(s_obj)
            
            st.success(f"{s_obj.name} kaydedildi!")
            
            # 4. Global değişkeni güncelle
            globals()['GLOBAL_LAST_STUDENT'] = s_obj
            
            # 5. LİSTENİN GÜNCELLENMESİ İÇİN SAYFAYI YENİLE (KRİTİK NOKTA)
            time.sleep(0.5)
            st.rerun()

with tab2:
    if st.session_state.student_data['notes']:
        df = pd.DataFrame(list(st.session_state.student_data['notes'].items()), columns=["Ders", "Puan"])
        st.bar_chart(df.set_index("Ders"))
    else:
        st.info("Not yok.")

with tab3:
    if st.button("Analiz Et", type="primary"):
        s_data = st.session_state.student_data
        prompt = f"""
        ÖĞRENCİ: {s_data['name']} ({s_data['class']})
        NOTLAR: {json.dumps(s_data['notes'], ensure_ascii=False)}
        DAVRANIŞLAR: {', '.join(s_data['behavior'])}
        DOSYA: {s_data.get('file_content', '')[:1000]}...
        GÖREV: Analiz et ve 3 öneri ver.
        """
        cont = st.empty()
        full = ""
        for chunk in get_ai_response(model, prompt, temp):
            full += chunk
            cont.markdown(full + "▌")
        cont.markdown(full)
