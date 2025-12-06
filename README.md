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

## 🚀 Kurulum

### Ön Gereksinimler
* **Python 3.8** veya üzeri
* **[Ollama](https://ollama.com/)** (AI Modellerini çalıştırmak için),
```python
pip install rich
pip install requests
pip install streamlit
```
* Yukarıdaki **pip** paketleri

### 1. Projeyi Klonlayın
```bash
git clone https://github.com/Sranzx/uft-bilsem.git
cd uft-bilsem
