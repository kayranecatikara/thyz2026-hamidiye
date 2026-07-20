#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bridge.py — mock_server ile uçtan uca prova köprüsü (FAZ 8.3/8.5)

Tüm Görev 2 mantığı gorev2_engine.Gorev2Engine içindedir; resmi yarışmada da
AYNI motor (assets/resmi_repo/TAKIM_BAGLANTI_ARAYUZU/src/object_detection_model.py
üzerinden) kullanılır. Bu dosya yalnız mock protokol taşıyıcısıdır.
"""

import argparse
import base64
import json
import os
import socket
import time

import numpy as np
import cv2

from gorev2_engine import Gorev2Engine


class MockLink:
    """mock_server.py'nin newline-JSON protokolü."""

    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port))
        self.rfile = self.sock.makefile("r", encoding="utf-8")

    def recv_frame(self):
        line = self.rfile.readline()
        if not line:
            return None
        msg = json.loads(line)
        if msg.get("type") == "end":
            return None
        buf = np.frombuffer(base64.b64decode(msg["img_b64"]), dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
        ref = msg.get("ref")
        ref_xyz = None
        if ref is not None:
            ref_xyz = np.array([ref["x"], ref["y"], ref["z"]], dtype=float)
            if not np.all(np.isfinite(ref_xyz)):
                ref_xyz = None
        return msg["frame_id"], img, ref_xyz, int(msg["saglik"])

    def send_pred(self, frame_id, xyz):
        out = {"type": "pred", "frame_id": int(frame_id),
               "x": float(xyz[0]), "y": float(xyz[1]), "z": float(xyz[2])}
        self.sock.sendall((json.dumps(out) + "\n").encode("utf-8"))

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="127.0.0.1:5555")
    ap.add_argument("--settings", required=True)
    ap.add_argument("--run-dir", default="run")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--pose-timeout", type=float, default=1.2)
    ap.add_argument("--min-pairs", type=int, default=10)
    ap.add_argument("--window", type=int, default=300)
    ap.add_argument("--out", default="predictions.csv")
    ap.add_argument("--viewer", action="store_true",
                    help="Pangolin görüntüleyici (demo/hata ayıklama)")
    ap.add_argument("--blend-tau", type=float, default=0.0,
                    help="SLAM->DR ufuk harmanı (0=kapalı; sim3 dönemi yaması)")
    args = ap.parse_args()

    eng = Gorev2Engine(settings=args.settings, run_dir=args.run_dir,
                       width=args.width, pose_timeout=args.pose_timeout,
                       min_pairs=args.min_pairs, window=args.window,
                       predictions_csv=args.out, viewer=args.viewer,
                       blend_tau=args.blend_tau)
    print("[bridge] SLAM baslatiliyor (sozluk ~20-60 sn)...")
    t0 = time.monotonic()
    eng.start()
    print(f"[bridge] SLAM hazir ({time.monotonic()-t0:.1f} sn).")

    host, port = args.server.split(":")
    link = MockLink(host, int(port))
    print(f"[bridge] sunucuya baglandi: {args.server}")

    t_start = time.monotonic()
    n = 0
    try:
        while True:
            item = link.recv_frame()
            if item is None:
                break
            fid, img, ref_xyz, saglik = item
            out, kaynak = eng.process_frame(fid, img, ref_xyz, saglik)
            if out is None:               # health None gelmez ama sözleşme gereği
                out = np.zeros(3)
            link.send_pred(fid, out)
            n += 1
            if fid % 100 == 0:
                s = eng.stats()
                print(f"[bridge] kare {fid} saglik={saglik} kaynak={kaynak} "
                      f"cift={s['pairs']} tf={s['transform']}")
    finally:
        link.close()
        eng.shutdown()

    dur = time.monotonic() - t_start
    s = eng.stats()
    print("=" * 60)
    print(f"[bridge] bitti: {n} kare, {dur:.1f} sn "
          f"({dur/max(n,1):.3f} sn/kare uctan uca)")
    print(f"  kaynak: {s['kaynak']}")
    print(f"  saglik=0 SLAM durumlari: {s['slam_states']}")
    print(f"  predictions: {args.out}")


if __name__ == "__main__":
    main()
