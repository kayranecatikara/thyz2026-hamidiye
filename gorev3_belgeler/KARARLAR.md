# Genelleme turu — kabul/red kararları ve gerekçeleri

Amaç bu iki videoda puan yükseltmek DEĞİL; yarışmada gelecek **görmediğimiz** video
ve referanslarda çökmemek. Kabul ölçütü buna göre:

1. Bir rejimi düzeltip diğerini bozan ayar **kabul edilmez** (hangisinin geleceğini bilmiyoruz).
2. Sihirli sayı **eklemek** yerine **kaldırmak** tercih edilir.
3. Eşik yerine ölçeksiz sinyal tercih edilir (mutlak eşiklerin taşınmadığı ölçüldü).
4. Güven aralığı sıfırı içeren kazanç kabul edilmez.

---

## KABUL EDİLDİ

### `oneri.maks_alan` : 0.50 → 0.80

| | v1 pay0 | v1 pay10 | v2 pay0 | v2 pay10 |
|---|---|---|---|---|
| 0.50 | 0.9051 | 0.6407 | 0.6531 | 0.5077 |
| **0.80** | 0.8960 | 0.6379 | **0.7360** | **0.5910** |
| 0.95 | 0.8966 | 0.6341 | 0.7360 | 0.5910 |

**Gerekçe.** Bu sınır "gerçek nesne karenin yarısından büyük olmaz" varsayımıydı ve
FastSAM'in tüm kareyi kaplayan arka plan segmentlerini elemek için konmuştu. Ölçüm
gösterdi ki artık **doğru kutuyu eliyor**: v2-05 (beton saha) GT alan oranı 0.485'e
çıkıyor, nesneyi iyi saran öneriler 0.5'i aşıp süzgece takılıyordu.

- v1'de bedeli sabit ve küçük (−0.009), termalde kazancı büyük (+0.083), **iki koşulda da**.
- 0.80 ve 0.95 birebir aynı → bir platonun ortasında, kenarına ayarlanmış değil.
- Kırılgan bir mutlak varsayımı **kaldırıyor**: alçak irtifadan çekilmiş bir videoda
  veya büyük bir sahne referansında eski sınır doğru nesneyi elerdi.

**Dürüstlük notu:** bu değişiklik v2'ye bakılarak seçildi, yani v2 artık mühürlü bir
sınav değil. Ama gerekçesi v2'ye özgü değil — kaldırılan şey bir varsayım, eklenen
bir ayar değil, ve v1'de bedelsiz olduğu ayrıca doğrulandı.

### `gomme.kirpma` 224 → 288 — ÖNCE KABUL EDİLDİ, SONRA GERİ ALINDI

Tek başına iki rejimde de pozitifti (+0.006 büyük, +0.031 küçük) ve "kesin kabul"
diye kaydedilmişti. **Birleşim doğrulaması bunu çürüttü.**

| v1_640 (küçük nesne) | mAP |
|---|---|
| taban | 0.7418 |
| uyarlanır 80 tek | **0.8219** (+0.080) |
| k288 tek | 0.7732 (+0.031) |
| **uyarlanır 80 + k288** | **0.7323 (−0.010)** |

İkisi de gömücüye "daha fazla içerik" veriyor — biri bağlam, diğeri çözünürlük olarak —
ve birlikte hedefi aşıp nesneyi yeniden seyreltiyorlar.

Ayrıca etki **monoton değil**: `80+k288` çöküyor ama `110+k288` iyi (0.8209). Bu, dar
bir sırtın üzerinde oturmak demek. Kendi kuralımız gereği platolar sırtlara tercih
edilir (`maks_alan` 0.80/0.95 birebir aynıydı — o bir platoydu).

**Sonuç:** k288 alınmıyor. `uyarlanır 80` tek başına daha çok kazandırıyor, tek
değişiklik, ve kırılgan bir etkileşime dayanmıyor.

**Bu kayıt bilerek silinmedi.** Tek tek ölçüp toplamayı varsaysaydık, sistemi taban
altına indiren bir yapılandırma "iki kabul edilmiş iyileştirme" diye teslim edilecekti.

### `gomme.pay_hedef_px` (uyarlanır bağlam payı) — ALINMADI, BELGELENDİ

Sabit `pay=0.15` yerine: kırpmanın kısa kenarı en az `hedef_px` olacak şekilde bağlam ekle.

| rejim | uyarlanır 80 | k288 |
|---|---|---|
| v1_rgb | 0.000 | +0.006 |
| v1_640 | **+0.080** | +0.031 |
| v1_g640 | +0.033 | +0.079 |
| v1_t640 (sahte-termal) | +0.068 | −0.095 |
| v2_termal (gerçek sensör) | −0.040 | **−0.117** |
| v1_cm640 (çapraz-modal) | **−0.077** | −0.112 |

Karar ölçütü VERİ GÖRÜLMEDEN yazıldı: *kabul için altı rejimin en az dördünde pozitif
veya nötr olmalı VE tek negatifi o rejimin gürültü tabanı içinde kalmalı.* Çapraz-modal
satırı gelince ölçüt başarısız oldu — ikinci negatif, üstelik 5 referans / 689 kare ile
ölçülmüş, yani v2'nin aksine ayırt etme gücü yüksek bir sette.

**Neden alınmadı — üç sebep:**

1. **Kazanç yalnızca sentetik rejimlerde.** v1_640 ve v1_g640, v1'in benim tarafımdan
   küçültülmüş/griye çevrilmiş halleri. Elimdeki tek GERÇEK sensör farkında (v2 termal)
   etki ayırt edilemiyor: 60→−0.007, 80→−0.040, 110→−0.002 — monoton değil, ve v2'de
   **tek bir karenin mAP etkisi ~0.025** (2 referans, 201 kare). Yani bu salınımlar
   1–2 karelik gürültü.
2. **Mekanizma açıklaması YALANLANDI.** "Küçük nesneye daha çok bağlam ver" diye
   savunulmuştu. Çapraz-modal ölçekte AYNI küçük nesne (ref03) bağlamdan **kaybediyor**:
   0.651 → 0.188. Oysa v1_640'ta aynı nesne bağlamdan kazanıyordu (0.211 → 0.769).
   Aynı nesne, zıt yön. Etki nesne boyutuyla ilgili değil, veriye bağlı ve mekanizması
   bilinmiyor. Ayrıca v2'nin nesneleri büyük olduğu halde sonuç değişiyor — demek ki
   baskın etki **çeldirici önerilerde**, doğru nesnede değil.
3. **Kuralımız:** nedenini bilmediğimiz bir kazancı, görmediğimiz videoya taşınacağını
   varsayarak kabul etmiyoruz. `maks_alan` bundan farklıydı — mekanizması netti,
   gerçek sensörde ölçülebilir kazanç verdi, ve bir platonun ortasındaydı.

**Kod duruyor** (`arena/lib.py::pay_hesapla`, `gomme.pay_hedef_px`). Yarışmada düşük
çözünürlüklü bir video ile karşılaşılırsa tek satırla açılabilir; yukarıdaki tablo
beklenen etkiyi veriyor.

### YAMA DÜZEYİNDE SKORLAMA — KOŞULLU KABUL (gri/termal kare · w=0.30)

Kırpmanın yama tokenlarının ORTALAMASI yerine, her öneri yaması için referans
yamaları üzerinde MAKS kosinüs + döngüsel tutarlılık süzgeci (δ=5) + ön plan
maskesi (0.87). `s = 0.70·s_cls + 0.30·s_appe`. Yalnızca `is_grayish(kare)` iken.

**w=0.30 doğrulaması — dört rejim × iki koşul, referans: yalnız maks_alan=0.80**

| rejim | pay0 | pay10 (yarışma gerçeği) |
|---|---|---|
| **v2_termal (gerçek sensör)** | **+0.039** | **+0.030** |
| v1_g640 (gri) | **+0.071** | +0.012 |
| v1_t640 (sahte-termal) | −0.001 | −0.011 |
| v1_cm640 (çapraz-modal) | +0.006 | **+0.055** |

Sekiz koşulun altısı pozitif, iki küçük negatif (ikisi de sentetik rejimde),
**net +0.200**, ağır kayıp yok.

**AĞIRLIK SEÇİMİNDE YAPILAN HATA ve düzeltilmesi.** İlk taramada w=0.67 seçilmişti
ve "gerçek sensörde +0.069" diye kaydedilmişti. Ama yama skorlamanın **on iki
ölçümünün hepsi pay=0'daydı** — yani bütün oturum boyunca üç ayrı ekseni yeniden
açmama sebep olan "tek rejimde ölçüm" hatasının aynısı. Birleşim koşusu bunu
yakaladı: w=0.67 paylı koşulda 0.5910 → **0.5019** yapıyordu, yani yarışma
koşulunda TABANI DA kaybettiriyordu. w=0.30 ikisinde de kazanıyor.

