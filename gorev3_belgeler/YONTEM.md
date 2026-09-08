# Bizim yöntem — nasıl çalışıyor

## Problem

Sunucu bir **referans fotoğrafı** ve bir **kare aralığı** veriyor. O aralıktaki her
karede nesnenin kutusunu göndermemiz gerekiyor. Nesne sınıfı bilinmiyor, eğitim
verisi yok — **tek örnekten tespit** (one-shot detection).

Payload'da güven skoru alanı yok → skorsuz mAP ≈ kesinlik × duyarlılık.
Bu, "emin değilsen gönderme" ile "her karede gönder" arasındaki dengeyi
ölçüm sorusu haline getiriyor.

---

## Boru hattı

```
pencere içindeki her kare
   │
   ├─ 1. FastSAM-s @768 ──────► ~50 sınıf-bağımsız kutu önerisi
   │                            (referanstan BAĞIMSIZ · kare başına BİR kez)
   │                            alan: min 200 px · maks kare alanının %80'i
   │
   ├─ 2. DINOv3-S/16 @224 ────► her önerinin kırpma gömmesi
   │                            %15 bağlam payı · letterbox · fp16 · tek batch
   │                            └─ referansla kosinüs → en iyi 8 aday
   │                               · RENKLİ kare : CLS + ortalama-yama
   │                               · GRİ/TERMAL  : CLS + yama-başına-maksimum
   │                            └─ kutu birleştirme (bölünmüş nesneyi topla)
   │
   ├─ 3. ego-hareket H(t-1→t)  ORB + MAGSAC homografisi
   │
   └─ 4. RefTrack ────────────► "dedektör önce, takipçi veto/doldurma"
                                + %80 ego-hareket harmanı
                                └─ KAPI: kilitli mi VE kutuyu dedektör mü üretti?
                                     └─► kare başına EN FAZLA 1 kutu
```

**N referans aktif olsa da 1. ve 2. adım kare başına bir kez çalışır.** Referans
başına ek maliyet yalnızca bir matmul.

---

## Her adım neden böyle — ölçümlerle

### 1. Öneri: FastSAM, ızgara değil

| yaklaşım | mAP |
|---|---|
| **FastSAM-s @768** | **0.871** |
| ızgara (kayan pencere) | 0.392 |
| SAM (mobile_sam @1024) | 0.656 · **7218 ms/kare** |

Nesneyi segmentleyip kırpmak, rastgele pencerelerden kırpmaktan katbekat iyi.
SAM'in "her şeyi segmentle" kipi hem daha kötü hem bütçenin 4,5 katı.

FastSAM-x (145 MB) < FastSAM-s (24 MB): 0.818 vs 0.871. Büyük model kaybediyor.

Güven eşiği 0.35 en iyi; 0.05'e düşürünce mAP yarıya iniyor — her çöp segment,
referansla yanlışlıkla yüksek kosinüs alma şansı demek.

**`maks_alan` = %80.** Bu sınır, FastSAM'in tüm kareyi kaplayan arka plan
segmentlerini elemek için var. Ama %50'de **doğru kutuyu da eliyordu**: v2-05
(beton saha) GT alan oranı 0.485'e çıkıyor, nesneyi iyi saran öneriler %50'yi
aşıp süzgece takılıyordu. %80'e çıkarmak termalde **+0.083** kazandırdı,
v1'de −0.009 ödetti. On koşulda doğrulandı.

### 2. Gömme: küçük omurga kazanıyor

| model | mAP |
|---|---|
| **DINOv3-S/16** | **0.871** |
| DINOv3-B/16 | 0.789 |
| DINOv3-L/16 | 0.697 |
| DINOv3-L sat493m (uydu ön-eğitimli) | 0.240 |
| DINOv2 | 0.62 |
| CLIP | 0.32 |
| SigLIP | 0.18 |

Tam monoton ve sezgiye aykırı. Uydu görüntüleriyle eğitilmiş model neredeyse en
kötüsü: kareler nadir havadan ama **referans** tarafı eğik/yer seviyesi fotoğraf,
yani model yanlış yöne uzmanlaşmış.

**%15 bağlam payı**: 0.8063 → 0.9170. %30 yıkıcı. Uyarlanır (piksel hedefli) pay
denendi ve reddedildi — gerekçe `06_KARARLAR/`'da.

