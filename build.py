import os
import streamlit
import PyInstaller.__main__

# 1. Streamlit'in dosya yollarını bul
streamlit_dir = os.path.dirname(streamlit.__file__)
static_path = os.path.join(streamlit_dir, "static")

# İkon dosyası (Varsa)
icon_file = "uft.ico"

print(f"📍 Streamlit dizini: {streamlit_dir}")

# İşletim sistemi ayracı (Windows için ; Mac/Linux için :)
sep = os.pathsep

# Komut listesini hazırlıyoruz
commands = [
    'run_app.py',                       # Başlatıcı dosya
    '--onefile',                        # Tek dosya
    '--name=UFT-BILSEM',                # Exe'nin adı
    '--clean',                          # Önbelleği temizle
    '--noconsole',                      # Konsol penceresini gizle
    
    # --- 1. EKSİK DOSYALAR (DATA) ---
    # Hem app.py hem de student_streamable.py dosyasını exe içine gömüyoruz
    f'--add-data=app.py{sep}.',
    f'--add-data=student_streamable.py{sep}.', 
    
    # --- 2. ARAYÜZ DOSYALARI ---
    # Streamlit static dosyalarını ekliyoruz (index.html hatasını çözer)
    f'--add-data={static_path}{sep}streamlit/static',

    # --- 3. GİZLİ MODÜLLER (HIDDEN IMPORTS) ---
    # PyInstaller'ın göremediği Streamlit ve diğer modüller
    '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
    '--hidden-import=streamlit.runtime.scriptrunner.script_runner',
    '--hidden-import=streamlit.web.cli',
    '--hidden-import=streamlit.runtime.media_file_manager',
    '--hidden-import=streamlit.runtime.memory_media_file_manager',
    
    # Sizin projenizin bağımlılıkları
    '--hidden-import=openai',
    '--hidden-import=anthropic',
    '--hidden-import=google.generativeai',
    '--hidden-import=docx',
    '--hidden-import=PyPDF2',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=requests',
    
    # --- METADATA KOPYALAMA ---
    # Versiyon bilgileri için şart
    '--copy-metadata=streamlit',
    '--copy-metadata=google-generativeai',
    '--copy-metadata=requests',
    '--copy-metadata=packaging',
    # regex paketini kaldırdım, eğer yukarıdaki pip install regex'i yaptıysanız
    # aşağıdaki satırın başındaki # işaretini kaldırabilirsiniz.
    # '--copy-metadata=regex', 
]

# Eğer ikon varsa komutlara ekle
if os.path.exists(icon_file):
    print(f"✅ İkon eklendi: {icon_file}")
    commands.insert(3, f'--icon={icon_file}')
else:
    print("⚠️ İkon bulunamadı, varsayılan ikon kullanılacak.")

print("🚀 Derleme işlemi başlıyor...")

# 2. PyInstaller'ı çalıştır
try:
    PyInstaller.__main__.run(commands)
    print("\n✅ İŞLEM BAŞARIYLA TAMAMLANDI!")
    print("Oluşan dosyayı 'dist' klasöründe bulabilirsiniz.")
except Exception as e:
    print(f"\n❌ BİR HATA OLUŞTU: {e}")
