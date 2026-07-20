# TEKNOFEST 2026 — Havacılıkta Yapay Zeka · Takım hamidiye_4907501

Üç görevi **tek istemcide** birleştiren yarışma sistemi. 16 Temmuz 2026 çevrim içi
simülasyonunda **2250/2250 kareyi 53.5 dakikada** işleyip gönderdi (0 ret, 0 kopma):
6834 nesne kutusu (Görev 1), kesintideki 1547 karenin tamamında SLAM konumu
(Görev 2), 6 referans nesnede 304 pencere-içi kutu (Görev 3).

## Mimari — tek komut, üç görev

```
python3 main.py  (resmî TAKIM_BAGLANTI_ARAYUZU — yalnız object_detection_model.py değiştirildi)
        │  kareyi indirir → detect() → tahmini gönderir → sonraki kare
        ▼
┌─ Görev 1 ──────────┐ ┌─ Görev 2 ───────────────┐ ┌─ Görev 3 ─────────────┐
│ YOLO26l (run7)     │ │ SP-SLAM3 (C++ süreç)    │ │ FastSAM + DINOv2      │
│ + ped hakemi       │ │ SuperPoint + LightGlue  │ │ + ELoFTR (termal)     │
│ + ped-içi insan    │ │ + yansımalı planar      │ │ emin değilse kutu     │
│ + ego-hareket      │ │   hizalama (Umeyama'nın │ │ GÖNDERMEZ (FP cezalı) │
│   takibi           │ │   el-yönü-güvenli hali) │ │                       │
└─ gorev_1/          ┘ └─ gorev2_engine.py+SP_SLAM3┘ └─ hyz reposu (ayrı)  ┘
```

**Çelik zırh ilkesi:** hangi görev hata verirse versin her kareye tam 1 geçerli
tahmin gider — sunucu tahminsiz sonraki kareyi vermez, takılmak oturumu kaybettirir.

## Görevlerin özeti

### Görev 1 — Nesne Tespiti (`gorev_1/`)
YOLO26l, 4 sınıf (taşıt/insan/UAP/UAİ), ~34k görüntüyle eğitim, saklanan oturumda
mAP@0.5 = 0.849. Tam hat: 1280 tam-kare tespit → ped adaylarına 192px "hakem"
doğrulaması → onaylı pedde 640px insan taraması (insan varsa iniş=İnilemez) →
ORB/RANSAC ego-hareket telafili hareketli/sabit takibi. Hız: **p95 = 70 ms** (4K).
Yarışma modeli: `gorev_1/birincil_run7_26l.pt` (repoda).