| w | v2 pay0 | v2 pay10 |
|---|---|---|
| yalnız maks_alan | 0.7360 | 0.5910 |
| **0.30** | **0.7747** | **0.6209** |
| 0.50 | 0.7747 | 0.6061 |
| 0.67 | 0.7953 | **0.5019** |

Paysız koşul ağır yama terimini sever, paylı koşul hafifini. Yarışma paylıdır.

**Çürütülen ara hipotez:** "yama skoru, CLS'in elediği arka plan kutularını yüzeye
çıkarıyor" denmişti. Ön eleme (CLS kısa listesiyle sınırlama) eklendi ve
**hiçbir ağırlıkta hiçbir şey değiştirmedi** — yani seçilen kutular zaten CLS'in de
makul bulduğu kutular. Kayıp, makul adaylar arasındaki tercih farkından geliyor.
Kod duruyor (`on_eleme`) ama varsayılan 0.

**Mekanizma doğrulandı, uygulama sadakati denetlendi:**
- δ eğrisinin TEPESİ var (sahte-termal: 0 → 0.4994 · 3 → 0.5048 · **5 → 0.5377** ·
  8 ve 13 → 0.5213). Süzgeç iş görüyor, yalnızca örneklem küçültmüyor.
- Ön plan maskesi w=0.67'de +0.013, w=0.5'te etkisiz. Bu, uygulamamla yayımlanmış
  yöntem arasındaki tek yapısal farktı; ölçüldü.
- w=1.0 (yalnız yama) her rejimde kötü → CLS terimi vazgeçilmez.
- **Maliyet yok:** ön kontrol termal karede ısınmış kare **0.15 sn** (bütçe 1.6 sn).
  Aynı ileri geçiş, farklı skorlama.

**Koşul neden `gri_mi`:** ortalama-yama global renk/doku istatistiklerine dayanır ve
renk varken güçlüdür. Renkli rejimlerde yama skorlama ZARARLI (v1_rgb −0.013,
v1_640 −0.070); gri rejimlerin dördünde de faydalı. Koşul çalışma anında hesaplanan
**yapısal** bir ayrım — ayarlanmış bir eşik değil. Bu oturumda mutlak eşiklerin
videolar arası taşınmadığı defalarca ölçüldü.

### `referans.gri_ekle` = True — AÇIK KARARA BAĞLANDI (korunuyor)

Referansın CLAHE-normalize gri kopyasını bankaya ekler (referans zaten griyse
eklemez). Modalite farkına dayanıklılık için konmuştu ama uzun süre açık bir karara
bağlanmamıştı.

| ölçek | gri kopya VAR | gri kopya YOK |
|---|---|---|
| v1_rgb | 0.9051 | 0.9051 |
| v1_640 | 0.7418 | **0.7766** |
| v1_t640 (sahte-termal) | 0.5219 | 0.5234 |
| v2_termal | 0.6531 | 0.6531 |
| **v1_cm640 (çapraz-modal)** | **0.5720** | 0.5632 |

**Korunuyor.** Tek kaybettiği yer v1_640 (−0.035) ama **eklenme sebebi olan durumda
kazanıyor**: çapraz-modal ölçekte (RGB nadir referans → termal kare) +0.009, ve o,
yarışmada karşılaşılması muhtemel gerçek bir referans tipi. Diğer üç rejimde nötr.

Yan ders: **bankaya eklenen her görünümün bedeli var.** Bu, "eşik koyma, görünüm
ekle" desenini bedava sanmamak gerektiğini gösteriyor — her ekleme yanlış eşleşme
fırsatı da yaratıyor ve ölçülmeden kabul edilmemeli.

---

## REDDEDİLDİ

### `zamansal.uyum` 0.45 → 0.25
v1_pay10 −0.008, v2 **+0.059**. Reddedildi: kazanç yalnızca v2-05'te; v1'in kendi
sahne referansı (halı saha) hiç etkilenmiyor. Yani ilkeli bir "sahne nesnesi" etkisi
değil, **mühürlü sete uydurma**.

### `zamansal.birak` 3 → 2, ve aday düzeyinde zamansal EMA
v1_pay10 +0.018 ve +0.015. Reddedildi: eşleştirilmiş bootstrap %90 GA'sı sıfırı
içeriyor ([−0.009, +0.061]) ve kazancın tamamı beş referanstan **birinden** geliyor.

### Negatif banka (arka plan bastırma)
0.2516 — felaket. Literatür bağımsız olarak doğruladı (FSS-SAM3: −21.9 mIoU,
"tahmin çöküşü"). **Bir daha açılmayacak.**

### Online referans bankası
0.917 → 0.80. Banka kirleniyor. Sunucunun verdiği `frame_start_image_url` ile
yeniden denemek cazip görünüyor ama o görüntülerde **kutu yok** — aynı tavuk-yumurta.

### Yer seviyesi cephe → nadir çatı
Peşine düşülmeyecek. Cephe ile çatının ortak yüzeyi yok. Aynı 951 binada ölçülmüş:
yerden-uyduya %1.20, eğik-görüntüden-uyduya %58.49. Metin aracılı yol da kurtarmıyor
(nadir görüntüde metin istemi 11.67 mAP, görsel örnek 66.55).

### `referans.ters_ekle` (polarite tersi görünüm)

| video | taban | + ters | yalnız ters | çıplak |
|---|---|---|---|---|
| v1_rgb | 0.9051 | 0.9051 | 0.9051 | 0.9051 |
| v1_640 | 0.7418 | 0.7418 | 0.6958 | **0.7766** |
| v1_t640 (sahte-termal) | 0.5219 | 0.5087 | 0.5087 | 0.5234 |
| v2_termal | 0.6531 | — | 0.6431 | 0.6531 |

Reddedildi. Fikir sağlamdı — termalde beyaz-sıcak/siyah-sıcak bir ayardır ve videodan
videoya değişir — ama işe yaramıyor. Referans bazında sebebi görülüyor: v1_t640'ta
ref03 0.017→0.151 ve ref05 0.576→0.676 yükselirken ref01 0.613→0.322 çöküyor.
Kimini kurtarıp kimini batırıyor, net sıfır.

**Ders:** öğrenilmiş öznitelikte, ters çevrilmiş bir görüntünün gömmesi, gerçekten
polaritesi dönmüş bir sahnenin gömmesine DENK DEĞİL. Polarite sorunu gömme uzayında
çözülmüyor; farklı bir mekanizma gerekiyor (bkz. SOC).

### Referansın "geniş çekim mi" olduğunu tespit etme

Ölçüldü ve öldü. FastSAM ile referanstaki "nesne alan oranı":
bozulmamış referanslarda 0.00–0.88 arası saçılıyor (üç referansta baskın nesne
bulunamıyor), geniş4'te 0.06–0.81. **Tam ihtiyaç duyulan yerde yanılıyor** — bulanık
tuvali nesne sanıyor. Gradyan enerjisiyle daha iyi bir seçici yazılabilir ama o,
sentetik bozunuma (düz bulanık tuval) uyar; gerçek geniş çekimde çevre dokuludur.
Kendi test verisine uydurma olurdu.

---

## ÖLÇÜLDÜ — KARAR KULLANICIYA BIRAKILIYOR

### `referans.gorunum` : tam vs piramit

| görünüm | v1 bozulmamış | v1 en kötü | v2 bozulmamış | v2 en kötü | 6 hücre ort. |
|---|---|---|---|---|---|
| **tam** (mevcut) | **0.9051** | 0.4866 | **0.6531** | 0.0678 | 0.542 |
| merkez50 | 0.7935 | 0.7728 | 0.5474 | 0.2341 | 0.657 |
| **piramit** | 0.7862 | 0.7713 | 0.6186 | **0.3220** | **0.678** |
| sam_kirp | 0.7624 | 0.2712 | 0.3628 | 0.2712 | 0.583 |

`piramit` hem ortalamada hem en kötü durumda kazanıyor; `tam` yalnızca bozulmamış
durumda. Karar, **geniş çekim referans gelme olasılığına** bağlı:

- v1'de başabaş noktası p ≈ 0.29, v2'de p ≈ 0.11.
- Örnek veri setinde **12 referansın 12'si de sıkı kırpma** → p muhtemelen düşük.

Bu yüzden varsayılan `tam` kalıyor. Ama karar tek bir sayıya bağlı olduğu için
kullanıcıya açıkça sunuluyor: *yarışmada geniş çekim referans gelme ihtimalini %30'un
üstünde görüyorsak `piramit`'e geçmeliyiz.*

