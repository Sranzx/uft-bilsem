import os
import sys
import streamlit
import PyInstaller.__main__
from pathlib import Path


def build_executable():
    # 1. Streamlit'in dosya yollarını bul
    streamlit_dir = os.path.dirname(streamlit.__file__)
    static_path = os.path.join(streamlit_dir, "static")

    # Proje dizini
    project_dir = Path.cwd()

    # İkon dosyası (Varsa)
    icon_file = project_dir / "uft.ico"

    print(f"📍 Streamlit dizini: {streamlit_dir}")
    print(f"📍 Proje dizini: {project_dir}")

    # İşletim sistemi ayracı (Windows için ; Mac/Linux için :)
    sep = os.pathsep

    # Komut listesini hazırlıyoruz
    commands = [
        'run_app.py',  # Başlatıcı dosya
        '--onefile',  # Tek dosya
        '--name=UFT-BILSEM',  # Exe'nin adı
        '--clean',  # Önbelleği temizle
        '--noconfirm',  # Otomatik onay
        '--noconsole',  # Konsol penceresini gizle (production için)
        # '--console',  # Debug için konsolu açmak isterseniz bunu kullanın

        # --- 1. GEREKLİ DOSYALAR ---
        # Ana uygulama dosyalarını ekle
        f'--add-data={project_dir}/app.py{sep}.',
        f'--add-data={project_dir}/student_streamable.py{sep}.',

        # --- 2. ARAYÜZ DOSYALARI ---
        # Streamlit static dosyalarını ekliyoruz
        f'--add-data={static_path}{sep}streamlit/static',

        # --- 3. GİZLİ MODÜLLER (HIDDEN IMPORTS) ---
        # Streamlit için gerekli gizli importlar
        '--hidden-import=streamlit',
        '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
        '--hidden-import=streamlit.runtime.scriptrunner.script_runner',
        '--hidden-import=streamlit.web.cli',
        '--hidden-import=streamlit.runtime.media_file_manager',
        '--hidden-import=streamlit.runtime.memory_media_file_manager',
        '--hidden-import=streamlit.elements',
        '--hidden-import=streamlit.proto',
        '--hidden-import=streamlit.logger',
        '--hidden-import=streamlit.config',

        # Proje bağımlılıkları
        '--hidden-import=requests',
        '--hidden-import=PyPDF2',
        '--hidden-import=docx',
        '--hidden-import=python-docx',
        '--hidden-import=pandas',
        '--hidden-import=numpy',

        # JSON ve diğer temel modüller
        '--hidden-import=json',
        '--hidden-import=uuid',
        '--hidden-import=dataclasses',
        '--hidden-import=typing',

        # --- EXCLUDES (Boyut küçültme için) ---
        '--exclude-module=matplotlib',
        '--exclude-module=tkinter',
        '--exclude-module=unittest',
        '--exclude-module=pydoc',

        # --- METADATA ---
        '--copy-metadata=streamlit',
        '--copy-metadata=requests',
        '--copy-metadata=packaging',
    ]

    # Eğer ikon varsa komutlara ekle
    if icon_file.exists():
        print(f"✅ İkon eklendi: {icon_file}")
        commands.insert(5, f'--icon={icon_file}')  # 5. sıraya ekliyoruz
    else:
        print("⚠️ İkon bulunamadı, varsayılan ikon kullanılacak.")

    print("🚀 Derleme işlemi başlıyor...")
    print(f"Komutlar: {' '.join(commands[:3])} ... ({len(commands)} toplam parametre)")

    # 2. PyInstaller'ı çalıştır
    try:
        PyInstaller.__main__.run(commands)
        print("\n✅ İŞLEM BAŞARIYLA TAMAMLANDI!")
        print("Oluşan dosyayı 'dist' klasöründe bulabilirsiniz.")

        # Oluşan exe dosyasının bilgilerini göster
        exe_path = Path("dist") / "UFT-BILSEM.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📁 EXE Dosya Boyutu: {size_mb:.1f} MB")
            print(f"📍 Dosya Konumu: {exe_path.absolute()}")

    except Exception as e:
        print(f"\n❌ BİR HATA OLUŞTU: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_executable()