### Görev 2 — GPS'siz Konum Kestirimi (bu repo + [SP_SLAM3](https://github.com/kayranecatikara/SP_SLAM3))
Tek kamera SLAM (SuperPoint+LightGlue'lu ORB-SLAM3 çatalı) + sağlıklı karelerdeki
GT ile ölçek/çerçeve hizalaması. Kritik keşifler (ayrıntı: `SETUP_LOG.md`):
- **Init nokta tavanı (Tracking.cc):** izlenmiş LightGlue ~1600 nokta üstünde
  bozulur; init çıkarıcısı ≤1200'e sınırlandı → "init'te takılma" tamamen bitti.
- **El-yönü (yansıma) keşfi:** SLAM çerçevesi ile GT çerçevesi arasında yansıma
  var; det=+1 kısıtlı klasik sim3 z'yi ters çevirir. Çözüm: her zaman
  **yansımalı 2B (xy) + ayrı 1B (z)** hizalama (`alignment.py`).
- **Kamera otomatiği:** ilk karenin çözünürlüğünden doğru kalibrasyon seçilir
  (4000→4K, 3840→cropA, 1920→1080p, 640→termal yaml).
- 2025 doğrulama (Denklem-2): **O2 8.8 / O3 4.3 / O4 4.7 m** (v1'e göre ~8×).
  2026 örnek videoda ~35 m (hatanın %98'i z; kalibrasyon dakikası düz uçuşsa z
  ölçeği gözlemlenemez — fiziksel sınır, xy hatası 5.4 m).

### Görev 3 — Referans Nesne Tespiti ([hyz reposu](https://github.com/KubraNurTiryaki/hyz))
Hibrit sistem: FastSAM segmentasyonu + DINOv2 kosinüs eşlemesi (+ termalde
ELoFTR + MAGSAC). Pencere kurallarına yapısal uyum (kare başına ≤1 kutu) ve
yanlış-pozitif koruması. Simülasyonda 6/7 referansta isabetli kutular.

## Depo haritası

| Yol | İçerik |
|---|---|
| `gorev2_engine.py`, `alignment.py` | Görev 2 motoru + hizalama matematiği |
| `istemci/TAKIM_BAGLANTI_ARAYUZU/` | Yarışma istemcisi (3 görev entegre; `.env`'siz) |
| `gorev_1/` | Görev 1 hattı + run7 model ağırlığı |
| `bridge.py`, `mock_server.py`, `resmi_mock.py` | Prova altyapısı (TCP mock + resmî-protokol HTTP taklidi) |
| `canli_prova.sh`, `video_analiz.sh`, `canli_panel.py`, `analiz_3eksen.py` | Canlı izleme: Pangolin + paneller |
| `tam_prova.py`, `yarisma_video_ciz.py`, `analiz_ozet.py` | Uçtan uca prova ve raporlama araçları |
| `prova2025/oturum*_gt.csv` | Oturum GT'leri (kareler hariç — KURULUM §9) |
| `kanitlar/` | 16 Temmuz oturumunun şifre-temizlenmiş sunucu logu + gönderilen paketler |
| `SETUP_LOG.md` | Tüm geliştirme/karar günlüğü (sorun çözümleri burada) |
| `YARISMA_GUNU.md` | Yarışma günü çalıştırma rehberi (tek komut + arıza tablosu) |
| `KURULUM.md` | **Sıfır makineden kurulum** (aşağıdaki master prompt bunu izler) |

## İlişkili depolar (üçü birlikte tam sistem)
1. **Bu repo** — motor, istemci, Görev 1, araçlar, belgeler
2. **[kayranecatikara/SP_SLAM3](https://github.com/kayranecatikara/SP_SLAM3)** — SLAM C++ (modeller LFS'te: `lightglue.pt`, `cosplace.pt`, sözlük)
3. **[KubraNurTiryaki/hyz](https://github.com/KubraNurTiryaki/hyz)** — Görev 3 hibrit sistemi

## Hızlı başlangıç
Kurulum: `KURULUM.md` (adım adım). Yarışma günü: `YARISMA_GUNU.md` — özü:
```bash
cd ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU && \
HF_HUB_OFFLINE=1 python3 main.py
```

---

## 🤖 MASTER PROMPT — Claude Code ile sıfırdan kurulum

Aşağıdaki bloğu olduğu gibi kopyalayıp temiz bir Ubuntu 22.04 + NVIDIA GPU
makinesinde **Claude Code**'a yapıştırın. Sizden yalnızca sudo şifresi ve
(yarışma bağlanacaksanız) takım kimlik bilgileri istenecektir.

```text
TEKNOFEST 2026 Havacılıkta Yapay Zeka (takım hamidiye_4907501) üç görevli yarışma
sistemini bu makineye SIFIRDAN kur. Ben teknik detay bilmiyorum; her şeyi sen yap,
her aşamayı doğrulayarak ilerle, sorun çıkarsa kendin çöz.

KAYNAKLAR (üç repo, TAM şu yollara klonlanacak — kodlardaki varsayılanlar bu yolları bekler):
- https://github.com/kayranecatikara/thyz2026-hamidiye  →  ~/Masaüstü/teknofest_gorev2
- https://github.com/kayranecatikara/SP_SLAM3           →  ~/SP_SLAM3   (git-lfs ŞART)
- https://github.com/KubraNurTiryaki/hyz                →  ~/Masaüstü/hyz_gorev3

TALİMAT:
1. Önce ~/Masaüstü/teknofest_gorev2 reposunu klonla ve içindeki KURULUM.md ile
   README.md'yi OKU. KURULUM.md'yi 1'den 10'a SIRAYLA uygula; her bölümün
   sonundaki doğrulama komutunu çalıştırıp geçtiğini görmeden sonrakine geçme.
2. Kritik noktalar:
   - SP_SLAM3 klonunda LFS dosyalarını doğrula (lightglue.pt ~46 MB olmalı;
     birkaç KB ise `git lfs pull`).
   - SLAM derlemesi (KURULUM §5) uzun sürer; hata çıkarsa çözümler
     ~/Masaüstü/teknofest_gorev2/SETUP_LOG.md içindeki FAZ 2-5 kayıtlarındadır
     (takas alanı, make -j3, Pangolin sürümü vb.) — önce oraya bak.
   - Derleme sonrası sözlük dönüşümünü unutma:
     ./tools/convert_vocab Vocabulary/superpoint_voc.yml.gz Vocabulary/superpoint_voc.dbow3
   - İKİ Python ortamı var: sistem python3 (istemci; torch cu121 + ultralytics +
     transformers + kornia + LightGlue) ve ~/venvs/slam (paneller; numpy+opencv+matplotlib).
   - İstemciyi repo içinden şu yola kopyala:
     ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU
   - config/example.env'den config/.env oluştur; TEAM_NAME/PASSWORD/SUNUCU adresini
     KULLANICIYA SOR (e-postadaki bilgiler) — asla git'e ekleme.
3. Görev 3 modellerini önden indirt: cd ~/Masaüstü/hyz_gorev3 && python3 test_offline.py
   (üç model ✅ görmeli; sonraki koşularda HF_HUB_OFFLINE=1 kullanılır).
4. KURULUM.md §10'daki DOĞRULAMA SIRASINI eksiksiz koş:
   alignment.py öz-testleri, Görev 1 model+sınıf doğrulaması ve (2025 O2 kareleri
   indirildiyse) resmi_mock.py ile 300 karelik uçtan uca yerel prova
   ("Session complete" görülmeli). Veri yoksa bu son adımı "veri bekliyor" diye
   raporla, hata sayma.
5. Bittiğinde bana şu formatta özet ver: her kurulum bölümü için ✅/❌, doğrulama
   çıktılarının önemli satırları, ve yarışma günü çalıştırılacak tek komut
   (YARISMA_GUNU.md Bölüm 0'daki). ❌ kalan madde varsa sebebini ve ne
   gerektiğini açıkça yaz.
```

---
*Sistem, 15-16 Temmuz 2026'da Claude Code ile birlikte geliştirildi ve canlı
yarışmada doğrulandı. Geliştirme kararlarının tam gerekçeleri için `SETUP_LOG.md`.*
