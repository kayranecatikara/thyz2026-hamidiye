# Geniş kıyas — videodan geometriyle üretilmiş yer gerçeği

## Neden

Ölçüm tabanının en dar yeri **mühürlü taraf**: 2 puanlanabilir referans, ~201
etiketli kare, tek karenin mAP etkisi ~0.025. Bu gecenin adaylarının çoğu tam o
büyüklükte (+0.01…+0.03), yani mevcut sette **ayırt edilemiyorlar**.

## Nasıl üretildi

1. Video boyunca eşit aralıklarla **çapa kareleri** seçilir.
2. Çapa karesinde FastSAM önerileri çıkarılır; ayırt edici olanlar "nesne" sayılır.
3. Çapa ile değerlendirme karesi arasında **sıçramalı bileşke homografi** kurulur:
   doğrudan ORB eşlemesi ~25 karede kopuyor (ölçüldü: içkatman 20 karede 111–230,
   30 karede 6–9), bu yüzden 15'er karelik güvenilir adımlar birleştirilir.
   Kare kare zincirlemeye göre 15 kat az adım → çok daha az sürüklenme.
4. Kutu geometriyle taşınır; bu **yer gerçeğidir** ve hiçbir dedektörden gelmez.
5. Referans fotoğrafı = çapa karesindeki kırpma; değerlendirme çapadan 10 kare
   sonra başlayan ardışık şeritte yapılır.

## Süzgeçler (gözle denetimden sonra eklendi)

İlk turda GT'nin bir kısmı kullanılamazdı: yol kenarı gibi **ayırt edici olmayan**
yamalar ve homografinin ince şeritlere dejenere ettiği kutular. Eklenen kapılar:

| kapı | değer | neden |
|---|---|---|
| referans kırpması kontrastı | std ≥ 14 | termalde FastSAM düz alanları da bölütlüyor |
| kutu alanı | %0.2 – %8 | çok küçük/çok büyük olan ölçmüyor |
| en-boy kararlılığı | \|log oran\| ≤ 0.30 | şeride dejenere olan kutuyu eler |
| kenar payı | 8 px | kadraj dışına çıkanı eler |
| referans başına en az kare | 15 | kısa/kırılgan izleri eler |

## Fotometrik doğrulama (ikinci gözle denetimden sonra eklendi)

İkinci turda v1_rgb kümesi **kullanılamazdı**: kutuların çoğu ince şerit çıktı.
Sebebi, FastSAM'in RGB'de çatı kenarı / yol gibi uzun ince bölütler üretmesi ve
en-boy süzgecimin yalnız *değişimi* denetlemesiydi. İki kapı eklendi:

* mutlak en-boy `0.45 < w/h < 2.2`, kısa kenar ≥ kare kenarının %3'ü
* **ZNCC doğrulaması:** çapa kırpması ile taşınan kırpma arasındaki normalize
  korelasyon. Homografi geometrik olarak makul görünse bile kutu yanlış yere
  oturabilir (özellikle **düzlem dışı** yapılarda: bina çatısı, ağaç).
  İz *bütünüyle* kabul veya reddedilir (medyan ZNCC ≥ 0.55, min ≥ 0.25) —
  kare kare ayıklama YAPILMAZ, çünkü o, zor kareleri atıp kıyası kolaylaştırırdı.

Bu, yer gerçeğini **dedektörden bağımsız ikinci bir kanaldan** denetler.

## Ne ölçer, ne ölçmez — açıkça

* **Ölçer:** sıralama ve zamansal katman — sistemin ölçülmüş asıl darboğazı.
* **Yanlı:** "nesne" adayları çapa karesinde **FastSAM ile** seçildiği için küme,
  dedektörün bulabildiği nesnelere yanlıdır. Öneri aşamasının tavanı burada
  ölçülemez.
* **Kolaydır:** referans, değerlendirme karelerinden yalnızca 10–50 kare önce ve
  aynı modalitede alınır. Gerçek görevdeki bakış açısı/modalite farkı **yoktur**.
* **Ama susmak cezalandırılır:** GT değerlendirme karesinde dedektörden bağımsız
  (geometrik) üretilir. Reponun döngüsel kalibrasyonundaki hata burada yok.

**Bu yüzden:** elle denetlenmiş GT'nin *yerine* geçmez. Yanında duran, büyük
örneklemli bir **teyit kümesidir** — "kabul edilen değişiklik geniş örneklemde de
zarar vermiyor mu?" sorusuna cevap verir.

## Boyut

| küme | referans | etiketli kare |
|---|---|---|
| v2_termal (elle denetlenmiş) | 2 | 201 |
| **v2_termal_genis** | **23** | **601** |

---

## Üçüncü sahne denemesi (internetten)

`SINIRLAR.md` "üçüncü bir video, yapılabilecek en değerli tek eklemedir" diyor.
Otomatik yer gerçeği üretimi hazır olduğu için bu artık mümkün.

| deneme | sonuç |
|---|---|
| Wikimedia Commons araması | nadir çekim bulunamadı (hepsi eğik/yörüngesel) |
| Pixabay "tarla/yol" klibi | **elendi** — ufuk çizgisi görünüyor, düzlem varsayımı çöker |
| Pixabay "otopark" klibi | alındı: 583 kare, zemin düzlemsel, çok sayıda **birbirine çok benzer araç** |

Otopark klibi **eğiktir**, görev ise nadir. Bu yüzden karar verdirici bir küme
olarak kullanılmaz; yalnızca "tanımadık bir sahnede bir şey kırılıyor mu?"
sorusuna bakılır. Ayrıca birbirinin aynı onlarca araç içerdiği için tek-örnekle
eşleştirmenin **en zor** hali: doğru cevap yapısal olarak belirsiz.

Video dosyası yalnızca yerel ölçüm için indirildi; **teslim klasörüne konmadı.**
