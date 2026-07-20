#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dr_deney.py — Ölü hesap modellerinin çevrimdışı yarışı (GT tekrarı).

Her kesinti başlangıcı k için: son GEÇMİŞ kareden durum kestir (hız, yön,
dönüş hızı), H kare ileriye ekstrapole et, GT ile ortalama hatayı ölç.
Modeller:
  M0  sönümlü sabit-hız (mevcut motor, τ=40)
  M1  sabit dönüş + sönümlü hız (koordineli dönüş)
  M2  sönümlü dönüş + sönümlü hız (τ_ω ile)
"""
import csv
import numpy as np

BASE = "/home/zeylo/Masaüstü/teknofest_gorev2/prova2025/"
GECMIS = 20          # durum kestirimi için kullanılan kare sayısı
TAU_V = 40.0
TAU_W = 150.0


def yukle(o):
    fid, P = [], []
    for r in csv.DictReader(open(BASE + f"oturum{o}_gt.csv")):
        fid.append(int(r["frame_id"]))
        P.append([float(r["x"]), float(r["y"]), float(r["z"])])
    idx = np.argsort(fid)
    return np.array(P)[idx]


def durum(H):
    """Geçmiş pencereden: konum, hız vektörü, yatay sürat, yön, dönüş hızı."""
    p0 = H[-1]
    v = (H[-1] - H[0]) / (len(H) - 1)          # ort. hız vektörü (M0 ile aynı)
    adim = np.diff(H[:, :2], axis=0)           # yatay adımlar
    surat = np.linalg.norm(adim, axis=1)
    yon = np.unwrap(np.arctan2(adim[:, 1], adim[:, 0]))
    # dönüş hızı: yönün kare başına eğimi (en küçük kareler)
    t = np.arange(len(yon))
    w = np.polyfit(t, yon, 1)[0] if len(yon) >= 3 else 0.0
    return p0, v, float(surat.mean()), float(yon[-1]), float(w), float(v[2])


def m0(H, n):
    p0, v, *_ = durum(H)
    d = np.arange(1, n + 1)[:, None]
    return p0 + v * TAU_V * (1 - np.exp(-d / TAU_V))


def m1(H, n, tau_w=None):
    p0, v, s, psi, w, vz = durum(H)
    out = np.empty((n, 3))
    p = p0.copy().astype(float)
    for i in range(n):
        di = i + 1
        sv = s * np.exp(-di / TAU_V)              # sürat sönümü
        wz = w if tau_w is None else w * np.exp(-di / tau_w)
        psi += wz
        p = p + np.array([sv * np.cos(psi), sv * np.sin(psi),
                          vz * np.exp(-di / TAU_V)])
        out[i] = p
    return out


def m2(H, n):
    return m1(H, n, tau_w=TAU_W)


MODELLER = {"M0 duz+sonum": m0, "M1 donus": m1, "M2 donus+sonum": m2}

for o in ("2", "3", "1", "4"):
    G = yukle(o)
    print(f"\n== Oturum {o} (N={len(G)})")
    for H_ufuk in (250, 750, 990):
        sonuc = {ad: [] for ad in MODELLER}
        for k in range(GECMIS, len(G) - H_ufuk, 25):
            gecmis = G[k - GECMIS:k]
            hedef = G[k:k + H_ufuk]
            for ad, fn in MODELLER.items():
                tahmin = fn(gecmis, H_ufuk)
                sonuc[ad].append(
                    np.linalg.norm(tahmin - hedef, axis=1).mean())
        satir = f"  H={H_ufuk:4d}: "
        for ad in MODELLER:
            v = np.array(sonuc[ad])
            satir += f"{ad}: med={np.median(v):6.1f} p90={np.percentile(v,90):6.1f}   "
        print(satir + f"(n={len(v)})")
