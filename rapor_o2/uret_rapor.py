#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""O2 tam prova karşılaştırma raporu — GT vs tahmin (dataviz yöntemiyle)."""
import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

BASE = "/home/zeylo/Masaüstü/teknofest_gorev2"
OUT = os.path.join(BASE, "rapor_o2")
PRED = os.path.join(BASE, "prova2025/pred_O2full.csv")
GTF = os.path.join(BASE, "prova2025/oturum2_gt.csv")
POSE = os.path.join(BASE, "prova2025/run_O2full/outbox/pose.txt")

# ── Palet (dataviz referans paleti, açık mod — önceden doğrulanmış) ──────────
SURFACE = "#fcfcfb"
INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
GRID = "#e1e0d9"; AXIS = "#c3c2b7"
C_MAVI = "#2a78d6"   # slot 1 — echo / tahmin(sağlıklı)
C_AQUA = "#1baf7a"   # slot 2 — slam
C_SARI = "#eda100"   # slot 3 — deadreckon (düşük kontrast → lejant+etiket şart)
C_TURUNCU = "#eb6834"  # slot 8 — tahmin(sağlık=0) durum vurgusu
C_KRITIK = "#d03b3b"   # durum: harita sıfırlaması işareti (ikon+etiketle)
SAGLIK0_WASH = "#e9e7e0"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.9,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.labelcolor": INK2, "text.color": INK,
    "font.size": 10.5, "axes.titlesize": 13,
    "legend.frameon": False,
})

# ── Veri ─────────────────────────────────────────────────────────────────────
gt = {}
for r in csv.DictReader(open(GTF)):
    gt[int(r["frame_id"])] = np.array(
        [float(r["x"]), float(r["y"]), float(r["z"])])

rows = []
for r in csv.DictReader(open(PRED)):
    fid = int(r["frame_id"])
    if fid not in gt:
        continue
    rows.append((fid,
                 np.array([float(r["x"]), float(r["y"]), float(r["z"])]),
                 int(r["saglik"]), r["kaynak"], float(r["islem_suresi_s"])))
rows.sort(key=lambda t: t[0])
fid = np.array([t[0] for t in rows])
P = np.array([t[1] for t in rows])            # tahmin
G = np.array([gt[f] for f in fid])            # gerçek
sag = np.array([t[2] for t in rows])
kay = np.array([t[3] for t in rows])
sure = np.array([t[4] for t in rows])
err = np.linalg.norm(P - G, axis=1)

# Harita sıfırlama anları (pose.txt: OK görüldükten sonra NOT_INITIALIZED)
resets = []
saw_ok = False
for line in open(POSE):
    p = line.split()
    if len(p) != 9:
        continue
    st = p[8]
    if st == "OK":
        saw_ok = True
    elif st == "NOT_INITIALIZED" and saw_ok:
        resets.append(int(p[0]))
        saw_ok = False
reset_set = sorted(resets)

# Sağlık=0 pencereleri (ardışık bloklar)
def bloklar(mask):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]:
                j += 1
            out.append((fid[i], fid[j]))
            i = j + 1
        else:
            i += 1
    return out

s0_blok = bloklar(sag == 0)

def stil(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, which="major", axis="both")
    ax.set_axisbelow(True)

# ── 1) Kuşbakışı yörünge ─────────────────────────────────────────────────────
f1, ax = plt.subplots(figsize=(9.5, 9))
ax.plot(G[:, 0], G[:, 1], color=INK2, lw=1.6, label="Gerçek yörünge (GT)",
        zorder=2)
# tahmini sağlık durumuna göre parçala (ardışık koşular tek çizimde)
i = 0
ilk = {1: True, 0: True}
while i < len(fid):
    j = i
    while j + 1 < len(fid) and sag[j + 1] == sag[i]:
        j += 1
    seg = slice(i, j + 2 if j + 1 < len(fid) else j + 1)  # bitişik görünüm
    renk = C_MAVI if sag[i] == 1 else C_TURUNCU
    lbl = None
    if ilk[sag[i]]:
        lbl = "Tahmin — sağlık=1 (echo)" if sag[i] == 1 else "Tahmin — sağlık=0"
        ilk[sag[i]] = False
    ax.plot(P[seg, 0], P[seg, 1], color=renk, lw=2.0, label=lbl, zorder=3)
    i = j + 1