**Test edilmemiş alternatif:** çevrimiçi geri çekilme — bir referans için takipçi
N kare boyunca hiç kilitlenmezse o referansı `piramit` görünümlerine geçirmek.
Kilit durumu ölçeksiz bir sinyal ve işler yolundayken hiçbir bedeli yok.

---

## REDDEDİLDİ — SOC (kare alınmış yönelim korelasyonu)

**Uçtan uca sonuç: mAP 0.0002.** İsabet %0–2. Aday üretici olarak kullanılamaz.

Ara ölçüm doğruydu ama YANLIŞ SORUYU cevaplıyordu. Yama testinde şablon, aynı karenin
birebir kırpmasıydı:

| şablon | SOC | NCC |
|---|---|---|
| 64/96/128 px | **%100** | **%0** |

Bu test **polarite değişmezliğini** kanıtladı ve o kısım geçerli. Ama gerçek görev
yama yeniden konumlandırma değil, **zaman ve bakış açısı boyunca nesne yeniden tanıma**.
SOC'un polarite dışında hiçbir değişmezliği yok:

- **dönme ±6°** (kendi ölçümüm: 0° %100 · 5° %99 · 8° %50 · 12° %15 · 20° %2)
- **ölçek ±%10**
- şablonun **arka planını da** eşleştiriyor: referans kırpması pencere 1'in çevresini
  taşır, pencere 2'de o çevre yoktur

Sabit nesnede bile çalışmadı (halı saha AP 0.000) — ölçek ve açı farkı toleransların
çok üstünde. Drone uçuşunda irtifa ve yönelim sürekli değişiyor.

**KALICI DEĞER:** NCC ailesinin neden öldüğünün açıklaması. Polarite ters çevrildiğinde
NCC "zayıf" değil, tam olarak SIFIR. Bu yol bir daha denenmeyecek — ama çözümü SOC değil.

**DERS (metodolojik):** bir ara ölçümün yüksek çıkması, görevin çözüldüğü anlamına
gelmiyor. Ara test, görevin hangi zorluklarını KAPSAMADIĞINI de söylemeli. Bu turda
%100'lük bir sonucu "en büyük bulgu" diye sunup uçtan uca 0.0002 ile karşılaştım.

---

## ÖLÇÜLDÜ, KARAR BEKLİYOR

- referans görünüm × bozunum (ölçek piramidi) — *koşuyor*
- çapraz-modal: polarite tersi referans görünümü — *kuyrukta*
- küçük nesne rejimi: bağlam payı / kırpma boyutu — *kuyrukta*
- sıkıştırma vs bulanıklık ayrıştırması — *kuyrukta*
- **yama düzeyinde skorlama + döngüsel tutarlılık süzgeci** — *kuyrukta, en yüksek beklentili*

---

## ÖLÇÜLEN KIRILGANLIKLAR (düzeltme aranıyor)

| kırılganlık | kayıp | nereden vuruyor | eyleme dönüşü |
|---|---|---|---|
| referansta nesne 1/16 | −0.445 | temsil | sunucudan gelen referans; bizim elimizde değil |
| **bulanıklık** (σ≈5) | −0.211 | **öneri + sıralama** | **uçuş profili: gimbal kararlılığı, hız, odak** |
| JPEG q40 | −0.144 | sıralama | sunucunun sıkıştırması; kontrolümüzde değil |
| sahte-termal (polarite) | −0.383 | temsil | gri −0.07, polarite ek −0.15 |
| düşük çözünürlük | −0.163 | **yalnız sıralama** (tavan 1.000, top-1 0.627) | irtifa/zoom |

**Bulanıklık, sıkıştırmadan daha zararlı** ve tek fark bu: sıkıştırma sunucunun elinde,
bulanıklık bizim. Görev 3'ün puanı için gimbal kararlılığı, akış kalitesinden önemli.

**Aşama teşhisi — üç bozulma üç ayrı yerden vuruyor:**

| bozulma | öneri tavanı | top-1 |
|---|---|---|
| düşük çözünürlük | 1.000 (bozulmuyor) | 0.627 |
| sıkıştırma+bulanıklık | 0.759 (çöküyor) | 0.500 |
| sahte-termal | 0.980 | 0.451 |

Bunları tek ilaçla çözmeye çalışmak hata olurdu.

## ÇALIŞMA ARALIĞI (ampirik)

top-1 doğruluğu nesnenin kenar uzunluğuna göre: ~120 px üstü ≥0.95 · ~90 px ≈0.85 ·
~47 px ≈0.67 · ~31 px ≈0.63. **Nesne bir kenarı ~50 px'in altına düşerse güvenilirlik
hızla kayboluyor** — bu, irtifa/zoom için doğrudan bir sınır.

---

## ZORUNLU SON ADIM — BİRLEŞİM DOĞRULAMASI

Kazananlar seçildikten sonra **birleşik yapılandırma ayrıca koşulacak** ve tabanı
gerçekten geçtiği doğrulanacak. Bu isteğe bağlı bir titizlik değil, bu oturumda
bir kez yaşanmış bir hata: tek tek tabanı geçen yedi ayarın hepsi bir arada
**0.871 → 0.779** yapmıştı. Eksenler bağımsız değil.

Doğrulama, dört koşulun hepsinde yapılır (v1/v2 × pay 0/10) ve ayrıca üretim
paketi `arena/dogrula_uretim.py` ile bağımsız olarak yeniden koşulur.

---

# EK — GECE KOŞUSU (7–8 Eylül 2026)

Aşağısı, arenadaki karar günlüğünün gece bölümünün **tamamıdır** —
teslim dosyası tek başına anlaşılır kalsın diye buraya kopyalandı.

## Ara katman / havuzlama taraması (gece koşusu)

**Soru:** DINOv3'ün SON katmanı kırpma gömmesi için doğru yer mi? Literatürde
tespit işleri için ara katmanların daha iyi olduğu bildiriliyor.

| varyant | v1_rgb | v2_termal | v1_640 |
|---|---|---|---|
| son katman (taban) | 0.8960 | 0.7360 | 0.7403 |
| katman 8 | 0.1624 | 0.0596 | 0.0348 |
| katman 9 | 0.1477 | 0.0617 | 0.0339 |
| katman 10 | 0.2142 | 0.0576 | 0.1830 |
| katman 11 | 0.5664 | 0.3655 | 0.3023 |
| **son + GeM havuzlama (p=1.5)** | 0.8950 | **0.7694** | **0.7727** |

**Karar 1 — ara katmanlar REDDEDİLDİ.** Kademeli değil, çöküş var: katman 8–10
üç videoda da kullanılamaz. Bu bir ayar meselesi değil; ara katman tokenları
kırpma-düzeyinde anlamsal eşleştirme için uygun bir uzay üretmiyor. Eksen kapandı.

**Karar 2 — GeM havuzlama ADAY.** Üç rejimin ikisinde +0.033, birinde −0.001.
Ancak bu ölçüm TABAN yolda (yama skorlaması olmadan) ve yalnız pay=0'da yapıldı.
Bu projede "tek rejimde ölçüp kabul etme" hatası daha önce iki kez yakalandı;
kabul için üretim yolunda ve pay=10'da yeniden koşulması şart (`_gem.py`).

**GeM'in üretim yolunda neden doğrudan geçerli olmadığı.** Ölçüm taban yolda
(`kosucu` + `lib.Gomucu`) yapıldı; o yolun vektörü `[CLS | ortalama-yama]`.
Üretim yolu ise `s_cls`'i **yalnız CLS yarısından** hesaplıyor — `api.py`
`E[:, :D]` dilimleyip yeniden normalize ediyor ve birleşik normalizasyon düzgün
bir ölçekleme olduğu için bu tam olarak `normalize(cls)` demektir. Yani havuzlanan
yarım üretimde **kullanılmıyor**; GeM oraya olduğu gibi taşınırsa hiçbir şeyi
değiştirmez.

Bunu fark etmeden önce `arena/yama_skor.py`'yi "üretimle hizalıyorum" diyerek
birleşik vektöre çevirmiştim — **ters yöne**. Üretim kodundaki açıklama, CLS-only
seçiminin bilinçli olduğunu ve bir kez ölçülüp hizalandığını yazıyor. Geri alındı;
yerine `vektor_skor` ekseni açıldı (`cls` = dağıtılan sistem, `cls+yama` = aday).
Doğru sıralanmış soru: **(a)** `s_cls` CLS-only'dan mı birleşikten mi daha iyi,
**(b)** birleşik kazanırsa havuzlama `ort` mu `gem` mi. `_gem.py` ikisini birden
ölçüyor ve `cls` sütunu teslim rakamlarını yeniden üretmek zorunda.

