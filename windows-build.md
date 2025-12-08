### Adım 1: Temiz Bir Başlangıç Yapın

Windows bilgisayarınızda projenizin olduğu klasörü açın. Eğer kodlar henüz orada değilse `git clone` ile çekin veya kopyalayın.

Klasörün içinde **`Shift`** tuşuna basılı tutarak sağ tıklayın ve **"PowerShell penceresini buradan aç"** (veya Terminalde Aç) deyin.

### Adım 2: Gerekli Dosyayı Oluşturun (`run_app.py`)

Streamlit'i exe içinde çalıştırmak için bir "tetikleyici" dosyaya ihtiyacımız var. Proje klasörünüzde **`run_app.py`** adında yeni bir metin belgesi oluşturun, uzantısını `.py` yapın ve içine şu kodu yapıştırıp kaydedin:

```python
import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.getcwd(), path)

if __name__ == "__main__":
    app_path = resolve_path("app.py")
    # Streamlit'i başlatma komutunu simüle ediyoruz
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
```

### Adım 3: Kütüphaneleri Yükleyin

PowerShell penceresine şu komutları sırasıyla girerek temiz bir kurulum yapın:

```powershell
# 1. Sanal ortam oluştur (tavsiye edilir)
python -m venv venv

# 2. Sanal ortamı aktif et
.\venv\Scripts\activate

# 3. PyInstaller ve projenin gereksinimlerini yükle
# (requirements.txt yoksa kullandığınız kütüphaneleri manuel yazın: pandas, rich vb.)
pip install pyinstaller streamlit rich pandas google-generativeai requests
```

### Adım 4: `.exe` Oluşturma Komutu (Windows İçin)

En kritik adım burasıdır. Windows'ta dosya ayıracı olarak noktalı virgül (`;`) kullanılır. Aşağıdaki komutu **tek satır** halinde kopyalayıp yapıştırın:

```powershell
pyinstaller --onefile --noconsole --add-data "app.py;." --copy-metadata streamlit run_app.py
```

**Komutun Detayları:**

  * `--onefile`: Tek bir exe dosyası çıkarır.
  * `--noconsole`: Siyah komut penceresi açılmaz, direkt tarayıcı açılır. (Eğer hata ayıklamak isterseniz bu kısmı silin, siyah ekran görünür).
  * `--add-data "app.py;."`: `app.py` dosyasını exe'nin içine gömer (Windows için `;` kullanılır).
  * `--copy-metadata streamlit`: Streamlit'in çalışması için gereken gizli dosyaları kopyalar.

### Adım 5: Sonuç

İşlem tamamlandığında proje klasörünüzde **`dist`** adında bir klasör oluşacak.
İçindeki **`run_app.exe`** dosyası artık hazırdır\!

Bu dosyayı alıp (Ollama kurulu olan) herhangi bir Windows bilgisayarda çalıştırabilirsiniz.

-----

### 💡 İpucu: Dosya İsmini ve Simgeyi Değiştirmek

Eğer çıkan dosyanın adının `run_app.exe` değil de mesela `UFT-Bilsem.exe` olmasını ve güzel bir simgesi olmasını isterseniz komutu şöyle güncelleyin:

```powershell
pyinstaller --onefile --noconsole --name "UFT-Bilsem" --icon "logo.ico" --add-data "app.py;." --copy-metadata streamlit run_app.py
```

*(Bunun için klasörde `logo.ico` adında bir simge dosyası olması gerekir.)*