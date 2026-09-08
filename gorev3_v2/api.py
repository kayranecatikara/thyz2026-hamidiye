"""Resmî arayüze bağlanan üst seviye API.

Mevcut `gorev3.integrate.ReferenceObjectDetector` ile AYNI imzayı sunar, böylece
`object_detection_model.py` içindeki tek satır değiştirilerek geçiş yapılabilir:

    from gorev3_v2.api import ReferenceObjectDetectorV2 as ReferenceObjectDetector

Önemli davranış farkı — GÖNDERİM POLİTİKASI (ölçümle DEĞİŞTİ):
    Payload'da güven skoru alanı yoktur, dolayısıyla skorsuz mAP ~= P x R'dir.
    Bu, "kararsızken de gönder" demeye yatkın — ve v1'de nesnenin her karede
    bulunduğu varsayıldığında doğrudur. AMA sunucunun verdiği pencere gerçek
    görünürlükten GENİŞTİR (ölçüldü: 51 karelik pencerede nesne 31 karede var).
    Kenarlardaki her kutu saf yanlış pozitiftir. Gerçekçi koşulda ölçüm
    (pay = +-10 kare; DÜZELTİLMİŞ ego önbelleğiyle — önceki tablo bayat önbellek
    yüzünden kilit kapısını haksız kayırıyordu):

        kapı                       v1        v2
        her karede gönder        0.5785    0.4779
        kosinüs eşiği 0.60       0.6497    0.4887
        kosinüs eşiği 0.65       0.4425    0.5165   <-- v1'i çökerten değer v2'nin en iyisi
        kilit                    0.6221    0.4994
        KİLİT + DEDEKTÖR         0.6407    0.5090   <-- varsayılan

    Mutlak eşik videolar arası TAŞINMIYOR (yukarıdaki 0.65 satırı). Kilit ve
    dedektör-kaynaklılık ise ÖLÇEKSİZDİR, bu yüzden varsayılan odur.
    Dedektör kapısının kazancı v1'de 5/5 referansta pozitif, %90 GA [+0.012,+0.025].

    DİKKAT — ters yönü de ölçüldü: nesne pencerenin HER karesinde varsa kapı
    ZARARLI olur (v1 0.9778 -> 0.9051, v2 0.6951 -> 0.6549), çünkü orada yayılım
    dedektörün düşüşlerini kapatan faydalı bir şeydir. Pencerenin dar olduğu
    biliniyorsa emit_policy="always" + gate_detector=False kullanın.

    Eski davranış: emit_policy="always".
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

import cv2
import torch

from .detector import (Embedder, Proposer, clahe_gray, crops_of, embed_proposals,
                       gradient_view, is_grayish, merge_boxes, patch_skor, rank_against,
                       reference_embedding)
from .tracker import EgoMotion, RefTrack

BBox = Tuple[float, float, float, float]
log = logging.getLogger(__name__)


def _fastsam_yolu(verilen=None):
    """FastSAM ağırlığını GÖRELİ yol varsayımı olmadan bul.

    Varsayılan "FastSAM-s.pt" idi ve çalışma dizinine göre çözülüyordu; entegrasyon
    istemciyi başka bir dizinden çalıştırdığı için ağırlık bulunamıyordu. Sıra:
      1. açıkça verilen yol
      2. GOREV3_FASTSAM ortam değişkeni
      3. paketin bir üstü (depo kökü) — kurulumda oraya iner
      4. paketin kendi içi
      5. çıplak ad (ultralytics kendi indirir; ağ gerekir)
    """
    if verilen:
        return verilen
    cev = os.environ.get("GOREV3_FASTSAM")
    if cev:
        return cev
    burada = os.path.dirname(os.path.abspath(__file__))
    for aday in (os.path.join(os.path.dirname(burada), "FastSAM-s.pt"),
                 os.path.join(burada, "FastSAM-s.pt")):
        if os.path.exists(aday):
            return aday
    return "FastSAM-s.pt"


class ReferenceObjectDetectorV2:
    def __init__(self,
                 model_name="vit_small_patch16_dinov3.lvd1689m",
                 fastsam_weights=None,   # None -> paket kökünde ara (bkz. _fastsam_yolu)
                 crop=224,          # 176'ya düşürmek çapraz-modali bozuyor (C 0.968 -> 0.774)
                 fastsam_imgsz=768, # 1024'ten hem daha hızlı hem daha isabetli (ölçüldü)
                 max_props=50,      # 100 öneriye göre fark yok, 3x hızlı
                 max_area_ratio=0.80,# kareyi kaplayan arka plan segmentini ele; 0.50 DOĞRU
                                     # kutuyu da eliyordu (termal +0.083, bkz. README)
                 agree=0.45,        # takipçide "aynı yer mi" eşiği (IoMin)
                 kucuk_px=0,        # bu px altındaki kutuda IoMin yerine merkez mesafesi (0=kapalı)
                 kucuk_tol=1.0,     # izin verilen kayma = kucuk_tol × kutunun kısa kenarı
                 pad=0.15,          # gömme için bağlam payı (0.8063 -> 0.9170); %30 yıkıcı
                 kucuk_pad=0.05,    # KÜÇÜK kutularda bağlam payı (bkz. detector.pay_sec)
                 dar_px=0,          # KİLİTLENEN kutu bu px'in altındaysa o REFERANS için
                 # sıkı kırpmaya geç (0=kapalı). Ölçüldü: küçük nesnede bağlam payı
                 # 0.15 -> 0.05 en büyük tek kazanç (+0.048), ama GLOBAL uygulanınca
                 # mühürlü videoda -0.099. Referans başına, kilit sonrası ölçülen
                 # boyuta göre uygulanırsa iki taraf da korunabilir.
                 dar_pad=0.05,
                 kucuk_esik=0,      # 0 = KAPALI. Ölçüldü ve reddedildi: küçük-nesne
                 # kümesinde +0.046 veriyor ama mühürlü v2'de sonuç TEKDÜZE DEĞİL
                 # (eşik 0/30/40/60 -> 0.5719 / 0.5046 / 0.5916 / 0.4745). Yani
                 # sistematik kazanç değil, kilit kararlarını çeviren tedirginlik.
                 merge_iomin=0.30,  # parçalanan nesneyi birleştir (0.8710 -> 0.9285)
                 merge_margin=0.03,
                 blend=0.8,         # ego-hareket harmanı (0.9149 -> 0.9754); 1.0 DÜŞÜYOR
                 topk=8,
                 emit_policy="locked_only",   # "locked_only" | "always" | "threshold"
                 gate_detector=True,  # yayılımla gelen kutuyu gönderme (aşağıdaki tablo)
                 streak_gate_alpha=0.03,  # L = alfa * pencere uzunluğu
                 streak_gate_floor=0,     # 0 = KAPALI (varsayılan); açıkken L'nin taban katı
                 cross_modal=True,    # kareler gri/termal + referans renkli ise köprü görünümü SEÇ
                 cross_modal_views=("ters",),  # aday köprüler: "ters" ve/veya "gradyan"
                 adaptive_views=5,    # N kare kilitlenmezse referans bankasını ölçek piramidiyle genişlet (0=kapalı)
                 cross_modal_margin=1.00,     # köprüyü kabul için gereken oran
                 # (1.05 denendi: v1_cm640 kazancını +0.086 -> +0.059 düşürdü,
                 #  v1_g640 kaybını hiç azaltmadı. Marj ayırt etmiyor.)
                 patch_gray=True,     # GRİ/TERMAL karede yama düzeyinde skorlama
                 # w: 0.67 PAYSIZ kosulda daha iyiydi ama PAYLI (yarisma) kosulda
                 # cokuyordu (v2 0.5910 -> 0.5019). 0.30 sekiz kosulun altisinda
                 # pozitif, net +0.200. Agirlik tek rejimde secilmemeli.
                 patch_w=0.30, patch_delta=5, patch_inner=0.87,
                 min_score=0.0,
                 use_external_homography=False,
                 ref_add_gray=True,   # RGB oturumda nötr ölçüldü; termalde faydalı bekleniyor
                 use_tracker=True):
        self.emb = Embedder(model_name, crop=crop)
        self.prop = Proposer(_fastsam_yolu(fastsam_weights), imgsz=fastsam_imgsz)
        self.max_props = max_props
        self.max_area_ratio = max_area_ratio
        self.agree = float(agree)
        self.kucuk_px = int(kucuk_px)
        self.kucuk_tol = float(kucuk_tol)
        self.pad = pad
        self.kucuk_pad = float(kucuk_pad)
        self.kucuk_esik = int(kucuk_esik)
        self.dar_px = int(dar_px)
        self.dar_pad = float(dar_pad)
        self._ref_dar = {}        # ref_url -> sıkı kırpma kipinde mi
        self.merge_iomin = merge_iomin
        self.merge_margin = merge_margin
        self.blend = blend
        self.topk = topk
        self.emit_policy = emit_policy
        self.gate_detector = gate_detector
        # PENCERE-ORANLI SERİ KAPISI — varsayılan KAPALI. Ölçüm: dolgu varsa
        # kazandırıyor, dolgu yoksa kaybettiriyor; başabaş ~7-8 kare kenar dolgusu.
        # Sunucunun penceresi görünürlükten belirgin genişse floor=5 ile açın.
        self.streak_gate_alpha = float(streak_gate_alpha)
        self.streak_gate_floor = int(streak_gate_floor)
        self._ref_win = {}        # ref_url -> pencere uzunluğu (kare)
        self._ref_armed = {}      # ref_url -> seri bir kez L'ye ulaştı mı
        # ÇAPRAZ-MODAL GÖRÜNÜM SEÇİMİ — koşullu, eşiksiz.
        # Ölçüldü: sabit bir köprü görünümü yok. Polarite tersi görünüm yalnız
        # kareler ters polariteliyse kazandırıyor (+0.087), düz gride
        # kaybettiriyor (−0.028). Hangisinin gerektiği VİDEODAN okunur: üç aday
        # (gri / ters / gradyan) ilk 3 gri karenin önerileri üzerinde yarıştırılır,
        # taban gri görünümü geçen EN İYİ TEK aday bankaya eklenir.
        # Referans griyse veya kareler renkliyse hiç çalışmaz -> bedeli sıfırdır.
        self.cross_modal = bool(cross_modal)
        self.cross_modal_views = tuple(cross_modal_views)
        # UYARLANIR REFERANS GÖRÜNÜMÜ — koşullu, ayarsız.
        # Referansta nesnenin ne kadar yer kapladığını BİLMİYORUZ; sunucu geniş
        # çekim bir fotoğraf da verebilir. Ölçüldü (nesne referansın 1/16'si,
        # pay=10): tam 0.157 / sabit piramit 0.525 / uyarlanır 0.533 (v2_termal),
        # ve 0.301 / 0.547 / 0.555 (v1_640). SIKI referansta bedeli TAM SIFIR
        # (0.6209=0.6209, 0.5797=0.5797) çünkü kilit ilk karelerde oluşur ve
        # ek banka hiç açılmaz. Bu, ayar değil KOŞULA BAĞLI bir yedek yoldur.
        self.adaptive_views = int(adaptive_views)
        self._ref_pyr = {}       # ref_url -> (E, Y, M) piramit kırpmaları
        self._ref_uy = {}        # ref_url -> {n, kilit, genis}
        self.cross_modal_margin = float(cross_modal_margin)
        self._ref_cm = {}
        self.patch_gray = patch_gray
        self.patch_w, self.patch_delta, self.patch_inner = patch_w, patch_delta, patch_inner
        self.min_score = min_score
        self.ego = None if use_external_homography else EgoMotion()
        self.ref_add_gray = ref_add_gray
        self.use_tracker = use_tracker
        self._refs = {}          # ref_url -> gömme tensörü
        self._ref_patch = {}     # ref_url -> (yama tokenları, maske)  [gri kare yolu]
        self._tracks = {}        # ref_url -> RefTrack
        self._fno = 0            # görülen KARE sayacı (pencere kopukluğunu anlamak için)
        self._ref_last = {}      # ref_url -> o referansın en son güncellendiği kare sayacı
        self._fkey = None        # geçerli kare anahtarı (yol)
        self._fctx = None        # (im, boxes, E, H)
        self._video = None
        self._ext_H = None
        # TELEMETRI DENETLEYICISI (istege bagli, bkz. set_translation)
        self._tel = None          # onceki karenin kumulatif konumu (x, y, z)
        self._tel_d = None        # bu kare icin metrik yer degistirme buyuklugu
        self._tel_orn = []        # olcek kalibrasyonu icin (px/m) ornekleri
        self._tel_olcek = None

    # ---------- oturum yönetimi ----------

    def reset_session(self):
        self._tracks.clear()
        self._ref_last.clear()
        self._fno = 0
        self._fkey = self._fctx = None
        self._tel = self._tel_d = None
        self._tel_orn, self._tel_olcek = [], None
        if self.ego is not None:
            self.ego = EgoMotion()

    def register_reference(self, ref_url: str, ref_image_path: str):
        im = cv2.imread(ref_image_path)
        if im is None:
            raise FileNotFoundError(ref_image_path)
        self._refs[ref_url] = reference_embedding(self.emb, im, add_gray=self.ref_add_gray)
        if self.patch_gray:
            # Yama tokenları YALNIZCA gri/termal karede kullanılır ama referans
            # tarafında oturum başında bir kez hesaplanır — kare başına maliyeti yok.
            v = [im] if is_grayish(im) else [im, clahe_gray(im)]
            _, Y, M = self.emb(v, yama=True, ic_oran=self.patch_inner)
            self._ref_patch[ref_url] = (Y, M)
        if self.adaptive_views:
            h, w = im.shape[:2]
            kirp = []
            for c in (0.7, 0.5, 0.35):
                cw, ch = max(16, int(w * c)), max(16, int(h * c))
                kirp.append(im[(h - ch) // 2:(h - ch) // 2 + ch,
                               (w - cw) // 2:(w - cw) // 2 + cw])
            Ep = self.emb(kirp)
            _, Yp2, Mp2 = self.emb(kirp, yama=True, ic_oran=self.patch_inner)
            self._ref_pyr[ref_url] = (Ep, Yp2, Mp2)
            self._ref_uy[ref_url] = dict(n=0, kilit=False, genis=False)
        if self.cross_modal and not is_grayish(im):
            g = clahe_gray(im)
            uretici = {"ters": lambda: 255 - g, "gradyan": lambda: gradient_view(im)}
            adlar = ["gri"] + [k for k in ("ters", "gradyan") if k in self.cross_modal_views]
            adaylar = [g] + [uretici[k]() for k in adlar[1:]]
            E3 = self.emb(adaylar)
            _, Y3, M3 = self.emb(adaylar, yama=True, ic_oran=self.patch_inner)
            self._ref_cm[ref_url] = dict(ad=adlar, E=E3, Y=Y3, M=M3,
                                         tepe=[-9e9] * len(adlar), n=0, bitti=False)
        log.info("[gorev3v2] referans kaydedildi: %s (%s)",
                 ref_url, os.path.basename(ref_image_path))

    def set_window(self, ref_url: str, frame_start: int, frame_end: int) -> None:
        """Sunucunun verdiği pencere sınırlarını bildir (`GET /reference/`).

        Yalnızca seri kapısı için kullanılır ve OPSİYONELDİR; çağrılmazsa kapı
        taban katıyla çalışır. Entegrasyon katmanı bu iki değeri zaten biliyor.
        """
        try:
            self._ref_win[ref_url] = max(1, int(frame_end) - int(frame_start) + 1)
        except Exception:
            pass

    def reset_reference(self, ref_url: str):
        """Bir referansın penceresi (yeniden) açıldığında izini sıfırla.

        Neden gerekli: `_fno` sezgisi yalnızca ARDIŞIK İŞLENEN kareleri sayar.
        İki pencere arasında başka referans aktif değilse sayaç ilerlemez ve
        kopukluk fark edilmez; eski kutu tek adımlık bir homografiyle taşınır ki
        bu anlamsızdır. Entegrasyon katmanı `frame_start`/`frame_end`'i zaten
        sunucudan biliyor — pencere açılışında bunu çağırmak kesin çözümdür.
        """
        self._tracks.pop(ref_url, None)
        self._ref_last.pop(ref_url, None)
        self._ref_armed.pop(ref_url, None)
        self._ref_dar.pop(ref_url, None)
        if ref_url in self._ref_uy:
            # `kilit` ve `genis` KORUNUR, yalnız sayaç sıfırlanır.
            # Gerekçe: bu referans BİR KEZ kilitlenebildiyse geniş çekim
            # değildir; pencere yeniden açıldığında sıfırlamak, dolgu
            # bölgesinde sahte genişletmeye yol açıyordu (ölçüldü: v1_rgb
            # pay=10 0.6379 -> 0.6054). `genis` de korunur, yoksa aynı
            # görünümler bankaya iki kez eklenirdi.
            self._ref_uy[ref_url]["n"] = 0

    def set_translation(self, x, y, z=0.0):
        """Sunucunun verdiği kümülatif konumu bu kare için bildir (metre).

        NE İŞE YARAR: ego-hareket homografisini DENETLER, yerine geçmez.
        Telemetri yalnızca konum veriyor, yönelim (yaw) vermiyor; drone döndükçe
        dünya→görüntü eşlemesi de döner, dolayısıyla yön tahmin edilemez. Ama
        nadir kamerada hareketin BÜYÜKLÜĞÜ dönmeden bağımsızdır:

            |piksel| ≈ (f / Z) · |metre|

        Ölçüldü: |piksel| ile |metre| korelasyonu **+0.87 / +0.89** (v1 / v2),
        büyüklük tahmininde medyan hata %20–25. Bu, ORB'un yerine geçmeye yetmez
        ama KABA hatalarını yakalar. Ölçek ilk 40 kareden kendiliğinden kalibre olur.

        3× eşikte **yanlış alarm oranı %0** (774 çift, iki video) — yani doğru
        çalışan homografiyi hiç bozmaz.

        ⚠ DÜRÜSTLÜK NOTU: yakalama faydası ÖLÇÜLMEDİ — elimizdeki iki videoda ORB
        hiç başarısız olmadı (0/198 ve 0/516). Ölçülen tek şey bedelinin sıfır
        olduğu. Bu bir sigorta; ORB'un çökebileceği düşük dokulu sahneler (su,
        sis, düz tarla) için var.

        Kullanım: her kare için, `detect_for_frame`'den ÖNCE çağırın.
        Sunucu bu değeri `GET /translation/` ile zaten veriyor.
        """
        import math
        yeni = (float(x), float(y), float(z))
        self._tel_d = (math.hypot(yeni[0] - self._tel[0], yeni[1] - self._tel[1])
                       if self._tel is not None else None)
        self._tel = yeni

    def _telemetri_onayi(self, H, W, Himg):
        """H'nin ima ettiği hareket, telemetriyle uyumlu mu? -> H ya da None."""
        if H is None or self._tel_d is None or self._tel_d <= 1e-6:
            return H
        import numpy as _np
        c = _np.float32([[[W / 2.0, Himg / 2.0]]])
        q = cv2.perspectiveTransform(c, H.astype(_np.float64))[0, 0]
        px = float(_np.hypot(q[0] - W / 2.0, q[1] - Himg / 2.0))
        if self._tel_olcek is None:
            self._tel_orn.append(px / self._tel_d)
            if len(self._tel_orn) >= 40:
                self._tel_olcek = float(_np.median(self._tel_orn))
            return H                                    # kalibrasyon bitene kadar denetim yok
        beklenen = max(self._tel_olcek * self._tel_d, 1.0)
        oran = max(px, 1.0) / beklenen
        if oran > 3.0 or oran < 1 / 3.0:
            log.warning("[gorev3v2] homografi telemetriyle uyumsuz "
                        "(%.0f px, beklenen %.0f px) — bu karede güvenilmiyor", px, beklenen)
            return None
        return H

    def set_homography(self, H):
        """Görev 2'nin SLAM'inden gelen önceki->bu kare homografisi (varsa)."""
        self._ext_H = H

    # ---------- kare bağlamı (kare başına BİR kez) ----------

    def _frame_ctx(self, frame_image_path: str):
        if self._fkey == frame_image_path:
            return self._fctx
        self._fno += 1
        im = cv2.imread(frame_image_path)
        if im is None:
            self._fkey, self._fctx = frame_image_path, None
            return None
        # Gerçekten termal/gri kare ise kontrastı normalize et (eşik için detector.py'ye bak).
        work = clahe_gray(im) if is_grayish(im) else im
        boxes = self.prop(work, max_props=self.max_props,
                          max_area_ratio=self.max_area_ratio)
        gri = is_grayish(im)
        Yp = Mp = None
        if self.patch_gray and gri:
            # GRİ/TERMAL YOL: aynı ileri geçiş, ek olarak yama tokenları da alınır.
            # Renkli karede bu yol HİÇ çalışmaz — ölçüldü, orada zararlı.
            krp, keep = crops_of(work, boxes, pad=self.pad,
                                 kucuk_pay=self.kucuk_pad, kucuk_esik=self.kucuk_esik)
            boxes = [boxes[i] for i in keep]
            if krp:
                E, Yp, Mp = self.emb(krp, yama=True, ic_oran=self.patch_inner)
            else:
                E = None
        else:
            boxes, E = embed_proposals(self.emb, work, boxes, pad=self.pad,
                                       kucuk_pay=self.kucuk_pad, kucuk_esik=self.kucuk_esik)
        if self.ego is not None:
            H = self.ego.step(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY))
        else:
            H = self._ext_H
        H = self._telemetri_onayi(H, im.shape[1], im.shape[0])
        self._fkey, self._fctx = frame_image_path, [im, boxes, E, H, Yp, Mp, None]
        return self._fctx

    # ---------- ana giriş noktası ----------

    def detect_for_frame(self, frame_image_path: str, ref_url: str,
                         ref_image_path: Optional[str],
                         video_name: Optional[str] = None) -> Optional[BBox]:
        try:
            if video_name and video_name != self._video:
                self._video = video_name
                self.reset_session()
            if ref_url not in self._refs:
                if not ref_image_path:
                    return None
                self.register_reference(ref_url, ref_image_path)

            ctx = self._frame_ctx(frame_image_path)
            if ctx is None:
                return None
            im, boxes, E, H, Yp, Mp = ctx[0], ctx[1], ctx[2], ctx[3], ctx[4], ctx[5]
            # SIKI KIRPMA KİPİ: bu referans küçük bir nesneye kilitlendiyse
            # kare gömmeleri dar bağlam payıyla YENİDEN hesaplanır (kare
            # başına bir kez, tüm dar-kip referanslar paylaşır).
            if self.dar_px and self._ref_dar.get(ref_url):
                if ctx[6] is None:
                    work2 = clahe_gray(im) if is_grayish(im) else im
                    if self.patch_gray and is_grayish(im):
                        k2, keep2 = crops_of(work2, ctx[1], pad=self.dar_pad)
                        b2 = [ctx[1][i] for i in keep2]
                        E2, Y2, M2 = (self.emb(k2, yama=True, ic_oran=self.patch_inner)
                                      if k2 else (None, None, None))
                    else:
                        b2, E2 = embed_proposals(self.emb, work2, ctx[1], pad=self.dar_pad)
                        Y2 = M2 = None
                    ctx[6] = (b2, E2, Y2, M2)
                if ctx[6][1] is not None and len(ctx[6][1]):
                    boxes, E, Yp, Mp = ctx[6]
            # ÇAPRAZ-MODAL GÖRÜNÜM SEÇİMİ (ilk 3 gri karede, referans başına bir kez).
            # Adaylar yalnız BİRBİRLERİYLE kıyaslanır -> mutlak eşik yok, videodan
            # videoya taşınır. Ölçüm ve gerekçe: arena/KARARLAR.md
            st = self._ref_cm.get(ref_url)
            # SECIM YALNIZ KILITLI KARELERDE: karsilastirmanin anlamli olmasi icin
            # o karede gercekten bir eslesme olmali. Dolgu karelerinde (nesne yok)
            # yapilan secim yanlis cikiyordu — olculdu: v1_g640 pay=10'da secim
            # dolgu karelerinde yapilinca -0.028, hic yapilmayinca 0.000.
            _kilitli_mi = bool(self._tracks.get(ref_url) is not None
                               and self._tracks[ref_url].locked)
            if st is not None and not st["bitti"] and _kilitli_mi                     and Yp is not None and E is not None and len(E):
                D = E.shape[1] // 2
                nrm = torch.nn.functional.normalize
                S = nrm(st["E"][:, :D], dim=-1) @ nrm(E[:, :D], dim=-1).T
                pk = S.max(1).values
                st["tepe"] = [max(a, float(b)) for a, b in zip(st["tepe"], pk)]
                st["n"] += 1
                if st["n"] >= 3:
                    st["bitti"] = True
                    j = max(range(1, len(st["ad"])), key=lambda i: st["tepe"][i])                         if len(st["ad"]) > 1 else 0
                    if j and st["tepe"][j] > st["tepe"][0] * self.cross_modal_margin:
                        self._refs[ref_url] = torch.cat(
                            [self._refs[ref_url], st["E"][j:j + 1]], 0)
                        if ref_url in self._ref_patch:
                            Yr, Mr = self._ref_patch[ref_url]
                            self._ref_patch[ref_url] = (
                                torch.cat([Yr, st["Y"][j:j + 1]], 0),
                                torch.cat([Mr, st["M"][j:j + 1]], 0))
                        log.info("[gorev3v2] %s: köprü görünümü eklendi (%s) | %s",
                                 ref_url, st["ad"][j],
                                 " ".join(f"{k}={v:.3f}" for k, v in zip(st["ad"], st["tepe"])))
                    else:
                        log.info("[gorev3v2] %s: köprü görünümü eklenmedi | %s", ref_url,
                                 " ".join(f"{k}={v:.3f}" for k, v in zip(st["ad"], st["tepe"])))
            if Yp is not None and ref_url in self._ref_patch:
                Yr, Mr = self._ref_patch[ref_url]
                # s_cls YALNIZ CLS yarisindan hesaplanir — birlesik [CLS|ortalama-yama]
                # vektorunden DEGIL. Arenada dogrulanan yapilandirma boyleydi; birlesik
                # vektorle kosunca uretim 0.7406 verirken arena 0.7747 veriyordu.
                # (normalize(concat) dilimleyip yeniden normalize etmek = normalize(cls),
                #  cunku birlesik normalizasyon duzgun bir olceklemedir.)
                D = E.shape[1] // 2
                nrm = torch.nn.functional.normalize
                s_cls = (nrm(E[:, :D], dim=-1)
                         @ nrm(self._refs[ref_url][:, :D], dim=-1).T).max(1).values
                G = self.emb.crop // self.emb.patch
                s_app = patch_skor(Yp, Mp, Yr, Mr, G, self.patch_delta)
                sk = (1 - self.patch_w) * s_cls + self.patch_w * s_app
                cands = sorted(zip(boxes, sk.tolist()), key=lambda z: -z[1])[:self.topk]
            else:
                cands = rank_against(E, self._refs[ref_url], boxes)[:self.topk]
            if self.merge_iomin:
                cands = merge_boxes(cands, self.merge_iomin, self.merge_margin)
            if self.min_score:
                cands = [c for c in cands if c[1] >= self.min_score]

            if self.use_tracker:
                # PENCERE KOPUKLUGU: bu referans BIR ONCEKI karede sorulmadiysa
                # aradan bilinmeyen kadar zaman gecmistir. Eski kutuyu tek adimlik
                # homografiyle tasimak anlamsizdir — iz sifirlanir.
                # (Olculdu: v1-02'nin 6 ayri penceresi var; sifirlamayan hal
                # pencere basinda gecersiz bir tahminle acilip celiskiyle
                # toparlaniyordu, yani dogru sonucu KAZA ile buluyordu.)
                if (ref_url in self._ref_last
                        and self._fno - self._ref_last[ref_url] > 1):
                    self._tracks.pop(ref_url, None)
                    self._ref_armed.pop(ref_url, None)
                self._ref_last[ref_url] = self._fno
                trk = self._tracks.setdefault(ref_url, RefTrack(blend=self.blend, agree=self.agree,
                                                     kucuk_px=self.kucuk_px,
                                                     kucuk_tol=self.kucuk_tol))
                box = trk.update(H, cands, im.shape[1], im.shape[0])
                # EŞİKSİZ VARLIK KAPISI — bkz. modül başlığındaki ölçüm tablosu.
                if self.emit_policy == "locked_only" and not trk.locked:
                    box = None
                # DEDEKTÖR KAYNAKLI KAPISI: kutuyu bu karede dedektör mü üretti?
                # Yayılımla gelen kutu, nesne pencereden ÇIKTIKTAN sonra da
                # üretilmeye devam eder ve saf yanlış pozitiftir.
                if self.gate_detector and not trk.from_detector:
                    box = None
                # UYARLANIR GÖRÜNÜM: N kare boyunca hiç kilitlenmediyse referans
                # muhtemelen geniş çekimdir -> bankayı ölçek piramidiyle genişlet.
                if self.dar_px and box is not None and trk.locked                         and not self._ref_dar.get(ref_url):
                    kisa = min(box[2] - box[0], box[3] - box[1])
                    if kisa < self.dar_px:
                        self._ref_dar[ref_url] = True
                        log.info("[gorev3v2] %s: kilitlenen kutu %.0f px -> sıkı kırpma kipi",
                                 ref_url, kisa)
                uy = self._ref_uy.get(ref_url)
                if uy is not None and not uy["genis"]:
                    uy["n"] += 1
                    if trk.locked:
                        uy["kilit"] = True
                    elif not uy["kilit"] and uy["n"] >= self.adaptive_views:
                        Ep, Yp2, Mp2 = self._ref_pyr[ref_url]
                        self._refs[ref_url] = torch.cat([self._refs[ref_url], Ep], 0)
                        if ref_url in self._ref_patch:
                            Yr, Mr = self._ref_patch[ref_url]
                            self._ref_patch[ref_url] = (torch.cat([Yr, Yp2], 0),
                                                        torch.cat([Mr, Mp2], 0))
                        uy["genis"] = True
                        log.info("[gorev3v2] %s: %d karede kilit yok -> referans bankası "
                                 "ölçek piramidiyle genişletildi", ref_url, uy["n"])
                # SERİ KAPISI: referansın serisi bir kez L'ye ulaşana kadar sus.
                # Ulaştıktan sonra normal kilit kapısı geçerli — bu "bir kez
                # kurulma" kipi, şartın her kilit kopuşunda yeniden ödenmesini
                # engeller (ölçüldü: bedel yarıya iniyor).
                if self.streak_gate_floor:
                    W = self._ref_win.get(ref_url)
                    L = self.streak_gate_floor if not W else int(
                        min(60, max(self.streak_gate_floor,
                                    round(self.streak_gate_alpha * W))))
                    if trk.streak >= L:
                        self._ref_armed[ref_url] = True
                    if not self._ref_armed.get(ref_url):
                        box = None
            else:
                box = cands[0][0] if cands else None
            if box is None and self.emit_policy == "always" and cands:
                box = cands[0][0]
            return tuple(box) if box else None
        except Exception as e:                      # çelik zırh: Görev 3 asla kareyi durdurmaz
            log.error("[gorev3v2] hata: %s", e)
            return None
