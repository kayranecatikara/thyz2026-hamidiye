#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gorev2_engine.py — Görev 2 çekirdek motoru (FAZ 8.3)

SLAM sürücüsünü (mono_folder_watch) yönetir; kare besleme, poz okuma, Umeyama
hizalama (kayan pencere + çapa düzeltmesi), sabit-hız ölü hesabı ve loglamayı
tek sınıfta toplar. İKİ tüketicisi var:
  - bridge.py            → mock_server ile prova
  - object_detection_model.py (resmi TAKIM_BAGLANTI_ARAYUZU) → yarışma

Sözleşme:
    eng = Gorev2Engine(settings=".../teknofest.yaml", run_dir="run")
    eng.start()                              # SLAM'i başlatır, READY bekler
    xyz, kaynak = eng.process_frame(fid, img, ref_xyz, health)
        img     : BGR numpy dizisi YA DA görüntü dosya yolu (webp/png/jpg)
        ref_xyz : sağlık=1'de sunucu referansı (3,) — sağlık=0/None'da None
        health  : 1, 0 ya da None (None → kare beslenir, çıktı üretilmez: None döner)
        kaynak  : "echo" | "slam" | "deadreckon"
    eng.shutdown()
Asla NaN döndürmez (health 0/1 için).
"""

import atexit
import collections
import os
import subprocess
import threading
import time

import numpy as np
import cv2

from alignment import solve_alignment


class PoseReader(threading.Thread):
    """outbox/pose.txt'i tail eder; frame_id → (pos, state); yeni pozda callback."""

    def __init__(self, pose_path):
        super().__init__(daemon=True)
        self.path = pose_path
        self.lock = threading.Lock()
        self.poses = {}
        self.on_pose = None
        self._stop = False

    def run(self):
        while not os.path.exists(self.path) and not self._stop:
            time.sleep(0.02)
        if self._stop:
            return
        f = open(self.path, "r", encoding="utf-8")
        buf = ""
        while not self._stop:
            chunk = f.readline()
            if not chunk:
                time.sleep(0.004)
                continue
            buf += chunk
            if not buf.endswith("\n"):
                continue
            line, buf = buf, ""
            parts = line.split()
            if len(parts) != 9:
                continue
            try:
                fid = int(parts[0])
                pos = np.array([float(parts[1]), float(parts[2]),
                                float(parts[3])], dtype=float)
                state = parts[8]
            except ValueError:
                continue
            with self.lock:
                self.poses[fid] = (pos, state)
            if self.on_pose:
                self.on_pose(fid, pos, state)
        f.close()

    def get(self, fid):
        with self.lock:
            return self.poses.get(fid)

    def stop(self):
        self._stop = True


