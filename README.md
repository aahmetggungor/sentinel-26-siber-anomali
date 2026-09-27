# SENTINEL 26

## Çevrimiçi yayın

**Canlı demo:** https://sentinel-26-siber-anomali.streamlit.app/  
**Kaynak kod:** https://github.com/aahmetggungor/sentinel-26-siber-anomali

Streamlit Community Cloud için giriş dosyası `app.py`, Python sürümü 3.12'dir. Gerekli eğitim çıktıları (`artifacts/isolation_forest.joblib`, `artifacts/test_scored.parquet`, `artifacts/metrics.json`) depoda bulunur; sunucu açılırken eğitim yeniden çalıştırılmaz. Çevrimiçi demoda alarm kayıtları ziyaretçi oturumunda tutulur. Yüklenen CSV sunucuda işlenir; gerçek ağ kayıtları veya gizli veri yüklemeyin.

SAYZEK PDF'inin 26. konusu için hazırlanmış, tek bilgisayarda çalışan ağ akışı anomalisi ve alarm demosu. Ayrıntılı amaç, mimari, ölçümler ve tez planı için [PROJE_TASLAGI.md](PROJE_TASLAGI.md); temel kavramlar için [KAVRAMLAR.md](KAVRAMLAR.md) dosyasını açın.

> Mevcut uygulama **canlı ağı dinlemez**. UNSW-NB15 test kayıtlarını akış gibi tekrar oynatır, her partiyi gerçekten modelden geçirir ve alarmları yerel JSONL dosyasına yazar.

## Windows'ta başlat

Bu klasörde PowerShell açın:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_data.py
.\.venv\Scripts\python.exe train.py
.\start_pdf26.ps1
```

Son komut tarayıcıda `http://127.0.0.1:8502/` açar. İlk dört komut bir kez yeterlidir; daha sonra yalnızca `start_pdf26.ps1` gerekir. `py -3` bulunmazsa kurulu Python 3.12+ ile `.venv` oluşturun. Proje için RTX 4060 gerekmez; model CPU kullanır. Veri indirme yaklaşık 48 MB'dır.

PowerShell betiği çalıştırma ilkesi komutu engellerse, proje klasöründe şu komutla doğrudan başlatabilirsiniz:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

## Hızlı demo

1. **Komuta merkezi:** Tekil ve eğitimde görülmemiş test ayrımındaki sonuçları görün. Soldaki hedef yanlış alarm sürgüsünü `%2`'den `%5`'e değiştirip alarm/recall dengesini inceleyin.
2. **Akış simülasyonu:** `▶ Başlat` ile test kayıtlarını puanlayın; alarm, çıkarım gecikmesi, skor grafiği ve ipuçları görünür. `Ⅱ Durdur` ile durdurun. `Etiketli referans` ile öğrenme biçimlerinin farkını görün.
3. **Model laboratuvarı:** Isolation Forest ile etiketli Random Forest'ı karşılaştırın. Veri tekrar/sızıntı denetimini açın.
4. **Veri ve log:** `logs/alerts.jsonl` dosyasını indirin. UNSW-NB15'in **aynı 42 özellik sütununu** içeren bir CSV yükleyip puanlanmış çıktıyı indirin. Ham PCAP veya keyfi ağ logu burada doğrudan çalışmaz.

## Dosyalar

| Yol | İşlev |
| --- | --- |
| `app.py` | Streamlit arayüzü ve akış simülasyonu |
| `engine.py` | Ön işleme, eğitim, skor, eşik, veri denetimi ve metrikler |
| `train.py` | Eğitimi çalıştırır, `artifacts/` çıktılarını yazar |
| `verify.py` | Ayrım, model skoru ve kayıtlı metrik tutarlılığını kontrol eder |
| `download_data.py` | CSV kopyalarını indirir, SHA-256 ve satır sayısını doğrular |
| `alert_log.py` | JSONL alarm kaydı ve okuma |
| `data/README.md` | Veri kaynağı, hash ve akademik atıf |
| `PROJE_TASLAGI.md` | Bitirme projesi taslağı, deneyler ve tez yol haritası |
| `KAVRAMLAR.md` | Başlangıç düzeyi ağ ve model değerlendirme sözlüğü |
| `artifacts/metrics.json` | Son eğitimden hesaplanan metrikler |
| `logs/alerts.jsonl` | Demo alarmları; ilk alarmdan sonra oluşur |

CSV verileri, eğitilmiş model, test skorları, yerel log ve sanal ortam `.gitignore` ile Git dışındadır. Başka bilgisayarda ilk dört kurulum komutuyla yeniden üretilebilir.

Yeniden üretme kontrolü: `.\.venv\Scripts\python.exe verify.py`.

## Bugünkü sonuç ve sınır

Normal doğrulamada `%2` hedef yanlış alarm eşiğiyle, tekil ve eğitimde görülmemiş 52.644 test kaydında etiketsiz Isolation Forest saldırı recall'u `%7,4`, test FPR'si `%2,0` çıktı. Bu sonuç yüksek başarı iddiası değildir; eşik ve model kıyasının araştırma sorusunu oluşturur. Ayrıntılı tablo ve veri tekrar denetimi taslakta yer alır. Testte saldırı oranı yüksektir, bu nedenle precision gerçek ağdaki precision gibi yorumlanmamalıdır.

## Kaynak

[UNSW-NB15 resmi sayfası](https://research.unsw.edu.au/projects/unsw-nb15-dataset); erişilebilir [CSV kopyası](https://github.com/Nir-J/ML-Projects/tree/master/UNSW-Network_Packet_Classification). Akademik kullanımda orijinal veri çalışmasına atıf yapın. Model dosyalarını yalnızca bu projenin kendi eğitim komutundan üretip yükleyin.