## Ölçülüp kapanan risk: homografi düşmesi

`sadece_kilitli` kapısı homografiye bağlı — `H=None` gelirse iz kopar ve sistem
**tamamen susar** (reponun asıl arızasının aynısı, başka yoldan). Bunun ne sıklıkta
olduğu hiç ölçülmemişti.

Önbellekteki bütün ego çiftleri sayıldı:

| video | çift | H=None | oran |
|---|---|---|---|
| v1_rgb · v1_960 · v1_640 · v1_g640 · v1_j640 · v1_k640 · v1_t640 · **v1_b640 (bulanık)** · v1_cm640 | 516 (450) | **0** | **%0.0** |
| v2_termal | 258 | **0** | **%0.0** |

ORB + USAC_MAGSAC on videonun hiçbirinde, bulanıklaştırılmış ve termal olanlar
dahil, tek bir kare çiftinde bile düşmedi. **Bu arıza yolu ölçümle kapandı.**

Kalan uyarı: elimizdeki bütün videolar doku bakımından zengin (tarla/yerleşim).
Su üstü, sis veya tek renkli yüzeyde ORB düşebilir; o koşul ölçülmedi.

---

## Varlık kapısı arayışı — kaybın anatomisinden çıkan iş

### Neden bu iş yapıldı

Gerçekçi koşulda (pay=10) kaybın nereden geldiği ilk kez kare kare çıkarıldı:

| kalem | kare (v1_rgb + v2_termal) |
|---|---|
| başlangıç gecikmesi | 22 |
| bitiş kuyruğu | 3 |
| orta boşluk | 42 |
| yanlış kutu | 39 |
| **dolgu yanlış-pozitifi** | **308** |

Duyarlılık neredeyse kusursuz (v1-01 169/170, v1-05 34/34) — puanı **kesinlik**
yiyor. Örnek: v1-05'te R=1.000, P=34/65 → AP 0.523. Mekanizma: kilit koptuğunda
takipçi üç karede arka plandaki başka bir yapıya **yeniden kilitleniyor**.

### Dürüstlük: bu ne kadar gerçek?

FP'lerin **%97'si sunucu penceresinin içinde değil, benim seçtiğim ±10 karelik
dolgu şeridinde**. Yani büyüklük benim varsayımımın eseri. Mekanizma yine de
gerçek: protokol notu 16 Temmuz oturumundan gerçek bir vaka belgeliyor —
pencere 161–205, nesne 173–203, yani 14 kare dolgu. Doğru okuma şu:
**olay gerçek, ölçeği varsayıma bağlı.**

### Çürütülen hipotez

"Gerçek eşleşme kare içindeki adaylar arasından belirgin biçimde sıyrılır"
→ **yanlış.** Kare içi z-skoru (medyan/MAD'e göre öne çıkış) ayırt etmiyor
(AUC 0.58–0.67) ve eşik taraması **sıfır** kazanç veriyor. Aynı şey marj için de
geçerli. `ara.py`'de referans aramada işe yarayan istatistik, kare içi varlık
kararında işe yaramıyor.

### Elenen kural: sabit uzun seri

`seri >= 11` v1 türevlerinde +0.07…+0.11 kazandırıyor — ama **mühürlü v2'de
−0.0284**. Dört "geliştirme videosu" aynı videonun türevleri olduğu için bu,
tek videoya uyumdan başka bir şey değil. **Reddedildi.** Sebebi yapısal:
v2-06'nın penceresi 31 kare; 11 karelik seri şartı duyarlılığı öldürüyor.

### Ayakta kalan aday: pencere-oranlı seri şartı

    L = kırp(alfa * pencere_uzunlugu, taban_kat, 60)      # gönder <=> seri >= L
    pencere_uzunlugu SUNUCUDAN biliniyor (frame_start / frame_end)

İki yönlü seçim sınavı (pay=10):

| seçim | alfa | kat | v1_rgb | v1_640 | v1_g640 | v1_cm640 | v2_termal |
|---|---|---|---|---|---|---|---|
| v1'in argmax'ı | 0.030 | 10 | +0.0934 | +0.0671 | +0.0662 | −0.0015 | **−0.0115** |
| v2'nin argmax'ı | 0.035 | 5 | +0.0347 | +0.0281 | +0.0275 | +0.0017 | **+0.0213** |
| uzlaşı | 0.030 | 5 | +0.0359 | +0.0283 | +0.0267 | +0.0037 | **+0.0185** |
| sade: sabit L=5 | — | 5 | +0.0287 | +0.0254 | +0.0238 | +0.0016 | +0.0185 |

Duyarlılık: asıl etki **taban kat**tan geliyor, alfa yalnız 375 karelik pencerede
fark yaratıyor. Güvenli bant dar (alfa 0.025–0.035; 0.05'te v1_cm640 negatife
dönüyor).

**Açık kayıt:** taban kat seçilirken mühürlü videoya bakıldı. Yani bu parametre
için v2 artık temiz bir sınav değildir — dayanak, **beş rejimde ve her iki seçim
yönünde işaretin aynı kalması**, temiz bir tutulmuş-küme rakamı değil.

**Kabulden önce yapılacak (ve yapılıyor):** iz, dağıtılan sistemin vektörüyle ve
**pay = 0 / 10 / 20** ile yeniden üretilip kural üç dolgu koşulunda da
sınanacak. pay=0'da dolgu yok — kural orada yalnızca duyarlılıktan yer.

### Kare kare kalıp — kuralın neden işlediği

pay=10 izinden çıkarılan kare dizileri (`#`=isabet, `x`=yanlış kutu, `_`=sustu,
`F`=dolgu FP, `.`=doğru sustu):

```
v2-05  ..FFF....F####…####_#####__......FFF.....FFFFFFxxxxxxxxxx
       xxxxxx__xxx#######################xx#####…#####_
v1-02  ..FFFF.F..__####…####FFFFFF......FFFFFFFFxxxx####…####
```

İki ayrı olay görünüyor ve ikisi de **pencere geçişlerinde**:

1. **Dolgu FP'leri (`F`)** pencere kenarlarında — beklenen.
2. **Yanlış kutular (`x`) pencere başlangıçlarında kümeleniyor.** v2-05'te
   art arda 16 kare. Pencere yeniden açıldığında önceki kutu yok, ilk kilit
   arka plandaki bir yapıya oturuyor, sistem birkaç kare sonra `çelişki`
   mekanizmasıyla kendini düzeltiyor.

Yani seri şartı yalnız dolguyu değil, **yanlış ilk kilidi de** susturuyor.
Mekanizma tahmin edilenden geniş; kuralın beş rejimde birden pozitif çıkması
bununla tutarlı.

Kalan açık: sürekli yanlış kilit (16 kare) seri şartıyla tamamen kapanmıyor,
çünkü yanlış kilit de seri biriktiriyor. Bu, ayrı bir iş kalemi olarak duruyor.

### Elenen: görünüm skoruna dayalı varlık kapıları (üç formülasyon)

Skor seviyeleri sınıflara göre ayrışıyor — ama işe yaramıyor:

| video · ref | isabet s_top | yanlış kutu | dolgu FP |
|---|---|---|---|
| v1-05 | 0.614±0.049 | — | 0.543±0.065 |
| v2-05 | 0.754±0.076 | 0.686±0.024 | 0.610±0.053 |
| v1-02 | 0.778±0.040 | 0.699±0.050 | 0.727±0.093 |

İsabetler tutarlı biçimde 0.05–0.08 daha yüksek. Ama **mutlak seviye referanstan
referansa 0.535–0.778 arasında geziniyor** ve sınıflar ~1σ örtüşüyor.

Üç formülasyon denendi, üçü de iki yönlü aktarım sınavında **düştü**:

| kural | v1'den seçilen → v2 | v2'den seçilen → v1 | sonuç |
|---|---|---|---|
| küresel eşik `s_top >= t` | +0.0052 | — | ihmal edilebilir (0.2 kare) |
| kare içi z / marj | 0.0000 | 0.0000 | hiç ayırmıyor |
| koşan MAKS oranı `s >= β·max` | −0.0434 | −0.0001 | RED |
| koşan Q90 oranı | −0.0240 | +0.0095 | RED |

**Sonuç — kayda değer:** bu sistemde varlık kararı **görünüm skorundan
çıkarılamıyor**. Yalnız **zamansal yapı** (kilit serisi) videodan videoya
taşınıyor. Bu, eşiksiz tasarım tercihini bağımsız bir yoldan doğruluyor:
reponun mutlak kosinüs eşiğiyle sustuğu yerde sorun eşiğin *değeri* değil,
skorun *kendisinin* taşınabilir bir varlık sinyali olmaması.

### Açık kalan iş kalemi: sürekli yanlış kilit

v2-05'te pencere geçişinde **26 kare boyunca** nesne görünürken kutu başka yerde
(`xxxxxxxxxx` + `xxxxxx__xxx`). Bu, dolgu FP'si değil — gerçek yanlış yerelleştirme
ve v2-05'in yanlış-kutu kaleminin (21 kare) neredeyse tamamı.

Seri kapısı bunu **kapatmaz**: yanlış kilit de seri biriktirir. Mevcut `çelişki>=3`
mekanizması ancak dedektörün en iyi adayı izle *çeliştiğinde* devreye giriyor;
dedektör ısrarla aynı yanlış yapıyı gösterirse çelişki doğmuyor.

Denenmedi çünkü çevrimdışı simüle edilemez (takipçinin durumunu değiştirir, yani
her fikir tam koşu ister). Not olarak duruyor:
* skor düşüşü tetikli **yeniden çapalama** (susturma değil, izi bırakma)
* periyodik zorunlu yeniden tespit

Uyarı: skor tabanlı tetikleyicilerin eşiği bu projede **taşınmıyor** (yukarıdaki
üç formülasyon); aynı tuzağa düşme riski yüksek.

### Seri kapısının gerçek bedeli — dolgu yokken ölçüldü

İlk tur yalnız pay=10'da ölçülmüştü ve kural umut vericiydi. Üretim vektörüyle
**pay=0** izleri alınınca tablo değişti:

| kural | pay=0 (dolgu YOK) en kötü | pay=10 en kötü |
|---|---|---|
| oranlı 0.030 / kat 5 | **−0.0808** | +0.0016 |
| sade sabit L=5 | −0.0698 | −0.0005 |
| oranlı 0.030 / kat 3 | −0.0338 | +0.0021 |
| sade sabit L=8 | −0.1718 | −0.0103 |

Ön kayıttaki ölçüt "pay=0'da en kötü ≥ −0.030" idi; **hiçbiri geçmiyor.**

**Neden bu kadar pahalı olduğu bulundu:** şart *her kilit epizodunda* yeniden
ödeniyor. v1-02'nin altı ayrı penceresi var; her yeniden kilitlenmede L−3 kare
daha kaybediliyor. Yarışmada bir referansın **tek** penceresi olacağı için bu
maliyet bizim yer gerçeğimizin yapısından kaynaklanıyor, protokolden değil.

**Düzeltilmiş sürüm — "bir kez kurulunca şart düşer":** L bir kez sağlandıktan
sonra normal kilide dönülür.

| kural (kurul kipi) | pay=0 en kötü | pay=10 en kötü | pay=10 · v2 (mühürlü) |
|---|---|---|---|
| oranlı 0.030 / kat 5 | −0.0380 | **+0.0057** | **+0.0201** |
| sade L=5 | −0.0380 | +0.0063 | +0.0201 |
| oranlı 0.030 / kat 3 | −0.0091 | +0.0001 | +0.0036 |

Bu kipte pay=10'da **beş rejimin beşi de pozitif** ve maliyet yarıya iniyor.

### Karar: varsayılan DEĞİL, belgelenmiş seçenek

Başabaş noktası hesaplandı (iki nokta arasında doğrusal): kural ancak sunucunun
dolgusu **kenar başına ~7–8 kareyi** aşarsa kâra geçiyor.

Elimizdeki tek belgelenmiş gerçek vaka: pencere 161–205 (45 kare), nesne 173–203
(31 kare) → 12 kare baş, 2 kare son, ortalama ~7. **Tam başabaş noktasında.**

Dolayısıyla beklenen kazanç ≈ 0, belirsizlik yüksek. Bu projede "beklenen kazancı
sıfır olan bir karmaşıklık" eklenmez. Kural üretime **kapalı** olarak konur
(`streak_gate_floor=0`), ölçüm tablosuyla birlikte belgelenir: sunucunun penceresi
görünürlükten belirgin biçimde genişse tek satırla açılır.

**Not:** pay=20 izleri koşuyor; eğim beklenenden dik çıkarsa bu karar gözden
geçirilecek ve burada güncellenecek.

### Elenen: uç karesi kalibrasyonu (protokolün bedava sinyali)

`PROTOKOL_NOTLARI §4`: sunucu her referans için pencerenin **ilk ve son karesinin
görüntüsünü** veriyor (`frame_start_image_url` / `frame_end_image_url`) ve bunlar
şu ana dek hiç kullanılmıyordu. Fikir: pencere gerçek görünürlükten geniş olduğu
için uç kareler çoğunlukla nesneyi **içermez**; oradaki en iyi skor, o referansın
o videodaki **arka plan seviyesidir**. Kapı bundan türeyebilir:
`gönder ⇔ s_top ≥ β · min(uç seviyeleri)`. Mutlak eşik yok, ölçek referans ve
video başına kendini ayarlıyor, ikisi de oturum başında elde edilir → nedensel.

İlk bakışta en umut verici aday oldu:

| β seçimi | pay=0 en kötü | pay=10 en kötü | pay=10 ortalama |
|---|---|---|---|
| v1'de seçilen β=0.94 | −0.0245 | **+0.0022** | **+0.0216** |
| v2'de seçilen β=1.02 | **−0.1739** | **−0.0921** | −0.0108 |

**İki yönlü aktarım sınavında düştü.** v2'nin kendi en iyisi (1.02) v1'i yıkıyor;
üstelik β>1.00'de dik bir uçurum var (β=1.05'te −0.20). Güvenli uç β=0.88:
pay=10 en kötü +0.0027, pay=0 en kötü −0.0075 — yani neredeyse hiçbir şey.

