"""TEKNOFEST 2026 HYZ — hamidiye_4907501 BİRLEŞİK YARIŞMA MODELİ (3 görev).

Kural gereği resmi arayüzde YALNIZ bu dosya değiştirildi. Ağır kodlar dışarıda:
  Görev 1 (nesne tespiti)      : ~/Masaüstü/teknofest_gorev2/gorev_1/yarisma_pipeline.py
  Görev 2 (konum kestirimi)    : ~/Masaüstü/teknofest_gorev2/gorev2_engine.py (SP-SLAM3)
  Görev 3 (referans nesne)     : ~/Masaüstü/hyz_gorev3/gorev3/ (SAM+DINO/ELoFTR hibrit)

İlkeler:
  - HER kareye tam 1 tahmin gönderilir; hangi görev hata verirse versin kare
    boş-ama-geçerli çıktıyla İLERLETİLİR (sunucu tahmin gelmeden sonraki kareyi
    vermez; takılmak = tüm oturumu kaybetmek).
  - DetectedObject.create_payload cls'yi indeksler (cls[0]) → sınıf TUPLE verilir.
  - Görev 2: sağlık=1'de GT aynen geri (0 hata) + motor hizalama çifti toplar;
    sağlık=0'da SLAM tahmini. Kamera kalibrasyonu ilk kareden otomatik seçilir.

Ortam değişkenleri (hepsi opsiyonel):
  GOREV1_DIR, GOREV1_MODEL, GOREV2_DIR, GOREV2_SETTINGS, GOREV2_RUN_DIR, GOREV3_DIR
"""
import logging
import os
import sys
import time

import cv2
import requests

from .constants import classes, landing_statuses, moving_statuses
from .detected_object import DetectedObject
from .detected_translation import DetectedTranslation
from .reference_prediction import ReferencePrediction

GOREV2_DIR = os.environ.get(
    "GOREV2_DIR", os.path.expanduser("~/Masaüstü/teknofest_gorev2"))
GOREV1_DIR = os.environ.get("GOREV1_DIR", os.path.join(GOREV2_DIR, "gorev_1"))
GOREV3_DIR = os.environ.get(
    "GOREV3_DIR", os.path.expanduser("~/Masaüstü/hyz_gorev3"))
