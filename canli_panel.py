#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canli_panel.py — Prova koşarken canlı karşılaştırma paneli.

Pencereler:
  [Kuşbakışı]  GT tam rota (soluk) + gezilen GT + tahmin (kaynağa göre renkli)
  [Hata]       anlık Öklid hata eğrisi
  [Yönelim]    GT hareket yönü (heading) vs SLAM yaw
  [Kare]       akan video karesi (fid/sağlık/durum yazılı)
  [z(t)]       irtifa: GT vs tahmin
  [Durum]      SLAM durum şeridi + doku (Laplacian) eğrisi

Kullanım:
  python canli_panel.py --gt prova2025/oturum2_gt.csv \
      --pred prova2025/pred_canli.csv --run-dir prova2025/run_canli \
      --frames-dir prova2025/frames_o2 [--start 0]
Dosyalar henüz yoksa bekler; prova ile aynı anda başlatılabilir.
"""
import argparse
import csv
import glob
import os

import numpy as np
import cv2
import matplotlib
matplotlib.use(os.environ.get("MPLBACKEND", "TkAgg"))
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.lines import Line2D

# dataviz referans paleti (açık mod)
SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
GRID = "#e1e0d9"; AXIS = "#c3c2b7"
C = {"echo": "#2a78d6", "slam": "#1baf7a", "deadreckon": "#eda100"}
C_GT = "#52514e"; C_KRITIK = "#d03b3b"
DURUM_RENK = {"OK": "#0ca30c", "NOT_INITIALIZED": "#898781",
              "LOST": "#d03b3b", "RECENTLY_LOST": "#ec835a",
              "NO_IMAGE": "#c3c2b7"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.labelcolor": INK2, "text.color": INK, "font.size": 9.5,
    "legend.frameon": False,
})


def quat_to_ypr(qx, qy, qz, qw):
    """Kuaterniyon → yaw/pitch/roll (derece)."""
    yaw = np.degrees(np.arctan2(2 * (qw * qz + qx * qy),
                                1 - 2 * (qy * qy + qz * qz)))
    sinp = np.clip(2 * (qw * qy - qz * qx), -1, 1)
    pitch = np.degrees(np.arcsin(sinp))
    roll = np.degrees(np.arctan2(2 * (qw * qx + qy * qz),
                                 1 - 2 * (qx * qx + qy * qy)))
    return yaw, pitch, roll


class Panel:
    def __init__(self, a):
        self.a = a
        self.gt = {}
        for r in csv.DictReader(open(a.gt)):
            self.gt[int(r["frame_id"])] = np.array(
                [float(r["x"]), float(r["y"]), float(r["z"])])
        self.gt_yol = np.array([self.gt[k] for k in sorted(self.gt)])
        self.pred_off = 0        # pred csv'de okunan bayt
        self.pose_off = 0
        self.rows = []           # (fid, xyz, saglik, kaynak)
        self.pose = {}           # fid -> (durum, yaw)
        self.doku = {}           # fid -> laplacian log10
        self.son_kare = None
        self.kare_meta = ""

        self.fig = plt.figure(figsize=(15.5, 8.5))
        self.fig.canvas.manager.set_window_title("Görev 2 — Canlı Prova Paneli")
        gs = self.fig.add_gridspec(2, 3, hspace=0.32, wspace=0.28,
                                   left=0.05, right=0.98, top=0.94, bottom=0.07)
        self.ax_kus = self.fig.add_subplot(gs[0, 0])
        self.ax_hata = self.fig.add_subplot(gs[0, 1])
        self.ax_yon = self.fig.add_subplot(gs[0, 2])
        self.ax_kare = self.fig.add_subplot(gs[1, 0])
        self.ax_z = self.fig.add_subplot(gs[1, 1])
        self.ax_durum = self.fig.add_subplot(gs[1, 2])

    # ── artımlı okuma ────────────────────────────────────────────────────────
    def oku(self):
        a = self.a
        if os.path.exists(a.pred):
            with open(a.pred) as f:
                f.seek(self.pred_off)
                for line in f:
                    if not line.endswith("\n"):
                        break
                    self.pred_off += len(line)
                    p = line.strip().split(",")
                    if p[0] == "frame_id" or len(p) < 6:
                        continue
                    self.rows.append((int(p[0]),
                                      np.array([float(p[1]), float(p[2]),
                                                float(p[3])]),
                                      p[4], p[5]))
        pt = os.path.join(a.run_dir, "outbox", "pose.txt")
        if os.path.exists(pt):
            with open(pt) as f:
                f.seek(self.pose_off)
                for line in f:
                    if not line.endswith("\n"):
                        break
                    self.pose_off += len(line)
                    p = line.split()
                    if len(p) != 9:
                        continue
                    yaw = quat_to_ypr(*map(float, p[4:8]))[0] \
                        if p[8] == "OK" else np.nan
                    self.pose[int(p[0])] = (p[8], yaw)
        # akan kare + doku
        if self.rows:
            fid = self.rows[-1][0]
            yol = os.path.join(a.frames_dir,
                               f"frame_{fid + a.start:06d}.webp")
            if not os.path.exists(yol):
                c = glob.glob(os.path.join(a.frames_dir,
                                           f"*{fid + a.start:06d}*"))
                yol = c[0] if c else None
            if yol:
                img = cv2.imread(yol)
                if img is not None:
                    kucuk = cv2.resize(img, (640, 360))
                    gri = cv2.cvtColor(kucuk, cv2.COLOR_BGR2GRAY)
                    self.doku[fid] = float(np.log10(
                        max(cv2.Laplacian(gri, cv2.CV_64F).var(), 1e-3)))
                    self.son_kare = cv2.cvtColor(kucuk, cv2.COLOR_BGR2RGB)
                    st = self.pose.get(fid, ("?",))[0]
                    self.kare_meta = (f"kare {fid}  sağlık={self.rows[-1][2]}  "
                                      f"kaynak={self.rows[-1][3]}  SLAM={st}")

    # ── çizim ────────────────────────────────────────────────────────────────
    def ciz(self, _):
        self.oku()
        if not self.rows:
            return
        fids = np.array([r[0] for r in self.rows])
        P = np.array([r[1] for r in self.rows])
        sag = np.array([r[2] for r in self.rows])
        kay = np.array([r[3] for r in self.rows])
        G = np.array([self.gt.get(f + self.a.start, [np.nan] * 3)
                      for f in fids])
        e = np.linalg.norm(P - G, axis=1)

        ax = self.ax_kus; ax.clear()
        ax.plot(self.gt_yol[:, 0], self.gt_yol[:, 1], color=GRID, lw=1.2)
        m = ~np.isnan(G[:, 0])
        ax.plot(G[m, 0], G[m, 1], color=C_GT, lw=1.8)
        for ad, renk in C.items():
            mm = kay == ad
            if mm.any():
                ax.scatter(P[mm, 0], P[mm, 1], s=5, color=renk)
        ax.scatter(*G[m][-1, :2], s=80, marker="o", facecolor="none",
                   edgecolor=INK, linewidth=1.8)
        ax.scatter(*P[-1, :2], s=60, marker="s", facecolor="none",
                   edgecolor=C_KRITIK, linewidth=1.8)
        ax.set_title("Kuşbakışı — GT (gri) vs tahmin", loc="left",
                     fontweight="bold", fontsize=10.5)
        ax.set_aspect("equal")

        ax = self.ax_hata; ax.clear()
        ax.plot(fids, e, color=MUTED, lw=0.8)
        for ad, renk in C.items():
            mm = kay == ad
            if mm.any():
                ax.scatter(fids[mm], e[mm], s=4, color=renk)
        son = e[~np.isnan(e)]
        ort = son.mean() if len(son) else 0
        ax.set_title(f"Anlık hata — Denklem2(şu ana dek)={ort:.1f} m",
                     loc="left", fontweight="bold", fontsize=10.5)
        ax.set_ylim(bottom=0)

        # Yönelim: iki eğri de DÜNYA çerçevesinde rota yönü (GT konumlarından
        # ve tahmin konumlarından). Ham SLAM yaw'ı SLAM'in kendi çerçevesinde
        # olduğundan (dünyadan dönük + AYNALI; el-yönü farkı) ters trendli
        # görünüyordu — hata değil ama kafa karıştırıyordu.
        ax = self.ax_yon; ax.clear()
        if m.sum() > 10:
            d = np.diff(G[m][:, :2], axis=0)
            iyi = np.linalg.norm(d, axis=1) > 0.05
            hd = np.degrees(np.unwrap(np.arctan2(d[iyi, 1], d[iyi, 0])))
            ax.plot(fids[m][1:][iyi], hd, color=C_GT, lw=1.6,
                    label="GT rota yönü")
        if len(P) > 10:
            dp = np.diff(P[:, :2], axis=0)
            iyip = np.linalg.norm(dp, axis=1) > 0.05
            if iyip.any():
                hp = np.degrees(np.unwrap(np.arctan2(dp[iyip, 1],
                                                     dp[iyip, 0])))
                ax.plot(fids[1:][iyip], hp, color=C["slam"], lw=1.6,
                        label="tahmin rota yönü")
        ax.legend(fontsize=8.5, loc="upper left")
        ax.set_title("Yönelim — rota yönü: GT vs tahmin",
                     loc="left", fontweight="bold", fontsize=10.5)

        ax = self.ax_kare; ax.clear(); ax.axis("off")
        if self.son_kare is not None:
            ax.imshow(self.son_kare)
            ax.set_title(self.kare_meta, loc="left", fontsize=10,
                         fontweight="bold")

        ax = self.ax_z; ax.clear()
        ax.plot(fids[m], G[m][:, 2], color=C_GT, lw=1.6, label="GT z")
        ax.plot(fids, P[:, 2], color=C["echo"], lw=1.6, label="tahmin z")
        ax.legend(fontsize=8.5, loc="upper left")
        ax.set_title("İrtifa z(t)", loc="left", fontweight="bold",
                     fontsize=10.5)

        ax = self.ax_durum; ax.clear()
        if self.pose:
            pf = np.array(sorted(self.pose))
            renkler = [DURUM_RENK.get(self.pose[f][0], MUTED) for f in pf]
            ax.scatter(pf, np.ones(len(pf)), s=14, c=renkler, marker="|")
        if self.doku:
            df = np.array(sorted(self.doku))
            ax.plot(df, [self.doku[f] for f in df], color=C["echo"], lw=1.4)
            ax.axhline(np.log10(30), color=C_KRITIK, lw=0.9, ls="--")
            ax.text(0.01, 0.06, "kesikli çizgi altı ≈ dokusuz/su",
                    transform=ax.transAxes, fontsize=8, color=INK2)
        say = {a: int((kay == a).sum()) for a in C}
        ax.set_title(f"SLAM durumu + doku   echo:{say['echo']} "
                     f"slam:{say['slam']} DR:{say['deadreckon']}",
                     loc="left", fontweight="bold", fontsize=10.5)
        ax.set_ylim(0, 5)
        leg = [Line2D([], [], color=DURUM_RENK["OK"], lw=3, label="OK"),
               Line2D([], [], color=DURUM_RENK["NOT_INITIALIZED"], lw=3,
                      label="init bekliyor"),
               Line2D([], [], color=DURUM_RENK["LOST"], lw=3, label="kayıp"),
               Line2D([], [], color=C["echo"], lw=1.4, label="doku (log10)")]
        ax.legend(handles=leg, fontsize=8, ncol=2, loc="upper right")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--frames-dir", required=True)
    ap.add_argument("--start", type=int, default=0,
                    help="mock --start ile aynı (fid → GT kare no kayması)")
    a = ap.parse_args()
    p = Panel(a)
    anim = FuncAnimation(p.fig, p.ciz, interval=500, cache_frame_data=False)
    plt.show()


if __name__ == "__main__":
    main()