class Gorev2Engine:
    def __init__(self, settings,
                 slam_root=os.path.expanduser("~/SP_SLAM3"),
                 vocab="Vocabulary/superpoint_voc.dbow3",
                 run_dir="run", width=1280,
                 pose_timeout=1.2, min_pairs=10, window=300,
                 predictions_csv="predictions.csv", spawn=True,
                 keep_frames=False, dr_tau=40.0, viewer=False,
                 blend_tau=0.0):
        self.settings = os.path.abspath(settings)
        self.slam_root = slam_root
        self.vocab = vocab
        self.run_dir = os.path.abspath(run_dir)
        self.width = width
        self.pose_timeout = pose_timeout
        self.min_pairs = min_pairs
        self.window = window
        self.predictions_csv = predictions_csv
        self.spawn = spawn
        self.keep_frames = keep_frames
        self.dr_tau = float(dr_tau)   # ölü hesap hız sönüm sabiti (kare)
        self.pair_age_frames = None   # çift tazelik filtresi (None=kapalı;
                                      # planar hizalamada eski çiftler faydalı)
        # Ufka bağlı SLAM->DR harmanı: sim3 dönemi yaması (o zaman 990 karede
        # 150 m drift vardı). Planar hizalama driftin kökünü çözdüğü için
        # VARSAYILAN KAPALI (0) — v7'de harman k2'yi 11-15 m'den 44-73 m'ye
        # KÖTÜLEŞTİRDİ. w=exp(-d/blend_tau); acil geri dönüş bayrağı olarak
        # duruyor.
        self.blend_tau = blend_tau
        self.viewer = viewer          # Pangolin (demo/hata ayıklama; yarışmada KAPALI)

        self.inbox = os.path.join(self.run_dir, "inbox")
        self.outbox = os.path.join(self.run_dir, "outbox")
        self.proc = None
        self.reader = None
        self.csvf = None

        self.pair_lock = threading.Lock()
        self.pairs = collections.deque(maxlen=window)
        self.pending_refs = {}
        self.transform = None
        self.anchor = {"fid": -1, "slam": None, "ref": None}
        self.sent_hist = collections.deque(maxlen=5)   # (fid, xyz) güvenilir
        # Harman için donmuş DR temeli: sent_hist'e slam çıktıları da girdiği
        # için canlı DR kesintide SLAM'in kendi uzantısına döner (harman no-op
        # olur). Bu yüzden son sağlıklı karedeki geçmiş burada dondurulur.
        self.dr_snapshot = []
        self.counters = collections.Counter()
        self.slam_states = collections.Counter()
        self._started = False
        self._saw_ok = False      # harita sıfırlaması tespiti için
        self.reset_count = 0

    # ── yaşam döngüsü ────────────────────────────────────────────────────────
    def start(self, ready_timeout=180):
        os.makedirs(self.inbox, exist_ok=True)
        os.makedirs(self.outbox, exist_ok=True)
        for d in (self.inbox, self.outbox):
            for f in os.listdir(d):
                os.remove(os.path.join(d, f))

        if self.spawn:
            binp = os.path.join(self.slam_root,
                                "Examples/Monocular/mono_folder_watch")
            cmd = [binp, self.vocab, self.settings, self.inbox, self.outbox]
            if self.viewer:
                cmd.append("viewer")
            self.proc = subprocess.Popen(
                cmd,
                cwd=self.slam_root,
                stdout=open(os.path.join(self.run_dir, "slam_stdout.log"), "w"),
                stderr=subprocess.STDOUT)
            ready = os.path.join(self.outbox, "READY")
            t0 = time.monotonic()
            while not os.path.exists(ready):
                if self.proc.poll() is not None:
                    raise RuntimeError(
                        f"SLAM erken oldu — log: {self.run_dir}/slam_stdout.log")
                if time.monotonic() - t0 > ready_timeout:
                    raise RuntimeError("SLAM READY zaman asimi")
                time.sleep(0.2)

        self.reader = PoseReader(os.path.join(self.outbox, "pose.txt"))
        self.reader.on_pose = self._on_pose
        self.reader.start()

        self.csvf = open(self.predictions_csv, "w", encoding="utf-8")
        self.csvf.write("frame_id,x,y,z,saglik,kaynak,islem_suresi_s\n")
        self._started = True
        atexit.register(self.shutdown)

    def shutdown(self):
        if not self._started:
            return
        self._started = False
        try:
            with open(os.path.join(self.inbox, "STOP"), "w") as f:
                f.write("1\n")
        except OSError:
            pass
        if self.csvf:
            self.csvf.close()
            self.csvf = None
        if self.proc is not None:
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
        if self.reader:
            self.reader.stop()

    # ── iç mantık ────────────────────────────────────────────────────────────
    def _on_pose(self, fid, pos, state):
        # SLAM bu kareyi tüketti → disk hijyeni: PNG'yi sil (4K oturumlar GB'larca
        # birikiyor; /tmp-dolu vakası SETUP_LOG'da)
        if not self.keep_frames:
            try:
                os.unlink(os.path.join(self.inbox, f"{fid}.png"))
            except OSError:
                pass
        if state != "OK":
            # HARİTA SIFIRLAMASI: OK görmüş sistem NOT_INITIALIZED'a döndüyse
            # ORB-SLAM3 Atlas yeni harita açtı → eski haritanın hizalaması,
            # çiftleri ve çapası YENİ haritada GEÇERSİZ. Hepsini temizle;
            # sağlıklı kareler yeni haritada hizalamayı yeniden kurar.
            if state == "NOT_INITIALIZED" and self._saw_ok:
                with self.pair_lock:
                    self.pairs.clear()
                    self.transform = None
                    self.anchor = {"fid": -1, "slam": None, "ref": None}
                self._saw_ok = False
                self.reset_count += 1
            self.pending_refs.pop(fid, None)
            return
        self._saw_ok = True
        ref = self.pending_refs.pop(fid, None)
        if ref is None:
            return
        with self.pair_lock:
            self.pairs.append((fid, pos.copy(), ref.copy()))
            if fid > self.anchor["fid"]:
                self.anchor["fid"] = fid
                self.anchor["slam"] = pos.copy()
                self.anchor["ref"] = ref.copy()
            # Çift tazelik filtresi KALDIRILDI: "bayat çift zehirlenmesi"
            # (O2v3) sim3'ün ayna geometrisinin belirtisiymiş. Planar
            # hizalamada tüm geçmiş çiftler yardımcı — v7 kayıtlarıyla ölçüm:
            # patlama-sonrası k2, yalnız-taze 60 çiftle O4 74.9 m; tüm
            # geçmişle 4.5 m. pair_age_frames=None => filtre kapalı.
            if self.pair_age_frames is None:
                taze = [(s, r) for (_, s, r) in self.pairs]
            else:
                taze = [(s, r) for (f, s, r) in self.pairs
                        if fid - f <= self.pair_age_frames]
            if len(taze) >= self.min_pairs:
                X = np.array([t[0] for t in taze])
                Y = np.array([t[1] for t in taze])
                try:
                    # plane_ratio=1.0 => HER ZAMAN planar (xy 2B yansımalı +
                    # z 1B). Tam sim3 burada yapısal olarak yanlış: SLAM ile
                    # GT çerçevesi arasında el-yönü uyumsuzluğu var (yansıma
                    # gerekir); det=+1 kısıtlı Umeyama xy'yi eşleyip z'yi ters
                    # çeviriyor (O2/O3/O4'te R·ẑ→−z ölçüldü; planar kör bölge
                    # hatasını O3 48→7, O4 21→7 m'ye indirdi).
                    tf = solve_alignment(X, Y, min_pairs=self.min_pairs,
                                         plane_ratio=1.0)
                    if tf is not None:
                        self.transform = tf
                except ValueError:
                    pass

    def _feed_frame(self, fid, img):
        """Kareyi küçültüp inbox'a atomik yazar. img: ndarray ya da dosya yolu."""
        if isinstance(img, str):
            img = cv2.imread(img, cv2.IMREAD_UNCHANGED)
        if img is None or img.size == 0:
            return False
        if img.shape[1] > self.width:
            scale = self.width / img.shape[1]
            img = cv2.resize(img, (self.width, int(round(img.shape[0] * scale))),
                             interpolation=cv2.INTER_AREA)
        # PNG: kayıpsız — JPEG q95 bile SuperPoint'i zayıflatıp izleme kaybı
        # tetikleyebiliyor (SETUP_LOG: paced JPEG koşusunda 10 harita sıfırlaması).
        path = os.path.join(self.inbox, f"{fid}.png")
        tmp = os.path.join(self.inbox, f".tmp_{fid}.png")
        cv2.imwrite(tmp, img)
        os.replace(tmp, path)
        return True

    def _dead_reckon(self, fid, hist=None):
        """Sönümlü sabit-hız: p(Δ) = p1 + v·τ·(1 − e^(−Δ/τ)).
        Küçük Δ'da klasik sabit-hız; büyük Δ'da sınırlı (v·τ) — uzun kesintide
        sınırsız savrulmayı önler (Denklem 2 mutlak hata topluyor)."""
        if hist is None:
            hist = self.sent_hist
        if len(hist) >= 2:
            f0, p0 = hist[0]
            f1, p1 = hist[-1]
            if f1 > f0:
                v = (p1 - p0) / (f1 - f0)
                delta = float(fid - f1)
                tau = max(self.dr_tau, 1e-6)
                return p1 + v * tau * (1.0 - np.exp(-delta / tau))
        if hist:
            return hist[-1][1].copy()
        return np.zeros(3)

    # ── ana giriş ────────────────────────────────────────────────────────────
    def process_frame(self, fid, img, ref_xyz, health):
        """(xyz, kaynak) döndürür; health None ise (None, 'none')."""
        if not self._started:
            self.start()
        t0 = time.monotonic()
        fed = self._feed_frame(fid, img)          # SLAM daima beslenir

        if health is None:
            # Görev 2 çıktısı istenmiyor; kare yine de SLAM'e gitti
            return None, "none"

        if int(health) == 1 and ref_xyz is not None and \
                np.all(np.isfinite(np.asarray(ref_xyz, dtype=float))):
            out = np.asarray(ref_xyz, dtype=float)
            kaynak = "echo"
            if fed:
                self.pending_refs[fid] = out.copy()
        else:
            # beslenmemiş karenin pozu asla gelmez — boşuna bekleme
            deadline = t0 + (self.pose_timeout if fed else 0.05)
            got = None
            while time.monotonic() < deadline:
                got = self.reader.get(fid)
                if got is not None:
                    break
                time.sleep(0.004)
            tf = self.transform
            if got is not None and got[1] == "OK" and tf is not None:
                out = tf.apply(got[0])
                with self.pair_lock:
                    a_slam, a_ref = self.anchor["slam"], self.anchor["ref"]
                    a_fid = self.anchor["fid"]
                if a_slam is not None:
                    out = out + (a_ref - tf.apply(a_slam))
                if self.blend_tau and a_fid >= 0 and fid > a_fid \
                        and len(self.dr_snapshot) >= 2:
                    w = float(np.exp(-(fid - a_fid) / self.blend_tau))
                    out = w * out + (1.0 - w) * self._dead_reckon(
                        fid, self.dr_snapshot)
                kaynak = "slam"
            else:
                out = self._dead_reckon(fid)
                kaynak = "deadreckon"
            self.slam_states[got[1] if got is not None else "TIMEOUT"] += 1

        if not np.all(np.isfinite(out)):
            out = self._dead_reckon(fid)
            kaynak = "deadreckon"
            if not np.all(np.isfinite(out)):
                out = np.zeros(3)

        if kaynak in ("echo", "slam"):
            self.sent_hist.append((fid, np.asarray(out, dtype=float)))
        if kaynak == "echo":
            self.dr_snapshot = list(self.sent_hist)
        self.counters[kaynak] += 1
        dt = time.monotonic() - t0
        if self.csvf:
            self.csvf.write(f"{fid},{out[0]:.6f},{out[1]:.6f},{out[2]:.6f},"
                            f"{int(health)},{kaynak},{dt:.4f}\n")
            self.csvf.flush()
        return out, kaynak

    def stats(self):
        tf = self.transform
        return {"kaynak": dict(self.counters),
                "slam_states": dict(self.slam_states),
                "pairs": len(self.pairs),
                "transform": (tf.mode if tf else None),
                "transform_rms": (tf.rms if tf else None),
                "resets": self.reset_count}