for _p in (GOREV2_DIR, GOREV1_DIR, GOREV3_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gorev2_engine import Gorev2Engine          # noqa: E402
import yarisma_pipeline as g1                   # noqa: E402  (Görev 1)
from gorev3.integrate import ReferenceObjectDetector  # noqa: E402


class ObjectDetectionModel:
    # Base class for team models

    def __init__(self, evaluation_server_url):
        logging.info('Created Object Detection Model')
        self.evaulation_server = evaluation_server_url

        # ── Görev 1: YOLO26l — program başında BİR kez yükle + GPU ısıt ─────
        self._g1_hazir = False
        self._g1_video = None            # video değişiminde oturum_sifirla()
        try:
            model_yolu = os.environ.get(
                "GOREV1_MODEL", os.path.join(GOREV1_DIR, "birincil_run7_26l.pt"))
            g1.model_yukle(model_yolu)
            g1.isit()
            self._g1_hazir = True
            logging.info(f"Gorev1 hazir: {model_yolu}")
        except Exception as e:
            logging.error(f"Gorev1 YUKLENEMEDI (bos tespitle devam): {e}")

        # ── Görev 3: hibrit referans dedektörü — BİR kez yükle ──────────────
        self.ref_detector = None
        try:
            self.ref_detector = ReferenceObjectDetector()
            logging.info("Gorev3 ReferenceObjectDetector hazir")
        except Exception as e:
            logging.error(f"Gorev3 YUKLENEMEDI (referans tahminsiz devam): {e}")

        # ── Görev 2: SLAM ağır (sözlük ~30 sn) → ilk karede tembel başlar; ──
        # kamera kalibrasyonu da ilk karenin çözünürlüğünden seçilir.
        self._engine = None
        self._frame_seq = 0

    # ── Görev 2 yardımcıları ────────────────────────────────────────────────
    @staticmethod
    def _auto_settings(frame_image_path):
        """İlk karenin çözünürlüğünden doğru kalibrasyonu seç (2026 resmi
        parametreleri: 4K RGB 4000x3000, 1080p RGB 1920x1080, termal 640x512).
        3840 genişlik = 2025 tarzı 4K-kırpma (cropA). GOREV2_SETTINGS ortam
        değişkeni verilirse bu fonksiyon hiç çağrılmaz (elle geçersiz kılma)."""
        yol = os.path.expanduser("~/SP_SLAM3/Examples/Monocular/")
        w = None
        try:
            img = cv2.imread(frame_image_path)
            if img is not None:
                w = img.shape[1]
        except Exception as e:
            logging.error(f"Gorev2 kamera tespiti okuma hatasi: {e}")
        if w is None:
            secim = "teknofest.yaml"          # okunamadıysa 4K varsay
        elif w >= 3900:
            secim = "teknofest.yaml"          # 4000x3000 native 4K
        elif w >= 2500:
            secim = "thyz2025_cropA.yaml"     # 3840x2160 (4K kırpma)
        elif w >= 1500:
            secim = "teknofest_1080p.yaml"    # 1920x1080
        else:
            secim = "teknofest_termal.yaml"   # 640x512 termal
        logging.info(f"Gorev2 kamera tespiti: genislik={w} -> {secim}")
        return os.path.join(yol, secim)

    def _get_engine(self, frame_image_path=None):
        if self._engine is None:
            settings = os.environ.get("GOREV2_SETTINGS")
            if not settings:
                settings = self._auto_settings(frame_image_path)
            run_dir = os.environ.get(
                "GOREV2_RUN_DIR", os.path.join(GOREV2_DIR, "run_yarisma"))
            # Eski koşu kalıntısı zehirlenmesi: outbox/pose.txt'te önceki
            # koşunun kare numaraları kalırsa yeni koşunun aynı numaralı
            # kareleriyle eşleşip hizalamayı bozar. Var olan klasörü SİLME
            # (denetim izi), zaman damgasıyla kenara taşı.
            if os.path.exists(run_dir):
                eski = f"{run_dir}_eski_{int(time.time())}"
                os.rename(run_dir, eski)
                logging.info(f"Gorev2 eski run klasoru kenara tasindi: {eski}")
            self._engine = Gorev2Engine(
                settings=settings, run_dir=run_dir,
                predictions_csv=os.path.join(run_dir, "predictions.csv"))
            logging.info("Gorev2Engine baslatiliyor (SLAM sozluk yuklemesi)...")
            t0 = time.perf_counter()
            self._engine.start()
            logging.info(f"Gorev2Engine hazir ({time.perf_counter()-t0:.1f} sn).")
        return self._engine

    @staticmethod
    def download_image(img_url, images_folder, images_files, retries=3, initial_wait_time=0.1, auth_token=None):
        t1 = time.perf_counter()
        wait_time = initial_wait_time
        # Indirmek istedigimiz frame frames.json dosyasinda mevcut mu kontrol edelim
        image_name = img_url.split("/")[-1]
        # Eger indirecegimiz frame'i daha once indirmediysek indirme islemine gecelim
        if image_name not in images_files:
            headers = {'Authorization': f'Token {auth_token}'} if auth_token else {}
            for attempt in range(retries):
                    try:
                        response = requests.get(img_url, headers=headers, timeout=60)
                        response.raise_for_status()

                        img_bytes = response.content
                        with open(images_folder + image_name, 'wb') as img_file:
                            img_file.write(img_bytes)

                        t2 = time.perf_counter()
                        logging.info(f'{img_url} - Download Finished in {t2 - t1} seconds to {images_folder + image_name}')
                        return

                    except requests.exceptions.RequestException as e:
                        logging.error(f"Download failed for {img_url} on attempt {attempt + 1}: {e}")
                        logging.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        wait_time *= 2

            logging.error(f"Failed to download image from {img_url} after {retries} attempts.")
        # Eger indirecegimiz frame'i daha once indirdiysek indirme yapmadan devam edebiliriz
        else:
            logging.info(f'{image_name} already exists in {images_folder}, skipping download.')

    def process(self, prediction, evaluation_server_url, health_status, images_folder, images_files,
                active_refs=None, ref_image_paths=None, auth_token=None):
        # Yarışmacılar resim indirme, pre ve post process vb işlemlerini burada gerçekleştirebilir.
        # Download image (Ornek)
        self.download_image(evaluation_server_url + "media" + prediction.image_url, images_folder, images_files, auth_token=auth_token)
        # Örnek: Burada OpenCV gibi bir tool ile preprocessing işlemi yapılabilir. (Tercihe Bağlı)
        # ...
        # Nesne tespiti (Gorev 1), pozisyon kestirim (Gorev 2) ve referans nesne tespiti (Gorev 3)
        # modellerinin tumu self.detect() icinde sira ile calistirilir.
        frame_image_path = images_folder + prediction.image_url.split("/")[-1]
        frame_results = self.detect(prediction, health_status,
                                    active_refs=active_refs or [],
                                    ref_image_paths=ref_image_paths or {},
                                    frame_image_path=frame_image_path)
        # Tahminler objesi FramePrediction sınıfında return olarak dönülmelidir.
        return frame_results

    def detect(self, prediction, health_status, active_refs=None, ref_image_paths=None, frame_image_path=None):
        fid = self._frame_seq
        self._frame_seq += 1
        # Sunucu sağlık bitini str gönderir ('0'/'1'); int gelirse de çalışsın.
        if health_status is not None:
            health_status = str(health_status)

        # Kareyi BİR kez oku; Görev 1 ve Görev 2 aynı diziyi paylaşır (4K webp
        # çözümü pahalı). Okunamazsa fail-safe: boş-ama-geçerli tahmin gider.
        kare = None
        try:
            kare = cv2.imread(frame_image_path)
        except Exception as e:
            logging.error(f"Kare okunamadi ({frame_image_path}): {e}")
        if kare is None:
            logging.error(f"Gorev1/2 frame {fid}: kare bozuk/okunamadi — "
                          f"bos tespit + olu-hesap konumla ilerletiliyor.")

        # ── Görev 1 (Nesne Tespiti — YOLO26l tam hat) ───────────────────────
        # kare_isle SIRALI çağrılmalı (takipçi ardışıklık varsayar); video
        # değişiminde oturum_sifirla ZORUNLU. Hata ne olursa olsun kare
        # gönderimi engellenmez (boş detected_objects geçerlidir).
        if self._g1_hazir and kare is not None:
            try:
                if prediction.video_name != self._g1_video:
                    g1.oturum_sifirla()
                    self._g1_video = prediction.video_name
                    logging.info(f"Gorev1 oturum_sifirla (video={prediction.video_name})")
                for t in g1.kare_isle(kare):
                    x1, y1, x2, y2 = t['kutu']
                    # create_payload cls[0] indeksler -> tuple zorunlu.
                    # hareket/inis kodları constants ile birebir (str çevrimi).
                    prediction.add_detected_object(DetectedObject(
                        (int(t['sinif']),),
                        str(int(t['inis'])),      # landing_status
                        str(int(t['hareket'])),   # moving_status
                        float(x1), float(y1), float(x2), float(y2)))
            except Exception as e:
                logging.error(f"Gorev1 hata (frame {fid}, bos tespitle devam): {e}")

        # ── Görev 2 (Konum Kestirimi — SP-SLAM3 + yansımalı hizalama) ──────
        if health_status is None:
            # Çeviri yok: Görev 2 çıktısı üretilmez ama SLAM haritası kopmasın
            # diye kare yine de motora beslenir.
            try:
                self._get_engine(frame_image_path).process_frame(
                    fid, kare if kare is not None else frame_image_path, None, None)
            except Exception as e:
                logging.error(f"Gorev2 motor beslemesi basarisiz (frame {fid}): {e}")
            logging.info("No translation/health_status; skipping Mission 2 output.")
        else:
            ref_xyz = None
            if health_status == '1' and None not in (
                    prediction.gt_translation_x,
                    prediction.gt_translation_y,
                    prediction.gt_translation_z):
                ref_xyz = (float(prediction.gt_translation_x),
                           float(prediction.gt_translation_y),
                           float(prediction.gt_translation_z))
            try:
                out, kaynak = self._get_engine(frame_image_path).process_frame(
                    fid, kare if kare is not None else frame_image_path,
                    ref_xyz, int(health_status))
            except Exception as e:
                # Motor ne olursa olsun cevap üretir; buraya düşersek bile kareyi
                # boş Görev 2 çıktısıyla ilerletmek en güvenlisi.
                logging.error(f"Gorev2 motoru hata verdi (frame {fid}): {e}")
                out, kaynak = None, "hata"

            if health_status == '0':
                if out is not None:
                    prediction.add_translation_object(
                        DetectedTranslation(float(out[0]), float(out[1]),
                                            float(out[2])))
                    logging.info(f"Gorev2 frame {fid}: kaynak={kaynak} "
                                 f"xyz=({out[0]:.3f},{out[1]:.3f},{out[2]:.3f})")
                else:
                    logging.error(f"Gorev2 frame {fid}: cikti YOK (hata yolu)")
            else:
                # Sağlıklı: GT aynen geri (sıfır hata) — motor çifti zaten kaydetti
                if ref_xyz is not None:
                    prediction.add_translation_object(DetectedTranslation(
                        prediction.gt_translation_x,
                        prediction.gt_translation_y,
                        prediction.gt_translation_z))
                else:
                    logging.info("Healthy frame but GT translation is null; "
                                 "skipping Mission 2 output.")

        # ── Görev 3 (Referans Nesne Tespiti — hibrit, FP korumalı) ─────────
        # Pencere-içi her aktif referans için çalışır; emin olunmayan karede
        # bbox None döner ve HİÇBİR kutu gönderilmez (güven alanı yok, her
        # kutu kesin pozitif sayılır). Kare başına segmentasyon 1 kez
        # (detektör path-cache'i), referanslar onu paylaşır.
        if self.ref_detector is not None:
            for ref in (active_refs or []):
                start_img = ref.get('frame_start_image_url', '')
                end_img = ref.get('frame_end_image_url', '')
                if not (start_img and end_img and
                        start_img <= prediction.image_url <= end_img):
                    continue
                try:
                    bbox = self.ref_detector.detect_for_frame(
                        frame_image_path,
                        ref['url'],
                        (ref_image_paths or {}).get(ref['url']),
                        video_name=prediction.video_name,
                    )
                except Exception as e:
                    logging.error(f"Gorev3 hata ({ref.get('url')}): {e}")
                    bbox = None
                if not bbox:
                    continue
                prediction.add_reference_prediction(
                    ReferencePrediction(ref['url'], prediction.frame_url, *bbox))

        return prediction
