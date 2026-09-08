# Model ağırlıkları — kurulum

Paketin çalışması için iki ağırlık gerekir. **İkisi de bu klasörde**, yani makinede
internet olmasa da çalışır:

| Ağırlık | Nerede | Boyut |
|---|---|---|
| **FastSAM-s.pt** | `../FastSAM-s.pt` (bir üst klasör) | 23 MB |
| **DINOv3-S/16** | `models--timm--vit_small_patch16_dinov3.lvd1689m/` | 83 MB |

## DINOv3 nasıl yerine konur

`timm` bu ağırlığı Hugging Face önbelleğinden okur. Buradaki klasörü önbelleğe
kopyalayın:

**Windows**
```
xcopy /E /I "models--timm--vit_small_patch16_dinov3.lvd1689m" ^
  "%USERPROFILE%\.cache\huggingface\hub\models--timm--vit_small_patch16_dinov3.lvd1689m"
```

**Linux / macOS**
```
cp -r models--timm--vit_small_patch16_dinov3.lvd1689m \
   ~/.cache/huggingface/hub/
```

Alternatif: `HF_HOME` ortam değişkenini bu klasörün bir üstüne işaret ettirin.

## Doğrulama

```
python -m gorev3_v2.onkontrol
```

Çıktıda `modeller yüklendi` görünüyorsa ağırlıklar yerindedir. Görünmüyorsa hata
mesajı ne yapılacağını söyler.

> Paket içe aktarılırken `HF_HUB_OFFLINE=1` **otomatik açılır** — yarışmada internet
> yok ve ağa çıkma denemesi zaman aşımına düşüp sahada "neden takıldı" sorusu
> sordurur. Ağırlık indirmek gerekirse `GOREV3_ALLOW_NETWORK=1` ile açın.
