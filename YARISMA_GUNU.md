# YARIŞMA GÜNÜ REHBERİ — hamidiye_4907501 (3 görev birleşik)

## 0) TEK KOMUT (her şey buna indirgendi)

Oturum aktif olduğunda tek yapman gereken:

```bash
cd ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU
HF_HUB_OFFLINE=1 python3 main.py
```

Bu komut: sunucuya girer → kaldığı kareyi bulur → referans görüntülerini indirir →
kareleri tek tek çekip 3 görevi de çalıştırır → tahminleri gönderir → oturum bitince
"Session complete" der ve çıkar. **Başka hiçbir şey çalıştırman gerekmiyor.**

> Puanlı oturum başlamadan çalıştırırsan zarar yok: "No active session" ya da test
> oturumu doluysa "All frames already submitted" der ve çıkar.

## 1) OTURUM ÖNCESİ KONTROL (5 dakika, sırayla)

```bash
# 1. Başka GPU/istemci süreci kalmasın (prova araçları):
pkill -f mono_folder_watch; pkill -f bridge.py; pkill -f mock_server.py; pkill -f canli_panel
# 2. GPU boş mu? (birkaç yüz MiB normaldir)
nvidia-smi --query-gpu=memory.used --format=csv
# 3. İnternet var mı?
ping -c 2 havaciliktayapayzeka.teknofest.org
# 4. Kimlik bilgileri (değiştirme, sadece bak):
cat ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU/config/.env
```

Ayrıca: **şarj kablosu takılı**, otomatik askıya alma KAPALI
(Ayarlar → Güç → Boşta ekran kapansın ama askıya alma olmasın), diz üstü kapağını kapatma.

## 2) ÇALIŞIRKEN NE GÖRECEKSİN

1. `Started...` → ~10 sn model yüklemesi (Görev 1 + Görev 3).
2. `Session: <ad> — resuming from frame X of N` → oturum bulundu.
3. `Frames: ...%` ilerleme çubuğu. **İlk karede ~30 sn tek seferlik duraklama
   normaldir** (SLAM sözlük yüklemesi) — panik yok.
4. Kare hızı: sağlıklı karelerde ~0.3-0.5 sn/kare; kesinti karelerinde ~0.5-1.4 sn;
   referans penceresi içindeki karelerde birkaç saniye olabilir (Görev 3 çalışıyor).

İkinci terminalden canlı izlemek istersen (opsiyonel, dokunma-sadece-izle):

```bash
tail -f ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU/_logs/$(ls -t ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU/_logs | head -1)
```

Logda arayacağın güven verici satırlar:
- `Gorev1 hazir`, `Gorev3 ReferenceObjectDetector hazir`
- `Gorev2 kamera tespiti: genislik=#### -> ####.yaml`  ← kamera otomatik seçildi
- `Gorev2 frame N: kaynak=slam xyz=(...)` ← kesintide SLAM konum üretiyor

## 3) SORUN ANINDA (sakin ol, hepsi planlı)

| Durum | Yapılacak |
|---|---|
| Bağlantı koptu / program çöktü / elektrik gitti | **Aynı komutu tekrar çalıştır.** Kaldığı kareden devam eder. SLAM çalışma klasörü otomatik kenara alınır, sistem ilk sağlıklı karelerde kendini yeniden hizalar. |
| `Aborting: current frame is not advancing` | Log dosyasının son satırlarına bak (üstteki tail komutu), hatayı oku. Genelde geçici sunucu hatasıdır → tekrar başlat. |
| İlk kare çok uzun sürüyor | 30-40 sn normal (SLAM sözlüğü). 3 dakikayı aşarsa Ctrl+C → tekrar başlat. |
| `No active session found` | Oturum henüz açılmamış. Bekle, birkaç dakikada bir tekrar dene. |
| GPU bellek hatası (loglarda CUDA out of memory) | Ctrl+C → `nvidia-smi` ile artık süreç var mı bak → varsa öldür → tekrar başlat. |

**ASLA yapma:** aynı anda iki `main.py` çalıştırmak; koşarken `pkill python` gibi
genel komutlar; koşarken prova betikleri (`canli_prova.sh` vs.) açmak.

## 4) ACİL DURUM DÜĞMELERİ (ortam değişkenleri — normalde GEREKMİYOR)

Komutun başına eklenerek kullanılır, ör. `GOREV2_SETTINGS=... python3 main.py`:

- `GOREV2_SETTINGS=~/SP_SLAM3/Examples/Monocular/teknofest_termal.yaml` — kamera
  otomatik seçimi yanlış seçerse elle dayat (log satırından anlarsın).
- Görev 1 modeli: birincil_run7_26l.pt (ince ayarlı, 2026-07-16; eski run4
  kullanıcı kararıyla silindi). Model yüklenemezse sistem çökmez, Görev 1
  boş tespitle devam eder (fail-safe).
- Görev 1/3 yüklenemezse program ÇÖKMEZ: o görev boş çıktıyla devam eder, loga
  `YUKLENEMEDI` yazar. Görev 2 motoru da her hatada ölü-hesap konum üretir.

## 5) OTURUM BİTİNCE

1. `Session complete` mesajını gör.
2. Kanıtları yedekle (log + Görev 2 iç kaydı):
   ```bash
   cp -r ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU/_logs ~/Masaüstü/yarisma_kanit_logs
   cp -r ~/Masaüstü/teknofest_gorev2/run_yarisma ~/Masaüstü/yarisma_kanit_gorev2
   ```
3. Yarışma tamamen bittikten sonra güvenlik temizliği: `sudo rm /etc/sudoers.d/99-claude-setup`

## 6) SİSTEMİN İÇİNDE NE VAR (özet — soru gelirse)

- **Görev 1:** YOLO26l (`gorev_1/birincil_run7_26l.pt`, mAP@0.5=0.849) + ped hakemi +
  ped-içi insan taraması + ego-hareket telafili hareket takibi. Hız: p95 = 70 ms (4K).
- **Görev 2:** SP-SLAM3 (SuperPoint+LightGlue) + yansımalı planar hizalama.
  Sağlık=1'de GT aynen geri (0 hata), sağlık=0'da SLAM konumu. 2025 verisinde
  Denklem-2: O2 8.8 / O3 4.3 / O4 4.7 m. Kamera kalibrasyonu ilk kareden otomatik:
  4000→4K yaml, 3840→cropA, 1920→1080p yaml, 640→termal.
- **Görev 3:** FastSAM+DINOv2 hibrit + ELoFTR termal yolu (takım deposu hyz).
  Emin olunmayan karede kutu GÖNDERMEZ (yanlış-pozitif koruması).
- **Fail-safe ilkesi:** her kareye tam 1 tahmin; hangi görev hata verirse versin kare
  boş-ama-geçerli çıktıyla ilerletilir (takılmak = oturumu kaybetmek).

## 6.5) YEREL PROVA — istediğin kadar tekrar edebilirsin (sunucuya dokunmaz)

Resmî sunucunun yerel taklidi var (`resmi_mock.py`). İki terminal:

```bash
# Terminal 1 (taklit sunucu):
cd ~/Masaüstü/teknofest_gorev2 && python3 resmi_mock.py --limit 600 --drop 450-599
# Terminal 2 (yarışma komutunun TA KENDİSİ, sadece URL yerelde):
cd ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU
rm -rf _images/YEREL_PROVA
EVALUATION_SERVER_URL="http://127.0.0.1:5580/" HF_HUB_OFFLINE=1 python3 main.py
```

Bitince Terminal 1'i Ctrl+C ile kapat. Gönderimler `mock_gonderimler.jsonl`e yazılır.
16 Tem provası: 600/600 kare 3 dk 22 sn'de; sağlıklı yankı hatası tam 0; kör bölge
ort. 7.9 m; G1 8.3 kutu/kare; G3 iki pencerede 86 kutu. (FastSAM ağırlığı bu provada
otomatik indirilip önbelleğe alındı — yarışmada tekrar inmez.)

## 7) DOĞRULANANLAR (2026-07-16 gecesi, test sunucusunda)

- Giriş + token + ilerleme sorgusu: ✅ canlı (`Login Successfully`, progress 2250/2250)
- Referans uç noktası: ✅ canlı (5 referans + pencereler çekildi)
- 3 görev tek süreçte, aynı GPU'da: ✅ (10 karelik uçtan uca kuru koşu; payload
  serileştirme birebir doğrulandı — sınıf tuple/URL kuralı dahil)
- Kare döngüsü + gönderim mekaniği: ✅ (aynı main.py ile önceki 2250/2250 canlı koşu)
- Eski çalışma klasörü kenara alma: ✅ (run_yarisma_eski_* oluşuyor)
