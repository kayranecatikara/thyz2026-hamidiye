# Görev 3 protokol notları — resmî arayüz kodundan doğrulandı

Kaynak: `rakip/hyz/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU/src/`
(şartnamede yazmayan, yalnızca koddan görülen şeyler).

---

## 1. Referans penceresi baştan belli

`GET /reference/` her referans için şunu döner:

```
{url, session, image_url, frame_start, frame_end,
 frame_start_image_url, frame_end_image_url, order}
```

Yani nesnenin hangi kare aralığında aranacağı önceden biliniyor. **Pencere gerçek
görünürlükten geniştir** — 16 Temmuz oturumunda referans 1'in penceresi 161–205'ti,
biçerdöver 173–203 arasında görünüyordu. Kenarlardaki her kutu saf yanlış pozitiftir;
ölçüldü, "her karede gönder" politikası bu yüzden kaybediyor.

`frame_start_image_url` / `frame_end_image_url` de veriliyor: pencerenin ilk ve son
karesinin görüntüsü. **Şu an bunları kullanmıyoruz** — nesnenin o iki karedeki
görünümü, referans bankasına eklenebilecek *modalite ve bakış açısı olarak doğru*
iki ek görünüm demek. Denenmeye değer (bkz. bölüm 4).

## 2. Skor alanı YOK

`ReferencePrediction.create_payload()` şunu üretiyor:

```python
{'reference', 'frame', 'top_left_x', 'top_left_y', 'bottom_right_x', 'bottom_right_y'}
```

Güven skoru alanı yok → skorsuz mAP ≈ P × R.

## 3. ⚠ AÇIK SORU: bir referans için karede kaç kutu gönderilebilir?

`FramePredictions.reference_predictions` bir **listedir** ve `add_reference_prediction`
yalnızca `append` yapar. Aynı `reference_url` için birden fazla kutu eklemeyi
**yapısal olarak engelleyen bir şey yok**. Ama `ReferencePrediction`'ın kendi
belgesi tekil konuşuyor: *"the team submits a bounding box per frame in that interval"*.

**Bu neden önemli:** karede *k* kutu gönderildiğinde, kare başına tek GT varsayımıyla

    kesinlik = R_k / k ,  duyarlılık = R_k  →  AP ≈ R_k² / k

- **İyi sıralayıcı** (R₁ ≈ 0.95): k=1 → 0.90 · k=2 → 0.48. **Tek kutu doğru.**
- **Rastgeleye yakın sıralayıcı**, N aday: R_k = k/N → AP = k/N², *k ile artıyor*.
  Hepsini göndermek 1/N, tek tahmin 1/N². N=10'da **10 kat fark**.

Yani çözülemeyen bir referansta (bizde: yer seviyesi cephe fotoğrafı) şu an sıfır
alıyoruz; tüm makul adayları göndermek ~1/N getirebilir.

**AMA bu, AP'nin nasıl toplandığına bağlı.** Referans bazında hesaplanıyorsa
kazanç serbest. Tüm gönderimler havuzlanıyorsa, umutsuz referansta saçmak
**iyi referansların kesinliğini de düşürür** ve net zarar olabilir. Bunu çevrimdışı
doğrulamak mümkün değil.

**Organizasyona sorulacak:** *AP referans başına mı hesaplanıyor yoksa tüm
gönderimler havuzlanıyor mu? Bir referans için aynı karede birden fazla kutu
kabul ediliyor mu, ediliyorsa fazlası nasıl puanlanıyor?*

Cevap gelene kadar **k = 1** varsayılan kalır. Doğrulanmamış bir metrik varsayımı
üzerine tüm skoru kumar oynamak doğru değil.

## 4. Kullanılmayan bedava sinyal: pencere uç karesi görüntüleri

`frame_start_image_url` ve `frame_end_image_url`, nesnenin **kare modalitesinde ve
nadir bakış açısında** iki örneği demek. Referans fotoğrafı eğik/yer seviyesi/RGB
olabilir; bu ikisi tanım gereği videonun kendi alanında. Referans bankasına
eklenirlerse çapraz-modal ve çapraz-bakış açısı problemlerinin ikisini de doğrudan
hafifletir.

