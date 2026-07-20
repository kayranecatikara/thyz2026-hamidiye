# yarisma_pipeline.py - TEKNOFEST HYZ Gorev 1
# Hiz testi: python3 yarisma_pipeline.py video.mp4 [model.pt]
# Entegrasyon: from yarisma_pipeline import model_yukle, isit, oturum_sifirla, kare_isle
import sys, time, cv2, numpy as np
from collections import deque
from ultralytics import YOLO

CFG = dict(tasit=0.30, insan=0.25, ped_tetik=0.05, ped_hakem=0.50, ped_insan=0.25,
           anomali=0.25, kenar_px=3, kenar_min=0.15, max_ped=6,
           hiz_px=2.5, hiz_oran=0.045, min_ornek=4)
_model = None

def model_yukle(yol):
    global _model
    _model = YOLO(yol)
    return _model

def isit(bo=(1080, 1920, 3)):
    d = np.zeros(bo, np.uint8)
    for sz in (1280, 640, 192):
        _model.predict(d, imgsz=sz, conf=0.5, verbose=False)

def _det(img, imgsz, conf):
    r = _model.predict(img, imgsz=imgsz, conf=conf, verbose=False)[0]
    return [(int(b.cls), float(b.conf), int(b.xyxy[0][0]), int(b.xyxy[0][1]),
             int(b.xyxy[0][2]), int(b.xyxy[0][3])) for b in r.boxes]

def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    k = max(0, x2 - x1) * max(0, y2 - y1)
    return k / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - k + 1e-9)

def _kirp(kare, x1, y1, x2, y2, buyut=1.6):
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    yr = max(32, int(max(x2 - x1, y2 - y1) * buyut))
    X1, Y1 = max(0, cx - yr), max(0, cy - yr)
    X2, Y2 = min(kare.shape[1], cx + yr), min(kare.shape[0], cy + yr)
    return kare[Y1:Y2, X1:X2], X1, Y1