**Gri/termal karede yama düzeyinde skorlama.** Kırpmanın yama tokenlarının
*ortalaması*, nesnenin ayırt edici yamalarını arka planla seyreltiyor. Renk varken
sorun değil; renk gidince global istatistikler bozuluyor. O yüzden gri/termal
karede her öneri yaması için referans yamaları üzerinde **maksimum** kosinüs alınıp
ortalanıyor, üstüne **döngüsel tutarlılık süzgeci** uygulanıyor (yamadan referansa
git, geri dön; aynı yere düşmüyorsa at).

Ağırlık `s = 0.70·s_cls + 0.30·s_appe`, δ=5, ön plan maskesi 0.87.
Sekiz koşulda net **+0.200**. Ek maliyet yok — aynı ileri geçiş, farklı skorlama.

Koşul `is_grayish(kare)` ile çalışma anında belirleniyor. **Bu bir eşik değil,
yapısal bir ayrım** — renkli karede kod yolu hiç değişmiyor.

### 3–4. Zamansal katman: en büyük tek kaldıraç

**%80 ego-hareket harmanı**: 0.9149 → **0.9754**.

Dedektörün kutusu kare kare titriyor; ego-hareketle taşınan tahmin pürüzsüz ama
zamanla kayıyor. %80 tahmin + %20 dedektör ikisinin de zayıflığını kapatıyor.

**Kritik ayrıntı:** harman 1.0'da (saf taşıma) **düşüyor**. Yani takipçi dedektörün
yerine geçemiyor, sadece titremesini yumuşatıyor.

"Aynı yer mi?" testinde IoU değil **IoMin** (kesişim / küçük kutunun alanı)
kullanılıyor: halı saha gibi kenardan kırpılan nesnelerin görünen alanı kare kare
değişiyor, IoU ile test doğru tespitleri veto ediyordu (0.868 → 0.711).

---

## Gönderim kapısı — yöntemin en ayırt edici kısmı

Payload'da güven alanı olmadığı için "kararsızken de gönder" cazip. Ama pencere
görünürlükten geniş olduğundan kenarlarda nesne yok.

| kapı (pay = ±10 kare) | v1 | v2 |
|---|---|---|
| her karede gönder | 0.5785 | 0.4779 |
| kosinüs eşiği 0.60 | 0.6497 | 0.4887 |
| kosinüs eşiği 0.65 | **0.4425** | **0.5165** |
| takipçi kilitli | 0.6221 | 0.4994 |
| **kilit + dedektör kaynaklı** | **0.6407** | **0.5090** |

**Mutlak eşik videolar arası TAŞINMIYOR.** v1'i uçurumdan atan 0.65 değeri,
v2'nin en iyisi. Sabit eşik seçmek yarışmada kumardır — ve repodaki yöntemin
temel sorunu tam olarak budur.

Yerine iki **ölçeksiz** sinyal:

1. **Takipçi kilitli mi?** Nesne pencereye girmediyse takipçi kilitlenemez.
2. **Kutuyu bu karede dedektör mü üretti?** Nesne pencereden çıkınca dedektörün
   top-1'i ize uymaz, iz yayılmaya devam eder — ve biz susarız.

v1'de 5/5 referansta pozitif, %90 güven aralığı [+0.012, +0.025].

**Ters yönü de ölçüldü:** nesnenin pencerenin her karesinde bulunduğu biliniyorsa
kapı **zararlıdır** (v1 0.9778 → 0.9051). O durumda `emit_policy="always"`.

---

## Uyarlanır referans görünümü — geniş çekim referans riski

Sistem, referansta nesnenin **büyük** olacağını varsayıyordu. Bozunum sınavı bu
varsayımın ne kadar kırılgan olduğunu göstermişti: nesne referansın 1/16'si
olduğunda mAP 0.905 → 0.460. Ölçek piramidi kurtarıyor ama **sıkı** referansta
bedel ödetiyor — bu yüzden daha önce bir **karar noktası** olarak bırakılmıştı
("geniş çekim gelme olasılığı %11–29'u geçerse piramide geçin").

**Artık bahis yok.** Taban banka `tam`; ama takipçi **5 kare boyunca hiç
kilitlenmezse** — yani hiçbir aday tutmuyorsa — banka ölçek piramidiyle
kendiliğinden genişletilir. Sıkı referansta kilit ilk karelerde oluşur, ek banka
**hiç açılmaz**, bedel tam sıfırdır.

