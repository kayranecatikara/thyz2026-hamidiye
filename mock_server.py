#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mock_server.py — Yarışma sunucusu taklidi (FAZ 8.3)

Resmi TAKIM_BAGLANTI_ARAYUZU gelene dek aynı akışı simüle eder:
her karede görüntü + referans pozisyon (x,y,z) + sağlık bayrağı gönderir,
istemciden tahmin (x,y,z) bekler.

Protokol (newline-delimited JSON, TCP):
  S→C: {"type":"frame","frame_id":i,"saglik":0|1,
        "ref":{"x":..,"y":..,"z":..} (yalniz saglik=1'de gercek; saglik=0'da null),
        "img_b64":"...","img_ext":"png"}
  C→S: {"type":"pred","frame_id":i,"x":..,"y":..,"z":..}
  S→C: {"type":"end"}

Kullanım örneği:
  python mock_server.py --frames-dir frames/ --gt gt.csv \
      --health-drop 600-900,1500-1800 --port 5555 --limit 2250
GT biçimi: her satır "frame_id,x,y,z" (başlık opsiyonel; boşluk da olur).
--paced verilirse kareler gerçek zamanda (1/fps aralıkla) gönderilir; verilmezse
istemci yanıtı gelince sıradaki kare gönderilir (deterministik prova).
"""

import argparse
import base64
import json
import os
import socket
import sys
import time


def parse_ranges(spec):
    """'600-900,1500-1800' → [(600,900),(1500,1800)]  (uçlar dahil)"""
    out = []
    if not spec:
        return out
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        a, b = part.split("-")
        out.append((int(a), int(b)))
    return out


def in_ranges(i, ranges):
    return any(a <= i <= b for a, b in ranges)


def load_gt(path):
    gt = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p for p in line.replace(",", " ").split() if p]
            try:
                fid = int(round(float(parts[0])))
                gt[fid] = (float(parts[1]), float(parts[2]), float(parts[3]))
            except (ValueError, IndexError):
                continue  # başlık satırı vb.
    return gt


def list_frames(frames_dir):
    exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    files = [f for f in os.listdir(frames_dir)
             if f.lower().endswith(exts)]
    def key(f):
        stem = os.path.splitext(f)[0]
        return (0, int(stem)) if stem.isdigit() else (1, stem)
    files.sort(key=key)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames-dir", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--fps", type=float, default=7.5)
    ap.add_argument("--health-drop", default="",
                    help="saglik=0 araliklari: '600-900,1500-1800' (frame_id, uclar dahil)")
    ap.add_argument("--limit", type=int, default=0, help="en fazla N kare (0=hepsi)")
    ap.add_argument("--start", type=int, default=0, help="ilk N kareyi atla")
    ap.add_argument("--paced", action="store_true",
                    help="kareleri 1/fps gercek-zaman aralikla gonder (yoksa lockstep)")
    ap.add_argument("--out", default="mock_server_log.csv",
                    help="sunucu tarafi kayit (frame_id,saglik,ref_x..,pred_x..)")
    args = ap.parse_args()

    ranges = parse_ranges(args.health_drop)
    gt = load_gt(args.gt)
    files = list_frames(args.frames_dir)[args.start:]
    if args.limit > 0:
        files = files[:args.limit]
    if not files:
        sys.exit("frames-dir bos")
    print(f"[mock] {len(files)} kare, {len(gt)} GT kaydi, "
          f"saglik-dusurme={ranges or 'yok'}, port={args.port}")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", args.port))
    srv.listen(1)
    print("[mock] istemci bekleniyor...")
    conn, addr = srv.accept()
    print(f"[mock] istemci geldi: {addr}")
    rfile = conn.makefile("r", encoding="utf-8")

    period = 1.0 / args.fps if args.fps > 0 else 0.0
    t_next = time.monotonic()

    with open(args.out, "w", encoding="utf-8") as log:
        log.write("frame_id,saglik,ref_x,ref_y,ref_z,pred_x,pred_y,pred_z,yanit_suresi_s\n")
        for seq, fname in enumerate(files):
            fid = seq  # kare kimliği: sıra numarası (dosya adından bağımsız, deterministik)
            saglik = 0 if in_ranges(fid, ranges) else 1
            ref = gt.get(fid)
            if ref is None:
                ref = (float("nan"),) * 3

            with open(os.path.join(args.frames_dir, fname), "rb") as f:
                img = f.read()
            msg = {
                "type": "frame",
                "frame_id": fid,
                "saglik": saglik,
                # Gerçek sunucu gibi: sağlık=0 iken referans YOK
                "ref": ({"x": ref[0], "y": ref[1], "z": ref[2]}
                        if saglik == 1 else None),
                "img_b64": base64.b64encode(img).decode("ascii"),
                "img_ext": os.path.splitext(fname)[1].lstrip("."),
            }

            if args.paced:
                now = time.monotonic()
                if now < t_next:
                    time.sleep(t_next - now)
                t_next += period

            t0 = time.monotonic()
            conn.sendall((json.dumps(msg) + "\n").encode("utf-8"))

            line = rfile.readline()
            if not line:
                print("[mock] istemci koptu!", file=sys.stderr)
                break
            t1 = time.monotonic()
            try:
                pred = json.loads(line)
                px, py, pz = pred["x"], pred["y"], pred["z"]
            except (json.JSONDecodeError, KeyError):
                print(f"[mock] BOZUK yanit (frame {fid}): {line[:80]}",
                      file=sys.stderr)
                px = py = pz = float("nan")

            log.write(f"{fid},{saglik},{ref[0]:.6f},{ref[1]:.6f},{ref[2]:.6f},"
                      f"{px:.6f},{py:.6f},{pz:.6f},{t1-t0:.4f}\n")
            if seq % 100 == 0:
                print(f"[mock] kare {fid} saglik={saglik} "
                      f"yanit={t1-t0:.3f}s")

        conn.sendall((json.dumps({"type": "end"}) + "\n").encode("utf-8"))
        time.sleep(0.3)

    conn.close()
    srv.close()
    print(f"[mock] bitti. kayit: {args.out}")


if __name__ == "__main__":
    main()
