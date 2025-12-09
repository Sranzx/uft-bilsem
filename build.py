import os
import streamlit
import PyInstaller.__main__

# 1. Streamlit'in dosya yollarını bul
streamlit_dir = os.path.dirname(streamlit.__file__)
static_path = os.path.join(streamlit_dir, "static")

# İkon dosyasının adı (build.py ile aynı klasörde olmalı)
icon_file = "uft.ico"

print(f"Streamlit şurada bulundu: {streamlit_dir}")

# İkon kontrolü (Dosya yoksa hata vermemesi için uyarı sistemi)
if os.path.exists(icon_file):
    print(f"✅ İkon dosyası bulundu: {icon_file}")
    icon_command = f'--icon={icon_file}'
else:
    print(f"⚠️ UYARI: '{icon_file}' bulunamadı! Varsayılan ikon kullanılacak.")
    icon_command = None

print("Derleme işlemi başlıyor...")

# Komut listesini hazırlıyoruz
commands = [
    'run_app.py',                       # Başlatıcı dosya
    '--onefile',                        # Tek dosya
    '--name=UFT-BILSEM',                # Exe'nin adı
    '--clean',                          # Önbelleği temizle
    '--noconsole',                      # Konsol penceresini gizle
    
    # --- EKSİK MODÜLLER (Hidden Imports) ---
    '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
    '--hidden-import=streamlit.runtime.scriptrunner.script_runner',
    '--hidden-import=streamlit.web.cli',
    '--hidden-import=streamlit.runtime.media_file_manager',
    '--hidden-import=streamlit.runtime.memory_media_file_manager',
    
    # --- VERİ DOSYALARI ---
    f'--add-data={static_path};streamlit/static',  # Streamlit arayüzü
    '--add-data=app.py;.',                         # Ana uygulama
    
    # --- METADATA ---
    '--copy-metadata=streamlit',
    '--copy-metadata=google-generativeai',
    '--copy-metadata=pandas',
    '--copy-metadata=numpy',
]

# Eğer ikon varsa komutlara ekle
if icon_command:
    commands.insert(3, icon_command)

# 2. PyInstaller'ı çalıştır
PyInstaller.__main__.run(commands)
