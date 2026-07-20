#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alignment.py — SLAM(ölçeksiz) → referans(metre) benzerlik dönüşümü (FAZ 8.3.4)

Umeyama kapalı-form çözümü, salt numpy SVD (scipy YOK).
    y ≈ s · R · x + t

Dejenerasyon koruması (MASTER_PROMPT):
  Yörünge düz çizgiye yakınsa (merkezlenmiş SLAM noktalarının 2. tekil değeri,
  1.'ye oranla küçükse) tam 3B dönme belirsizleşir. Bu durumda:
    - z ekseni dünya-dikey varsayılır,
    - x-y düzleminde 2B dönme+ölçek (gerekirse yansımalı) çözülür,
    - z için ayrı 1B ölçek+öteleme (en küçük kareler) çözülür.

Kullanım:
    tf = solve_alignment(slam_pts, ref_pts)      # her ikisi Nx3
    y_hat = tf.apply(x)                          # x: (3,) veya (N,3)
"""

import numpy as np


class Transform:
    """Benzerlik (ya da dejenere modda blok) dönüşümü kabı."""

    def __init__(self, mode, s=1.0, R=None, t=None,
                 s2d=1.0, R2d=None, t2d=None, sz=1.0, tz=0.0, n_pairs=0,
                 rms=float("nan")):
        self.mode = mode          # "sim3" | "planar" | "identity"
        self.s = s
        self.R = R if R is not None else np.eye(3)
        self.t = t if t is not None else np.zeros(3)
        self.s2d = s2d
        self.R2d = R2d if R2d is not None else np.eye(2)
        self.t2d = t2d if t2d is not None else np.zeros(2)
        self.sz = sz
        self.tz = tz
        self.n_pairs = n_pairs
        self.rms = rms            # eğitim çiftleri üzerindeki artık RMS (m)

    def apply(self, x):
        x = np.asarray(x, dtype=float)
        single = (x.ndim == 1)
        pts = x.reshape(-1, 3)
        if self.mode == "sim3":
            out = (self.s * (self.R @ pts.T)).T + self.t
        elif self.mode == "planar":
            xy = (self.s2d * (self.R2d @ pts[:, :2].T)).T + self.t2d
            z = self.sz * pts[:, 2] + self.tz
            out = np.column_stack([xy, z])
        else:  # identity — hiç çözüm yoksa asla kullanma; sigorta katmanı devrede olmalı
            out = pts.copy()
        return out[0] if single else out

    def __repr__(self):
        return (f"Transform(mode={self.mode}, n={self.n_pairs}, "
                f"rms={self.rms:.3f} m)")


def _umeyama_sim3(X, Y):
    """Tam 3B Umeyama: Y ≈ s·R·X + t.  X,Y: Nx3 (N≥3)."""
    mu_x = X.mean(axis=0)
    mu_y = Y.mean(axis=0)
    Xc = X - mu_x
    Yc = Y - mu_y
    n = X.shape[0]

    Sigma = (Yc.T @ Xc) / n                 # 3x3 çapraz-kovaryans
    U, D, Vt = np.linalg.svd(Sigma)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1.0
    R = U @ S @ Vt

    var_x = (Xc ** 2).sum() / n
    if var_x < 1e-12:
        raise ValueError("SLAM noktalari tek noktaya cokmus (var=0)")
    s = float(np.trace(np.diag(D) @ S) / var_x)
    t = mu_y - s * (R @ mu_x)
    return s, R, t


def _umeyama_2d(X2, Y2, allow_reflection=True):
    """2B Procrustes+ölçek: Y2 ≈ s·R·X2 + t. Yansıma opsiyonel (daha iyi ise)."""
    mu_x = X2.mean(axis=0)
    mu_y = Y2.mean(axis=0)
    Xc = X2 - mu_x
    Yc = Y2 - mu_y
    n = X2.shape[0]

    Sigma = (Yc.T @ Xc) / n
    U, D, Vt = np.linalg.svd(Sigma)
    var_x = (Xc ** 2).sum() / n
    if var_x < 1e-12:
        raise ValueError("SLAM xy noktalari cokmus")

    def build(S):
        R = U @ S @ Vt
        s = float(np.trace(np.diag(D) @ S) / var_x)
        t = mu_y - s * (R @ mu_x)
        res = Yc - s * (Xc @ R.T)
        rms = float(np.sqrt((res ** 2).sum(axis=1).mean()))
        return s, R, t, rms

    # Uygun (det=+1) çözüm
    S_proper = np.eye(2)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S_proper[1, 1] = -1.0
    best = build(S_proper)

    if allow_reflection:
        # Yansımalı aday (monokülerde z işaret belirsizliği xy'ye yansıma
        # olarak düşebilir; artığı küçükse onu seç)
        S_refl = np.eye(2)
        if np.linalg.det(U) * np.linalg.det(Vt) >= 0:
            S_refl[1, 1] = -1.0
        cand = build(S_refl)
        if cand[3] < best[3]:
            best = cand

    return best  # s, R, t, rms


def solve_alignment(slam_pts, ref_pts, min_pairs=30, degenerate_ratio=0.05,
                    plane_ratio=0.05):
    """
    slam_pts, ref_pts: Nx3 eşleşmiş nokta çiftleri (aynı sırada).
    min_pairs: bundan az çiftle çözüm YOK (None döner).
    degenerate_ratio: sigma2/sigma1 bu değerin altındaysa "düz çizgi" kabul et.
    plane_ratio: sigma3/sigma1 bu değerin altındaysa "düz düzlem" kabul et —
      sabit irtifa uçuşunda tam sim3'ün z işareti gözlemlenemez (düzlemi
      kendine eşleyen 180° dönme z'yi ters çevirir, artık aynı kalır; O2
      canlı koşusunda z aynası böyle oluştu). Bu durumda da planar yol
      kullanılır: xy 2B + z ayrı, işaret nadir önseliyle pozitif.
    Döndürür: Transform ya da None.
    """
    X = np.asarray(slam_pts, dtype=float).reshape(-1, 3)
    Y = np.asarray(ref_pts, dtype=float).reshape(-1, 3)
    if X.shape[0] != Y.shape[0]:
        raise ValueError("cift sayilari esit degil")
    n = X.shape[0]
    if n < min_pairs:
        return None

    # Dejenerasyon tespiti: merkezlenmiş SLAM bulutunun tekil değerleri
    Xc = X - X.mean(axis=0)
    sv = np.linalg.svd(Xc, compute_uv=False)   # sigma1 >= sigma2 >= sigma3
    line_degenerate = (sv[0] < 1e-9) or (sv[1] / sv[0] < degenerate_ratio)
    plane_degenerate = (sv[0] < 1e-9) or (sv[2] / sv[0] < plane_ratio)

    if not line_degenerate and not plane_degenerate:
        s, R, t = _umeyama_sim3(X, Y)
        res = Y - (s * (X @ R.T) + t)
        rms = float(np.sqrt((res ** 2).sum(axis=1).mean()))
        return Transform("sim3", s=s, R=R, t=t, n_pairs=n, rms=rms)

    # ── Dejenere yol: xy 2B + z 1B ──
    s2d, R2d, t2d, rms_xy = _umeyama_2d(X[:, :2], Y[:, :2])

    # z: 1B en küçük kareler  Yz ≈ sz·Xz + tz
    # Anlamlı z hareketi yoksa lstsq gürültüye oturur (sz işareti/büyüklüğü
    # çöp olur, kör bölgede z tahminini patlatır) → ölçek xy'den, işaret
    # pozitif: nadir kamerada SLAM +z ≈ yere doğru, GT de aşağı-pozitif
    # (NED; O2'de yere yaklaşırken GT z artıyor).
    Xz = X[:, 2]
    Yz = Y[:, 2]
    if float(np.std(Xz)) < 0.02 * max(float(sv[0]), 1e-12):
        sz = s2d
        tz = float(Yz.mean() - sz * Xz.mean())
    else:
        A = np.column_stack([Xz, np.ones_like(Xz)])
        coef, *_ = np.linalg.lstsq(A, Yz, rcond=None)
        sz, tz = float(coef[0]), float(coef[1])

    res_z = Yz - (sz * Xz + tz)
    rms = float(np.sqrt((rms_xy ** 2) + (res_z ** 2).mean()))
    return Transform("planar", s2d=s2d, R2d=R2d, t2d=t2d, sz=sz, tz=tz,
                     n_pairs=n, rms=rms)


# ─── Hızlı öz-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    rng = np.random.default_rng(42)

    def rand_rot():
        A = rng.normal(size=(3, 3))
        Q, _ = np.linalg.qr(A)
        if np.linalg.det(Q) < 0:
            Q[:, 0] *= -1
        return Q

    # Test 1: genel 3B benzerlik geri kazanımı
    X = rng.normal(size=(200, 3)) * [5, 3, 1.5]
    R_true = rand_rot()
    s_true = 3.7
    t_true = np.array([10.0, -4.0, 2.5])
    Y = s_true * (X @ R_true.T) + t_true + rng.normal(scale=1e-3, size=X.shape)
    tf = solve_alignment(X, Y)
    err = np.abs(tf.apply(X) - Y).max()
    assert tf.mode == "sim3", tf.mode
    assert abs(tf.s - s_true) < 1e-3, tf.s
    assert err < 5e-3, err
    print(f"T1 sim3 OK   (s={tf.s:.4f}, maks hata={err:.2e} m, rms={tf.rms:.2e})")

    # Test 2: düz çizgi yörünge (dejenere) — z'de GERÇEK hareket var,
    # lstsq işareti veriden çözmeli (ters işaret dahil)
    tdir = np.array([1.0, 0.4, 0.0]) / np.linalg.norm([1.0, 0.4, 0.0])
    line = np.outer(np.linspace(0, 10, 120), tdir)
    line[:, 2] = np.linspace(0, 2.5, 120) + rng.normal(scale=0.01, size=120)
    ang = 0.6
    R2 = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    Yl = np.empty_like(line)
    Yl[:, :2] = 2.2 * (line[:, :2] @ R2.T) + [3.0, -1.0]
    Yl[:, 2] = -2.2 * line[:, 2] + 50.0                      # z ters işaretli!
    tf2 = solve_alignment(line, Yl, degenerate_ratio=0.05)
    err2 = np.abs(tf2.apply(line) - Yl).max()
    assert tf2.mode == "planar", tf2.mode
    assert err2 < 0.05, err2
    print(f"T2 planar OK (s2d={tf2.s2d:.4f}, sz={tf2.sz:.4f}, maks hata={err2:.2e} m)")

    # Test 3: yetersiz çift → None
    assert solve_alignment(X[:10], Y[:10]) is None
    print("T3 min_pairs OK (n<30 -> None)")

    # Test 4: xy'de yansıma gereken durum (z ekseni ters SLAM)
    Xm = X.copy()
    Ym = Y.copy()
    Xm[:, 2] *= -1          # SLAM z'yi ters çevir → xy hizalaması yansıma ister
    tfm = solve_alignment(Xm[:, :], Ym, degenerate_ratio=0.99)  # zorla planar
    errm = np.abs(tfm.apply(Xm) - Ym).max()
    print(f"T4 yansima OK (mode={tfm.mode}, maks hata={errm:.2e} m)"
          if errm < 0.6 else f"T4 UYARI: hata={errm:.3f} m (planar yaklasim siniri)")

    # Test 5: düz DÜZLEM yörünge (sabit irtifa) + z'yi aynalayan uygun dönme —
    # eski kod sim3 ile aynayı "doğru" diye kabul ederdi; yeni kod planar'a
    # düşüp z işaretini pozitif tutmalı (O2 canlı z-aynası vakası).
    th = np.linspace(0, 2.5, 300)
    Xp = np.column_stack([5 * np.cos(th), 3 * np.sin(th),
                          rng.normal(scale=0.005, size=300)])
    ang5 = 0.9
    Rz = np.array([[np.cos(ang5), -np.sin(ang5), 0],
                   [np.sin(ang5), np.cos(ang5), 0], [0, 0, 1.0]])
    Rflip = np.diag([1.0, -1.0, -1.0])          # x etrafında 180° (uygun dönme)
    Yp = 2.0 * (Xp @ (Rz @ Rflip).T) + np.array([7.0, -3.0, 55.0])
    tf5 = solve_alignment(Xp, Yp)
    assert tf5.mode == "planar", f"plane dejenerasyonu kacti: {tf5.mode}"
    assert tf5.sz > 0, f"z isareti negatif kaldi: sz={tf5.sz}"
    exy5 = np.abs(tf5.apply(Xp)[:, :2] - Yp[:, :2]).max()
    assert exy5 < 0.1, exy5
    print(f"T5 duzlem-aynasi OK (mode={tf5.mode}, sz={tf5.sz:.3f}>0, "
          f"xy maks hata={exy5:.2e} m)")

    print("alignment.py oz-testleri tamam.")
