#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resmi_mock.py — TEKNOFEST değerlendirme sunucusunun YEREL taklidi.

Resmî istemcinin (TAKIM_BAGLANTI_ARAYUZU/main.py) kullandığı uç noktaların
birebir taklidi: auth/ progress/ frames/ translation/ prediction/ reference/
+ media/ dosya servisi. Amaç: yarışma komutunun kendisini (python3 main.py)
taze bir oturumla uçtan uca prova etmek.

Kullanım:
  python3 resmi_mock.py --limit 600 --drop 450-599 --port 5580
Sonra istemci tarafında:
  EVALUATION_SERVER_URL="http://127.0.0.1:5580/" python3 main.py

Gönderilen her tahmin mock_gonderimler.jsonl'e yazılır (analiz için).
"""
import argparse
import csv
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

BURADA = os.path.dirname(os.path.abspath(__file__))


def yukle_gt(yol):
    gt = {}
    with open(yol) as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            gt[int(row[0])] = (float(row[1]), float(row[2]), float(row[3]))
    return gt


def aralik_coz(s):
    kapsam = set()
    if s:
        for parca in s.split(","):
            a, b = parca.split("-")
            kapsam.update(range(int(a), int(b) + 1))
    return kapsam


class Durum:
    def __init__(self, a):
        self.a = a
        self.idx = 0
        self.kilit = threading.Lock()
        self.gt = yukle_gt(a.gt)
        self.drop = aralik_coz(a.drop)
        self.out = open(a.out, "w")
        # Referans görüntüleri: pencere içi karelerden merkez kırpma üret
        self.ref_dir = os.path.join(BURADA, "mock_referanslar")
        os.makedirs(self.ref_dir, exist_ok=True)
        self.refs = []
        for i, (kaynak_kare, w0, w1) in enumerate(
                [(110, 90, 130), (230, 200, 260)], start=1):
            img = cv2.imread(os.path.join(a.frames_dir,
                                          f"frame_{kaynak_kare:06d}.webp"))
            h, w = img.shape[:2]
            cy, cx, yr = h // 2, w // 2, 260
            kirp = img[cy - yr:cy + yr, cx - yr:cx + yr]
            ryol = os.path.join(self.ref_dir, f"ref_{i}.webp")
            cv2.imwrite(ryol, kirp)
            self.refs.append({
                "url": f"http://127.0.0.1:{a.port}/reference/{i}/",
                "session": a.session,
                "image_url": f"/{a.session}/references/ref_{i}.webp",
                "frame_start_image_url": f"/{a.session}/frame_{w0:06d}.webp",
                "frame_end_image_url": f"/{a.session}/frame_{w1:06d}.webp",
                "order": i,
            })
        print(f"[mock] {a.limit} kare, kesinti={sorted(self.drop)[:1]}..regex, "
              f"{len(self.refs)} referans, port {a.port}")


D = None  # global Durum


class Istekci(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # sessiz
        pass

    def _json(self, obj, code=200):
        veri = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        govde = self.rfile.read(n) if n else b""
        if self.path.startswith("/auth"):
            return self._json({"token": "yerel-prova-token"})
        if self.path.startswith("/prediction"):
            try:
                p = json.loads(govde)
            except ValueError:
                return self._json({"detail": "bozuk json"}, 400)
            with D.kilit:
                kayit = {"idx": D.idx, "payload": p}
                D.out.write(json.dumps(kayit) + "\n")
                D.out.flush()
                D.idx += 1
                kalan = D.a.limit - D.idx
            if D.idx % 50 == 0 or kalan == 0:
                print(f"[mock] tahmin {D.idx}/{D.a.limit}")
            return self._json({"detail": "kayit alindi"}, 201)
        return self._json({"detail": "bilinmeyen"}, 404)

    def do_GET(self):
        a = D.a
        if self.path.startswith("/progress"):
            with D.kilit:
                return self._json({
                    "frame_index": D.idx, "total_frames": a.limit,
                    "completed": D.idx >= a.limit, "session_name": a.session})
        if self.path.startswith("/frames"):
            with D.kilit:
                i = D.idx
            if i >= a.limit:
                return self._json([])
            return self._json([{
                "url": f"http://127.0.0.1:{a.port}/frames/{i}/",
                "image_url": f"/{a.session}/frame_{i:06d}.webp",
                "video_name": a.session, "order": i}])
        if self.path.startswith("/translation"):
            with D.kilit:
                i = D.idx
            if i >= a.limit:
                return self._json([])
            saglik = "0" if i in D.drop else "1"
            x, y, z = D.gt.get(i, (None, None, None))
            if saglik == "0":
                x = y = z = None
            return self._json([{
                "image_url": f"/{a.session}/frame_{i:06d}.webp",
                "translation_x": x, "translation_y": y, "translation_z": z,
                "health_status": saglik}])
        if self.path.startswith("/reference"):
            return self._json(D.refs)
        if self.path.startswith("/media/"):
            yol = self.path[len("/media/"):]
            if yol.startswith(a.session + "/references/"):
                dosya = os.path.join(D.ref_dir, os.path.basename(yol))
            elif yol.startswith(a.session + "/"):
                dosya = os.path.join(a.frames_dir, os.path.basename(yol))
            else:
                dosya = None
            if dosya and os.path.exists(dosya):
                with open(dosya, "rb") as f:
                    veri = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/webp")
                self.send_header("Content-Length", str(len(veri)))
                self.end_headers()
                self.wfile.write(veri)
                return
            return self._json({"detail": "dosya yok"}, 404)
        return self._json({"detail": "bilinmeyen"}, 404)


def main():
    global D
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames-dir",
                    default=os.path.join(BURADA, "prova2025/frames_o2"))
    ap.add_argument("--gt",
                    default=os.path.join(BURADA, "prova2025/oturum2_gt.csv"))
    ap.add_argument("--limit", type=int, default=600)
    ap.add_argument("--drop", default="450-599")
    ap.add_argument("--port", type=int, default=5580)
    ap.add_argument("--session", default="YEREL_PROVA")
    ap.add_argument("--out",
                    default=os.path.join(BURADA, "mock_gonderimler.jsonl"))
    a = ap.parse_args()
    D = Durum(a)
    sunucu = ThreadingHTTPServer(("127.0.0.1", a.port), Istekci)
    print(f"[mock] hazir: http://127.0.0.1:{a.port}/  (durdurmak: Ctrl+C)")
    sunucu.serve_forever()


if __name__ == "__main__":
    main()
