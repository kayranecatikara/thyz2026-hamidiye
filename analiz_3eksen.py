#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analiz_3eksen.py — 1 dk kalibrasyon + 4 dk kör SLAM analizi için canlı panel.

Üç alt grafik (x/y/z zaman serisi): gerçek konum vs SLAM tahmini, video
işlenirken gerçek zamanlı çizilir. 0..kalibrasyon-sonu arası gölgeli
"kalibrasyon bölgesi"dir; sonrasında sistem gerçek veriyi hiç görmez,
gerçek eğri yalnız değerlendirme için çizilir.

Kullanım:
  python analiz_3eksen.py --gt prova2025/oturum2_gt.csv \
      --pred prova2025/pred_analiz_o2.csv --baslik "Oturum 2" \
      --kaydet analiz_3eksen/oturum2.png
Pred dosyası henüz yoksa bekler; koşuyla aynı anda başlatılabilir.
MPLBACKEND=Agg ile penceresiz koşar (koşu bitene dek bekler, PNG kaydeder).
"""
import argparse
import csv
import os
import time

import numpy as np
import matplotlib
matplotlib.use(os.environ.get("MPLBACKEND", "TkAgg"))
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# dataviz referans paleti (açık mod)
SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
GRID = "#e1e0d9"; AXIS = "#c3c2b7"
C_GT = "#2a78d6"; C_SLAM = "#1baf7a"; C_DR = "#eda100"; C_KALIB = "#f0efe9"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.labelcolor": INK2, "text.color": INK, "font.size": 9.5,
    "legend.frameon": False,
})


class Panel3Eksen:
    def __init__(self, a):
        self.a = a
        self.gt = {}
        for r in csv.DictReader(open(a.gt)):
            self.gt[int(r["frame_id"])] = np.array(
                [float(r["x"]), float(r["y"]), float(r["z"])])
        self.pred_off = 0
        self.rows = []            # (fid, xyz, kaynak)
        self.kaydedildi = False

        self.fig, self.axs = plt.subplots(
            3, 1, sharex=True, figsize=(13.5, 8.0))
        self.fig.canvas.manager.set_window_title(
            f"3 Eksen Analiz — {a.baslik}")
        self.fig.subplots_adjust(left=0.07, right=0.985, top=0.90,
                                 bottom=0.07, hspace=0.16)
        for ax, ad in zip(self.axs, ("x (m)", "y (m)", "z (m)")):
            ax.set_ylabel(ad)
            ax.axvspan(0, a.kalibrasyon_sonu, color=C_KALIB, zorder=0)
            ax.axvline(a.kalibrasyon_sonu, color=MUTED, lw=1.0, ls="--")
            ax.set_xlim(0, a.toplam)
        self.axs[0].text(a.kalibrasyon_sonu / 2, 1.03, "kalibrasyon (1. dk)",
                         transform=self.axs[0].get_xaxis_transform(),
                         ha="center", color=INK2, fontsize=9)
        self.axs[0].text(a.kalibrasyon_sonu + 30, 1.03,
                         "kör bölge — sistem gerçek veriyi görmüyor",
                         transform=self.axs[0].get_xaxis_transform(),
                         ha="left", color=INK2, fontsize=9)
        self.axs[2].set_xlabel("kare (7.5 kare/sn ≈ 5 dk video)")

        self.l_gt, self.l_pr, self.s_dr = [], [], []
        for ax in self.axs:
            # GT kalın, tahmin üstünde ince: sağlıklı blokta değerler birebir
            # aynı olduğundan (yankı) ince yeşil, kalın mavinin içinden gider —
            # gerçek verinin NEREDE var olduğu görünür kalır.
            self.l_gt.append(ax.plot([], [], color=C_GT, lw=4.5,
                                     label="gerçek")[0])
            self.l_pr.append(ax.plot([], [], color=C_SLAM, lw=1.6,
                                     label="SLAM tahmini")[0])
            self.s_dr.append(ax.scatter([], [], s=7, color=C_DR, zorder=3,
                                        label="ölü hesap (poz yok)"))
        self.axs[0].legend(loc="upper right", ncol=3, fontsize=9)

    def oku(self):
        if not os.path.exists(self.a.pred):
            return
        with open(self.a.pred) as f:
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
                                            float(p[3])]), p[5]))

    def ciz(self, _):
        self.oku()
        if not self.rows:
            return
        a = self.a
        fids = np.array([r[0] for r in self.rows])
        xyz = np.array([r[1] for r in self.rows])
        # GT boşluklarında (ör. gerçek yarışma kaydı: kesintide GT yok) çizgiyi
        # KES — yoksa matplotlib kopuk blokları düz çizgiyle köprüler ve sahte
        # "gerçek veri" görüntüsü oluşur. Boşluğa NaN ekleyerek kırıyoruz.
        gt_list_f, gt_list_v = [], []
        onceki = None
        for f in fids:
            if f in self.gt:
                if onceki is not None and f - onceki > 1:
                    gt_list_f.append(onceki + 1)
                    gt_list_v.append([np.nan] * 3)
                gt_list_f.append(f)
                gt_list_v.append(self.gt[f])
                onceki = f
        gt_f = np.array(gt_list_f)
        gt_v = np.array(gt_list_v) if gt_list_v else np.zeros((0, 3))
        dr = np.array([r[0] for r in self.rows if r[2] == "deadreckon"])

        for i, ax in enumerate(self.axs):
            self.l_gt[i].set_data(gt_f, gt_v[:, i])
            self.l_pr[i].set_data(fids, xyz[:, i])
            if len(dr):
                drv = np.array([r[1][i] for r in self.rows
                                if r[2] == "deadreckon"])
                self.s_dr[i].set_offsets(np.c_[dr, drv])
            ax.relim(); ax.autoscale_view(scalex=False)

        # kör bölge metrikleri
        kor = [(f, p) for (f, p, _) in self.rows
               if f >= a.kalibrasyon_sonu and f in self.gt]
        if kor:
            e = np.array([p - self.gt[f] for f, p in kor])
            d2 = float(np.mean(np.linalg.norm(e, axis=1)))
            mae = np.mean(np.abs(e), axis=0)
            m = (f"kör bölge ort. Öklid hata: {d2:.1f} m   "
                 f"eksen MAE  x:{mae[0]:.1f}  y:{mae[1]:.1f}  z:{mae[2]:.1f} m")
        else:
            m = "kalibrasyon sürüyor..."
        self.fig.suptitle(f"{a.baslik} — kare {fids[-1]}/{a.toplam - 1}   |   "
                          f"{m}", fontsize=11, color=INK)

        if len(self.rows) >= a.toplam and not self.kaydedildi:
            self.kaydet()

    def kaydet(self):
        os.makedirs(os.path.dirname(self.a.kaydet) or ".", exist_ok=True)
        self.fig.savefig(self.a.kaydet, dpi=130, facecolor=SURFACE)
        self.kaydedildi = True
        print(f"[panel] grafik kaydedildi: {self.a.kaydet}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--baslik", default="Video Analizi")
    ap.add_argument("--kalibrasyon-sonu", type=int, default=450)
    ap.add_argument("--toplam", type=int, default=2250)
    ap.add_argument("--kaydet", default="analiz_3eksen/analiz.png")
    a = ap.parse_args()

    panel = Panel3Eksen(a)
    if matplotlib.get_backend().lower().startswith("agg"):
        # penceresiz: koşu bitene dek dosyayı izle, sonra kaydet
        while not panel.kaydedildi:
            panel.ciz(0)
            if len(panel.rows) >= a.toplam:
                break
            time.sleep(1.0)
        if not panel.kaydedildi:
            panel.kaydet()
    else:
        anim = FuncAnimation(panel.fig, panel.ciz, interval=500,
                             cache_frame_data=False)
        plt.show()
        if not panel.kaydedildi and panel.rows:
            panel.kaydet()          # erken kapatılsa da eldekini sakla


if __name__ == "__main__":
    main()