| koşul | `tam` | sabit `piramit` | **uyarlanır** |
|---|---|---|---|
| nesne referansın 1/16'si (v2_termal, pay=10) | 0.1569 | 0.5254 | **0.5334** |
| nesne referansın 1/16'si (v1_640, pay=10) | 0.3005 | 0.5468 | **0.5552** |
| bozulmamış referans (v2_termal, pay=10) | 0.6209 | — | **0.6209** |
| bozulmamış referans (v1_640, pay=10) | 0.5797 | — | **0.5797** |

Üretim paketiyle uçtan uca: v2_termal pay=10, referans 1/16 →
**0.1505 → 0.5121 (+0.362)**; teslim edilen rakamlarda değişiklik **yok**.

---

## Çapraz-modal köprü — referans RGB, video termal

Şartnamenin açıkça istediği ve örnek veri setinde **fiilen gerçekleşen** durum:
mühürlü termal videonun 6 referansından 4'ü nadir **RGB kırpma**. O sınıftan şu
ana kadar sıfır alınıyordu.

**Neden zor:** DINOv3 gömmesi renk/parlaklık ilişkisine dayanıyor; termalde
parlaklık sıcaklıktır, RGB'de albedodur. İkisi ilişkisiz.

**Denenip elenen basit çözüm:** referans bankasına sabit bir "köprü" görünüm
eklemek. Ölçüldü — sabit hiçbir görünüm iş görmüyor:

| eklenen görünüm | ters-polariteli karede | düz gri karede |
|---|---|---|
| polarite tersi | **+0.074** | **−0.028** |
| gradyan (yapı) | +0.009 | +0.007 |
| ikisi birden | **+0.083** | **−0.024** |

Polarite tersi görünüm yalnızca **kareler ters polariteliyse** kazandırıyor.
Termal kameranın beyaz-sıcak mı siyah-sıcak mı olduğunu yarışmada bilmiyoruz —
yani sabit seçim kumardır.

**Yaptığımız: köprüyü videodan okumak.** Referans yüklenirken polarite tersi
kopyası hazırlanır; **ilk 3 gri karenin önerileri üzerinde** taban gri görünümle
yarıştırılır; yalnız tabanı geçerse bankaya eklenir. Mutlak eşik yok — adaylar
sadece birbirleriyle kıyaslanır, dolayısıyla videodan videoya taşınır.

**Koşul sağlanmazsa hiç çalışmaz.** Kareler renkliyse veya referans zaten griyse
dal açılmaz; bedeli **yapısal olarak sıfırdır**.

Üretim paketiyle ölçüldü:

| küme | koşul | kapalı | açık | fark |
|---|---|---|---|---|
| RGB nadir referans → termal kare | pay=0 | 0.5320 | **0.5751** | **+0.0431** |
| RGB nadir referans → termal kare | pay=10 | 0.3874 | **0.4507** | **+0.0633** |
| RGB fotoğraf referans → sahte-termal | pay=0 | 0.4410 | 0.4356 | −0.0054 |
| RGB fotoğraf referans → sahte-termal | pay=10 | 0.3171 | **0.3283** | **+0.0112** |
| v1_rgb (renkli) | pay=10 | 0.6379 | 0.6379 | 0.0000 |
| v2_termal (termal referans) | pay=0/10 | 0.7585 / 0.5719 | aynı | 0.0000 |

**Açık maliyet:** "RGB referans → düz gri video" sondasında −0.0280. Düz gri video
şartnamede bir senaryo değil (RGB ve termal kamera var); buna karşılık çapraz-modal
durum örnek veri setinde gerçekten görüldü.

Ayrıntı ve elenen varyantlar: `KARARLAR.md`.

---

## Dondurulmuş ayarlar

`ayarlar.json` dosyasına bakın. Kodda her sabitin yanında hangi ölçümden geldiği
yazılıdır — bir değeri değiştirmeden önce oradaki notu okuyun.

## Yarışma günü

```
python -m gorev3_v2.onkontrol           # ağırlıklar yerinde mi, süre bütçede mi
```

İlk çağrı gerçek karede **4,02 sn** sürüyor (model ısınması) — bütçenin 2,5 katı.
Ön kontrol bu bedeli önceden ödetir. Isınmış kare 0,15–0,36 sn.

Paket içe aktarılırken çevrimdışı kip otomatik açılır (`HF_HUB_OFFLINE=1`);
yarışmada internet yok ve ağ zaman aşımı sahada "neden takıldı" sorusu sordurur.

**Entegrasyonun üç zorunlu kuralı** `kod/README.md`'de — özellikle pencere
açılışında `reset_reference()` çağrısı.
