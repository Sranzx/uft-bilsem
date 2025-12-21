import os
import sys
import streamlit
import PyInstaller.__main__
from pathlib import Path


def check_upx():
    """Check if UPX is available in PATH"""
    try:
        import subprocess
        result = subprocess.run(['upx', '--version'],
                                capture_output=True,
                                text=True,
                                timeout=5)
        if result.returncode == 0:
            print("✅ UPX bulundu, dosya sıkıştırma etkin")
            return True
        else:
            print("⚠️ UPX bulunamadı, dosya sıkıştırma devre dışı")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️ UPX bulunamadı, dosya sıkıştırma devre dışı")
        return False


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

    # UPX kontrolü
    use_upx = check_upx()

    # Komut listesini hazırlıyoruz
    commands = [
        'run_app.py',  # Başlatıcı dosya
        '--onefile',  # Tek dosya
        '--name=UFT-BILSEM',  # Exe'nin adı
        '--clean',  # Önbelleği temizle
        '--noconfirm',  # Otomatik onay
        '--noconsole',  # Konsol penceresini gizle (production için)

        # Performans optimizasyonu
        '--strip',  # Sembolleri kaldır
        '--log-level=WARN',  # Sadece uyarı ve hataları göster

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
        '--hidden-import=streamlit.elements.utils',
        '--hidden-import=streamlit.runtime.state',
        '--hidden-import=streamlit.runtime.secrets',
        '--hidden-import=streamlit.web.server.server_util',
        '--hidden-import=streamlit.web.server',
        '--hidden-import=streamlit.web.bootstrap',

        # Proje bağımlılıkları
        '--hidden-import=requests',
        '--hidden-import=PyPDF2',
        '--hidden-import=docx',
        '--hidden-import=python-docx',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=numpy.core._methods',
        '--hidden-import=numpy.lib.format',

        # JSON ve diğer temel modüller
        '--hidden-import=json',
        '--hidden-import=uuid',
        '--hidden-import=dataclasses',
        '--hidden-import=typing',
        '--hidden-import=datetime',
        '--hidden-import=threading',
        '--hidden-import=os',
        '--hidden-import=sys',
        '--hidden-import=pathlib',

        # --- EXCLUDES (Boyut küçültme için) ---
        '--exclude-module=matplotlib',
        '--exclude-module=tkinter',
        '--exclude-module=unittest',
        '--exclude-module=pydoc',
        '--exclude-module=scipy',
        '--exclude-module=PIL',
        '--exclude-module=cryptography',
        '--exclude-module=pytz',
        '--exclude-module=pytest',

        # --- METADATA (Fixed section) ---
        '--copy-metadata=streamlit',
        '--copy-metadata=requests',
        '--copy-metadata=packaging',
        '--copy-metadata=altair',
        '--copy-metadata=blinker',
        '--copy-metadata=cachetools',
        '--copy-metadata=click',
        '--copy-metadata=gitdb',
        '--copy-metadata=GitPython',
        '--copy-metadata=importlib-metadata',  # FIXED: Added this
        '--copy-metadata=Jinja2',
        '--copy-metadata=jsonschema',
        '--copy-metadata=jsonschema-specifications',
        '--copy-metadata=markdown-it-py',
        '--copy-metadata=mdurl',
        '--copy-metadata=numpy',
        '--copy-metadata=pandas',
        '--copy-metadata=Pillow',
        '--copy-metadata=protobuf',
        '--copy-metadata=pyarrow',
        '--copy-metadata=pydeck',
        '--copy-metadata=Pygments',
        '--copy-metadata=PyPDF2',
        '--copy-metadata=python-dateutil',
        '--copy-metadata=python-docx',
        '--copy-metadata=referencing',
        '--copy-metadata=rich',
        '--copy-metadata=rpds-py',
        '--copy-metadata=semver',
        '--copy-metadata=smmap',
        '--copy-metadata=tenacity',
        '--copy-metadata=toml',
        '--copy-metadata=toolz',
        '--copy-metadata=tornado',
        '--copy-metadata=typing_extensions',  # FIXED: Added this
        '--copy-metadata=watchdog',
        '--copy-metadata=zipp',  # FIXED: Added this
    ]

    # UPX kullan
    if use_upx:
        commands.extend([
            '--upx-dir=.',  # UPX'nin bulunduğu dizin
        ])

    # Eğer ikon varsa komutlara ekle
    if icon_file.exists():
        print(f"✅ İkon eklendi: {icon_file}")
        commands.insert(7, f'--icon={icon_file}')  # 7. sıraya ekliyoruz
    else:
        print("⚠️ İkon bulunamadı, varsayılan ikon kullanılacak.")

    print("🚀 Derleme işlemi başlıyor...")
    print(f"Komutlar: {' '.join(commands[:5])} ... ({len(commands)} toplam parametre)")

    # 2. PyInstaller'ı çalıştır
    try:
        print("🔨 EXE dosyası oluşturuluyor, bu işlem birkaç dakika sürebilir...")
        PyInstaller.__main__.run(commands)
        print("\n✅ İŞLEM BAŞARIYLA TAMAMLANDI!")
        print("Oluşan dosyayı 'dist' klasöründe bulabilirsiniz.")

        # Oluşan exe dosyasının bilgilerini göster
        exe_path = Path("dist") / "UFT-BILSEM.exe"
        if exe_path.exists():
            size_bytes = exe_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            print(f"📁 EXE Dosya Boyutu: {size_mb:.1f} MB ({size_bytes:,} bytes)")
            print(f"📍 Dosya Konumu: {exe_path.absolute()}")

            # UPX uygulanmışsa bilgi ver
            if use_upx:
                print("🔒 UPX ile sıkıştırıldı")

        return True

    except Exception as e:
        print(f"\n❌ BİR HATA OLUŞTU: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