⚠ Dikkat: bu görüntüler **kutu içermez**, sadece karenin tamamıdır. Yani nesnenin
kare içinde nerede olduğu bilinmiyor — doğrudan referans olarak kullanılamazlar.
Kullanılabilmesi için o karede nesnenin bulunması gerekir, ki bu tavuk-yumurta
problemidir. Yine de: pencerenin ilk karesinde tespit yapılıp kilitlendikten sonra
o kırpma bankaya eklenebilir (bizim ölçtüğümüz "online banka" fikri — 0.917 → 0.80,
**zarar verdi**, banka kirleniyor). Denenmişti, kaybetti.

## 5. Hız sınırı

`get_reference_objects` için: **dakikada en fazla 5 istek**. Resmî istemci
referansları `references.json`'a önbellekliyor ve `force_download` verilmedikçe
dosyadan okuyor. Oturum başında bir kez çekip saklamak şart.

## 6. IoU eşiği 0.25

Resmî TEKNOFEST reposunun README'sinden. Şartname 9.3 "detaylar revizyonda" diyor.
Takımın mevcut `gorev3` kodu 0.5 varsayarak kalibre edilmişti — yanlış çalışma noktası.

---

## 7. KULLANILMAYAN SİNYAL: telemetri (`GET /translation/`)

Resmî istemci **her kare için** `GET /translation/` çekiyor ve dönen
`translation_x/y/z` değerlerini `FramePredictions`'a koyup `detection_model.process(...)`
çağrısına iletiyor (`main.py`). Yani drone'un konumu **çıkarım anında elimizde** ve
Görev 3 bunu şu ana kadar hiç kullanmıyordu.

Örnek veri setinde de var: `THYZ_2026_Ornek_Veri_{1,2}_translation.csv` — her iki
video için tam kare telemetrisi (9022 ve 9025 satır), artı
`Kamera_Kalibrasyon_Parametreleri_2026.txt` (termal f=732 @640×512,
RGB 1080p f=1390 @1920×1080, RGB 4K f=2792 @4000×3000).

**Veri kümülatif konumdur** (metre), kare başına delta değil. Kare başına hareket
~0.15–0.23 m (≈7 m/s).

### Ne yapabilir, ne yapamaz — ölçüldü

| | sonuç |
|---|---|
| Dünya→görüntü eşlemesi (tek 2×2 harita) | v2'de R²=+0.65, **v1'de R² negatif** |
| |piksel| ↔ |metre| korelasyonu | **+0.873 (v1) · +0.887 (v2)** |
| Büyüklük tahmininde hata | medyan %20 / %25 |
| Çözülen irtifa | **~42 m (v1) · ~32 m (v2)** |

**Yapamaz:** ego-hareketin yerine geçemez. Telemetri **yönelim (yaw) vermiyor**;
drone döndükçe dünya→görüntü eşlemesi de dönüyor. v1'de uçuş dönüşlü olduğu için
sabit bir harita tamamen başarısız (R² negatif).

**Yapabilir:** hareketin **büyüklüğünü** verir — bu dönmeden bağımsızdır. Bu yüzden
homografiyi **denetlemek** için kullanılabilir: 3× eşikte **yanlış alarm %0**
(774 çift, iki video). Pakette `set_translation()` olarak eklendi, isteğe bağlı.

**En değerli çıktısı:** çalışma sınırının fiziksel karşılığı.
`en küçük güvenilir nesne ≈ 40 · Z / f` → tipik irtifada **~1,2–1,7 m**.

## 8. AÇIK İZ: referans fotoğraflarındaki GPS

v1 referanslarından **01–04'ü EXIF GPS taşıyor** (DJI M3T, nesne başına farklı
koordinat: 41°06′27–28″N, 28°35′29–30″E). v1-05, v1-06 ve **v2'nin tüm PNG
referansları** metadata taşımıyor; kareler de temiz.

Yarışmada referanslar GPS taşırsa ve telemetrinin başlangıç noktası coğrafi olarak
bilinirse, referansın konumu kareye izdüşürülüp "nerede arayacağımıza" güçlü bir ön
bilgi çıkarılabilir. **Doğrulanamadı:** telemetrinin coğrafi orijini ve kameranın
yönelimi verilmiyor.

⚠ Bu iz, v2'nin çözülemeyen dört RGB referansı için de denendi ve **kapandı** —
o PNG'lerde EXIF yok, dolayısıyla o sınıfın yer gerçeği bu yolla kurulamıyor.
