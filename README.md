# UFT-BİLSEM — Yapay Zeka Destekli Öğrenci Ürün Dosyası Analizi

Bu doküman, proje hakkındaki teknik olmayan jüri üyelerine ve değerlendiricilere projenin ne yaptığı, neden önemli olduğu ve nasıl çalıştırılacağı hakkında açık, anlaşılır bir rehber sunar.

---

## Proje Özeti

UFT-BİLSEM, öğretmenlerin öğrenci ürünlerini (ödevler, projeler, sınavlar, davranış kayıtları vb.) yerel olarak çalıştırılan bir yapay zeka motoru ile analiz edip pedagojik öneriler almasını sağlayan, verileri dışarıya göndermeyen (offline) bir uygulamadır.

Uygulama, öğrencilerin bireysel gelişimlerini takip etmek, performanslarını analiz etmek ve kişiselleştirilmiş öğretim önerileri oluşturmak için geliştirilmiştir.

---

## Özellikler

### Temel Özellikler
- **Yerel Yapay Zeka Desteği**: Öğrenci dosyalarını Ollama ile çalışan yerel LLM üzerinden analiz eder
- **Tamamen Offline**: İnternet bağlantısı gerektirmez, tüm işlemler yerel olarak yapılır
- **Veri Gizliliği**: Öğrenci verileri cihazdan çıkmaz, KVKK ve uluslararası veri koruma standartlarına uygundur
- **Streamlit Arayüzü**: Kullanımı kolay, modern ve responsive web arayüzü
- **Çoklu Öğrenci Yönetimi**: Öğrenci ekleme, düzenleme, silme ve arama özellikleri

### Gelişmiş Veri Yönetimi
- **Veri Doğrulama**: Tüm öğrenci verileri SHA256 hash ile doğrulanır
- **Atomik Kayıt**: Veri kaybını önlemek için geçici dosya + atomik değiştirme yöntemi
- **Esnek Veri Yapıları**: Notlar, ödevler, projeler, sınavlar ve davranış kayıtları için ayrı yapılar
- **CSV Dışa Aktarma**: Öğrenci verilerini ve ödev detaylarını CSV formatında dışa aktarma
- **Otomatik Temizleme**: Geçersiz veya bozulmuş veriler otomatik olarak filtrelenebilir

### Kullanıcı Deneyimi
- **Veri Entegrasyonu**: Öğrenci verilerini tek bir merkezden yönetme
- **Veri Gözlemleme**: Öğrenci performanslarını ve davranışlarını gözlemleme
- **Ödev Takibi**: Ödev durumlarını ve teslim tarihlerini takip etme
- **Proje Yönetimi**: Öğrenci projelerini takip etme ve değerlendirme
- **Sınav Sonuçları**: Sınav sonuçlarını kaydetme ve analiz etme
- **Davranış Kayıtları**: Öğrenci davranışlarını ve gözlemleri kaydetme

---

## Teknik Detaylar

### Mimari Bileşenler
- **run_app.py**: Streamlit uygulamasının başlatıcısı, PyInstaller ile uyumlu çalışacak şekilde tasarlandı
- **app.py**: Streamlit tabanlı kullanıcı arayüzü - öğrenci yönetimi, navigasyon ve veri görüntüleme
- **core.py**: Ana veri işleme ve doğrulama modülü - öğrenci verilerinin yönetimi, doğrulanması ve kaydedilmesi
- **build.py**: PyInstaller ile EXE dosyası oluşturma betiği - dağıtım için otomatik paketleme

### Güvenlik ve Veri Bütünlüğü
- **SHA256 Hash Doğrulaması**: Her öğrenci dosyası değiştiğinde hash değeri hesaplanır ve doğrulanır
- **Atomik Yazma**: Veri yazılırken önce geçici dosyaya yazılır, sonra asıl dosya üzerine yazılır
- **Hata Toleranslı Okuma**: Bozulmuş veri olması durumunda düzgün şekilde ele alınır

---

## Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.8 veya üzeri
- Git
- Ollama (yerel LLM servisi)

### Kurulum Adımları

1. **Depoyu klonlayın**:
   ```bash
   git clone https://github.com/Sranzx/uft-bilsem.git
   cd uft-bilsem
   ```

2. **Sanal ortam oluşturun ve bağımlılıkları yükleyin**:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\Activate.ps1
   # macOS/Linux
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Ollama'yı başlatın**:
   ```bash
   ollama serve
   ```
   
   Gerekli modeli indirin:
   ```bash
   ollama pull llama3
   ```

4. **Uygulamayı başlatın**:
   ```bash
   streamlit run run_app.py
   ```

### EXE Olarak Derleme (İsteğe Bağlı)
Derlenmiş EXE dosyası oluşturmak için:
```bash
python build.py
```

Bu işlem sonrasında `dist/UFT-BILSEM.exe` dosyası oluşturulacaktır.

---

## Kullanım

Uygulama açıldığında üç ana bölüme erişebilirsiniz:

### Öğrenci Listele
Tüm öğrencileri ve temel bilgilerini görüntüleyin. Her öğrenci için detaylı bilgilere ulaşabilir, öğrenciyi seçebilir veya silebilirsiniz.

### Yeni Öğrenci Ekle
Form aracılığıyla yeni öğrenci ekleyin. Otomatik olarak benzersiz ID atanır ve veri bütünlüğü sağlanır.

### Öğrenci Ara
İsim veya sınıf bilgisine göre öğrenci araması yapın.

---

## Geliştirici Notları

### Proje Yapısı
- Veriler `student_data/` dizininde JSON dosyaları olarak saklanır
- Her öğrenci için ayrı bir UUID ile tanımlanmış dosya oluşturulur
- `core.py` tüm veri işlemlerini yönetir
- Streamlit arayüzü `app.py` içinde tanımlanmıştır

### Veri Yapısı
Her öğrenci aşağıdaki yapıya sahiptir:
```json
{
  "id": "benzersiz-uuid",
  "name": "Öğrenci Adı",
  "class_name": "Sınıf Bilgisi",
  "grades": [],        // Notlar
  "homeworks": [],     // Ödevler
  "projects": [],      // Projeler
  "exams": [],         // Sınavlar
  "behavior": [],      // Davranış kayıtları
  "observation": "",    // Genel gözlem notları
  "last_updated": "YYYY-MM-DD HH:MM:SS",
  "file_hash": "sha256-hash-degeri"
}
```

---

## Katkıda Bulunma

Projeye katkıda bulunmak için:
1. Repository'yi fork'layın
2. Yeni özellikler veya düzeltmeler ekleyin
3. Test edin ve Pull n
