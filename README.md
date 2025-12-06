# 🎓 Ollama AI Student Analyst

**Ollama AI Student Analyst**, eğitimciler için geliştirilmiş, yerel Yapay Zeka (Local LLM) destekli, gizlilik odaklı bir öğrenci performans takip ve analiz aracıdır.

Bu araç, öğrencilerin akademik notlarını ve davranışsal gözlemlerini takip eder; ardından **Ollama** üzerinden çalışan Llama 3.2, Mistral veya Gemma gibi modelleri kullanarak internete ihtiyaç duymadan detaylı pedagojik analizler sunar.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat&logo=python)
![Ollama](https://img.shields.io/badge/AI-Ollama-orange?style=flat&logo=openai)
![Rich](https://img.shields.io/badge/UI-Rich-purple?style=flat)

---

## 🌟 Özellikler

* **🧠 %100 Yerel & Gizli:** Öğrenci verileri hiçbir bulut sunucusuna gönderilmez. Tüm analizler bilgisayarınızdaki yerel LLM (Ollama) tarafından yapılır.
* **⚡ Canlı Akış (Streaming):** AI analiz yaparken sonuçlar kelime kelime ekrana akar (ChatGPT benzeri deneyim), bekleme süresini azaltır.
* **🎨 Modern Terminal Arayüzü (TUI):** `Rich` kütüphanesi ile güçlendirilmiş renkli paneller, tablolar ve yükleme animasyonları.
* **📊 Kapsamlı Takip:** Notlar, devamsızlık durumu ve detaylı davranış gözlem notları (Olumlu/Olumsuz/Nötr) ekleyebilirsiniz.
* **🛡️ Hata Toleransı:** Eksik veri, bozuk dosya veya bağlantı kopukluklarında sistem çökmez, sizi yönlendirir.
* **💾 JSON Veritabanı:** Karmaşık SQL kurulumlarına gerek yoktur. Veriler taşınabilir JSON dosyalarında saklanır.

---

## 🚀 Kurulum ve Hazırlık

Bu projeyi bilgisayarınızda çalıştırmak için aşağıdaki adımları sırasıyla takip edin.

### 1. Ön Hazırlıklar
* **Python 3.8+**: Bilgisayarınızda Python'un kurulu olduğundan emin olun.
* **Ollama**: Yapay zeka modellerini yerel olarak çalıştırmak için [Ollama'yı indirin ve kurun](https://ollama.com/).

### 2. Projeyi İndirin (Clone)
Terminal veya Komut İstemi'ni (CMD) açın ve projeyi bilgisayarınıza çekin:

```bash
git clone [https://github.com/Sranzx/uft-bilsem.git](https://github.com/Sranzx/uft-bilsem.git)
cd uft-bilsem
```

### 3\. Gerekli Kütüphaneleri Yükleyin

Projenin çalışması için gerekli Python paketlerini yükleyin:

```bash
pip install rich requests streamlit openai anthropic google-generativeai fpdf pandas
```

### 4\. Yapay Zeka Modelini Hazırlayın

Projenin analiz yapabilmesi için Ollama üzerinde ilgili modelin (varsayılan: llama3.2) indirilmiş olması gerekir. Terminalde şu komutu çalıştırın:

```bash
ollama pull llama3.2
```

*(Not: Eğer kod içerisinde farklı bir model kullanıyorsanız, örneğin `mistral`, komutu `ollama pull mistral` şeklinde düzenleyin.)*

-----

## 🏃‍♂️ Uygulamayı Başlatma

Kurulum tamamlandıktan sonra uygulama klasörü içerisindeyken aşağıdaki komutlardan birini kullanarak başlatabilirsiniz.

**Terminal Arayüzü (CLI) için:**

```bash
python app.py
```

**Web Arayüzü (Streamlit) için:**

```bash
streamlit run app.py
```

### ⚠️ Olası Sorunlar

  * **"Connection refused" Hatası:** Ollama uygulamasının arka planda çalıştığından emin olun. (Ollama simgesi çubuğunda görünmelidir).
  * **"Module not found" Hatası:** 3. adımdaki `pip install` komutlarını eksiksiz uyguladığınızı kontrol edin.
  * **Türkçe Karakter Sorunu:** Windows terminalinde Türkçe karakterler bozuk görünürse, terminalde önce `chcp 65001` komutunu çalıştırın.

<!-- end list -->