### Toplu sonuç: varlık kapısı yolu kapandı

Bu gece dört aile denendi, hepsi elendi:

| aile | neden düştü |
|---|---|
| küresel mutlak eşik (`s_top ≥ t`) | kazanç ihmal edilebilir (mühürlüde 0.2 kare) |
| kare içi öne çıkış (z, marj) | hiç ayırmıyor: AUC 0.58–0.68, kazanç 0.0000 |
| koşan öz-kalibrasyon (maks / Q90) | mühürlüde −0.024…−0.043 |
| uç karesi kalibrasyonu | iki yönlü aktarım yok; β>1'de uçurum |
| kilit serisi şartı (sabit / oranlı) | pay=0 ile pay=10 arasında başabaş |

**Vardığımız yer:** bu sistemde *"nesne bu karede var mı?"* sorusu, elimizdeki
sinyallerden **yeni bir videoya taşınacak biçimde cevaplanamıyor**. Mevcut
tasarım (kilit durumu + dedektör kaynağı) ulaşılabilir sınırda duruyor.

Bu, olumsuz ama **eyleme dönüşen** bir sonuç: ekibin bu yöne daha fazla zaman
harcaması gerekmiyor. Aynı zamanda reponun neden bu kadar sert çöktüğünü de
açıklıyor — sorun eşiğin *değeri* değil, skorun taşınabilir bir varlık sinyali
**olmaması**.

**Kalan boşluk da kapatıldı.** Bütün kapılarda harmanlanmış skor
(`0.70·s_cls + 0.30·s_app`) kullanılmıştı; **yalnız yama skoru** (`s_app`, döngüsel
tutarlılık süzgeçli) ayrı bir varlık sinyali olarak izlenmemişti. İz yeniden
üretilip ölçüldü:

| sinyal | AUC v1_640 | AUC v2_termal | v1'de seçilen eşik → v2 |
|---|---|---|---|
| `s_top` (harmanlanmış) | 0.759 | 0.889 | +0.0052 |
| `s_cls` | 0.759 | 0.884 | — |
| **`s_app` (yalnız yama)** | 0.742 | 0.897 | **+0.0055** |

Yama skoru **daha iyi değil** — ayırt ediciliği harmanlanmış skorla aynı mertebede
ve mühürlü videodaki kazancı yine ihmal edilebilir (0.2 kare). Böylece "varlık
kararı görünüm skorundan çıkarılamıyor" sonucu **bütün bileşenler için** geçerli.

### Ölçüm koşullarına dair kayıt: makine belleği

Gece koşusunun ortasında üç kez sistem RAM'i tükendi ve zincir kesildi. Sebep
ölçüm kodunda değildi: makinede **SolidWorks 7,3 GB** tutuyordu (kullanıcının açık
uygulaması, dokunulmadı) ve 15,7 GB'lık sistemde ~0,9 GB boş kalmıştı; taahhüt
50,1/53,7 GB.

Buna göre üç değişiklik yapıldı — **hiçbiri ölçümün anlamını değiştirmez**:

1. Her ölçüm hücresi artık **kendi sürecinde** koşuyor (`tek_kos.py`). Önceki
   betikler tek süreçte onlarca `kos()` çağırıyor ve her çağrıda yeni bir timm
   modeli yükleniyordu.
2. Yama gömücüsünün yığın boyutu 64 → **16**. Sonuç kırpma başına belirlenimci
   olduğu için rakamları değiştirmez, yalnız tepe bellek düşer.
3. **v1_rgb (1080p) taramalardan çıkarıldı**; renkli rejim `v1_640` ile temsil
   ediliyor — aynı sahnenin türevi. v1_rgb yalnız üretim doğrulamasında ve
   nihai birleşim kontrolünde koşuluyor.

Bu, ölçüm tabanını daraltır: renkli rejimde artık tek çözünürlük var. Kabul
edilen her şey nihai olarak yine v1_rgb üzerinde üretim paketiyle doğrulanacak.

---

## ÇAPRAZ-MODAL BANKA — gecenin en büyük kazancı (kısmi ölçüm)

**Fikir:** referans bankasına ek görünüm koy — ama **yalnızca kareler gri/termal
VE referans renkli ise**. Koşula bağlı olduğu için renkli→renkli durumda hiç
açılmaz; bedeli **yapısal olarak sıfırdır**. (Yapısal denetim geçti: v2_termal'de
`capraz="hepsi"` tabanla birebir aynı sonucu veriyor, 0.6209 = 0.6209.)

**v1_cm640** — bu kümenin ne olduğu önemli: referans, videonun **başka bir
penceresinden** kesilmiş **RGB nadir kırpma**; kareler sahte-termal. Yani mühürlü
setteki çözülemeyen dört referansın (v2-01…04) tam olarak modellenmiş hâli, ama
yer gerçeği elimizde.

| varyant | pay=0 | pay=10 |
|---|---|---|
| taban (`yok`) | 0.5806 | 0.4315 |
| `ters` (polarite tersi görünüm) | **0.6423** (+0.0617) | **0.5057** (+0.0742) |
| `hepsi` (ters + gradyan) | *koşuyor* | **0.5146** (+0.0831) |

Bu, bu gece ölçülen **en büyük tek kazanç** ve tam da en çok puan bırakılan
sınıfa vuruyor.

### Eski "polarite tersi reddedildi" kararıyla çelişki var mı — hayır

`referans.ters_ekle` daha önce ölçülüp reddedilmişti. Ama o ölçüm:
* **v1_cm640'ı kapsamıyordu** (v1_rgb, v1_640, v1_t640, v2_termal'de yapılmıştı),
* **taban yolda** (yama skorlaması olmadan) koşulmuştu,
* ve görünüm **koşulsuz** ekleniyordu — renkli rejimde de.

Yeni hâlde eklenme koşula bağlı ve ölçüm üretim yolunda. v1_t640'ta eski ölçüm
−0.013 vermişti; o kümede referanslar **özgün fotoğraflar** (bakış açısı da
farklı), v1_cm640'ta ise nadir kırpma (yalnız modalite farklı). İkisi farklı
sorular soruyor ve kabul için **ikisi de** ölçülmeli.

**Eksik ve koşuyor:** v1_t640, v1_g640, ve koruma rejimi v1_640.
Kabul, bunlar gelmeden verilmeyecek.

### KABUL: koşullu çapraz-modal görünüm SEÇİMİ (`referans.capraz = "sec"`)

Sabit bir ek görünüm işe yaramıyor — ölçüldü, her biri bir modalite boşluğunda
kazandırıp başkasında kaybettiriyor (pay=10):

| ek görünüm | v1_cm640 (RGB nadir ref → sahte-termal) | v1_t640 (RGB fotoğraf ref → sahte-termal) | v1_g640 (RGB fotoğraf ref → düz gri) |
|---|---|---|---|
| `ters` (polarite tersi) | **+0.0742** | +0.0098 | **−0.0280** |
| `gradyan` | +0.0094 | **+0.0458** | +0.0066 |
| `hepsi` (ikisi) | **+0.0831** | +0.0017 | **−0.0238** |

Örüntü fizikle tutarlı: **polarite tersi görünüm yalnızca kareler ters
polariteliyse kazandırıyor.** v1_t640/cm640 kurulurken `255−g` uygulandığı için
ters polariteli; v1_g640 düz gri. Yarışmada termal kameranın beyaz-sıcak mı
siyah-sıcak mı olduğunu **bilmiyoruz** — yani sabit seçim kumar.

**Çözüm: görünümü videodan oku.** Referans yüklenirken üç aday hazırlanır
(CLAHE-gri, polarite tersi, gradyan); ilk 3 karenin önerileri üzerinde her adayın
**tepe kosinüsü** ölçülür; taban gri görünümü geçen **en iyi tek** aday bankaya
eklenir. Mutlak eşik yok — adaylar yalnız birbirleriyle kıyaslanır.

| rejim | pay=0 | **pay=10 (karar satırı)** |
|---|---|---|
| v1_cm640 | +0.0617 | **+0.0868** |
| v1_t640 | −0.0085 | +0.0122 |
| v1_g640 | −0.0375 | −0.0080 |
| **v1_640 (renkli koruma)** | — | **0.0000** |
| **v2_termal (termal ref koruması)** | — | **0.0000** |

Seçimin doğru çalıştığı çıktıda görülüyor: ters-polariteli v1_cm640'ta beş
referansın dördüne `ters` ekliyor; düz gri v1_g640'ta dördün ikisinde **hiçbir
şey eklemiyor**.

**Neden bu, en değerli kalem:** v1_cm640 tam olarak mühürlü setteki çözülemeyen
dört referansın (v2-01…04, RGB nadir kırpma → termal kare) modellenmiş hâli ve
orada **+0.087** veriyor. Şu an o sınıftan sıfır alınıyor.

**Denenip elenen ölçüt:** kare içi z-sıyrılma. Gradyan uzayında z sistematik
olarak yüksek olduğu için seçim her zaman gradyanı seçiyor ve **polarite ayrımını
kaybediyor** (v1_cm640 +0.087 → −0.003). Tepe kosinüsü doğru sinyalmiş.

**Açık maliyet:** düz gri rejimde (mono kamera, RGB referans) pay=0'da −0.0375.
Karar satırı pay=10'da −0.0080 ile gürültü içinde. Kabul, karar satırına göre.

### NİHAİ HÂL ve ÜRETİM DOĞRULAMASI

Aday kümesi **yalnız `ters`** olarak daraltıldı. Gradyan adayı üretimde ölçüldü
ve zararlı çıktı: düz gri rejimde seçim her zaman gradyanı seçiyor, kaybı
−0.028'den **−0.042**'ye çıkarıyor; buna karşılık v1_cm640 kazancına **hiç**
katkısı yok (0.4731 her iki hâlde de aynı).

Marj şartı da denendi ve elendi: `marj=1.05` v1_cm640 kazancını +0.086 → +0.059
düşürdü, v1_g640 kaybını **hiç** azaltmadı. Zararlı seçimlerin oranı, yararlı
olanlarınkinden düşük değil — marj bu ikisini ayırmıyor.

**Üretim paketiyle uçtan uca ölçüm** (arena değil, dağıtılan kod):

| küme | koşul | kapalı | açık | fark |
|---|---|---|---|---|
| v1_cm640 (RGB nadir ref → sahte-termal) | pay=0 | 0.5320 | **0.5936** | **+0.0616** |
| v1_cm640 | pay=10 | 0.3874 | **0.4731** | **+0.0857** |
| v1_t640 (RGB fotoğraf ref → sahte-termal) | pay=0 | 0.4410 | 0.4356 | −0.0054 |
| v1_t640 | pay=10 | 0.3171 | **0.3283** | **+0.0112** |
| v1_g640 (RGB fotoğraf ref → düz gri) | pay=0 | 0.7449 | 0.7449 | **0.0000** |
| v1_g640 | pay=10 | 0.5286 | 0.5276 | **−0.0010** |
| v1_rgb | pay=10 | 0.6379 | 0.6379 | **0.0000** |
| v2_termal | pay=0 | 0.7288 | 0.7288 | **0.0000** |
| v2_termal | pay=10 | 0.5719 | 0.5719 | **0.0000** |

Arena +0.0868 demişti, üretim +0.0857 diyor — **bağımsız iki uygulama, aynı
büyüklük.** Teslim edilen üç rakamın üçü de değişmedi.

### Son iyileştirme: seçim yalnız KİLİTLİ karelerde

