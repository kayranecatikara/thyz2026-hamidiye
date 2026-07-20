#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analiz_ozet.py — video_analiz.sh koşuları bittikten sonra özet tablo üretir.
Girdi: prova2025/pred_analiz_oN.csv (N=1..4, olanlar) + oturumN_gt.csv
Çıktı: analiz_3eksen/OZET.md
"""
import csv
import os

import numpy as np

BURADA = os.path.dirname(os.path.abspath(__file__))
KALIB = 450


def yukle(p):
    d = {}
    with open(p) as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            d[int(row[0])] = np.array([float(row[1]), float(row[2]),
                                       float(row[3])])
    return d


def main():
    satirlar = []
    for ot in (1, 2, 3, 4):
        pred_p = os.path.join(BURADA, f"prova2025/pred_analiz_o{ot}.csv")
        if not os.path.exists(pred_p):
            continue
        gt = yukle(os.path.join(BURADA, f"prova2025/oturum{ot}_gt.csv"))
        kaynaklar = {}
        with open(pred_p) as f:
            r = csv.reader(f)
            next(r)
            pr = {}
            for row in r:
                pr[int(row[0])] = np.array([float(row[1]), float(row[2]),
                                            float(row[3])])
                kaynaklar[int(row[0])] = row[5]
        kor = sorted(f for f in pr if f >= KALIB and f in gt)
        if not kor:
            continue
        e = np.array([pr[f] - gt[f] for f in kor])
        d = np.linalg.norm(e, axis=1)
        mae = np.mean(np.abs(e), axis=0)
        i_mx = int(np.argmax(d))
        slam_pay = 100.0 * sum(1 for f in kor
                               if kaynaklar.get(f) == "slam") / len(kor)
        satirlar.append((ot, float(np.mean(d)), mae, float(d[i_mx]),
                         kor[i_mx], slam_pay, len(kor)))

    yol = os.path.join(BURADA, "analiz_3eksen", "OZET.md")
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w") as f:
        f.write("# 3-Eksen Kör SLAM Analizi — Özet\n\n")
        f.write("Protokol: ilk 450 kare (1. dk) gerçek veriyle kalibrasyon "
                "(Umeyama sim3); 450'den sonra sistem gerçek veriyi hiç "
                "görmez. Saf SLAM (harman kapalı). Metrikler yalnız kör "
                "bölgede (450-2249) hesaplanır.\n\n")
        f.write("| Oturum | Kör bölge ort. hata (m) | MAE x/y/z (m) | "
                "Maks hata (m) @ kare | SLAM payı |\n")
        f.write("|--------|------|------|------|------|\n")
        for ot, d2, mae, mx, mxf, pay, n in satirlar:
            f.write(f"| O{ot} | {d2:.1f} | "
                    f"{mae[0]:.1f} / {mae[1]:.1f} / {mae[2]:.1f} | "
                    f"{mx:.1f} @ {mxf} | %{pay:.0f} ({n} kare) |\n")
        f.write("\nGrafikler: analiz_3eksen/oturumN.png\n")
    print(f"Özet yazıldı: {yol}")
    for ot, d2, mae, mx, mxf, pay, n in satirlar:
        print(f"  O{ot}: ort={d2:.1f} m  maks={mx:.1f}@{mxf}  SLAM=%{pay:.0f}")


if __name__ == "__main__":
    main()
