# video_analiz.py - tam videoyu isler, kutulu izlenebilir video uretir
# Kullanim: python3 video_analiz.py video.mp4
import sys, time, cv2, numpy as np
from yarisma_pipeline import model_yukle, isit, oturum_sifirla, kare_isle

def calistir():
    video = sys.argv[1]
    model_yukle('birincil_run7_26l.pt')
    isit()
    oturum_sifirla()
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    W, H = int(cap.get(3)), int(cap.get(4))
    wr = cv2.VideoWriter('analiz_cikti.mp4', cv2.VideoWriter_fourcc(*'mp4v'),
                         max(fps / 4, 5), (W, H))
    RENK = {0: (255, 128, 0), 1: (0, 255, 255), 2: (0, 220, 0), 3: (0, 0, 255)}
    AD = {0: 'tasit', 1: 'insan', 2: 'uap', 3: 'uai'}
    S = {k: 0 for k in ('kare', 'tasit', 'h1', 'insan', 'uap', 'uai', 'inis1', 'inis0')}
    T, fi = [], -1
    while True:
        if not cap.grab():
            break
        fi += 1
        if fi % 4:
            continue
        ok, kare = cap.retrieve()
        if not ok:
            continue
        t0 = time.perf_counter()
        tsp = kare_isle(kare)
        T.append((time.perf_counter() - t0) * 1e3)
        S['kare'] += 1
        for t in tsp:
            s = t['sinif']
            x1, y1, x2, y2 = t['kutu']
            et = f"{AD[s]} {t['conf']:.2f}"
            if s == 0:
                et += f" h:{t['hareket']}"
                S['tasit'] += 1
                S['h1'] += (t['hareket'] == 1)
            if s == 1:
                S['insan'] += 1
            if s >= 2:
                et += f" inis:{t['inis']}"
                S[AD[s]] += 1
                S['inis1' if t['inis'] == 1 else 'inis0'] += 1
            cv2.rectangle(kare, (x1, y1), (x2, y2), RENK[s], 3 if s >= 2 else 2)
            cv2.putText(kare, et, (x1, max(26, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, RENK[s], 2)
        wr.write(kare)
        if S['kare'] % 150 == 0:
            print(f"islenen {S['kare']} kare...")
    cap.release()
    wr.release()
    T = np.array(T)
    print(f"kare {S['kare']} | tasit {S['tasit']} (h:1 {S['h1']}) insan {S['insan']} "
          f"uap {S['uap']} uai {S['uai']} | inis 1:{S['inis1']} 0:{S['inis0']}")
    print(f"ms/kare: ort {T.mean():.0f} p95 {np.percentile(T, 95):.0f} max {T.max():.0f}")
    print('video -> analiz_cikti.mp4')
    print('SON SATIR OK')

calistir()
