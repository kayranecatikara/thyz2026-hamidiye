#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate_denklem2.py — Yarışma metriği (FAZ 8.4)

Denklem 2 = (1/N) · Σ √(Δx² + Δy² + Δz²)   — HİZALAMA YAPILMADAN, mutlak hata.

Girdi:
  --pred predictions.csv   (bridge.py çıktısı: frame_id,x,y,z,saglik,kaynak,islem_suresi_s)
  --gt   <gt dosyası>      (esnek: virgül/boşluk ayraçlı, başlıklı/başlıksız;
                            varsayılan sütunlar: frame_id,x,y,z → --gt-cols ile değiştir)
Çıktı:
  - Konsol raporu: genel Denklem2, sağlık=0 dilimi, kaynak kırılımı, süre istatistiği
  - <out_prefix>_axes.png : eksen bazlı hata grafiği
"""

import argparse
import csv
import sys

import numpy as np


def read_table(path):
    """Virgül veya boşluk ayraçlı, opsiyonel başlıklı sayısal tablo okur."""
    rows = []
    header = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p for p in line.replace(",", " ").split() if p]
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                if header is None and rows == []:
                    header = [p.strip().lower() for p in
                              line.replace(",", " ").split()]
                continue
    return header, rows


def load_gt(path, cols):
    header, rows = read_table(path)
    idx = {}
    if header:
        for i, name in enumerate(header):
            idx[name] = i
    want = cols.split(",")
    gt = {}
    for r in rows:
        try:
            if header and all(w in idx for w in want):
                fid = int(round(r[idx[want[0]]]))
                x, y, z = (r[idx[want[1]]], r[idx[want[2]]], r[idx[want[3]]])
            else:
                fid = int(round(r[0]))
                x, y, z = r[1], r[2], r[3]
        except (IndexError, ValueError):
            continue
        gt[fid] = np.array([x, y, z], dtype=float)
    return gt


def load_pred(path):
    preds = []
    with open(path, "r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            preds.append({
                "frame_id": int(row["frame_id"]),
                "p": np.array([float(row["x"]), float(row["y"]),
                               float(row["z"])]),
                "saglik": int(row["saglik"]),
                "kaynak": row.get("kaynak", "?"),
                "sure": float(row.get("islem_suresi_s", "nan")),
            })
    return preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--gt-cols", default="frame_id,x,y,z",
                    help="GT sütun adları (başlıklı dosyada)")
    ap.add_argument("--out-prefix", default="denklem2")
    args = ap.parse_args()

    gt = load_gt(args.gt, args.gt_cols)
    preds = load_pred(args.pred)
    if not gt:
        sys.exit("GT bos okundu — format/sutunlari kontrol et")
    if not preds:
        sys.exit("predictions.csv bos")

    matched = [(p, gt[p["frame_id"]]) for p in preds if p["frame_id"] in gt]
    kayip = len(preds) - len(matched)
    if not matched:
        sys.exit("Hic frame_id eslesmedi — GT frame_id tabani farkli olabilir")

    err_v = np.array([p["p"] - g for p, g in matched])          # Nx3
    err_e = np.linalg.norm(err_v, axis=1)                        # N
    saglik = np.array([p["saglik"] for p, _ in matched])
    fids = np.array([p["frame_id"] for p, _ in matched])
    sure = np.array([p["sure"] for p, _ in matched])
    kaynak = [p["kaynak"] for p, _ in matched]

    d2_all = float(err_e.mean())
    m0 = saglik == 0
    d2_s0 = float(err_e[m0].mean()) if m0.any() else float("nan")
    d2_s1 = float(err_e[~m0].mean()) if (~m0).any() else float("nan")

    print("=" * 62)
    print(f"DENKLEM 2 (tum kareler, N={len(err_e)}):   {d2_all:.4f} m")
    print(f"  saglik=0 dilimi (N={int(m0.sum())}):     {d2_s0:.4f} m")
    print(f"  saglik=1 dilimi (N={int((~m0).sum())}):  {d2_s1:.4f} m  (echo=0 beklenir)")
    if kayip:
        print(f"  UYARI: GT'de bulunamayan tahmin: {kayip} kare")
    print("-" * 62)
    ks, cnt = np.unique(kaynak, return_counts=True)
    for k, c in zip(ks, cnt):
        sel = np.array([kk == k for kk in kaynak])
        print(f"  kaynak={k:<11} N={c:<5} ort.hata={err_e[sel].mean():.4f} m")
    print("-" * 62)
    valid_t = sure[np.isfinite(sure)]
    if valid_t.size:
        print(f"  islem suresi: ort={valid_t.mean():.3f} s  "
              f"p95={np.percentile(valid_t, 95):.3f} s  "
              f"maks={valid_t.max():.3f} s   (hedef ort < 1.6 s)")
    print("=" * 62)

    # ── Grafik ──
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    names = ["Δx (m)", "Δy (m)", "Δz (m)"]
    for i in range(3):
        axes[i].plot(fids, err_v[:, i], lw=0.8)
        axes[i].set_ylabel(names[i])
        axes[i].grid(alpha=0.3)
    axes[3].plot(fids, err_e, lw=0.9, color="crimson",
                 label=f"Oklid hata (Denklem2={d2_all:.3f} m)")
    if m0.any():
        axes[3].fill_between(fids, 0, err_e.max() * 1.05, where=m0,
                             alpha=0.15, color="orange", label="saglik=0")
    axes[3].set_ylabel("‖Δ‖ (m)")
    axes[3].set_xlabel("frame_id")
    axes[3].legend(loc="upper left")
    axes[3].grid(alpha=0.3)
    fig.suptitle("TEKNOFEST Gorev 2 — eksen bazli hata")
    fig.tight_layout()
    out = f"{args.out_prefix}_axes.png"
    fig.savefig(out, dpi=110)
    print(f"grafik: {out}")


if __name__ == "__main__":
    main()
