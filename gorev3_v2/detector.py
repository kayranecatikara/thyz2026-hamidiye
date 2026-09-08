"""Görev 3 v2 — çekirdek dedektör.

Mimari (gerçek yarışma verisiyle ölçülerek seçildi, bkz. ../README.md):

    kare -> FastSAM sınıf-bağımsız segment önerileri (~50 kutu, referanstan BAĞIMSIZ)
         -> her öneri kırpması DINOv3 ile gömülür (letterbox, fp16, tek batch)
         -> referans gömmesiyle kosinüs -> en yüksek skorlu kutu

Neden bu:
  * Kırpma-seviyesi gömme, yoğun yama korelasyonundan ve yerel öznitelik eşlemeden
    (SIFT/LightGlue) bu veride çok üstün: eğik/yer seviyesi referansı nadir kareye,
    hatta TERMAL referansı RGB kareye bağlayabiliyor.
  * FastSAM nesneyi ayrı segmentlediği için kutu SIKI çıkıyor (ölçülen mIoU ~0.75).
  * Öneriler referanstan bağımsız: bir karede N referans aktifse FastSAM 1 kez çalışır,
    kırpma gömmeleri 1 kez hesaplanır, her referans yalnızca bir matmul ekler.
"""
from __future__ import annotations

import cv2
import numpy as np
import timm
import torch

DEV = "cuda" if torch.cuda.is_available() else "cpu"


def iomin(a, b):
    """Kesişim / küçük kutunun alanı (kenardan kırpılan nesneler için IoU'dan iyi)."""
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    m = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return inter / m if m > 0 else 0.0


