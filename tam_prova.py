#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tam_prova.py — run7 + SLAM v8 + hibrit Görev 3'ü TEK videoda birlikte koşturur.

Video: THYZ_2026_Ornek_Veri_1.MP4 (gerçek 2026 örneği, 1080p, ~30fps).
Yarışma taklidi: kareler 4'te 1 örneklenir (≈7.5 kare/sn — sunucunun verdiği hız),
0.25 sn/kare taban tempo, sağlık profili 450 sağlıklı → kesinti → 60'lık sağlıklı
patlama → kesinti (Q&A profili). Görev 3'e 6 gerçek referans, iki pencerede verilir.

Her karenin SUNUCUYA GİDECEK JSON'u (create_payload çıktısı, birebir) şuraya yazılır:
  ~/Masaüstü/teknofest_gorev2/tam_prova_jsonlar/frame_XXXXXX.json
Sonda OZET.json (sayımlar + Görev 2 kör bölge hatası).
"""
import csv
import json
import os
import sys
import time

import cv2
import numpy as np

ISTEMCI = os.path.expanduser(
    "~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU")
VIDEO = os.path.expanduser(
    "~/Masaüstü/teknofest_gorev2/gorev_1/THYZ_2026_Ornek_Veri_1.MP4")
GT_CSV = os.path.expanduser(
    "~/Masaüstü/hyz_gorev3/THYZ_2026_Ornek_Veri_Seti/THYZ_2026_Ornek_Veri_1_translation.csv")
REF_DIR = os.path.expanduser(
    "~/Masaüstü/hyz_gorev3/THYZ_2026_Ornek_Veri_Seti/THYZ_2026_Ornek_Veri_1_Referans_Nesneler")
CIKTI = os.path.expanduser("~/Masaüstü/teknofest_gorev2/tam_prova_jsonlar")
TMP = os.path.expanduser("~/Masaüstü/teknofest_gorev2/tam_prova_tmp")
ORNEKLEME = 4           # 30fps -> 7.5 kare/sn
TOPLAM = 2250
TABAN_SN = 0.25         # MIN_FRAME_INTERVAL taklidi
SUNUCU = "http://tam-prova-yerel/"

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ["GOREV2_RUN_DIR"] = os.path.expanduser(
    "~/Masaüstü/teknofest_gorev2/run_tam_prova")

sys.path.insert(0, ISTEMCI)
os.chdir(ISTEMCI)
from src.object_detection_model import ObjectDetectionModel  # noqa: E402
from src.frame_predictions import FramePredictions           # noqa: E402


def saglik(s):
    if 450 <= s < 1200 or 1260 <= s < 2250:
        return "0"
    return "1"


def main():
    os.makedirs(CIKTI, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    gt = {}
    with open(GT_CSV) as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            gt[i] = (float(row["translation_x"]), float(row["translation_y"]),
                     float(row["translation_z"]))

    refler = sorted(os.listdir(REF_DIR))
    ref_image_paths = {f"ref://{ad}": os.path.join(REF_DIR, ad) for ad in refler}
    # iki pencere (örneklenmiş kare no): 500-560 ve 1950-2010
    pencereler = [(500, 560), (1950, 2010)]

    model = ObjectDetectionModel(SUNUCU)
    cap = cv2.VideoCapture(VIDEO)
    print(f"[prova] video acildi, {TOPLAM} ornek kare islenecek "
          f"(~{TOPLAM*TABAN_SN/60:.0f} dk)")

    t_baslangic = time.monotonic()
    raw_i = -1
    s = 0
    while s < TOPLAM:
        ok, kare = cap.read()
        if not ok:
            break
        raw_i += 1
        if raw_i % ORNEKLEME:
            continue
        t0 = time.monotonic()

        yol = os.path.join(TMP, f"frame_{s:06d}.webp")
        cv2.imwrite(yol, kare, [cv2.IMWRITE_WEBP_QUALITY, 100])

        sg = saglik(s)
        g = gt.get(raw_i, (None, None, None))
        gx, gy, gz = (g if sg == "1" else (None, None, None))

        aktif = []
        if any(a <= s <= b for a, b in pencereler):
            # DİKKAT: start/end, image_url ile AYNI biçimde olmalı (sunucu da
            # öyle gönderiyor); önek farklıysa dizge karşılaştırması pencereyi
            # hep dışarıda sayar (ilk koşuda G3'ün 0 çıkma sebebi buydu).
            aktif = [{"url": u,
                      "frame_start_image_url": "/PROVA/frame_000000.webp",
                      "frame_end_image_url": "/PROVA/frame_999999.webp"}
                     for u in ref_image_paths]

        fp = FramePredictions(f"{SUNUCU}frames/{s}/", f"/PROVA/frame_{s:06d}.webp",
                              "TAM_PROVA_2026_RGB", gx, gy, gz)
        fp = model.detect(fp, sg, active_refs=aktif,
                          ref_image_paths=ref_image_paths, frame_image_path=yol)
        payload = fp.create_payload(SUNUCU)
        with open(os.path.join(CIKTI, f"frame_{s:06d}.json"), "w") as f:
            json.dump(payload, f, indent=1)
        os.remove(yol)

        if s % 150 == 0:
            print(f"[prova] kare {s}/{TOPLAM} saglik={sg} "
                  f"nesne={len(payload['detected_objects'])} "
                  f"ceviri={len(payload['detected_translations'])} "
                  f"ref={len(payload['reference_predictions'])}")
        s += 1
        gecen = time.monotonic() - t0
        if gecen < TABAN_SN:
            time.sleep(TABAN_SN - gecen)

    cap.release()
    if model._engine:
        model._engine.shutdown()

    # ── özet ──
    nesne = ceviri = refk = 0
    kor = []
    for si in range(s):
        p = json.load(open(os.path.join(CIKTI, f"frame_{si:06d}.json")))
        nesne += len(p["detected_objects"])
        ceviri += len(p["detected_translations"])
        refk += len(p["reference_predictions"])
        if saglik(si) == "0" and p["detected_translations"]:
            t = p["detected_translations"][0]
            v = np.array([float(t["translation_x"]), float(t["translation_y"]),
                          float(t["translation_z"])])
            gv = np.array(gt[si * ORNEKLEME])
            kor.append(float(np.linalg.norm(v - gv)))
    ozet = {
        "islenen_kare": s,
        "sure_dk": round((time.monotonic() - t_baslangic) / 60, 1),
        "gorev1_toplam_nesne": nesne,
        "gorev2_ceviri_gonderilen": ceviri,
        "gorev2_kor_bolge_ort_hata_m": round(float(np.mean(kor)), 2) if kor else None,
        "gorev2_kor_bolge_maks_hata_m": round(float(np.max(kor)), 2) if kor else None,
        "gorev3_toplam_kutu": refk,
    }
    with open(os.path.join(CIKTI, "OZET.json"), "w") as f:
        json.dump(ozet, f, indent=1)
    print("[prova] OZET:", json.dumps(ozet))


if __name__ == "__main__":
    main()
