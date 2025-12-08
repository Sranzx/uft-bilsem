import streamlit.web.cli as stcli
import os, sys


def resolve_path(path):
    """
    PyInstaller tarafından oluşturulan geçici klasör (_MEIPASS)
    veya mevcut çalışma dizini arasındaki yol ayrımını çözer.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.getcwd(), path)


if __name__ == "__main__":
    # Uygulama dosyasının (app.py) tam yolunu bul
    app_path = resolve_path("app.py")

    # Sanki terminalden 'streamlit run app.py' yazılmış gibi komut argümanlarını ayarla
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",  # Geliştirici seçeneklerini kapat
        "--server.headless=false",  # Tarayıcıyı otomatik aç
    ]

    # Streamlit CLI'ını başlat
    sys.exit(stcli.main())