class Embedder:
    """DINOv3 kırpma gömücüsü (CLS + ortalama yama, L2-normalize)."""

    def __init__(self, model_name="vit_small_patch16_dinov3.lvd1689m", crop=224, amp=True):
        self.m = timm.create_model(
            model_name, pretrained=True, num_classes=0, dynamic_img_size=True
        ).eval().to(DEV)
        cfg = timm.data.resolve_model_data_config(self.m)
        self.mean = torch.tensor(cfg["mean"]).view(1, 3, 1, 1).to(DEV)
        self.std = torch.tensor(cfg["std"]).view(1, 3, 1, 1).to(DEV)
        self.npre = getattr(self.m, "num_prefix_tokens", 1)
        patch = self.m.patch_embed.patch_size[0]
        self.patch = patch
        self.crop = int(round(crop / patch)) * patch      # yama boyutuna hizala
        self.amp = amp and DEV == "cuda"

    @torch.no_grad()
    def __call__(self, crops, batch=128, yama=False, ic_oran=1.0):
        """crops: BGR np dizileri listesi -> (N, 2D) normalize gömme.

        yama=True ise ek olarak (yama_tokenlari, gecerlilik_maskesi) da döner:
        gri/termal karede yama düzeyinde skorlama için gerekli (bkz. patch_skor).
        ic_oran<1 ise bağlam payı bölgesindeki yamalar maskelenir.
        """
        outs, Ys, Ms = [], [], []
        S = self.crop
        for i in range(0, len(crops), batch):
            xs, masks = [], []
            for c in crops[i:i + batch]:
                h, w = c.shape[:2]
                s = S / max(h, w)
                nw, nh = max(1, int(w * s)), max(1, int(h * s))
                r = cv2.resize(c, (nw, nh), interpolation=cv2.INTER_AREA)
                canvas = np.zeros((S, S, 3), np.uint8)    # letterbox: en-boy oranı korunur
                y0, x0 = (S - nh) // 2, (S - nw) // 2
                canvas[y0:y0 + nh, x0:x0 + nw] = r
                xs.append(canvas)
                if yama:
                    G = S // self.patch
                    mk = np.zeros((S, S), np.uint8)
                    if ic_oran >= 1.0:
                        mk[y0:y0 + nh, x0:x0 + nw] = 1
                    else:
                        ih, iw = int(nh * ic_oran), int(nw * ic_oran)
                        mk[y0 + (nh - ih) // 2:y0 + (nh - ih) // 2 + ih,
                           x0 + (nw - iw) // 2:x0 + (nw - iw) // 2 + iw] = 1
                    masks.append(cv2.resize(mk, (G, G), interpolation=cv2.INTER_AREA) > 0.5)
            x = torch.from_numpy(np.stack(xs)[:, :, :, ::-1].copy()).permute(0, 3, 1, 2)
            x = x.float().div_(255).to(DEV)
            x = (x - self.mean) / self.std
            with torch.autocast("cuda", torch.float16, enabled=self.amp):
                f = self.m.forward_features(x)
            f = f.float()
            e = torch.cat([f[:, 0], f[:, self.npre:].mean(1)], -1)
            outs.append(torch.nn.functional.normalize(e, dim=-1))
            if yama:
                Ys.append(torch.nn.functional.normalize(f[:, self.npre:], dim=-1))
                Ms.append(torch.from_numpy(np.stack(masks).reshape(len(masks), -1)).to(DEV))
        E = torch.cat(outs, 0) if outs else torch.zeros((0, 1), device=DEV)
        if not yama:
            return E
        Y = torch.cat(Ys, 0) if Ys else torch.zeros((0, 1, 1), device=DEV)
        M = torch.cat(Ms, 0) if Ms else torch.zeros((0, 1), dtype=torch.bool, device=DEV)
        return E, Y, M


class Proposer:
    """FastSAM sınıf-bağımsız kutu önerileri (kare başına 1 kez, tüm referanslar paylaşır)."""

    def __init__(self, weights="FastSAM-s.pt", imgsz=768, conf=0.2, iou=0.75):
        from ultralytics import FastSAM
        self.m = FastSAM(weights)
        self.kw = dict(imgsz=imgsz, conf=conf, iou=iou, retina_masks=False, verbose=False,
                       device=0 if DEV == "cuda" else "cpu")

    def __call__(self, bgr, max_props=50, min_area=200, max_area_ratio=0.5):
        """Kutulari kareye kirp, cok kucuk ve cok BUYUK olanlari ele.

        UST SINIR KRITIK: FastSAM tum kareyi kaplayan arka plan segmenti uretiyor
        ve genel bir referansla kosinusu yuksek cikiyor -> gercek nesne eziliyor.
        Termal videoda kazanan kutularin alan orani 0.53-1.00 olculdu; bu filtre
        eklenmeden once termal taraf tamamen coküyordu.
        """
        r = self.m(bgr, **self.kw)[0]
        if r.boxes is None:
            return []
        H, W = bgr.shape[:2]
        full = float(H * W)
        out = []
        for x0, y0, x1, y1 in r.boxes.xyxy.cpu().numpy():
            x0, y0 = max(0.0, float(x0)), max(0.0, float(y0))
            x1, y1 = min(float(W), float(x1)), min(float(H), float(y1))
            a = (x1 - x0) * (y1 - y0)
            if a < min_area or a / full > max_area_ratio:
                continue
            if x1 - x0 < 12 or y1 - y0 < 12:      # her kutunun gecerli kirpmasi olsun
                continue
            out.append([x0, y0, x1, y1])
        out.sort(key=lambda z: -(z[2] - z[0]) * (z[3] - z[1]))
        return out[:max_props]


def is_grayish(bgr, thresh=2.0):
    """Görüntü gerçekten gri (termal/tek kanal) mi?

    DİKKAT — eski `gorev3` kodundaki eşik 12.0 idi ve YANLIŞTI: havadan çekilen
    soluk RGB kareler bile kanallar-arası ortalama std ~8-10 veriyor, yani RGB
    kareler "gri" sanılıp griye çevriliyordu (ölçüldü: halı saha isabeti
    0.895 -> 0.711'e düşüyor). Gerçek termal görüntüde std ~0'dır; bu yüzden
    ortalama değil YÜKSEK YÜZDELİK kullanılır ve eşik çok daha düşüktür.
    """
    b, g, r = cv2.split(bgr.astype(np.float32))
    sd = np.std(np.stack([b, g, r]), axis=0)
    return float(np.percentile(sd, 99)) < thresh


def clahe_gray(bgr, clip=2.0, grid=8):
    g = cv2.createCLAHE(clip, (grid, grid)).apply(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)


def gradient_view(bgr, clip=2.0, grid=8):
    """CLAHE + Sobel büyüklüğü: görünümü atar, YAPIYI bırakır.

    Modalite köprüsü adaylarından biri. Renk/parlaklık ilişkisi modaliteler
    arasında taşınmaz, kenar yapısı çoğu zaman taşınır.
    """
    g = cv2.createCLAHE(clip, (grid, grid)).apply(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    m = cv2.normalize(cv2.magnitude(gx, gy), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    m = cv2.createCLAHE(clip, (grid, grid)).apply(m)
    return cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)


def reference_embedding(emb: Embedder, ref_bgr, add_gray=True):
    """Referans gömmesi (oturum başında bir kez).

    ÖLÇÜM NOTU: çok-kırpma / çok-döndürme artırımı bu veride İŞE YARAMADI, hafif
    ZARAR verdi (A 1.000 -> 0.968, B 0.895 -> 0.816). Tek görünüm en iyisi.
    Tek istisna: gri/termal karelere dayanıklılık için referansın CLAHE-normalize
    gri kopyası ikinci görünüm olarak eklenir (RGB oturumda nötr ölçüldü).
    """
    views = [ref_bgr]
    if add_gray and not is_grayish(ref_bgr):
        views.append(clahe_gray(ref_bgr))
    return emb(views)


def crop_with_pad(im, box, pad=0.0):
    """Kutuyu kirp; pad>0 ise kutu boyutunun oraninda BAGLAM ekle.

    OLCUM: %15 baglam payi mAP'i 0.8063 -> 0.9170 yapiyor (en buyuk tek gomme
    kazanci). Nesnenin cevresi "bu nerede duruyor" bilgisini tasiyor. Ama %30
    yikici: nesne kaybolup arka plan bakin oluyor. Gonderilen kutu HER ZAMAN
    paysiz olandir; pay yalnizca gomme icin kullanilir.
    """
    H, W = im.shape[:2]
    x0, y0, x1, y1 = box
    if pad:
        dw, dh = (x1 - x0) * pad, (y1 - y0) * pad
        x0, y0, x1, y1 = x0 - dw, y0 - dh, x1 + dw, y1 + dh
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(W, int(x1)), min(H, int(y1))
    return im[y0:y1, x0:x1]


def merge_boxes(cands, iomin_th=0.30, margin=0.03):
    """En iyi adayi, ONUNLA ORTUSEN ve skoru yakin diger onerilerle birlestir.

    Gerekce: FastSAM bir nesneyi parcalara boluyor (bicerdover = govde + tabla).
    Tek segment secilince kutu nesnenin yarisini kaciriyor. OLCUM: 0.8710 -> 0.9285,
    ve marj 0.03'te iomin esigine duyarsiz — yani ayar hassasiyeti yok.
    """
    if not cands:
        return cands
    tb, ts = cands[0]
    b = list(tb)
    area_t = (tb[2] - tb[0]) * (tb[3] - tb[1])
    for o, sc in cands[1:]:
        if sc >= ts - margin and iomin(o, tb) >= iomin_th:
            if (o[2] - o[0]) * (o[3] - o[1]) <= 3.0 * area_t:   # dev segmenti yutma
                b = [min(b[0], o[0]), min(b[1], o[1]), max(b[2], o[2]), max(b[3], o[3])]
    return [(b, ts)] + cands[1:]


def pay_sec(box, pad, kucuk_pay, kucuk_esik):
    """Bağlam payını KUTUNUN BOYUTUNA göre seç.

    ÖLÇÜM: %15 bağlam büyük nesnede en büyük tek gömme kazancıydı (0.806→0.917),
    ama KÜÇÜK nesnede tersine çalışıyor — nesne kırpmanın içinde küçülüyor ve
    zaten kıt olan piksel çözünürlüğü bağlama harcanıyor. Termal videodan
    geometriyle üretilen 12 referanslık küçük-nesne kümesinde (31–97 px):
        pay 0.45 → 0.2198 · 0.30 → 0.2422 · 0.15 → 0.2795 · 0.05 → 0.3274
    Yani sabit bir pay yok; eşik kutunun kısa kenarıdır.
    """
    if not kucuk_pay or not kucuk_esik:
        return pad
    kisa = min(box[2] - box[0], box[3] - box[1])
    return kucuk_pay if kisa < kucuk_esik else pad


def crops_of(im, boxes, pad=0.0, min_side=4, kucuk_pay=0.0, kucuk_esik=0):
    crops, keep = [], []
    for i, b in enumerate(boxes):
        c = crop_with_pad(im, b, pay_sec(b, pad, kucuk_pay, kucuk_esik))
        if c.size and c.shape[0] > min_side and c.shape[1] > min_side:
            crops.append(c)
            keep.append(i)
    return crops, keep


@torch.no_grad()
def embed_proposals(emb: Embedder, im, boxes, pad=0.15, kucuk_pay=0.0, kucuk_esik=0):
    """Kare başına BİR kez: önerilerin gömmeleri. Döner: (kutular, gömme matrisi)."""
    crops, keep = crops_of(im, boxes, pad=pad, kucuk_pay=kucuk_pay, kucuk_esik=kucuk_esik)
    if not crops:
        return [], None
    return [boxes[i] for i in keep], emb(crops)


def patch_skor(Yp, Mp, Yr, Mr, G, delta=5):
    """Yama düzeyinde görünüm skoru + döngüsel tutarlılık süzgeci.

    NEDEN VAR: kırpmanın yama tokenlarının ORTALAMASI, nesnenin ayırt edici
    yamalarını arka planla seyreltir. Renk varken bu sorun değil — global renk/doku
    istatistikleri zaten güçlü. Renk gidince (gri/termal) o istatistikler bozulur ve
    ortalama yanıltıcı olur. Bu skor bunun yerine HER öneri yaması için referans
    yamaları üzerinde MAKS kosinüs alır, sonra ortalar.

    DÖNGÜSEL SÜZGEÇ: i -> j (referansta en iyi) -> u (öneride en iyi) gidip dön;
    |i-u| ızgara mesafesi delta'yı aşıyorsa o eşleşme atılır. Süzgeç olmadan yöntem
    zarar verir. Ölçüldü (sahte-termal): delta 0 -> 0.4994 · 3 -> 0.5048 ·
    **5 -> 0.5377** · 8 ve 13 -> 0.5213. Tepe 5-8'de, iki uç da daha kötü.

    ÖLÇÜLEN ETKİ (w=0.67, gerçek termal sensör): mAP 0.6531 -> 0.7221.
    Renkli karede ZARARLI (-0.013 ... -0.070), bu yüzden yalnızca gri/termal karede
    kullanılır — koşul çalışma anında `is_grayish` ile belirlenir.
    """
    N = Yp.shape[0]
    if N == 0 or Yr.shape[0] == 0:
        return torch.zeros(N, device=Yp.device)
    D = Yp.shape[-1]
    Yr_d = Yr.reshape(-1, D)[Mr.reshape(-1)]
    if Yr_d.shape[0] == 0:
        return torch.zeros(N, device=Yp.device)
    ir, ic = np.meshgrid(np.arange(G), np.arange(G), indexing="ij")
    izgara = torch.from_numpy(np.stack([ir.ravel(), ic.ravel()], 1)).float().to(Yp.device)

    out = torch.zeros(N, device=Yp.device)
    for n in range(N):
        gecerli = Mp[n]
        if int(gecerli.sum()) < 4:
            continue
        A = Yp[n][gecerli]
        S = A @ Yr_d.T
        en_iyi, j = S.max(1)
        u = (Yr_d[j] @ A.T).argmax(1)          # geri dönüş
        koor = izgara[gecerli]
        tut = (koor[u] - koor).abs().max(1).values <= delta
        out[n] = en_iyi[tut].mean() if bool(tut.any()) else en_iyi.mean() * 0.5
    return out


def rank_against(E, ref_embs, boxes):
    """E: (N,D) öneri gömmeleri, ref_embs: (M,D). Döner: skora göre sıralı [(box, cos)]."""
    if E is None or len(boxes) == 0:
        return []
    s = (E @ ref_embs.T).max(1).values.cpu().numpy()
    out = [(boxes[i], float(s[i])) for i in range(len(s))]
    out.sort(key=lambda z: -z[1])
    return out