# sıfırlama anları (tahmin konumunda)
if reset_set:
    m = np.isin(fid, reset_set)
    ax.scatter(P[m, 0], P[m, 1], marker="x", s=90, color=C_KRITIK,
               linewidths=2.2, label=f"Harita sıfırlaması (×{len(reset_set)})",
               zorder=5)
ax.scatter(*G[0, :2], marker="o", s=70, facecolor=SURFACE, edgecolor=INK,
           linewidth=1.6, zorder=6)
ax.annotate("başlangıç", G[0, :2], textcoords="offset points",
            xytext=(8, 6), fontsize=9.5, color=INK2)
ax.annotate("GT bitiş", G[-1, :2], textcoords="offset points",
            xytext=(8, -10), fontsize=9.5, color=INK2)
ax.set_xlabel("x (m)")
ax.set_ylabel("y (m)")
ax.set_aspect("equal")
ax.set_title("Kuşbakışı yörünge — THYZ 2025 Oturum 2 tam prova\n"
             f"Denklem 2 = {err.mean():.1f} m (N={len(fid)})",
             loc="left", fontweight="bold")
ax.legend(loc="best", fontsize=9.5)
stil(ax)
f1.tight_layout()
f1.savefig(os.path.join(OUT, "1_kusbakisi_yorunge.png"), dpi=130)

# ── 2) Eksen bazlı zaman serileri ────────────────────────────────────────────
f2, axs = plt.subplots(3, 1, figsize=(12.5, 9), sharex=True)
adlar = ["x (m)", "y (m)", "z (m)"]
for k, ax in enumerate(axs):
    for (a, b) in s0_blok:
        ax.axvspan(a, b, color=SAGLIK0_WASH, alpha=0.85, zorder=0, lw=0)
    for rfid in reset_set:
        ax.axvline(rfid, color=C_KRITIK, lw=1.0, ls="--", alpha=0.55, zorder=1)
    ax.plot(fid, G[:, k], color=INK2, lw=1.6, zorder=2)
    ax.plot(fid, P[:, k], color=C_MAVI, lw=1.8, zorder=3)
    ax.set_ylabel(adlar[k])
    stil(ax)
axs[-1].set_xlabel("kare (frame_id)")
lej = [Line2D([], [], color=INK2, lw=1.6, label="Gerçek (GT)"),
       Line2D([], [], color=C_MAVI, lw=1.8, label="Tahmin"),
       Patch(facecolor=SAGLIK0_WASH, label="sağlık=0 penceresi"),
       Line2D([], [], color=C_KRITIK, lw=1.0, ls="--",
              label="harita sıfırlaması")]
axs[0].legend(handles=lej, ncol=4, loc="upper left", fontsize=9.5)
axs[0].set_title("Eksen bazlı gerçek ve tahmin zaman serileri",
                 loc="left", fontweight="bold")
f2.tight_layout()
f2.savefig(os.path.join(OUT, "2_eksen_zaman_serileri.png"), dpi=130)

# ── 3) Hata–zaman (kaynak renk kodlu) ────────────────────────────────────────
f3, ax = plt.subplots(figsize=(12.5, 5.4))
for (a, b) in s0_blok:
    ax.axvspan(a, b, color=SAGLIK0_WASH, alpha=0.85, zorder=0, lw=0)
for rfid in reset_set:
    ax.axvline(rfid, color=C_KRITIK, lw=1.0, ls="--", alpha=0.55, zorder=1)
ax.plot(fid, err, color=MUTED, lw=0.7, alpha=0.7, zorder=2)
renkler = {"echo": C_MAVI, "slam": C_AQUA, "deadreckon": C_SARI}
for ad, renk in renkler.items():
    m = kay == ad
    ax.scatter(fid[m], err[m], s=7, color=renk, zorder=3,
               label=f"{ad} (N={int(m.sum())}, ort {err[m].mean():.1f} m)")
imax = int(np.argmax(err))
ax.annotate(f"maks {err[imax]:.0f} m @ kare {fid[imax]}",
            (fid[imax], err[imax]), textcoords="offset points",
            xytext=(-10, -16), ha="right", fontsize=9.5, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.9))
ax.set_xlabel("kare (frame_id)")
ax.set_ylabel("Öklid hata (m)")
ax.set_ylim(bottom=0)
ax.set_title("Anlık konum hatası ve yanıt kaynağı",
             loc="left", fontweight="bold")