def _anomali(kare, x1, y1, x2, y2, snf):
    roi = kare[max(0, y1):max(1, y2), max(0, x1):max(1, x2)]
    if roi.size == 0:
        return 0.0
    h, w = roi.shape[:2]
    m = np.zeros((h, w), np.uint8)
    cv2.circle(m, (w // 2, h // 2), max(3, int(0.42 * min(h, w))), 255, -1)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    if snf == 2:
        renk = cv2.inRange(hsv, (95, 80, 50), (135, 255, 255))
    else:
        renk = (cv2.inRange(hsv, (0, 80, 50), (12, 255, 255)) |
                cv2.inRange(hsv, (168, 80, 50), (180, 255, 255)))
    beyaz = cv2.inRange(hsv, (0, 0, 160), (180, 70, 255))
    ic = (m > 0)
    return 1.0 - (((renk > 0) | (beyaz > 0)) & ic).sum() / max(ic.sum(), 1)

class _Ego:
    def __init__(self, g=960):
        self.g = g
        self.orb = cv2.ORB_create(nfeatures=1500, fastThreshold=12)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.onceki = None

    def guncelle(self, kare, kutular):
        H0, W0 = kare.shape[:2]
        s = self.g / W0
        gri = cv2.cvtColor(cv2.resize(kare, (self.g, int(H0 * s))), cv2.COLOR_BGR2GRAY)
        maske = np.full(gri.shape, 255, np.uint8)
        for x1, y1, x2, y2 in kutular:
            cv2.rectangle(maske, (int(x1*s)-6, int(y1*s)-6), (int(x2*s)+6, int(y2*s)+6), 0, -1)
        kp, des = self.orb.detectAndCompute(gri, maske)
        Hf = None
        onceki_ok = (self.onceki is not None and des is not None
                     and self.onceki[1] is not None
                     and len(kp) >= 30 and len(self.onceki[0]) >= 30)
        if onceki_ok:
            m = sorted(self.bf.match(self.onceki[1], des), key=lambda x: x.distance)[:500]
            if len(m) >= 30:
                p1 = np.float32([self.onceki[0][i.queryIdx].pt for i in m])
                p2 = np.float32([kp[i.trainIdx].pt for i in m])
                Hs, mi = cv2.findHomography(p1, p2, cv2.RANSAC, 3.0)
                if Hs is not None and mi is not None and int(mi.sum()) >= 20:
                    S = np.diag([s, s, 1.0])
                    Si = np.diag([1.0/s, 1.0/s, 1.0])
                    Hf = Si @ Hs @ S
        self.onceki = (kp, des)
        return Hf

class _Takip:
    def __init__(self):
        self.izler = {}
        self.sid = 1

    def _tasi(self, H, pt):
        v = H @ np.array([pt[0], pt[1], 1.0])
        return v[:2] / v[2]

    def guncelle(self, kutular, H):
        merk = [((x1+x2)/2.0, (y1+y2)/2.0) for x1, y1, x2, y2 in kutular]
        diag = [float(np.hypot(x2-x1, y2-y1)) for x1, y1, x2, y2 in kutular]
        tah = {tid: (self._tasi(H, iz['merkez']) if H is not None else np.array(iz['merkez']))
               for tid, iz in self.izler.items()}
        kalan, sonuc = set(self.izler), []
        for i, mc in enumerate(merk):
            en, end = None, 1e9
            for tid in kalan:
                d = float(np.hypot(mc[0]-tah[tid][0], mc[1]-tah[tid][1]))
                if d < end:
                    en, end = tid, d
            if en is not None and end <= max(35.0, 0.9 * diag[i]):
                iz = self.izler[en]
                kalan.discard(en)
                if H is not None:
                    iz['res'].append(end)
                iz['merkez'] = merk[i]
                iz['diag'] = diag[i]
                iz['kayip'] = 0
                tid = en
            else:
                tid = self.sid
                self.sid += 1
                self.izler[tid] = dict(merkez=merk[i], diag=diag[i],
                                       res=deque(maxlen=8), durum=0, kayip=0)
                iz = self.izler[tid]
            if len(iz['res']) >= CFG['min_ornek']:
                med = float(np.median(iz['res']))
                esik = max(CFG['hiz_px'], CFG['hiz_oran'] * iz['diag'])
                if med > esik:
                    iz['durum'] = 1
                elif med < 0.5 * esik:
                    iz['durum'] = 0
            sonuc.append((tid, iz['durum']))
        for tid in list(kalan):
            self.izler[tid]['kayip'] += 1
            if self.izler[tid]['kayip'] > 3:
                del self.izler[tid]
        return sonuc

_ego, _takip = _Ego(), _Takip()

def oturum_sifirla():
    global _ego, _takip
    _ego, _takip = _Ego(), _Takip()

def kare_isle(kare):
    H, W = kare.shape[:2]
    tespit, aday = [], []
    for s, c, x1, y1, x2, y2 in _det(kare, 1280, CFG['ped_tetik']):
        if s == 0 and c >= CFG['tasit']:
            tespit.append(dict(sinif=0, kutu=[x1, y1, x2, y2], conf=c, hareket=0, inis=-1))
        elif s == 1 and c >= CFG['insan']:
            tespit.append(dict(sinif=1, kutu=[x1, y1, x2, y2], conf=c, hareket=-1, inis=-1))
        elif s in (2, 3):
            aday.append((c, s, x1, y1, x2, y2))
    for c, s, x1, y1, x2, y2 in sorted(aday, reverse=True)[:CFG['max_ped']]:
        kenar = (x1 <= CFG['kenar_px'] or y1 <= CFG['kenar_px'] or
                 x2 >= W - CFG['kenar_px'] or y2 >= H - CFG['kenar_px'])
        crop, ox, oy = _kirp(kare, x1, y1, x2, y2)
        if kenar:
            if c < CFG['kenar_min']:
                continue
        else:
            zc = max([cc for ss, cc, *_ in _det(crop, 192, 0.10) if ss in (2, 3)], default=0.0)
            if zc < CFG['ped_hakem']:
                continue
        dolu = False
        for si, ci, a1, b1, a2, b2 in _det(crop, 640, 0.10):
            if si not in (0, 1) or ci < CFG['ped_insan']:
                continue
            g = [a1 + ox, b1 + oy, a2 + ox, b2 + oy]
            mx, my = (g[0] + g[2]) // 2, (g[1] + g[3]) // 2
            if not (x1 <= mx <= x2 and y1 <= my <= y2):
                continue
            dolu = True
            es = [t for t in tespit if t['sinif'] == si and _iou(t['kutu'], g) > 0.45]
            if es:
                for t in es:
                    t['conf'] = max(t['conf'], ci)
            else:
                tespit.append(dict(sinif=si, kutu=g, conf=ci,
                                   hareket=(0 if si == 0 else -1), inis=-1))
        inis = 0 if (dolu or kenar or _anomali(kare, x1, y1, x2, y2, s) > CFG['anomali']) else 1
        tespit.append(dict(sinif=s, kutu=[x1, y1, x2, y2], conf=c, hareket=-1, inis=inis))
    Hf = _ego.guncelle(kare, [t['kutu'] for t in tespit])
    vi = [j for j, t in enumerate(tespit) if t['sinif'] == 0]
    if vi:
        for j, (tid, durum) in zip(vi, _takip.guncelle([tespit[j]['kutu'] for j in vi], Hf)):
            tespit[j]['hareket'] = durum
    return tespit

if __name__ == '__main__':
    import torch
    print('CUDA:', torch.cuda.is_available(), '|',
          torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU - YAVAS OLUR')
    video = sys.argv[1] if len(sys.argv) > 1 else None
    myol = sys.argv[2] if len(sys.argv) > 2 else 'birincil_run4_26l.pt'
    model_yukle(myol)
    print('model:', myol)
    isit()
    print('isinma tamam')
    oturum_sifirla()
    cap = cv2.VideoCapture(video)
    T, n, fi = [], 0, -1
    say = {0: 0, 1: 0, 2: 0, 3: 0}
    while n < 300:
        if not cap.grab():
            break
        fi += 1
        if fi % 4:
            continue
        ok, kare = cap.retrieve()
        if not ok:
            continue
        t0 = time.perf_counter()
        for t in kare_isle(kare):
            say[t['sinif']] += 1
        T.append((time.perf_counter() - t0) * 1e3)
        n += 1
    cap.release()
    T = np.array(T)
    print(f'kare: {n} | tespit: {say}')
    print(f'ms/kare: ort {T.mean():.0f} | p95 {np.percentile(T, 95):.0f} | max {T.max():.0f}')
    print('BUTCE: 1600 ms - p95 bunun ALTINDA olmali')
