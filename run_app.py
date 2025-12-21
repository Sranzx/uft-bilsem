import streamlit.web.cli as stcli
import os
import sys
from pathlib import Path


def resolve_path(path):
    """
    PyInstaller ile paketlenmiş uygulamalarda doğru yolu bulur.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller ile paketlenmişse
        application_path = Path(sys._MEIPASS)
    else:
        # Normal Python ortamındaysa
        application_path = Path(__file__).parent

    return application_path / path


def main():
    """
    Streamlit uygulamasını başlatır.
    """
    try:
        # app.py dosyasının yolunu belirle
        app_path = resolve_path("app.py")

        if not app_path.exists():
            print(f"❌ HATA: app.py dosyası bulunamadı: {app_path}")
            print("Mevcut dosyalar:")
            for file in Path(".").iterdir():
                print(f"  - {file}")
            sys.exit(1)

        print(f"🚀 Uygulama başlatılıyor: {app_path}")

        # Streamlit başlatma komutunu hazırla
        sys.argv = [
            "streamlit",
            "run",
            str(app_path),
            "--global.developmentMode=false",
            "--browser.gatherUsageStats=false",  # Gizlilik için
            "--logger.level=INFO",  # Log seviyesi
        ]

        # Streamlit'i başlat
        sys.exit(stcli.main())

    except Exception as e:
        print(f"❌ Uygulama başlatılamadı: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
