import os
import sys
import streamlit
import PyInstaller.__main__
from pathlib import Path


def build_debug_executable():
    """
    Debug modunda EXE oluşturur (konsol açık kalır, daha hızlı build).
    """
    # Streamlit dizinleri
    streamlit_dir = os.path.dirname(streamlit.__file__)
    static_path = os.path.join(streamlit_dir, "static")

    project_dir = Path.cwd()
    icon_file = project_dir / "uft.ico"

    print(f"📍 Streamlit dizini: {streamlit_dir}")

    sep = os.pathsep

    commands = [
        'run_app.py',
        '--onefile',
        '--name=UFT-BILSEM-DEBUG',
        '--clean',
        '--noconfirm',
        '--console',  # Debug için konsolu açık tut
        '--debug=all',  # Debug bilgilerini göster

        # Gerekli dosyalar
        f'--add-data={project_dir}/app.py{sep}.',
        f'--add-data={project_dir}/student_streamable.py{sep}.',

        # Streamlit dosyaları
        f'--add-data={static_path}{sep}streamlit/static',

        # Gizli importlar
        '--hidden-import=streamlit',
        '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
        '--hidden-import=streamlit.runtime.scriptrunner.script_runner',
        '--hidden-import=streamlit.web.cli',
        '--hidden-import=streamlit.runtime.media_file_manager',
        '--hidden-import=streamlit.runtime.memory_media_file_manager',
        '--hidden-import=streamlit.elements',
        '--hidden-import=requests',
        '--hidden-import=PyPDF2',
        '--hidden-import=docx',
        '--hidden-import=pandas',
        '--hidden-import=numpy',

        # Metadata
        '--copy-metadata=streamlit',
        '--copy-metadata=requests',
    ]

    # İkon ekle (varsa)
    if icon_file.exists():
        commands.insert(5, f'--icon={icon_file}')
        print(f"✅ İkon eklendi: {icon_file}")
    else:
        print("⚠️ İkon bulunamadı.")

    print("🚀 DEBUG modunda derleme başlıyor...")

    try:
        PyInstaller.__main__.run(commands)
        print("\n✅ DEBUG EXE oluşturuldu!")
        print("Dosya: dist/UFT-BILSEM-DEBUG.exe")

    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_debug_executable()
