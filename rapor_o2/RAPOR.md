# THYZ 2025 Oturum 2 — Tam Prova Karşılaştırma Raporu

Üretim: `rapor_o2/uret_rapor.py` • Veri: `prova2025/pred_O2full.csv` (tahmin),
`prova2025/oturum2_gt.csv` (gerçek), `prova2025/run_O2full/outbox/pose.txt`
(SLAM durumları).

**Senaryo:** 2250 kare, 4 fps gerçek-zaman temposu, sağlık profili Q&A uyumlu —
0–449 sağlıklı, 450–1199 kesinti, 1200–1259 sağlıklı pencere, 1260–2249 kesinti.
Konfig: `thyz2025_cropA.yaml` @1280 px, sıfırlama-korumalı motor, sönümlü ölü
hesap (τ=40).

## Özet

| Metrik | Değer |
|---|---|
| **Denklem 2 — tam oturum (N=2250)** | **40.23 m** |
| Denklem 2 — yalnız sağlık=0 (N=1740) | 52.02 m |
| Maksimum hata | 207.65 m (kare 2249, kaynak=deadreckon) |
| SLAM kapsaması (sağlık=0 içinde kaynak=slam) | %34.1 |
| Harita sıfırlaması | 2 kez (kareler: 385, 1854) |
| İşlem süresi | ort 0.173 s / p95 0.240 s (bütçe 1,6 s) |

### Kaynak bazlı hata

| Kaynak | N | Ortalama hata (m) | Maks (m) |
|---|---|---|---|
| echo | 510 | 0.00 | 0.00 |
| slam | 593 | 23.01 | 89.87 |
| deadreckon | 1147 | 67.02 | 207.65 |

## Grafikler

1. `1_kusbakisi_yorunge.png` — x-y düzleminde GT (gri) ve tahmin (mavi=sağlık 1,
   turuncu=sağlık 0); kırmızı × = harita sıfırlama anları.
2. `2_eksen_zaman_serileri.png` — x/y/z ayrı panellerde GT vs tahmin;
   gri gölge = sağlık=0 pencereleri; kesikli kırmızı = sıfırlamalar.
3. `3_hata_zaman.png` — anlık Öklid hata; nokta rengi yanıt kaynağı
   (mavi echo / yeşil-aqua slam / sarı deadreckon).

## Okuma notları

- Echo dilimi tanım gereği 0 hatadır (referans aynen geri gönderilir).
- İlk kesintide (450–1199) tahminler ağırlıkla sönümlü ölü hesaptan geldi;
  hata sınırlı kaldı (ort ≈ 29.4 m). İkinci uzun
  kesintide SLAM+hizalama devreye girdi (ort ≈ 69.2 m);
  sıfırlamalar sonrası pencere yeniden kurulana dek ölü hesap taşıdı.
- Palet: dataviz referans paleti (açık mod, sabit slot sırası; belge kaydına göre
  komşu CVD ΔE 24,2 ile geçer). Sarının açık zeminde <3:1 kontrastı nedeniyle
  lejantta N ve ortalamalar metinle verildi (relief kuralı).
