# UFT-BİLSEM — Yapay Zeka Destekli Öğrenci Ürün Dosyası Analizi

Bu doküman, proje hakkındaki teknik olmayan jüri üyelerine ve değerlendiricilere projenin ne yaptığı, neden önemli olduğu ve nasıl çalıştırılacağı hakkında açık, anlaşılır bir rehber sunar. Kod ve mimariyle ilgili temel noktalar da sade bir dille açıklanmıştır.

---

## Proje Özeti
UFT-BİLSEM, öğretmenlerin veya rehberlik uzmanlarının öğrenci ürünlerini (ödevler, raporlar vb.) yerel olarak çalıştırılan bir yapay zeka motoru ile analiz edip pedagojik öneriler almasını sağlayan, verileri dışarıya göndermeyen (offline) bir uygulamadır.

---

## Neden Bu Proje Önemli?
- Gizlilik odaklı: Öğrenci verileri cihazı/yerel ağ dışına çıkmaz — KVKK ve veri mahremiyeti gereksinimlerine uygundur.
- Kullanımı kolay: Arayüzü Streamlit ile hazırlanmış, öğretmenlerin teknik olmayan kişilerin kolayca kullanabileceği şekilde tasarlanmıştır.
- Güvenilir veriler: Geliştirilmiş kayıt/yedekleme ve kurtarma mekanizmaları sayesinde verileriniz güvenlidir; bozulma veya yanlışlık durumlarında geri dönebilirsiniz.
- Yerel yapay zeka (Ollama): İnternet bağlantısı olmadan yerel model çalıştırarak analiz yapar.

---

## Öne Çıkan Özellikler
- Yerel LLM tabanlı analiz (Ollama ile): Öğrenci dosyalarını analiz eder, öneriler üretir.
- JSON tabanlı sade kayıt: Her öğrenci verisi dosya olarak veya merkezi bir `data` dosyasında saklanabilir.
- Gelişmiş kalıcılık (persistence) modülü:
  - Atomik kayıt (transactional save): Kaydederken dosyanın yarım kalmasını engeller.
  - Otomatik yedekleme (backups) ve versiyonlama.
  - Değişiklik kayıtları (changelog) ile kimin/ne zaman değiştirdiğinin izlenmesi.
  - Veri doğrulama (hash/integrity) ve bozuk dosya kurtarma mekanizmaları.
  - CSV/JSON/pickle şeklinde dışa aktarma (export).
- Otomatik ve manuel kayıt seçenekleri + tarayıcı kapandığında otomatik yedekleme.

---

## Kullanılan Bileşenler
- app.py: Streamlit tabanlı kullanıcı arayüzü — form girişi, dosya yükleme, kayıt, analiz.
- student_streamable.py: Öğrenci modelleri, dosya okuma (PDF/DOCX/TXT), temel öğrenci kaydetme/yükleme mantığı.
- persistence.py: Yeni eklenen güçlü kalıcılık modülü — yedekleme, transactional kaydetme, kurtarma, değişiklik günlüğü, export fonksiyonları.
- Ollama (yerel LLM): Analizleri yapan yerel model sunucusu (kullanıcı bilgisayarında çalıştırılmalı).

---

## Teknik Olmayan Açıklama — "Persistence" (Veri Saklama) Nedir ve Neden Geliştirildi?
Persistence: Uygulamanın verileri (öğrenci bilgileri, notlar, dosya içeriği, model analizleri) diske kaydetme biçimidir.

Neden geliştirdik?
- Dosya bozulması veya beklenmedik kapanma durumlarında veri kaybı yaşanmasın.
- Geçmiş kayıtlar (sürümler) saklansın, istenirse geri dönüş yapılsın.
- Kimin ne zaman değişiklik yaptığını görebilelim (denetlenebilirlik).
- Veriler doğrulansın — kaydedilen veri bozulmadığını teyit edebilelim.

Bu amaçla persistence.py içinde:
- Atomic (geçişli) yazma: önce geçici dosyaya yazılır, sonra yerine konur — böylece asla yarım kalmış dosya olmaz.
- BackupManager: Her önemli işlemin öncesinde veya araçla istenildiğinde yedek oluşturur; yedeklerin meta verileri saklanır.
- ChangeLog: Kaydetme, güncelleme, geri alma gibi işlemleri zaman damgası ile kaydeder.
- RecoveryManager: Bozulma durumunda en son sağlıklı yedekten geri döner.
- ExportManager: Verileri CSV/JSON olarak dışarı verir, raporlama ve inceleme kolaylaşır.

---

## İlk Kurulum ve Çalıştırma (Adım Adım)

1. Gereksinimler:
   - Python 3.8 veya üzeri
   - Git
   - Ollama (yerel LLM servisi) — proje offline inference hedeflediği için Ollama bilgisayarınızda çalışmalıdır.
   - Gerekli Python kütüphaneleri: requirements.txt ile yüklenir.

2. Repoyu klonlayın:
   ```bash
   git clone https://github.com/Sranzx/uft-bilsem.git
   cd uft-bilsem
   ```

3. Sanal ortam oluşturun ve bağımlılıkları yükleyin:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\Activate.ps1
   # macOS/Linux
   source venv/bin/activate

   pip install -r requirements.txt
   ```

4. Ollama'yı başlatın (kurulduysa):
   ```bash
   ollama serve
   ```
   Not: Model indirme örneği:
   ```bash
   ollama pull gemma3
   ```

5. Uygulamayı başlatın:
   - Geliştirici modu (Streamlit):
     ```bash
     streamlit run app.py
     ```
   - Veya hazırladığınız .exe varsa doğrudan çalıştırın.

---

## Geliştirici Notları (Kısa Teknik Özet)
- Eski davranış: Her öğrenci için ayrı .json dosyası (student_data/). Bu yaklaşım taşınabilir ancak büyük projelerde yönetim zorlukları olabilir.
- Yeni eklenen persistence.py:
  - Merkezi bir `data/data.json` (veya tercih ettiğiniz format) ile tüm kayıtlar kontrol edilebilir.
  - TransactionalStorage ile "yarım yazılma" riskine karşı geçici dosya + atomik replace stratejisi kullanılır.
  - BackupManager, ChangeLog ve RecoveryManager bileşenleri veri bütünlüğünü ve geçmişi garanti eder.
- student_streamable.py içindeki Student/Grade/AIInsight yapısı, persistence.py ile uyumlu biçimde kullanılmalı. (repository içinde örnek entegrasyon hazırlandı.)

---

## Sık Karşılaşılan Sorunlar ve Çözümleri
- Ollama çalışmıyor / model yüklenmemiş:
  - Hata: Arayüzde "Ollama kapalı" uyarısı görürsünüz. Terminalde `ollama serve` çalıştırın ve modelin indiğinden emin olun.
- Kaydetme başarısız/permission hatası:
  - `data/` klasörü yazılabilir mi kontrol edin. Gerekirse uygulamayı yönetici/uygulama sahibi izinleriyle çalıştırın.
- Bozuk JSON dosyası:
  - `data/backups/` içinden son sağlıklı yedeği kullanarak geri yükleme yapılabilir (RecoveryManager).

---
