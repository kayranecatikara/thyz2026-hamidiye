# Görev 3 — belgeler

Kod: `../gorev3_v2/` (beş dosya, ~180 KB). Entegrasyon tek satır:
`istemci/TAKIM_BAGLANTI_ARAYUZU/src/object_detection_model.py` içinde

```python
from gorev3_v2.api import ReferenceObjectDetectorV2 as ReferenceObjectDetector
```

Çağrı imzası önceki hibrit sistemle **birebir aynı**
(`detect_for_frame(kare_yolu, ref_url, ref_gorsel_yolu, video_name=...)`),
bu yüzden çağıran taraf hiç değişmedi.

## Nereden başlamalı

| Dosya | İçerik |
|---|---|
| **`KIYAS_RAPORU.html`** | **Buradan başlayın.** Önceki yöntemle yan yana karşılaştırma — sayılar + kare kare görüntüler. Tarayıcıda açılır, görseller dosyanın içinde, internet gerekmez. |
| `YONTEM.md` | Yöntem nasıl çalışıyor, her adım neden böyle |
| `SINIRLAR.md` | **Nerede çalışmıyor** — çalışma aralığı, bozulma dayanıklılığı, çözülemeyen referans sınıfları |
| `KARARLAR.md` | Kabul/red kararlarının tamamı, gerekçeleriyle |
| `OLCUM.md` | Yer gerçeğinin nasıl üretildiği — rakamların geçerliliği buna dayanıyor |
| `PROTOKOL_NOTLARI.md` | Resmî arayüz kodundan çıkarılan, şartnamede yazmayan ayrıntılar |
| `GENIS_KIYAS.md` | Videodan geometriyle üretilen büyük örneklemli teyit kümesi |
| `AGIRLIKLAR.md` | Model ağırlıkları — **depoyla birlikte geliyor**, indirme adımı yok |

## Bir bakışta

mAP @ IoU 0.25, skorsuz (payload'da güven alanı yok → mAP ≈ kesinlik × duyarlılık):

| Koşul | Bu yöntem | Önceki hibrit |
|---|---|---|
| v1 RGB · nesne her karede | **0.8960** | 0.5462 |
| v1 RGB · gerçekçi (pencere paylı) | **0.6379** | 0.3990 |
| v2 termal · **mühürlü** · nesne her karede | **0.7585** | 0.0519 |
| v2 termal · **mühürlü** · gerçekçi | **0.5719** | 0.0519 |
| kare başına süre | **153–279 ms** | 329–5088 ms |

`v1` bu yöntemin ayarlandığı videodur, dolayısıyla taraflıdır. **Tarafsız kanıt
`v2` satırlarıdır** — iki yöntem de o veriyi görmeden koştu.

## İki not

**`arena/...` atıfları.** Belgelerde geçen `arena/dogrula_uretim.py` gibi yollar,
ölçümlerin yapıldığı **ayrı** çalışma tezgâhına aittir (8,5 GB: ham kareler,
önbellekler, rakip kurulumu). Bu depoda yok; rakamları yeniden üretmek isteyen
o klasöre ihtiyaç duyar.

**Rakamlar büyük nesneleri anlatıyor.** Mühürlü videonun puanlanabilir iki
referansı 94 ve 329 piksel. Aynı videodan geometriyle üretilen 12 referanslık
küçük-nesne kümesinde (31–97 px) mAP 0.28. Ayrıntı: `SINIRLAR.md` §2.
