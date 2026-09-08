"""Ego-hareket tutarlılık süzgeci — "dedektör önce, takipçi yalnızca veto/doldurma".

Görev 3'ün yapısı gereği her referansın bir kare PENCERESİ var ve kamera sürekli
hareket ediyor. Sabit bir nesnenin kutusu ardışık karelerde ego-hareket homografisiyle
taşınabilir. Bu katman:
  * dedektörün "ışınlanan" (bir karede orada, ötekinde bambaşka yerde) çıktılarını eler,
  * dedektörün düştüğü karelerde kutuyu taşıyarak boşluğu doldurur,
  * yanlış bir ize takılıp kalmamak için üst üste çelişkide izi bırakır.

ÖLÇÜM (bench/ altındaki gerçek verilerle):
  * Güçlü dedektörde ZARAR VERMİYOR: 1.000 / 0.895 / 0.968 aynen korunuyor.
  * Zayıflatılmış (termal-benzeri) karede isabeti 0.774 -> 0.839 çıkarıyor.
  * Tek başına yayılım testi: tek doğru tespitten pencere sonuna kadar
    biçerdöver 30/30, halı saha (orta tohum) 18/18 kare IoU>=0.25.

KRİTİK AYRINTI — neden IoU değil IoMin:
  Halı saha gibi kenardan kırpılan nesnelerin GÖRÜNEN alanı kare kare büyüyüp
  küçülüyor; IoU ile "aynı yer mi?" testi bu yüzden düşük çıkıp doğru tespitleri
  veto ediyordu (B: 0.868 -> 0.711). Kesişim/küçük-alan (IoMin) ölçüsü bunu çözdü.
"""
from __future__ import annotations

import cv2
import numpy as np


def warp_box(H, b):
    x0, y0, x1, y1 = b
    p = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]).reshape(-1, 1, 2)
    q = cv2.perspectiveTransform(p, H).reshape(-1, 2)
    return [float(q[:, 0].min()), float(q[:, 1].min()),
            float(q[:, 0].max()), float(q[:, 1].max())]


def ayni_yer(a, b, agree, kucuk_px=0, kucuk_tol=1.0):
    """“Aynı yer mi?” — kutu boyutuna göre ÖLÇÜT DEĞİŞTİREN sürüm.

    Neden: IoMin sabit bir örtüşme oranı ister. 30 px'lik bir kutu birkaç piksel
    oynadığında bu oran çöküyor ve seri sıfırlanıyor — küçük nesnede kilit HİÇ
    kurulamıyor. Ölçüldü (termal, 12 referanslık küçük-nesne kümesi): sıfır alan
    üç referansın ikisi pencere boyunca TEK kutu gönderiyor.

    Küçük kutuda merkez mesafesi daha anlamlı bir ölçüttür: kutu kısa kenarının
    `kucuk_tol` katı kadar kayma aynı yer sayılır. Büyük kutuda IoMin korunur —
    orada oran zaten kararlı ve daha ayırt edici.

    `kucuk_px = 0` iken davranış birebir eskisi gibidir.
    """
    if kucuk_px:
        kisa = min(b[2] - b[0], b[3] - b[1])
        if kisa < kucuk_px:
            ax, ay = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
            bx, by = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 <= kucuk_tol * kisa
    return iomin(a, b) >= agree


def iomin(a, b):
    """Kesişim / küçük kutunun alanı."""
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    m = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return inter / m if m > 0 else 0.0


class EgoMotion:
    """Ardışık kareler arası homografi.

    Görev 2'nin SLAM'i zaten kare-kare eşleşme üretiyorsa homografiyi ORADAN alın —
    bu sınıf yalnızca yedek yoldur. 1080p'de tam çözünürlükte ORB ~0.8 s/kare;
    varsayılan 960 px çalışma genişliğiyle ~50-80 ms.
    """

    def __init__(self, nfeat=1500, work_width=960):
        self.orb = cv2.ORB_create(nfeat)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.prev = None
        self.ww = work_width

    def step(self, gray):
        s = self.ww / gray.shape[1]
        g = cv2.resize(gray, (self.ww, int(gray.shape[0] * s))) if s < 1 else gray
        k, d = self.orb.detectAndCompute(g, None)
        H = None
        if self.prev is not None and d is not None and self.prev[1] is not None:
            pk, pd = self.prev
            m = self.bf.match(pd, d)
            if len(m) >= 20:
                m = sorted(m, key=lambda x: x.distance)[:600]
                pa = np.float32([pk[x.queryIdx].pt for x in m]).reshape(-1, 1, 2)
                pb = np.float32([k[x.trainIdx].pt for x in m]).reshape(-1, 1, 2)
                Hc, mask = cv2.findHomography(pa, pb, cv2.USAC_MAGSAC, 3.0,
                                              maxIters=6000, confidence=0.999)
                if Hc is not None and mask.sum() >= 15:
                    S = np.diag([s, s, 1.0]).astype(np.float64)
                    H = np.linalg.inv(S) @ Hc @ S      # tam çözünürlüğe geri ölçekle
        self.prev = (k, d)
        return H


