# Bilinen sınırlar ve çalışma aralığı

Yöntemin nerede çalıştığı kadar **nerede çalışmadığı** da ölçüldü.
Bu belge, sahada sürpriz olmaması içindir.

---

## 1. Çözülemeyen iki referans sınıfı

| Sınıf | Örnek | Neden |
|---|---|---|
| **Yer seviyesi cephe fotoğrafı → nadir kare** | v1-06 (ahşap panelli çit) | Cephe ile çatının **ortak yüzeyi yok**. Nadir karede duvar görünmüyor. 40 aday = 40 farklı çatı, skorlar 0.54–0.60'ta yığılı. Literatür: yerden-uyduya eşleştirme %1.20, eğik-görüntüden-uyduya %58.49 (aynı 951 bina). |
| **RGB referans → termal kare** | v2-01…04 | Aynı bakış açısı, yalnızca modalite farkı. Nesneler termal videoda elle bulunamadı → **yer gerçeği yok**, ölçülemiyor. **Gece koşusunda bu sınıfa doğrudan bir yetenek eklendi** (çapraz-modal köprü): yer gerçeği olan eşdeğer kümede 0.3874 → 0.4507. Bu dört referansta doğrulanamaz ama artık kör değiliz. |

**Rapordaki bütün rakamlar çözülebilir 7 referans üzerinde ölçüldü.**
Örnek veri setinde 12 referansın 5'i bu sınıflardaydı.

Yarışmada bu tipten bir referans gelirse o referanstan sıfır alınır — hem bizde
hem repoda. **Tek bir sınıfı çözmek, tüm ayar taramasından daha fazla puan getirir.**

---

## 2. Çalışma aralığı — piksel cinsinden ve METRE cinsinden

Ampirik olarak ölçüldü (çözünürlük türevleriyle):

| Nesnenin kenar uzunluğu | AP |
|---|---|
| ~120 px ve üstü | 0.88–0.95 |
| ~90 px | 0.79–0.95 |
| ~47 px | 0.34 |
| **~41 px** | **0.88** |
| **~31 px** | **0.21** |

**Sınır ~40 piksel.** On piksellik bir aralıkta dört kat fark var.

### Bu sınır termal videoda, gerçek nesnelerle doğrulandı (gece koşusu)

Yukarıdaki tablo çözünürlük türevlerinden **dolaylı** geliyordu. Mühürlü videodan
geometriyle üretilen 12 referanslık küme (31–97 px araçlar, 316 kare) doğrudan
ölçüldü:

| küme | referans | nesne kenarı (ortanca) | mAP pay=0 | mAP pay=10 |
|---|---|---|---|---|
| v2 termal (elle denetlenmiş) | 2 | **212 px** | 0.7585 | 0.5719 |
| **v2 termal · geniş küme** | **12** | **61 px** | **0.2561** | **0.2795** |

`<50 px` ortalama AP **0.106** · `≥50 px` ortalama AP **0.403**.

> **Bu, teslim rakamlarının nasıl okunacağını değiştirir.** Mühürlü videodaki
> 0.7585 / 0.5719, nesne kenarı 94 ve 329 px olan **iki büyük nesneyi** anlatıyor.
> Yarışmada referans küçük bir araçsa beklenti çok daha düşük olmalı.

**Arıza öneride değil, sıralamada.** Her GT karesinde "öneriler arasında IoU ≥ 0.25
olan var mı" sayıldı: tavan **0.776** (≥50 px'te **0.941**), elde edilen 0.280.
Sıfır alan üç referansın öneri tavanı 0.688 / 0.947 / 1.000 — doğru kutu üretiliyor,
seçilemiyor. Sahnede birbirinin aynı çok sayıda araç var.

**Denenip elenen düzeltme:** bağlam payını kutu boyutuna bağlamak. Küçük nesnede
daha sıkı kırpma tekdüze biçimde daha iyi (pay 0.45→0.05: 0.2198→0.3274), ama
boyuta bağlı kural mühürlü sette **tekdüze olmayan** sonuç veriyor
(eşik 0/30/40/60 → 0.5719 / 0.5046 / 0.5916 / 0.4745). Kod pakette var,
**varsayılan kapalı** (`kucuk_esik=0`). Ayrıntı: `KARARLAR.md`.

**Ölçülüp seçenek olarak bırakıldı — takipçi uyum eşiği.** Teşhis: küçük nesnede
kilit **hiç kurulamıyor** (sıfır alan üç referansın ikisi pencere boyunca tek kutu
gönderiyor). Küçük kutu birkaç piksel oynayınca IoMin ≥ 0.45 uyum şartı sağlanmıyor.
Eşik 0.30'a indirilince:

| küme | pay | 0.45 | 0.30 |
|---|---|---|---|
| v2 termal (mühürlü) | 10 | 0.5719 | **0.6081** |
| v2 termal geniş küme | 10 | 0.2795 | **0.3010** |
| v1 RGB | 10 | 0.6379 | 0.6317 |
| **v1 gri sonda** | 10 | 0.5276 | **0.4766** |

