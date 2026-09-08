# Ölçüm yöntemi — bu rakamlara neden güvenilebilir

Bu belge en önemlisi. Bir karşılaştırma, ancak ölçüm zinciri sağlamsa bir şey
ifade eder — ve repodaki yöntemin asıl sorunu tam olarak burada başlıyordu.

---

## 1. Yer gerçeği hiçbir dedektörden gelmiyor

**Kaçınılan hata.** Repodaki sistemin kalibrasyonu döngüseldi: mini-doğrulama
etiketleri `label_minival.py --proposals` ile **sistemin kendi önerileriyle**
dolduruldu, sonra o etiketlerle eşik ayarlanıp AP 0.99 raporlandı. Sistem kendi
bulduğu kutuları "doğru cevap" kabul edip kendini onayladı.

**Bizim yol — üç bağımsız kanal:**

| Kanal | Nasıl |
|---|---|
| **Çapa + yayılım** | Gözle onaylanan tek bir görüşten başlanıp pencerenin tamamı **ego-hareket homografisiyle** dolduruldu. Bu adım hiçbir dedektörün çıktısını kullanmaz. |
| **Bağımsız segmentasyon** | Halı saha (sahne referansı) GT'si çim rengi + düşük doku ile ayrı ayrı çıkarıldı; hiçbir yönteme avantaj sağlamaz. |
| **Gözle ayıklama** | Her seri kare kare denetlendi. Çim segmentasyonu kiremit çatıyı ve sürülmüş tarlayı da "saha" sanmıştı — **4 sahte pencere elendi**, 397 kare 367'ye indi. |

Kimliği belirlenemeyen referanslar **dışarıda bırakıldı, uydurulmadı**.

---

## 2. Metrik

**mAP @ IoU 0.25, skorsuz.**

- IoU eşiği **0.25**: resmî TEKNOFEST reposunun README'sinden. Şartname 9.3
  "detaylar revizyonda" diyor. Repodaki `gorev3` kodu **0.5** varsayarak kalibre
  edilmişti — yanlış çalışma noktası.
- **Skorsuz**: `ReferencePrediction` payload'ında güven alanı yok, dolayısıyla
  sıralama yapılamıyor ve mAP ≈ kesinlik × duyarlılık.

Bunun sonucu: **duyarlılık sıfırsa AP de sıfırdır.** Repo v2-06'da hiç kutu
göndermediği için o referanstan matematiksel olarak 0 alıyor.

---

## 3. İki koşul neden ölçülüyor

Sunucunun verdiği pencere gerçek görünürlükten **geniştir**. 16 Temmuz oturumunda
referans 1'in penceresi 161–205'ti, biçerdöver 173–203 arasında görünüyordu.

- **pay = 0** — nesnenin her karede bulunduğu varsayımı. Saf konumlandırma yeteneği.
- **pay = ±10 kare** — yarışma gerçeğine yakın. Kenarlarda nesne yok, oraya atılan
  her kutu saf yanlış pozitif. **Karar bu satıra göre verilir.**

Bir ayarı yalnızca `pay=0`'da ölçüp kabul etmek, bu projede yapılmış ve sonradan
yakalanmış bir hatadır (bkz. `KARARLAR.md`, yama skorlama ağırlığı).

---

## 4. Aşırı uyuma karşı üç savunma

**Mühürlü sınav.** v2 termal video tek seferlik koşuldu ve kilit dosyasıyla korundu.
Sonuç dürüsttü: gelişme setinden sınava düşüş **−0.285**. Daha kötüsü, v1'de
0.9754–0.9778 arasında sıralanan beş finalist v2'de 0.683–0.708'e sıkıştı —
aralarındaki fark tamamen kayboldu. Son turlarda kovalanan küsurat gürültüymüş.

> Not: sonraki turda `maks_alan` kararı v2'ye bakılarak verildi, dolayısıyla
> **v2 artık tam anlamıyla mühürlü değildir.** Bu, kararların yanında açıkça yazılıdır.

**Bootstrap güven aralığı.** Kazananın %90 alt sınırı 0.933 ve 14 yapılandırma bunun
üstünde. "0.9778 en iyisidir" demek bu veri boyutunda savunulamaz. Bu yüzden en
tepedeki değil, **en sağlam ve en basit** olan donduruldu.

**Birleşim doğrulaması.** Tek tek kazanan ayarların toplamı geçerli değildir.
Ölçüldü: tek tek tabanı geçen yedi ayarın hepsi bir arada **0.871 → 0.779**.
Bu yüzden her kabul, birleşik yapılandırmayla yeniden koşulup doğrulanır.

---

## 5. Bağımsız ikinci uygulama

Ölçüm arenası ile teslim edilen paket **ayrı kod tabanlarıdır**.
`arena/dogrula_uretim.py`, paketi arenanın önbelleğini hiç kullanmadan — kendi
FastSAM'i, kendi gömücüsü, kendi ego-hareketiyle — aynı yer gerçeğine karşı koşar.

Bu kontrol **dört ayrı hata yakaladı**, hepsi sessizce yanlış sayı üretiyordu:

| # | Hata | Etkisi |
|---|---|---|
| 1 | Ego-hareket önbelleği artımlı değildi | Gerçekçi-koşul rakamları şişkindi (v1 0.696→0.622, v2 0.680→0.499) |
| 2 | Dedektör-kapısı yamalarından biri sessizce tutmamıştı | Kapı hiç ateşlenmiyordu |
| 3 | Batch dosyasında `\b` kaçış dizisine dönüşmüştü | Doğrulama koşusu hiç çalışmamıştı |
| 4 | Arenada CLS-only, üretimde birleşik vektör | Termal sonuçlar 0.7747 yerine 0.7406 |

Hiçbiri hata vermiyordu; sadece yanlış sayı üretiyorlardı. **Tek uygulamaya
güvenilseydi dördü de sessizce yayımlanacaktı.**

---

## 6. Ölçüm tabanının sınırı — açıkça

2 video · 7 puanlanabilir referans · ~650 etiketli kare.

**Ayırt edebildiği:** büyük farklar (0.73 vs 0.05).
**Ayırt edemediği:** küçük farklar. v2'de **tek bir karenin mAP etkisi ~0.025**
(2 referans, 201 kare). Bu yüzden ±0.03'ün altındaki farklar bu sette karar
verdirmez ve öyle muamele edildi.

Üçüncü bir video, bu projede yapılabilecek en değerli tek eklemedir.
