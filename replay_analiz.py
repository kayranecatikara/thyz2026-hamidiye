#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replay_analiz.py — pose.txt + GT'den çevrimdışı kesinti tekrarı.

Her olası kesinti noktası için: son W çiftle Umeyama + çapa, sonraki H karede
ortalama Öklid hata. SLAM/ayar değişikliklerini canlı prova olmadan karşılaştırır.

Kullanım:
  python replay_analiz.py --pose run/outbox/pose.txt --gt gt.csv --fid-offset 700
"""
import argparse
import csv
import sys

import numpy as np

sys.path.insert(0, "/home/zeylo/Masaüstü/teknofest_gorev2")
from alignment import solve_alignment


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pose", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--fid-offset", type=int, default=0,
                    help="pose fid + offset = GT frame_id")
    ap.add_argument("--windows", default="100,300")
    ap.add_argument("--horizons", default="75,150,250")
    ap.add_argument("--step", type=int, default=10)
    args = ap.parse_args()

    gt = {}
    for r in csv.DictReader(open(args.gt)):
        gt[int(r["frame_id"])] = np.array(
            [float(r["x"]), float(r["y"]), float(r["z"])])

    fids, X, Y = [], [], []
    for line in open(args.pose):
        p = line.split()
        if len(p) != 9 or p[8] != "OK":
            continue
        fid = int(p[0])
        g = gt.get(fid + args.fid_offset)
        if g is None:
            continue
        fids.append(fid)
        X.append([float(p[1]), float(p[2]), float(p[3])])
        Y.append(g)
    X, Y = np.array(X), np.array(Y)
    if len(X) < 60:
        sys.exit(f"yetersiz OK cift: {len(X)}")
    print(f"OK cift: {len(X)} (fid {fids[0]}..{fids[-1]})")

    tf = solve_alignment(X, Y, min_pairs=30)
    res = np.linalg.norm(tf.apply(X) - Y, axis=1)
    print(f"tam-fit: mod={tf.mode} s={getattr(tf,'s',0):.2f} "
          f"RMS={np.sqrt((res**2).mean()):.2f} m")

    # pencere-içi tutarlılık
    rms_in = []
    for k in range(100, len(X), 25):
        t = solve_alignment(X[k-100:k], Y[k-100:k], min_pairs=30)
        if t:
            rms_in.append(t.rms)
    if rms_in:
        print(f"pencere100-ici rms: medyan={np.median(rms_in):.2f} m")

    for W in (int(w) for w in args.windows.split(",")):
        for H in (int(h) for h in args.horizons.split(",")):
            errs = []
            for k in range(W, len(X) - H, args.step):
                t = solve_alignment(X[k-W:k], Y[k-W:k], min_pairs=30)
                if t is None:
                    continue
                off = Y[k-1] - t.apply(X[k-1])
                pred = t.apply(X[k:k+H]) + off
                errs.append(np.linalg.norm(pred - Y[k:k+H], axis=1).mean())
            if errs:
                print(f"W={W:3d} H={H:3d}: kesinti-ort medyan="
                      f"{np.median(errs):6.2f} m  p90={np.percentile(errs,90):6.2f} m"
                      f"  (n={len(errs)})")


if __name__ == "__main__":
    main()
