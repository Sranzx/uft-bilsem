import os
import streamlit
import PyInstaller.__main__

# 1. Streamlit'in dosya yollarını bul
streamlit_dir = os.path.dirname(streamlit.__file__)
static_path = os.path.join(streamlit_dir, "static")

# İkon dosyası (Varsa)
icon_file = "uft.ico"

print(f"📍 Streamlit dizini: {streamlit_dir}")

# Komut listesini hazırlıyoruz
commands = [
    'run_app.py',                       # Başlatıcı dosya
    '--onefile',                        # Tek dosya
    '--name=UFT-BILSEM',                # Exe'nin adı
    '--clean',                          # Önbelleği temizle
    '--noconsole',                      # Konsol penceresini gizle (Debug için silinebilir)
    
    # --- 1. HATA ÇÖZÜMÜ: EKSİK DOSYALAR (DATA) ---
    # app.py VE student_streamable.py dosyalarının ikisini de ekliyoruz
    '--add-data=app.py;.',
    '--add-data=student_streamable.py;.', 
    
    # --- 2. HATA ÇÖZÜMÜ: ARAYÜZ DOSYALARI ---
    # Streamlit static dosyalarını ekliyoruz
    f'--add-data={static_path};streamlit/static',

    # --- 3. HATA ÇÖZÜMÜ: GİZLİ MODÜLLER (HIDDEN IMPORTS) ---
    # PyInstaller'ın göremediği Streamlit modülleri
    '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
    '--hidden-import=streamlit.runtime.scriptrunner.script_runner',
    '--hidden-import=streamlit.web.cli',
    '--hidden-import=streamlit.runtime.media_file_manager',
    '--hidden-import=streamlit.runtime.memory_media_file_manager',
    
    # Diğer gerekli kütüphaneler
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=requests',
    '--hidden-import=docx',
    '--hidden-import=PyPDF2',
    
    # --- METADATA KOPYALAMA ---
    # Versiyon bilgileri için şart
    '--copy-metadata=streamlit',
    '--copy-metadata=google-generativeai',
    '--copy-metadata=tqdm',
    '--copy-metadata=regex',
    '--copy-metadata=requests',
    '--copy-metadata=packaging',
]

# Eğer ikon varsa komutlara ekle
if os.path.exists(icon_file):
    print(f"✅ İkon eklendi: {icon_file}")
    commands.insert(3, f'--icon={icon_file}')
else:
    print("⚠️ İkon bulunamadı, varsayılan ikon kullanılacak.")

print("🚀 Derleme işlemi başlıyor...")

# 2. PyInstaller'ı çalıştır
PyInstaller.__main__.run(commands)import os
import streamlit
import PyInstaller.__main__

# 1. Streamlit'in dosya yollarını bul
streamlit_dir = os.path.dirname(streamlit.__file__)
static_path = os.path.join(streamlit_dir, "static")

# İkon dosyası (Varsa)
icon_file = "uft.ico"

print(f"📍 Streamlit dizini: {streamlit_dir}")

# Komut listesini hazırlıyoruz
commands = [
    'run_app.py',                       # Başlatıcı dosya
    '--onefile',                        # Tek dosya
    '--name=UFT-BILSEM',                # Exe'nin adı
    '--clean',                          # Önbelleği temizle
    '--noconsole',                      # Konsol penceresini gizle (Debug için silinebilir)
    
    # --- 1. HATA ÇÖZÜMÜ: EKSİK DOSYALAR (DATA) ---
    # app.py VE student_streamable.py dosyalarının ikisini de ekliyoruz
    '--add-data=app.py;.',
    '--add-data=student_streamable.py;.', 
    
    # --- 2. HATA ÇÖZÜMÜ: ARAYÜZ DOSYALARI ---
    # Streamlit static dosyalarını ekliyoruz
    f'--add-data={static_path};streamlit/static',

    # --- 3. HATA ÇÖZÜMÜ: GİZLİ MODÜLLER (HIDDEN IMPORTS) ---
    # PyInstaller'ın göremediği Streamlit modülleri
    '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
    '--hidden-import=streamlit.runtime.scriptrunner.script_runner',
    '--hidden-import=streamlit.web.cli',
    '--hidden-import=streamlit.runtime.media_file_manager',
    '--hidden-import=streamlit.runtime.memory_media_file_manager',
    
    # Diğer gerekli kütüphaneler
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=requests',
    '--hidden-import=docx',
    '--hidden-import=PyPDF2',
    
    # --- METADATA KOPYALAMA ---
    # Versiyon bilgileri için şart
    '--copy-metadata=streamlit',
    '--copy-metadata=google-generativeai',
    '--copy-metadata=tqdm',
    '--copy-metadata=regex',
    '--copy-metadata=requests',
    '--copy-metadata=packaging',
]

# Eğer ikon varsa komutlara ekle
if os.path.exists(icon_file):
    print(f"✅ İkon eklendi: {icon_file}")
    commands.insert(3, f'--icon={icon_file}')
else:
    print("⚠️ İkon bulunamadı, varsayılan ikon kullanılacak.")

print("🚀 Derleme işlemi başlıyor...")

# 2. PyInstaller'ı çalıştır
PyInstaller.__main__.run(commands)