İlk hâlde seçim referansın gördüğü ilk 3 karede yapılıyordu — ama pay=10'da o
kareler **dolgu** bölgesinde, yani nesne henüz görünmüyor. Orada "hangi görünüm
daha iyi eşleşiyor" sorusunun anlamı yok; karşılaştırma arka planla yapılıyor ve
yanlış görünüm seçiliyordu. İzi ölçümde görünüyordu: v1_g640'ta seçim pay=0'da
hiç ateşlenmiyor (0.7449 = 0.7449) ama pay=10'da −0.0280 kaybettiriyordu.

Seçim, takipçinin **kilitli olduğu** karelere bağlandı:

| küme | koşul | önce | sonra |
|---|---|---|---|
| v1_cm640 | pay=10 | +0.0857 | **+0.0633** |
| v1_cm640 | pay=0 | +0.0616 | **+0.0431** |
| v1_g640 | pay=10 | **−0.0280** | **−0.0010** |
| v1_g640 | pay=0 | 0.0000 | **0.0000** |

Kazancın bir kısmı verildi, **ölçülebilir maliyet ortadan kalktı.** Bu projede
ölçülebilir dezavantajı olmayan bir kazanç, daha büyük ama riskli olana tercih
edilir. Mühürlü videonun puanlanan referanslarında değişiklik yine tam sıfırdır.

---

## KABUL: uyarlanır referans görünümü — açık karar kapatıldı

