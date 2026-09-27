# Veri kaynağı ve doğrulama

Bu klasördeki iki CSV, [UNSW-NB15'in yayımlanmış eğitim/test ayrımına](https://research.unsw.edu.au/projects/unsw-nb15-dataset) aittir. Üniversitenin sayfası veri tanımını ve akademik kullanım iznini verir; eski doğrudan CSV adresi bugün CSV yerine HTML döndürdüğü için dosyalar [erişilebilir GitHub kopyasından](https://github.com/Nir-J/ML-Projects/tree/master/UNSW-Network_Packet_Classification) indirilmiştir. `download_data.py` dosyası SHA-256 ve satır sayısını doğrular.

| Dosya | Satır | SHA-256 |
| --- | ---: | --- |
| `UNSW_NB15_training-set.csv` | 175341 | `bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa` |
| `UNSW_NB15_testing-set.csv` | 82332 | `734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559` |

Her dosyada 45 sütun bulunur. `id`, `label`, `attack_cat` model girdisi olarak kullanılmaz. Test ayrımının eğitimle çakışan ve kendi içinde tekrarlanan kayıtları ana metrikten ayrılır. Orijinal veri iki CSV dosyası olarak yerelde tutulur; `.gitignore` onları Git'e eklemez. Akademik kullanımlarda veri kümesinin özgün çalışmasına atıf yapılmalıdır: Moustafa ve Slay, *UNSW-NB15: a comprehensive data set for network intrusion detection systems*, MilCIS 2015.
