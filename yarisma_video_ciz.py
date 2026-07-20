#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yarışma koşusunun kutulu videosu: gönderilen her paketi karesine çizer."""
import csv
import json
import os

import cv2

FR = os.path.expanduser("~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/"
                        "TAKIM_BAGLANTI_ARAYUZU/_images/THYZ_2026_Online_Yarisma")
SENT = os.path.expanduser("~/Masaüstü/teknofest_gorev2/yarisma_sent.jsonl")
PRED = os.path.expanduser("~/Masaüstü/teknofest_gorev2/run_yarisma/predictions.csv")
CIKTI = os.path.expanduser("~/Masaüstü/teknofest_gorev2/yarisma_sonuc_video.mp4")
STILL = os.path.expanduser("~/Masaüstü/teknofest_gorev2/yarisma_kareler")
os.makedirs(STILL, exist_ok=True)

SINIF = {1: "tasit", 2: "insan", 3: "UAP", 4: "UAI"}
TURUNCU = (52, 104, 235); YESIL = (90, 175, 27); MAVI = (214, 120, 42)

sent = {}
for line in open(SENT):
    k = json.loads(line)
    sent[k["idx"]] = k["payload"]

meta = {}
with open(PRED) as f:
    r = csv.reader(f); next(r)
    for row in r:
        meta[int(row[0])] = (row[4], row[5])   # saglik, kaynak

vw = cv2.VideoWriter(CIKTI, cv2.VideoWriter_fourcc(*"mp4v"), 15.0, (1920, 1080))
for i in range(2250):
    img = cv2.imread(os.path.join(FR, f"frame_{i:06d}.webp"))
    if img is None:
        continue
    p = sent.get(i, {})
    for o in p.get("detected_objects", []):
        x1, y1 = int(float(o["top_left_x"])), int(float(o["top_left_y"]))
        x2, y2 = int(float(o["bottom_right_x"])), int(float(o["bottom_right_y"]))
        sid = int(o["cls"].rstrip("/").split("/")[-1])
        cv2.rectangle(img, (x1, y1), (x2, y2), TURUNCU, 2)
        cv2.putText(img, SINIF.get(sid, "?"), (x1, max(16, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, TURUNCU, 2)
    for rp in p.get("reference_predictions", []):
        x1, y1 = int(float(rp["top_left_x"])), int(float(rp["top_left_y"]))
        x2, y2 = int(float(rp["bottom_right_x"])), int(float(rp["bottom_right_y"]))
        rid = rp["reference"].rstrip("/").split("/")[-1]
        cv2.rectangle(img, (x1, y1), (x2, y2), YESIL, 3)
        cv2.putText(img, f"referans {rid}", (x1, min(1070, y2 + 26)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, YESIL, 2)
    sg, kay = meta.get(i, ("?", "?"))
    tr = p.get("detected_translations", [])
    txt = f"kare {i}  saglik={sg}  Gorev2={kay}"
    if tr:
        t = tr[0]
        txt += (f"  xyz=({float(t['translation_x']):.1f}, "
                f"{float(t['translation_y']):.1f}, {float(t['translation_z']):.1f})")
    bant = img.copy()
    cv2.rectangle(bant, (0, 0), (1920, 40), (30, 30, 30), -1)
    img = cv2.addWeighted(bant, 0.7, img, 0.3, 0)
    cv2.putText(img, txt, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                (255, 255, 255), 2)
    vw.write(img)
    if i in (150, 1100, 1920):
        cv2.imwrite(os.path.join(STILL, f"kare_{i:06d}.jpg"), img)
    if i % 500 == 0:
        print(f"cizildi: {i}/2250", flush=True)
vw.release()
print(f"VIDEO HAZIR: {CIKTI}")
