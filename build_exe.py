import PyInstaller.__main__
import os
import shutil

# --- AYARLAR ---
APP_NAME = "OllamaStudentAnalyst"  # Oluşacak uygulamanın adı
MAIN_SCRIPT = "run_app.py"  # Başlatıcı dosya
INCLUDED_FILE = "app.py"  # Streamlit ana dosyası
# ----------------

# Temizlik: Eski derleme klasörleri varsa sil
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

print(f"🚀 {APP_NAME} paketleniyor... Lütfen bekleyin.")

PyInstaller.__main__.run([
    MAIN_SCRIPT,
    f'--name={APP_NAME}',
    '--onefile',  # Tek bir .exe dosyası üret
    '--clean',  # Önbelleği temizle
    # '--windowed',                     # Hata ayıklamak için bu satırı yorumda tutun (konsol görünür).
    # Hata yoksa bu satırı aktifleştirip siyah ekranı gizleyebilirsiniz.

    # Dosyaları Dahil Et (Kaynak;Hedef)
    f'--add-data={INCLUDED_FILE};.',

    # Streamlit ve bağımlılıklarını topla (Otomatik hooklar)
    '--collect-all=streamlit',
    '--collect-all=altair',
    '--collect-all=pandas',
    '--collect-all=rich',
    '--collect-all=google.generativeai',  # Eğer kullanılıyorsa

    # Görünmeyen importları ekle
    '--hidden-import=streamlit',
    '--hidden-import=pandas',
])

print("\n✅ İşlem Tamamlandı!")
print(f"📂 Uygulamanız hazır: {os.path.join(os.getcwd(), 'dist', APP_NAME + '.exe')}")