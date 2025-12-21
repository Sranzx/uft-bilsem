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
            print("✅ UPX bulundu")
            return True
        else:
            print("⚠️ UPX bulunamadı")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️ UPX bulunamadı")
        return False


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

    # UPX kontrolü
    use_upx = check_upx()

    commands = [
        'run_app.py',
        '--onefile',
        '--name=UFT-BILSEM-DEBUG',
        '--clean',
        '--noconfirm',
        '--console',  # Debug için konsolu açık tut
        '--debug=all',  # Debug bilgilerini göster
        '--log-level=DEBUG',  # Detaylı log

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
        '--hidden-import=streamlit.proto',
        '--hidden-import=requests',
        '--hidden-import=PyPDF2',
        '--hidden-import=docx',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=json',
        '--hidden-import=uuid',
        '--hidden-import=dataclasses',

        # Metadata
        '--copy-metadata=streamlit',
        '--copy-metadata=requests',
        '--copy-metadata=packaging',
    ]

    # UPX kullan (debug için opsiyonel)
    if use_upx:
        commands.extend([
            '--upx-dir=.',
        ])

    # İkon ekle (varsa)
    if icon_file.exists():
        commands.insert(7, f'--icon={icon_file}')
        print(f"✅ İkon eklendi: {icon_file}")
    else:
        print("⚠️ İkon bulunamadı.")

    print("🚀 DEBUG modunda derleme başlıyor...")

    try:
        print("🔨 DEBUG EXE oluşturuluyor...")
        PyInstaller.__main__.run(commands)
        print("\n✅ DEBUG EXE oluşturuldu!")
        print("Dosya: dist/UFT-BILSEM-DEBUG.exe")

        # Dosya bilgileri
        exe_path = Path("dist") / "UFT-BILSEM-DEBUG.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📁 Dosya Boyutu: {size_mb:.1f} MB")
            if use_upx:
                print("🔒 UPX ile sıkıştırıldı")

        return True

    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = build_debug_executable()
    sys.exit(0 if success else 1)