Tepki tekdüze (0.45/0.40/0.35 aynı, basamak 0.30'da) — gerçek bir etki, gürültü
değil. Ama gri sondadaki −0.051 "hiçbir rejimde zarar yok" ölçütünü ihlal ettiği
için **varsayılan 0.45 kaldı**. Yarışma videosunun nesneleri küçükse `agree=0.30`
tek satırla açılır ve mühürlü videoda +0.036 getirir.

### Tam teşhis: bütün kapılar BÜYÜK nesneye göre ayarlanmış

12 referanslık küçük-nesne kümesinde her kapı tek tek kapatıldı (pay=10):

| değişiklik | mAP | isabet | fark |
|---|---|---|---|
| **mevcut** | 0.2795 | 0.447 | — |
| bağlam payı 0.15 → 0.05 | **0.3274** | 0.545 | **+0.0479** |
| dedektör kapısı kapalı | **0.3018** | 0.518 | **+0.0223** |
| uyum eşiği 0.45 → 0.30 | **0.3010** | 0.475 | **+0.0215** |
| `emit_policy="always"` | 0.2635 | 0.529 | −0.0160 |
| uyum ölçütü boyuta göre (`kucuk_px=50`) | 0.2688 | 0.453 | −0.0107 |

Her gevşetme küçük nesnede kazandırıyor — ama **aynı gevşeme büyük nesnede
kaybettiriyor**: dedektör kapısı v1'de +0.018, uyum 0.30 gri sondada −0.051,
bağlam payı mühürlüde tekdüze olmayan sonuç. `always` ise iki tarafta da kötü:
isabet yükseliyor (0.529), kesinlik çöküyor.

Boyuta-koşullu ilk deneme (küçük kutuda IoMin yerine merkez mesafesi) **transfer
etmedi** (−0.0107): küçük kutular birbirine daha kolay uydu ve takipçi yanlış
şeylere daha hızlı kilitlendi.

**Açık kalan en değerli iş kalemi, tam olarak şudur:** kapı politikasını nesne
boyutuna göre ayrıştırmak. Sinyal elimizde (aday kutunun piksel boyutu, kare
başına bedava), yön belli (küçükte gevşe, büyükte sıkı kal), ama ilk deneme
tutmadı. Değeri büyük: küçük nesnede öneri tavanı 0.55–0.94 iken elde edilen
0.106–0.403 — yani kayıp tamamen kapılarda, tespit yeteneğinde değil.

### Fiziksel karşılığı

Örnek veri setindeki `translation.csv` ve `Kamera_Kalibrasyon_Parametreleri_2026.txt`
kullanılarak uçuş irtifası çözüldü: ORB'un ölçtüğü piksel hareketi ile telemetrinin
verdiği metrik hareketin oranı `f/Z` verir.

| video | odak f | çözülen irtifa | 40 px karşılığı |
|---|---|---|---|
| v1 RGB 1080p | 1390 | **~42 m** | **1,20 m** |
| v2 termal | 732 | **~32 m** | **1,72 m** |

**Kural:** `en küçük güvenilir nesne ≈ 40 · Z / f`

Yani takım için kullanılabilir hâli: *tipik uçuş irtifasında **~1,2–1,7 metreden
küçük** nesnelere güvenmeyin.* İki katı irtifada sınır da iki katına çıkar.

> Not: irtifa doğrudan verilmiyor; z-bileşeni başlangıca göre yükseklik farkı.
> Yukarıdaki değerler piksel/metre oranından **çözüldü** ve iki bağımsız videoda
> makul çıktı (42 m ve 32 m). Kesin değil, mertebe doğru.

**Mekanizma teşhis edildi:** çözünürlük düşünce **öneri aşaması bozulmuyor**
(FastSAM 31 px nesneyi bile buluyor, tavan 1.000) — çöken şey **sıralama**.
Top-1 doğruluğu 94 px'de 0.961, 47 px'de 0.667, 31 px'de 0.627.

---

## 3. Bozulma dayanıklılığı — hangi arıza nereden vuruyor

v1 videosundan türetilmiş formatlarla, **dağıtılan üretim paketiyle**, `pay=0`
koşulunda ölçüldü (taban v1 RGB 1920×1080 = **0.8960**):

| Bozulma | mAP | kayıp | Hangi aşamadan | Kimin kontrolünde |
|---|---|---|---|---|
| 960×540 | 0.8021 | −0.094 | yalnız sıralama | irtifa/zoom |
| 640×360 | 0.7377 | −0.158 | yalnız sıralama | irtifa/zoom |
| 640 gri (mono kamera) | 0.7449 | −0.151 | sıralama | kamera |
| 640 + **JPEG q40** | 0.5551 | −0.341 | sıralama | **sunucu** |
| 640 + **bulanıklık** (σ≈5) | 0.5297 | −0.366 | **öneri + sıralama** | **BİZ** |
| 640 sahte-termal | 0.4356 | −0.460 | temsil | sensör |
| 640 + bulanık + JPEG | 0.3712 | −0.525 | ikisi birden | — |

> Bu tablo gece koşusunda **yeniden ölçüldü.** Önceki sürümü arenanın taban yolundan
> (taban 0.9051) geliyordu; buradaki rakamlar dağıtılan paketin kendisinden. Sıralama
> aynı kaldı, mutlak değerler kaydı. En belirgin fark **640 gri** satırında:
> 0.6712 → 0.7449; gri karede yama düzeyinde skorlama ve çapraz-modal köprü birlikte
> çalışıyor.

**Eyleme dönüşen bulgu: bulanıklık ile sıkıştırma aynı mertebede zarar veriyor**
(640 tabanına göre −0.208 ve −0.183) — ama tek fark şu: sıkıştırma **sunucunun**
elinde, bulanıklık **bizim** elimizde. Görev 3'ün puanı için gimbal kararlılığı,
akış kalitesinden önce gelir.

> Önceki sürümde bu fark daha keskin görünüyordu (−0.211 vs −0.144). Üretim
> paketiyle yeniden ölçülünce ikisi birbirine yaklaştı; **yön aynı, aradaki
> mesafe küçüldü.** Sonuç değişmiyor: kontrol edebildiğimiz tek kalem bulanıklık.

---

## 4. Referans fotoğrafının çerçevelemesi — açık risk

Sistem, referansta nesnenin büyük olacağını **varsayıyor**. Bozulma sınavı:

| Referans bozunumu | mAP | kayıp |
|---|---|---|
| (bozulmamış) | 0.9051 | — |
| 15° dönük | 0.8863 | −0.019 |
| bulanık | 0.8839 | −0.021 |
| 90° dönük | 0.8359 | −0.069 |
| nesne referansın ¼'ü | 0.8174 | −0.088 |
| **nesne referansın 1/16'sı** | **0.4603** | **−0.445** |

Dönme ve bulanıklık sorun değil. **Geniş çekim referans ise sorun.**

**BU KARAR NOKTASI KAPATILDI (gece koşusu).** Önceki hâlde seçenek "sabit ölçek
piramidi" idi: en kötü durumu düzeltiyor ama sıkı referansta −0.12 ödetiyor, yani
"geniş çekim gelme olasılığı %11–29'u geçer mi?" diye bahis gerektiriyordu.

Artık banka **koşula bağlı** genişliyor: takipçi 5 kare boyunca hiç
kilitlenmezse (hiçbir aday tutmuyor → referans muhtemelen geniş çekim) ölçek
piramidi kendiliğinden eklenir. Sıkı referansta kilit ilk karelerde oluşur, ek
banka hiç açılmaz.

| koşul | `tam` | sabit `piramit` | **uyarlanır (yeni varsayılan)** |
|---|---|---|---|
| nesne referansın 1/16'si · v2_termal | 0.1569 | 0.5254 | **0.5334** |
| nesne referansın 1/16'si · v1_640 | 0.3005 | 0.5468 | **0.5552** |
| bozulmamış referans · v2_termal | 0.6209 | — | **0.6209** (bedel sıfır) |
| bozulmamış referans · v1_640 | 0.5797 | — | **0.5797** (bedel sıfır) |

Üretim paketiyle uçtan uca doğrulandı: v2_termal pay=10, referans 1/16 →
**0.1505 → 0.5121**; teslim rakamlarında değişiklik yok.

Kapatmak gerekirse: `adaptive_views=0`.

---

## 5. Ölçüm tabanının sınırı

2 video · 7 referans · ~650 etiketli kare. v2'de **tek karenin mAP etkisi ~0.025**.

±0.03'ün altındaki farklar bu sette karar verdirmez ve öyle muamele edildi.
Üçüncü bir video, yapılabilecek en değerli tek eklemedir.

---

## 6. Denenip elenen fikirler

Ayrıntılı gerekçeleri `KARARLAR.md`'de. Özet — **yeniden denemeye değmez**:

| Fikir | Sonuç |
|---|---|
| Negatif banka (arka plan bastırma) | 0.2516 — felaket. Literatür bağımsız doğruladı (−21.9 mIoU) |
| Online referans bankası | 0.917 → 0.80, banka kirleniyor |
| Çok-görünüm / döndürme artırımı | sıkı referansta zararlı |
| SAM / SAM2 önerileri | 0.656 ve 7218 ms/kare |
| Büyük omurgalar (DINOv3 B/L, DINOv2, CLIP, SigLIP) | hepsi DINOv3-S'in altında |
| Uydu ön-eğitimli DINOv3-L | 0.240 |
| Polarite tersi referans görünümü | dört videoda da kazandırmıyor |
| SOC (gradyan yönelim korelasyonu) | yama testinde %100, uçtan uca **0.0002** |
| Uyarlanır bağlam payı | hipotezi yalanlandı; çapraz-modalde ters çalışıyor |
| `kirpma=288` | renkli rejimde iyi, termalde −0.117 |
| Metin aracılı yol (VLM + açık-sözlük dedektör) | nadir görüntüde metin istemi 11.67 mAP, görsel örnek 66.55 |
