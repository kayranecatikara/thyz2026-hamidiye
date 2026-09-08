"""ÖN KONTROL — yarışma başlamadan önce çalıştırılır, sahada sürpriz olmasın.

Görev 3'ün sessizce çökmesinin en olası iki yolu:
  1. Ağırlık önbellekte yok, internet de yok  -> model yüklenemiyor
  2. İlk çağrı yarışma sırasında yapılıyor    -> ilk kare 10+ sn sürüyor

İkisi de ÖNCEDEN, tek komutla anlaşılır:

    python -m gorev3_v2.onkontrol            # veya kodda: on_kontrol()
"""
from __future__ import annotations

import os
import time

import numpy as np


def on_kontrol(fastsam_weights="FastSAM-s.pt", ayrinti=True,
               kare_yolu=None, ref_yolu=None):
    """Modelleri yükle, sahte bir kare koştur, süreleri raporla.

    Döner: {"tamam": bool, "mesaj": str, "sureler": {...}}
    """
    rapor, sureler = [], {}
    try:
        import torch
        sureler["cuda"] = torch.cuda.is_available()
        rapor.append(f"torch {torch.__version__} · CUDA "
                     f"{'VAR: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'YOK (CPU — çok yavaş olur)'}")
    except Exception as e:                                   # pragma: no cover
        return dict(tamam=False, mesaj=f"torch yüklenemedi: {e}", sureler=sureler)

    from .api import ReferenceObjectDetectorV2

    t0 = time.time()
    try:
        det = ReferenceObjectDetectorV2(fastsam_weights=fastsam_weights)
    except Exception as e:
        ek = ""
        if "offline" in str(e).lower() or "connect" in str(e).lower():
            ek = ("\n  -> Ağırlıklar HF önbelleğinde yok ve çevrimdışı kipteyiz. "
                  "İnternetli bir makinede bir kez GOREV3_ALLOW_NETWORK=1 ile çalıştırıp "
                  "~/.cache/huggingface klasörünü taşıyın.")
        return dict(tamam=False, mesaj=f"model yüklenemedi: {e}{ek}", sureler=sureler)
    sureler["model_yukleme_s"] = round(time.time() - t0, 1)
    rapor.append(f"modeller yüklendi: {sureler['model_yukleme_s']} sn")

    # sahte referans + sahte kare: ilk çağrının maliyetini ISINMA olarak öde
    import cv2
    tmp = os.path.join(os.environ.get("TEMP", "."), "_g3_onkontrol")
    os.makedirs(tmp, exist_ok=True)
    ref_p = os.path.join(tmp, "ref.png")
    kare_p = os.path.join(tmp, "kare.png")
    # GERCEK kare/referans verilirse onlari kullan: rastgele gurultude FastSAM'in
    # urettigi segment sayisi gercekci degil, dolayisiyla sure de gercekci degil.
    # Elde gercek bir kare varsa olcum cok daha anlamli olur.
    if kare_yolu and os.path.exists(kare_yolu):
        kare_p = kare_yolu
    else:
        rng = np.random.default_rng(0)
        kare = rng.integers(0, 255, (1080, 1920, 3), dtype=np.uint8)
        cv2.imwrite(kare_p, kare)
        rapor.append("not: sentetik gurultu karesi kullanildi — gercek kare icin "
                     "on_kontrol(kare_yolu=...) verin")
    if ref_yolu and os.path.exists(ref_yolu):
        ref_p = ref_yolu
    else:
        rng = np.random.default_rng(1)
        cv2.imwrite(ref_p, rng.integers(0, 255, (240, 320, 3), dtype=np.uint8))

    t0 = time.time()
    det.detect_for_frame(kare_p, "onkontrol", ref_p, video_name="onkontrol")
    sureler["ilk_kare_s"] = round(time.time() - t0, 2)
    t0 = time.time()
    det._fkey = None
    det.detect_for_frame(kare_p, "onkontrol", ref_p, video_name="onkontrol")
    sureler["isinmis_kare_s"] = round(time.time() - t0, 2)
    rapor.append(f"ilk kare {sureler['ilk_kare_s']} sn · ısınmış kare "
                 f"{sureler['isinmis_kare_s']} sn (bütçe 1.6 sn)")

    tamam = sureler["isinmis_kare_s"] < 1.6
    if not tamam:
        rapor.append("UYARI: ısınmış kare bütçeyi aşıyor — imgsz veya kırpma boyutunu düşürün")
    if ayrinti:
        for r in rapor:
            print("  " + r)
    return dict(tamam=tamam, mesaj=" | ".join(rapor), sureler=sureler)


if __name__ == "__main__":
    import sys
    kare = sys.argv[1] if len(sys.argv) > 1 else None
    ref = sys.argv[2] if len(sys.argv) > 2 else None
    s = on_kontrol(kare_yolu=kare, ref_yolu=ref)
    print(("TAMAM" if s["tamam"] else "SORUN VAR") + ": " + s["mesaj"])
    sys.exit(0 if s["tamam"] else 1)
