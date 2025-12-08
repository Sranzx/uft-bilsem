import os
import streamlit
import PyInstaller.__main__

# 1. Streamlit'in bilgisayarındaki yerini otomatik bul
streamlit_dir = os.path.dirname(streamlit.__file__)
static_path = os.path.join(streamlit_dir, "static")

print(f"Streamlit şurada bulundu: {streamlit_dir}")
print("Derleme işlemi başlıyor...")

# 2. PyInstaller'ı Python içinden çalıştır
PyInstaller.__main__.run([
    'run_app.py',  # Başlatıcı dosyamız
    '--onefile',  # Tek parça exe olsun
    '--name=UFT-BILSEM',  # Exe'nin adı
    '--clean',  # Eski önbelleği temizle
    '--noconsole',  # Siyah pencereyi kapat (Test için --console yapabilirsin)

    # KRİTİK KISIM: Streamlit'in static dosyalarını exe içine kopyala
    f'--add-data={static_path};streamlit/static',

    # Senin ana uygulamanı kopyala
    '--add-data=app.py;.',

    # Gerekli meta verileri kopyala
    '--copy-metadata=streamlit',
    '--copy-metadata=google-generativeai',  # Eğer Gemini kullanıyorsan bu da gerekebilir
])