class RefTrack:
    """Tek referans için pencere-içi durum. Pencere içindeki HER karede update() çağırın."""

    def __init__(self, agree=0.45, need=3, drop_after=3, score_margin=0.04, max_gap=5,
                 blend=0.8, kucuk_px=0, kucuk_tol=1.0):
        self.blend = blend        # kabul edilen kutuyu TASINAN tahminle yumusat
        self.from_detector = False  # bu karedeki kutuyu DEDEKTOR mu uretti?
        self.pred = None
        self.streak = 0
        self.conflict = 0
        self.gap = 0
        self.agree = agree
        self.kucuk_px = int(kucuk_px)
        self.kucuk_tol = float(kucuk_tol)
        self.need = need
        self.drop_after = drop_after
        self.score_margin = score_margin
        self.max_gap = max_gap
        self.last_score = 0.0

    @property
    def locked(self):
        return self.pred is not None and self.streak >= self.need

    def update(self, H, cands, W, Himg):
        """H: önceki->bu kare homografisi (None olabilir). cands: skora göre sıralı [(box,score)]."""
        if self.pred is not None:
            if H is None:
                self.pred = None
                self.streak = 0
            else:
                self.pred = warp_box(H, self.pred)

        if not cands:
            if self.pred is not None and self.gap < self.max_gap:
                self.gap += 1
                out = self.pred
                self.from_detector = False        # boşluk doldurma
            else:
                return None
        else:
            top_b, top_s = cands[0]
            self.from_detector = True             # aksi kanıtlanana kadar
            if not self.locked:
                out, sc = top_b, top_s
                agrees = self.pred is not None and ayni_yer(self.pred, top_b, self.agree,
                                                          self.kucuk_px, self.kucuk_tol)
                self.streak = self.streak + 1 if agrees else 1
                self.gap = 0
            elif ayni_yer(self.pred, top_b, self.agree, self.kucuk_px, self.kucuk_tol):
                out, sc = top_b, top_s
                self.streak += 1
                self.conflict = 0
                self.gap = 0
            else:
                agree = [(b, s) for b, s in cands
                         if ayni_yer(self.pred, b, self.agree, self.kucuk_px, self.kucuk_tol)]
                if agree and top_s - agree[0][1] < self.score_margin:
                    out, sc = agree[0]          # izle uyumlu, skoru da yakın aday
                    self.streak += 1
                    self.conflict = 0
                    self.gap = 0
                else:
                    self.conflict += 1
                    if self.conflict >= self.drop_after:
                        out, sc = top_b, top_s  # ısrarlı çelişki -> izi bırak, dedektöre dön
                        self.streak = 1
                        self.conflict = 0
                        self.gap = 0
                    else:
                        out, sc = self.pred, self.last_score   # dedektör düştü -> yayıl
                        self.from_detector = False
                        self.gap += 1
            self.last_score = sc

        # EGO-HAREKET HARMANI — olculen EN BUYUK tek kazanc (0.9149 -> 0.9754).
        # Dedektorun kutusu kare kare titriyor; ego-hareketle tasinan tahmin
        # puruzsuz ama zamanla kayiyor. %80 tahmin + %20 dedektor ikisinin de
        # zayifligini kapatiyor. DIKKAT: 1.0'da (saf tasima) DUSUYOR — yani
        # dedektor hala gerekli, bu bir "takipci devrali" cozumu degil.
        # Yalnizca KILITLIYKEN uygulanir: kilit oncesi tahmin guvenilir degil.
        if self.blend and self.pred is not None and self.locked:
            w = float(self.blend)
            out = [(1 - w) * c + w * p for c, p in zip(out, self.pred)]

        self.pred = list(out)
        x0, y0, x1, y1 = out
        x0 = max(0.0, min(x0, W - 1))
        x1 = max(0.0, min(x1, W - 1))
        y0 = max(0.0, min(y0, Himg - 1))
        y1 = max(0.0, min(y1, Himg - 1))
        if x1 - x0 < 4 or y1 - y0 < 4:
            return None                          # nesne kare dışına çıktı
        return [x0, y0, x1, y1]
