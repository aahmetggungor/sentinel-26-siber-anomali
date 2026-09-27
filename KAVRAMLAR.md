# SENTINEL 26'yı anlayarak anlatmak için kısa notlar

## Ağ akışı nedir?

Bir **paket**, ağdaki tek bir iletim parçasıdır. Bir **akış kaydı**, aynı iletişimle ilgili paketlerden hesaplanmış bir özet satırdır. Bu projedeki CSV'de paketlerin kendisi yoktur; her satırda süre, protokol, servis, durum, gönderilen/alınan paket ve byte sayıları gibi özet özellikler bulunur. Model bir satırı puanlar. `10 kayıt/sn` demo hızı, saniyede 10 ağ paketi yakaladığımız anlamına gelmez.

| CSV alanı | Basit okuma |
| --- | --- |
| `dur` | Akış süresi |
| `proto` | Protokol türü |
| `service` | İlgili ağ servisi |
| `state` | Bağlantı durumu |
| `spkts`, `dpkts` | Kaynak ve hedef yönündeki paket sayıları |
| `sbytes`, `dbytes` | Kaynak ve hedef yönündeki byte miktarları |
| `rate` | Akışın hız/yoğunluk özeti |
| `label` | Sonradan ölçüm için normal (`0`) / saldırı (`1`) etiketi |
| `attack_cat` | Testte tür bazlı analiz için saldırı kategorisi |

`s` ve `d` öneklerini veri kümesinde sırasıyla kaynak ve hedef yönü olarak oku. Bazı alanlar, tek akışın değil, yakın zamandaki benzer akışların sayısı veya TCP zamanlamasının özetidir. Bu alanları daha derin anlatmak gerektiğinde UNSW-NB15'in resmi veri sözlüğüne başvur.

## Anomali tespiti ve etiketli sınıflandırma

**Isolation Forest** yalnızca normal eğitim satırlarını görür. Öğrendiği dağılımdan uzak örneklere daha yüksek anomali skoru verir. Skor tek başına saldırı kanıtı değildir. Birçok saldırı normal trafik gibi görünebilir; bazı normal olaylar aykırı olabilir.

**Random Forest referansı** normal ve saldırı etiketleriyle eğitilir. Bu yüzden daha yüksek test yakalaması, etiketsiz modelin başarısızlığını tek başına kanıtlamaz: iki yaklaşımın eğitime erişimi farklıdır. Karşılaştırma, etiketli örneklerin sağladığı avantajı görünür kılar.

## Karar eşiği ve yanlış alarm

Model skoru eşikten büyük veya eşitse **alarm** üretilir. Eşik düşerse genellikle daha çok saldırı yakalanır, ama daha çok normal akışa da alarm verilir. SENTINEL 26 eşiği test etiketlerine bakarak seçmez; eğitimden ayrılan normal doğrulama akışlarında hedef yanlış alarm yüzdeliğine göre seçer.

| Gerçek durum / karar | Normal kararı | Alarm kararı |
| --- | ---: | ---: |
| Gerçek normal | TN | FP (yanlış alarm) |
| Gerçek saldırı | FN (kaçan saldırı) | TP |

- **Recall:** `TP / (TP + FN)`; saldırıların kaçını yakaladık?
- **Precision:** `TP / (TP + FP)`; alarmların kaçı gerçekten saldırıydı?
- **FPR:** `FP / (FP + TN)`; normal akışların kaçına yanlış alarm verdik?
- **F1:** Precision ve recall'un harmonik ortalaması.
- **PR-AUC / Average Precision:** Eşikler boyunca precision–recall dengesini özetler. Nadir saldırı problemlerinde tek bir doğruluk yüzdesinden daha bilgilendiricidir.

Basit örnek: 1000 akışın 10'u saldırı olsun. Saldırıların yarısı yakalansın (`TP=5`, `FN=5`) ve 990 normalin `%5`'ine yanlış alarm verilsin (`FP≈50`). Precision yaklaşık `5/(5+50) = %9` olur. Demek ki yüksek recall ve küçük görünen FPR bile nadir saldırılarda çok sayıda boş alarma yol açabilir. Laboratuvardaki prevalans tablosu bu hesabı farklı oranlar için yapar.

## Veri sızıntısı neden önemli?

`label` veya `attack_cat` model girdisi olursa model sınavın cevabını önceden görmüş olur. Eğitimdeki aynı özellik satırı testte tekrar edilirse modelin bağımsız bir örneği öğrendiğini sanabiliriz. Bu yüzden üç alan (`id`, `label`, `attack_cat`) modelden çıkarılır; eğitim/test çakışması ölçülür ve ana test sonucu yalnızca tekil/görülmemiş satırlarda verilir. Bu temizleme, verinin sahadaki dağılımını temsil ettiği anlamına gelmez; sadece tekrar yanlılığını azaltır.

## Alarm ipuçlarını nasıl okumalı?

Örneğin `sbytes` normal eğitim kayıtlarının `%99` sınırının üstündeyse ekranda bu alan bir ipucu olarak gösterilebilir. Bu, Isolation Forest kararının gerçekten `sbytes` yüzünden verildiği anlamına gelmez. İpuçları, analistin satıra nereden bakacağını gösterir; nedensel açıklama veya saldırı imzası değildir.

## Öğrenirken bakılacak kaynaklar

- [UNSW-NB15 resmi veri açıklaması](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
- [scikit-learn precision–recall anlatımı](https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html)
- [scikit-learn aykırılık tespiti örnekleri](https://scikit-learn.org/stable/auto_examples/miscellaneous/plot_outlier_detection_bench.html)
