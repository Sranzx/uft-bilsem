-----

# 🎓 UFT-BİLSEM: Yerel Yapay Zeka Destekli Pedagojik Analiz Sistemi

## 📑 Proje Özeti

**UFT-BİLSEM**, eğitim süreçlerinde üretilen öğrenci verilerinin (akademik notlar, davranışsal gözlemler ve devamsızlık bilgileri), üçüncü parti bulut sunucularına iletilmeden, tamamen yerel ağ ve cihaz üzerinde çalışan Büyük Dil Modelleri (LLM) ile analiz edilmesini sağlayan bir yazılım projesidir.

Bu proje, KVKK ve veri mahrekiyeti esaslarına tam uyum sağlayarak, eğitimcilere öğrencilerin gelişim süreçleri hakkında derinlemesine, yapay zeka destekli pedagojik raporlar sunmayı hedefler.

-----

## 🌟 Temel Özellikler ve Özgün Değer

  * **🔒 Tam Veri Mahrekiyeti (Offline Inference):** Analiz süreci için internet bağlantısına ihtiyaç duymaz. Öğrenci verileri asla cihaz dışına çıkmaz; tüm işlemler `Ollama` üzerinden yerel donanım gücüyle gerçekleştirilir.
  * **🧠 İleri Seviye Pedagojik Analiz:** Llama 3.2, Mistral veya Gemma gibi açık kaynaklı modelleri kullanarak öğrenci profillerini yorumlar ve eğitimciye stratejik önerilerde bulunur.
  * **⚡ Gerçek Zamanlı Akış (Streaming):** Analiz çıktıları, kullanıcı deneyimini artırmak amacıyla kelime kelime (token-based streaming) ekrana yansıtılır.
  * **💾 JSON Tabanlı Veri Yapısı:** Karmaşık veritabanı kurulumlarına (SQL vb.) gerek duymadan, verileri taşınabilir ve hafif JSON formatında saklar.
  * **🛡️ Hata Toleranslı Mimari:** Eksik veri girişi veya model yanıt sorunlarında sistemi stabilize eden hata yakalama mekanizmalarına sahiptir.

-----

## 🚀 Kurulum ve Kullanım Yönergeleri

Proje, hem son kullanıcılar (hazır uygulama) hem de geliştiriciler (kaynak kod) için iki farklı şekilde kullanılabilir.

### Yöntem A: Son Kullanıcılar İçin (Hazır `exe` Kullanımı)

Kodlama bilgisi gerektirmeden uygulamayı doğrudan çalıştırmak için bu yöntemi izleyin.

1.  **Ollama Kurulumu:** Uygulamanın beyni olan yapay zeka motorunu çalıştırmak için [Ollama Resmi Web Sitesi](https://ollama.com/)'nden işletim sisteminize uygun sürümü indirin ve kurun.
2.  **Modelin İndirilmesi:** Terminal veya komut satırını açarak analiz için gerekli modeli indirin:
    ```bash
    ollama pull llama3.2
    ```
3.  **Uygulamanın İndirilmesi:**
      * Bu sayfanın sağ tarafında bulunan **[Releases](https://www.google.com/search?q=https://github.com/Sranzx/uft-bilsem/releases)** bölümüne gidin.
      * En güncel sürüm (Latest) altındaki `.exe` uzantılı dosyayı bilgisayarınıza indirin.
4.  **Çalıştırma:** İndirdiğiniz dosyaya çift tıklayarak sistemi başlatın.

> **Not:** Windows kullanıyorsanız ve "SmartScreen" uyarısı alırsanız, "Ek bilgi" -\> "Yine de çalıştır" seçeneklerini takip edebilirsiniz.

-----

### Yöntem B: Geliştiriciler İçin (Kaynak Koddan Derleme)

Projeyi geliştirmek veya kaynak koddan çalıştırmak isteyenler için adımlar aşağıdadır.

#### 1\. Gereksinimler

  * Python 3.8 veya üzeri
  * Git
  * Ollama (Yüklü ve çalışır durumda olmalı)

#### 2\. Repoyu Klonlama

Terminalinizi açın ve projeyi yerel diskinize kopyalayın:

```bash
git clone https://github.com/Sranzx/uft-bilsem.git
cd uft-bilsem
```

#### 3\. Sanal Ortam (Virtual Environment) Kurulumu

Bağımlılıkların sistem geneline yayılmasını önlemek için izole bir ortam oluşturun:

```bash
# Sanal ortamı oluştur
python -m venv venv

# Sanal ortamı aktif et
# Windows için:
venv\Scripts\activate

# macOS/Linux için:
source venv/bin/activate

# Fish Shell için:
source venv/bin/activate.fish
```

#### 4\. Kütüphanelerin Yüklenmesi

Gerekli Python paketlerini yükleyin:

```bash
pip install rich requests streamlit openai anthropic google-generativeai fpdf pandas
```

#### 5\. Uygulamayı Başlatma

Kurulum tamamlandıktan sonra tercih ettiğiniz arayüzü başlatın.

**Terminal Arayüzü (CLI) ile Başlat:**

```bash
python app.py
```

**Web Arayüzü (Streamlit) ile Başlat:**

```bash
streamlit run app.py
```

-----

## 🛠️ Sorun Giderme (Troubleshooting)

| Hata Mesajı | Olası Neden | Çözüm |
| :--- | :--- | :--- |
| `Connection refused` | Ollama kapalı olabilir. | Ollama uygulamasının arka planda çalıştığından emin olun. |
| `Module not found` | Eksik kütüphane. | `pip install` komutunu sanal ortam (venv) aktifken tekrar çalıştırın. |
| `Encoding Error` | Türkçe karakter sorunu. | Windows terminalinde `chcp 65001` komutunu uygulayın. |

-----