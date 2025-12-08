import os
import streamlit
import PyInstaller.__main__

# 1. Streamlit'in dosya yollarını bul
streamlit_dir = os.path.dirname(streamlit.__file__)
static_path = os.path.join(streamlit_dir, "static")

# Config dosyasının yolu (genelde venv içinde olur)
config_path = os.path.join(streamlit_dir, "config.py")

print(f"Streamlit şurada bulundu: {streamlit_dir}")
print("Derleme işlemi başlıyor...")

# 2. PyInstaller komutlarını hazırla
PyInstaller.__main__.run([
    'run_app.py',                       # Başlatıcı dosya
    '--onefile',                        # Tek dosya
    '--name=UFT-BILSEM',                # İsim
    '--clean',                          # Önbelleği temizle
    '--noconsole',                      # Konsol penceresini gizle
    
    # --- KRİTİK EKLENTİLER (HATA ÇÖZÜMLERİ) ---
    # Eksik modülleri manuel olarak ekliyoruz:
    '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
    '--hidden-import=streamlit.runtime.scriptrunner.script_runner',
    '--hidden-import=streamlit.web.cli',
    '--hidden-import=streamlit.runtime.media_file_manager',
    '--hidden-import=streamlit.runtime.memory_media_file_manager',
    
    # Dosya yolları (Data ekleme):
    f'--add-data={static_path};streamlit/static',  # Arayüz dosyaları
    '--add-data=app.py;.',                         # Senin kodun
    
    # Metadata kopyalama (Versiyon bilgileri için şart):
    '--copy-metadata=streamlit',
    '--copy-metadata=google-generativeai',
    '--copy-metadata=pandas',
    '--copy-metadata=numpy',
])
