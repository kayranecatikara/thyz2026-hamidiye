# Model ağırlıkları

**İndirme adımı yok.** İki ağırlık da depoyla birlikte geliyor:

| Ağırlık | Nerede | Boyut |
|---|---|---|
| **DINOv3-S/16** | `gorev3_v2/agirliklar/models--timm--vit_small_patch16_dinov3.lvd1689m/` | 82 MB |
| **FastSAM-s.pt** | depo kökü | 23 MB |

## Nasıl bulunuyorlar

**DINOv3.** Paket içe aktarılırken, yanındaki `agirliklar/` klasörünü Hugging Face
önbelleği olarak işaretler (`HF_HUB_CACHE`). Yani ev dizinine kopyalama da
gerekmez — klonla ve çalıştır. Kendi `HF_HOME` / `HF_HUB_CACHE` ayarınız varsa
**ona dokunulmaz**, sizinki kazanır.

**FastSAM.** Sırayla aranır: açıkça verilen yol → `GOREV3_FASTSAM` ortam
değişkeni → depo kökü → paket klasörü → çıplak ad (ultralytics indirir; ağ ister).

> Bu sıralama bir hata yüzünden eklendi: varsayılan `"FastSAM-s.pt"` göreli bir
> yoldu ve çalışma dizinine göre çözülüyordu. İstemci depo dışından çalıştığı için
> ağırlık sahada bulunamazdı.

## Doğrulama

```bash
python3 -m gorev3_v2.onkontrol
```

Çıktıda `modeller yüklendi` görünüyorsa her şey yerindedir. Bu komut ayrıca ilk
çağrıyı önceden yapar, böylece yarışmada ilk kare 10 saniye sürmez.

## Çevrimdışı kip

Paket içe aktarılır aktarılmaz `HF_HUB_OFFLINE=1` **kendiliğinden açılır** —
sahada internet yok ve ağa çıkma denemesi zaman aşımına düşüp "neden takıldı"
sorusu sordurur. Bilerek kapatmak için: `GOREV3_ALLOW_NETWORK=1`.
