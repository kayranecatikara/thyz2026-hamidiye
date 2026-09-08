"""Görev 3 v2 — Referans Nesne Tespiti (TEKNOFEST 2026 Havacılıkta Yapay Zekâ).

YARIŞMA ORTAMI: internet YOK. timm/HF varsayılan olarak ağa çıkmayı deneyip
zaman aşımına düşebilir — hem yavaşlatır hem de "neden takıldı" sorusunu
sahada sordurur. Bu yüzden paket içe aktarılır aktarılmaz çevrimdışı kip
AÇILIR. Ağırlıkların önceden indirilmiş olması şarttır; `on_kontrol()` bunu
denetler ve eksikse ERKEN, anlaşılır biçimde hata verir.

Çevrimdışı kipi bilerek kapatmak isteyen (ağırlık indirmek için) şunu yapar:
    GOREV3_ALLOW_NETWORK=1
"""
import os

if os.environ.get("GOREV3_ALLOW_NETWORK") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    # ultralytics sürüm/analitik çağrılarını da kapat
    os.environ.setdefault("YOLO_OFFLINE", "True")

from .api import ReferenceObjectDetectorV2          # noqa: E402
from .onkontrol import on_kontrol                    # noqa: E402

__all__ = ["ReferenceObjectDetectorV2", "on_kontrol"]
