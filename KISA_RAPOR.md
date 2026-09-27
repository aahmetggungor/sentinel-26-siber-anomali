# PDF 26 kısa proje raporu

**Konu:** Siber güvenlik için yapay zekâ ile anomali tespiti ve tehdit analizi. **Uygulama:** SENTINEL 26. **Durum:** Çalışan yerel demo ve yeniden üretilebilir ilk karşılaştırma.

## Amaç ve çalışan sistem

Ağ akışı kayıtlarını puanlayıp incelemeye değer anomaliler için anlık demo alarmı üretmek ve alarmı yerel JSONL dosyasına kaydetmek. Streamlit ekranı eşik ayarı, akış simülasyonu, iki modelin karşılaştırması ve aynı şemadaki CSV dosyalarını puanlama sunar. Simülasyon kayıtlı test verisini saniyelik partiler halinde işler; canlı ağ paketlerini dinlemez.

## Veri ve yöntem

[UNSW-NB15'in](https://research.unsw.edu.au/projects/unsw-nb15-dataset) yayımlanmış eğitim/test ayrımı kullanıldı: 175.341 eğitim, 82.332 test satırı. `id`, `label` ve `attack_cat` çıkarıldığında 42 model özelliği kalır. Özellik tekrarları ve eğitimle çakışmalar çıkarılınca ana ölçümde 52.644 tekil, eğitimde görülmemiş test kaydı vardır. Aynı özelliklerin farklı etiket taşıdığı eğitim grupları da dışlandı.

**Isolation Forest** yalnızca temiz normal eğitim kayıtlarıyla eğitildi. Eşik, ayrı normal doğrulama kayıtlarında `%2` hedef yanlış alarm oranına göre seçildi. **Random Forest** normal ve saldırı etiketleriyle eğitilmiş karşılaştırma modelidir. Her iki modelin son ölçümünde test etiketleri yalnızca sonuç hesaplamak için kullanıldı. Aynı öğrenme koşullarına sahip olmadıkları için modeller arasındaki fark, etiketli örneklerin değerini gösterir.

## Sonuçlar

| Model | Precision | Saldırı yakalama | F1 | Average Precision | Test yanlış alarm oranı |
| --- | ---: | ---: | ---: | ---: | ---: |
| Isolation Forest | %67,6 | %7,4 | %13,4 | %53,2 | %2,0 |
| Etiketli Random Forest | %86,4 | %82,9 | %84,6 | %94,8 | %7,3 |

Isolation Forest 18.982 saldırı kaydının 1.411'ini yakaladı; 33.662 normal kaydın 677'sinde yanlış alarm verdi. Sıkı eşikte yakalama düşük kaldı. Hedef yanlış alarm oranı `%5` yapıldığında saldırı yakalama yaklaşık `%20,5` olurken test yanlış alarmı yaklaşık `%7,6`'ya çıktı. Sonuç, eşik seçiminin operasyonel maliyetini açıkça gösteriyor.

## Yorum ve sınır

Test verisindeki saldırı oranı gerçek bir kurum ağından yüksek olabilir; bu nedenle buradaki precision başka bir ağa doğrudan taşınamaz. Veri eski bir araştırma kümesidir. Arayüzün sunduğu aykırılık ipuçları normal alan dağılımlarından türetilir; modelin nedensel açıklaması değildir. Bu sürümün güçlü yanı, veri tekrarlarını denetlemesi ve alarm miktarı ile yakalama oranını dürüstçe karşılaştırmasıdır. Canlı ağ için uygun akış alanlarını yeniden üretmek, modeli yeniden eğitmek ve sahada ayrı doğrulama yapmak gerekir.

## Yeniden üretme

Kurulum ve başlatma komutları [README.md](README.md) içinde. `python train.py` modeli ve metrikleri üretir; `python verify.py` veri ayrımını, 50 örnek skorunu ve rapor metriklerinin tutarlılığını denetler. Tam deney düzeni ve sonraki araştırma fikirleri [PROJE_TASLAGI.md](PROJE_TASLAGI.md) içinde kalır.