`SINIRLAR.md §4` bir **karar noktası** bırakmıştı: referansta nesne küçükse
sistem çöküyor (nesne referansın 1/16'si → mAP 0.905 → 0.460). Ölçek piramidi
kurtarıyor ama sıkı referansta −0.12 ödetiyor; başabaş "geniş çekim referans
gelme olasılığı %11–29'u geçerse". Yani kullanıcıya bir bahis bırakılmıştı.

**Bahsi kaldırdık.** Taban banka yine `tam`; ama takipçi **N kare boyunca hiç
kilitlenmezse** (= hiçbir aday tutmuyor, referans muhtemelen geniş çekim) banka
ölçek piramidiyle **kendiliğinden** genişletilir. Sıkı referansta kilit ilk
karelerde oluşur → ek banka hiç açılmaz → bedel **tam sıfır**.

### Bedel (referans bozulmamış, pay=10)

| küme | `tam` | `uyarlanır` | fark |
|---|---|---|---|
| v2_termal | 0.6209 | 0.6209 | **0.0000** |
| v1_640 | 0.5797 | 0.5797 | **0.0000** |

### Kazanç (nesne referansın 1/16'si, pay=10)

| küme | `tam` | sabit `piramit` | **`uyarlanır`** |
|---|---|---|---|
| v2_termal | 0.1569 | 0.5254 | **0.5334** |
| v1_640 | 0.3005 | 0.5468 | **0.5552** |

Uyarlanır hâl sabit piramitten **de** iyi: piramidin sıkı referansta ödettiği
bedeli ödemiyor, geniş çekimde ise aynı bankaya ulaşıyor.

### Üretim doğrulaması (dağıtılan paket, arena değil)

| koşul | kapalı | açık |
|---|---|---|
| v2_termal pay=10, referans 1/16 | 0.1505 | **0.5121** (+0.3616) |
| v1_rgb pay=0 | 0.8960 | **0.8960** |
| v1_rgb pay=10 | 0.6379 | **0.6379** |

### Portta yakalanan hata

İlk portta üretim v1_rgb pay=10'da 0.6379 → **0.6054** düştü. Sebep: pencere
kopukluğunda `kilit` bayrağı sıfırlanıyordu; dolgu bölgesinde beş kare kilit
oluşmayınca banka **sahte** genişletiliyordu. Arena bayrağı referans boyunca
kalıcı tutuyordu — doğrusu da o: bir referans **bir kez** kilitlenebildiyse geniş
çekim değildir. Düzeltildikten sonra rakam birebir geri geldi.

Yarışmada bir referansın **tek** penceresi olduğu için bu durum zaten oluşmaz;
hata bizim yer gerçeğimizin çok pencereli yapısı sayesinde görünür oldu.

---

## RED: ölçek-eşlemeli referans görünümü

**Fikir:** ölçüldü ki çözünürlük düşünce bozulan şey öneri değil **sıralama**
(tavan 1.000, top-1 0.961@94px → 0.627@31px). Referans keskin, aday bulanık;
gömme uzayında ayrışıyorlar. Referansın 64/128 px'e indirilip geri büyütülmüş
(yani adayın keskinlik seviyesine getirilmiş) kopyalarını bankaya koymak bu farkı
kapatmayı hedefliyordu.

| küme (pay=10) | taban | +64 px | +64/128 px |
|---|---|---|---|
| v2_termal | 0.6209 | **0.5548** | — |
| v1_640 | 0.5797 | **0.5591** | **0.5402** |

**Reddedildi**, hem de belirgin farkla (−0.066 / −0.021 / −0.040).

**Örüntü (bu projede üçüncü kez):** referans bankasına **koşulsuz** görünüm
eklemek zarar veriyor — çok-kırpma/döndürme, sıkı referansta ölçek piramidi, ve
şimdi ölçek-eşleme. Sebebi maks-kosinüs: her ek görünüm doğru eşleşmeyi
yükseltmiyor ama **yanlış adaylardan birini** yükseltebiliyor.

Buna karşılık bu gece kabul edilen iki eklemenin ikisi de **koşullu**:
* uyarlanır görünüm yalnız "hiç kilitlenmedi" ise açılıyor,
* çapraz-modal köprü yalnız kareler gri **ve** referans renkliyse, üstelik
  aday görünüm taban görünümü **yenmek zorunda**.

Ders: banka genişletmesi ancak **bir koşula bağlıysa ve kendini kanıtlıyorsa**
kazandırıyor.

---

## RED: skor vektörü ekseni (CLS-only vs [CLS | havuzlanmış yama], GeM)

Taban yolda (yama skorlaması olmadan) GeM havuzlaması umut vermişti: v2_termal
+0.0334, v1_640 +0.0324, v1_rgb −0.0011. Ama o yolun vektörü `[CLS|ortalama-yama]`;
dağıtılan sistem `s_cls`'i **yalnız CLS**'ten hesaplıyor. Doğru sorulmuş hâliyle
üretim yolunda ölçüldü (pay=10):

| varyant | v2_termal | v1_cm640 |
|---|---|---|
| `cls` (dağıtılan) | **0.6209** | **0.5057** |
| `cls+yama` / ortalama | 0.6331 (+0.012) | 0.4623 (**−0.043**) |
| `cls+yama` / GeM | 0.6061 (−0.015) | 0.5118 (+0.006) |

**İkisi de reddedildi.** `ort` termalde kazanıp çapraz-modalde çöküyor, `gem`
tam tersi. Hiçbiri iki rejimde birden kazanmıyor; taban yolda görülen GeM
kazancı üretim yoluna **taşınmıyor** çünkü orada havuzlanan yarım zaten
kullanılmıyor.

Mevcut `cls` seçimi doğrulanmış oldu.

---

## GENİŞ KÜMENİN ORTAYA ÇIKARDIĞI: teslim rakamları BÜYÜK nesneleri anlatıyor

Mühürlü videodan geometriyle üretilen 12 referanslık küme (`v2_termal_genis`,
316 kare) ilk kez koşuldu. Sonuç, elle denetlenmiş iki referansın verdiği resimden
**çok farklı**:

| küme | referans | nesne kenarı (ortanca) | mAP pay=0 | mAP pay=10 |
|---|---|---|---|---|
| v2_termal (elle denetlenmiş) | 2 | **212 px** (94 ve 329) | 0.7585 | 0.5719 |
| **v2_termal_genis** (geometrik) | **12** | **61 px** (31–97) | **0.2561** | **0.2795** |

**Sebep boyut.** Referans başına AP, nesne kenarıyla birlikte gidiyor:

| kenar | AP | | kenar | AP |
|---|---|---|---|---|
| 31 px | 0.149 | | 64 px | 0.690 |
| 37 px | 0.000 | | 64 px | 0.694 |
| 41 px | 0.160 | | 64 px | 0.000 |
| 48 px | 0.000 | | 67 px | 0.629 |
| 49 px | 0.222 | | 75 px | 0.588 |
| 58 px | 0.222 | | 97 px | 0.000 |

`<50 px` ortalama AP **0.106** · `≥50 px` ortalama AP **0.403**.

### Arıza ÖNERİDE değil, SIRALAMADA

Her GT karesinde "önerilerin arasında IoU ≥ 0.25 olan var mı" sayıldı:

| küme | öneri tavanı | elde edilen |
|---|---|---|
| tümü | **0.776** | 0.280 |
| < 50 px | 0.545 | — |
| ≥ 50 px | **0.941** | — |

Sıfır alan üç referansın **öneri tavanı 0.688 / 0.947 / 1.000**. Yani doğru kutu
üretiliyor, seçilemiyor. Sahnede birbirinin aynı çok sayıda araç var ve referans
kırpması hangisinin hedef olduğunu söylemiyor.

### Denenip elenen düzeltme: boyuta bağlı bağlam payı

Küçük nesnede bağlam açıkça zararlı — ve bu **tekdüze**:

| bağlam payı | v2_termal_genis pay=10 | isabet |
|---|---|---|
| 0.45 | 0.2198 | 0.329 |
| 0.30 | 0.2422 | 0.366 |
| **0.15 (mevcut)** | 0.2795 | 0.447 |
| **0.05** | **0.3274** | **0.545** |
| 0.00 | 0.3246 | 0.532 |

Payı kutunun kısa kenarına bağlamayı denedim (`kucuk_esik` px altında pay=0.05):

| eşik | v2_termal (mühürlü) | v2_termal_genis |
|---|---|---|
| kapalı | **0.5719** | 0.2795 |
| 30 px | 0.5046 | 0.2736 |
| 40 px | 0.5916 | 0.2857 |
| 60 px | **0.4745** | **0.3252** |

**Reddedildi.** Mühürlü sette sonuç **tekdüze değil** (0.572 → 0.505 → 0.592 →
0.475): bu sistematik bir kazanç değil, öneri yarışını rastgele çeviren bir
tedirginlik; 2 referanslık kümede ±0.05 zaten ~2 kare. Kod üretimde duruyor ama
**varsayılan kapalı** (`kucuk_esik=0`).

### Bunun anlamı

* Teslim edilen mühürlü rakamlar (0.7585 / 0.5719) **büyük nesneleri** anlatıyor.
  Yarışmada referans küçük bir araç olursa beklenti çok daha düşük olmalı.
* Bu, `SINIRLAR.md` §2'deki ~40 px sınırının **termal görüntüde, gerçek nesnelerle
  ve 12 referansla** doğrulanmış hâlidir; önceki kanıt çözünürlük türevlerinden
  dolaylı geliyordu.
* **Açık kalan en değerli iş kalemi budur** — öneri aşaması sağlam (tavan 0.94),
  kaybın tamamı sıralamada. Bağlam payı yolu ölçülerek kapandı; sıralama tarafına
  başka bir fikir gerekiyor.

---

## Ölçülüp SEÇENEK olarak bırakılan: takipçi uyum eşiği (`agree`)

Küçük nesnede kilit hiç oluşmuyordu. Teşhis: sıfır alan üç referansın ikisi
**neredeyse hiç kutu göndermiyor** (pencere boyunca 1 kutu), biri uzaktaki daha
küçük bir nesneye kilitleniyor — yani "aynı araca mı karıştı" değil, **kilit
kurulamıyor**. Küçük kutu birkaç piksel oynayınca IoMin ≥ 0.45 uyum şartı
sağlanmıyor ve seri sıfırlanıyor.

Eşik düşürüldü:

| küme | koşul | 0.45 (mevcut) | 0.30 | fark |
|---|---|---|---|---|
| v2_termal (mühürlü) | pay 10 | 0.5719 | **0.6081** | **+0.0362** |
| v2_termal | pay 0 | 0.7585 | 0.7585 | 0.0000 |
| v2_termal_genis (12 ref, küçük nesne) | pay 10 | 0.2795 | **0.3010** | **+0.0215** |
| v1_cm640 | pay 10 | 0.4507 | 0.4553 | +0.0046 |
| v1_rgb | pay 0 | 0.8960 | 0.8966 | +0.0006 |
| v1_rgb | pay 10 | 0.6379 | 0.6317 | −0.0062 |
| **v1_g640** | pay 10 | 0.5276 | **0.4766** | **−0.0510** |

Tepki **tekdüze**: 0.45 / 0.40 / 0.35 aynı sonucu veriyor, basamak 0.30'da
başlıyor (0.25'te 0.6109). Yani bağlam payı denemesindeki kaotik örüntü burada
**yok** — gerçek bir etki.

**Karar: varsayılan 0.45 kalıyor.** Bu gecenin standardı "ölçülen hiçbir rejimde
zarar yok"; gri sondadaki −0.0510 bunu ihlal ediyor. Kod pakette parametre olarak
duruyor (`agree`), ölçüm tablosuyla birlikte: yarışma videosunun nesneleri küçükse
`agree=0.30` **mühürlü videoda +0.036** getiriyor ve tek satırla açılıyor.

**Not — bu en umut verici açık kalemdir.** Küçük nesnedeki kaybın kaynağı
sıralama değil **kilit kurulamaması**; uyum ölçütünü kutu boyutuna göre
ölçekleyen bir sürüm (küçük kutuda piksel-mesafe, büyükte IoMin) her iki tarafı
da kazanabilir. Denenmedi; zaman yetmedi.

### Küçük nesne rejiminin tam teşhisi

`v2_termal_genis` (12 referans, 31–97 px) üzerinde her kapı tek tek kapatıldı:

| değişiklik | mAP | isabet | fark |
|---|---|---|---|
| **mevcut** | 0.2795 | 0.447 | — |
| dedektör kapısı kapalı | **0.3018** | 0.518 | **+0.0223** |
| uyum eşiği 0.45 → 0.30 | **0.3010** | 0.475 | **+0.0215** |
| bağlam payı 0.15 → 0.05 | **0.3274** | 0.545 | **+0.0479** |
| `politika=always` | 0.2635 | 0.529 | −0.0160 |
| uyum ölçütü boyuta göre (`kucuk_px=50`) | 0.2688 | 0.453 | −0.0107 |

**Örüntü net: bütün kapılar BÜYÜK nesneye göre ayarlanmış.** Her birini gevşetmek
küçük nesnede kazandırıyor — ama aynı gevşeme büyük nesnede kaybettiriyor
(dedektör kapısı v1'de +0.018, uyum 0.30 gri sondada −0.051, bağlam payı mühürlüde
tekdüze olmayan sonuç). `politika=always` ise her iki tarafta da kötü: isabet
yükseliyor (0.529) ama kesinlik çöküyor.

İlk boyuta-koşullu deneme (`kucuk_px`: küçük kutuda IoMin yerine merkez mesafesi)
**işe yaramadı** — küçük kutular birbirine daha kolay “uydu” ve takipçi yanlış
şeylere daha hızlı kilitlendi (−0.0107).

**Açık kalan iş, tam olarak şudur:** kapı politikasını nesne boyutuna göre
ayrıştırmak. Sinyal elimizde (aday kutunun piksel boyutu, kare başına bedava),
yön belli (küçükte gevşe, büyükte sıkı kal), ama ilk denemem transfer etmedi.
Bu kalemin değeri büyük: küçük nesnede öneri tavanı 0.55–0.94 iken elde edilen
0.106–0.403.

### RED: referans başına sıkı kırpma kipi (`dar_px`) — birleşimde çöküyor

Küçük nesnede en büyük tek kazanç bağlam payını düşürmekti (+0.048), ama global
uygulanınca mühürlü videoda −0.099 veriyordu. Doğal çözüm: **referans başına**,
kilit oluştuktan sonra ölçülen kutu boyutuna göre sıkı kırpmaya geçmek.

| eşik | v2_termal_genis | v2_termal | v1_rgb | v1_g640 | v1_cm640 |
|---|---|---|---|---|---|
| kapalı | 0.2795 | **0.5719** | **0.6379** | **0.5276** | **0.4507** |
| 50 px | 0.2891 (+0.010) | 0.5719 (0.000) | 0.6367 (−0.001) | 0.4929 (**−0.035**) | 0.3874 (**−0.063**) |
| 80 px | 0.2855 | 0.5851 | — | — | — |
| 120 px | 0.2855 | 0.4701 (−0.102) | — | — | — |

**Reddedildi.** İlk iki sütuna bakıp kabul etmek kolaydı — mühürlüde bedel sıfır,
küçük kümede +0.010. Ama çapraz-modal rejimde **tam olarak 0.3874**'e düşüyor;
yani köprü hiç eklenmemiş gibi. Sebep etkileşim: köprü seçimi kilitli karelerde
`E` üzerinden yapılıyor, sıkı kırpma kipi de kilitten sonra `E`'yi değiştiriyor —
seçimin dayandığı taban ile skorlamanın tabanı ayrışıyor.

**Bu, birleşim doğrulamasının neden şart olduğunun taze bir örneğidir.** İki
değişiklik tek tek zararsız, bir arada biri ötekini iptal ediyor. Kod pakette
duruyor, `dar_px=0` ile **kapalı**.