ax.legend(loc="upper left", fontsize=9.5)
stil(ax)
f3.tight_layout()
f3.savefig(os.path.join(OUT, "3_hata_zaman.png"), dpi=130)

# ── 4) Özet + RAPOR.md ───────────────────────────────────────────────────────
s0 = sag == 0
d2_all = err.mean()
d2_s0 = err[s0].mean()
slam_pay = 100.0 * (kay[s0] == "slam").sum() / max(s0.sum(), 1)
sat = []
for ad in ("echo", "slam", "deadreckon"):
    m = kay == ad
    sat.append(f"| {ad} | {int(m.sum())} | {err[m].mean():.2f} | "
               f"{err[m].max():.2f} |")

rapor = f"""# THYZ 2025 Oturum 2 — Tam Prova Karşılaştırma Raporu

Üretim: `rapor_o2/uret_rapor.py` • Veri: `prova2025/pred_O2full.csv` (tahmin),
`prova2025/oturum2_gt.csv` (gerçek), `prova2025/run_O2full/outbox/pose.txt`
(SLAM durumları).

**Senaryo:** 2250 kare, 4 fps gerçek-zaman temposu, sağlık profili Q&A uyumlu —
0–449 sağlıklı, 450–1199 kesinti, 1200–1259 sağlıklı pencere, 1260–2249 kesinti.
Konfig: `thyz2025_cropA.yaml` @1280 px, sıfırlama-korumalı motor, sönümlü ölü
hesap (τ=40).

## Özet

| Metrik | Değer |
|---|---|
| **Denklem 2 — tam oturum (N={len(fid)})** | **{d2_all:.2f} m** |
| Denklem 2 — yalnız sağlık=0 (N={int(s0.sum())}) | {d2_s0:.2f} m |
| Maksimum hata | {err.max():.2f} m (kare {fid[imax]}, kaynak={kay[imax]}) |
| SLAM kapsaması (sağlık=0 içinde kaynak=slam) | %{slam_pay:.1f} |
| Harita sıfırlaması | {len(reset_set)} kez (kareler: {', '.join(map(str, reset_set))}) |
| İşlem süresi | ort {sure.mean():.3f} s / p95 {np.percentile(sure, 95):.3f} s (bütçe 1,6 s) |

### Kaynak bazlı hata

| Kaynak | N | Ortalama hata (m) | Maks (m) |
|---|---|---|---|
{chr(10).join(sat)}

## Grafikler

1. `1_kusbakisi_yorunge.png` — x-y düzleminde GT (gri) ve tahmin (mavi=sağlık 1,
   turuncu=sağlık 0); kırmızı × = harita sıfırlama anları.
2. `2_eksen_zaman_serileri.png` — x/y/z ayrı panellerde GT vs tahmin;
   gri gölge = sağlık=0 pencereleri; kesikli kırmızı = sıfırlamalar.
3. `3_hata_zaman.png` — anlık Öklid hata; nokta rengi yanıt kaynağı
   (mavi echo / yeşil-aqua slam / sarı deadreckon).

## Okuma notları

- Echo dilimi tanım gereği 0 hatadır (referans aynen geri gönderilir).
- İlk kesintide (450–1199) tahminler ağırlıkla sönümlü ölü hesaptan geldi;
  hata sınırlı kaldı (ort ≈ {err[(s0) & (fid < 1200)].mean():.1f} m). İkinci uzun
  kesintide SLAM+hizalama devreye girdi (ort ≈ {err[(s0) & (fid >= 1260)].mean():.1f} m);
  sıfırlamalar sonrası pencere yeniden kurulana dek ölü hesap taşıdı.
- Palet: dataviz referans paleti (açık mod, sabit slot sırası; belge kaydına göre
  komşu CVD ΔE 24,2 ile geçer). Sarının açık zeminde <3:1 kontrastı nedeniyle
  lejantta N ve ortalamalar metinle verildi (relief kuralı).
"""
open(os.path.join(OUT, "RAPOR.md"), "w").write(rapor)
print("TAMAM")
print("d2_all=%.2f d2_s0=%.2f slam_pay=%.1f resets=%s maks=%.1f@%d"
      % (d2_all, d2_s0, slam_pay, reset_set, err.max(), fid[imax]))
