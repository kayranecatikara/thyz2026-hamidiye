# MASTER PROMPT — SP-SLAM3 Kurulumu + TEKNOFEST Görev 2 Entegrasyonu

## ROLÜN VE BAĞLAM

Sen bu projede benim sistem mühendisim ve entegrasyon geliştiricimsin. Benimle Türkçe konuş.

- **Makine:** Intel Core i7 (13. nesil) işlemcili bilgisayar, NVIDIA RTX 4060 ekran kartı (8 GB VRAM, Ada Lovelace / sm_89), 16 GB RAM, temiz kurulmuş Ubuntu 22.04. Üzerinde henüz hiçbir geliştirme aracı yok.
- **Hedef repo:** https://github.com/kayranecatikara/SP_SLAM3 (ORB-SLAM3 + SuperPoint + LightGlue + NetVLAD/CosPlace). Repo Ubuntu 20.04'te test edilmiş; 22.04'e biz uyarlayacağız.
- **Nihai amaç:** TEKNOFEST Havacılıkta Yapay Zeka yarışması **Görev 2** — GPS kesintisi sırasında salt kamera görüntüsünden hava aracının referans koordinat sistemindeki (x, y, z) yer değiştirmesini metre cinsinden kestirmek.
- **Yarışma kısıtları (asla unutma):**
  - Yarışma ortamı **tamamen offline** (internet yok, yerel ağda bir sunucu var).
  - Video ~7.5 FPS, oturum başına ~2250 kare, toplam süre 60 dk → kare başına ortalama işleme bütçesi **< 1.6 saniye**.
  - Kamera yere 70–90° açıyla bakıyor (nadir/nadire yakın), görüntüler ~4K çözünürlükte.
  - Sunucu her karede referans pozisyon (x, y, z) + **sağlık bayrağı** gönderir. Sağlık=1 iken referansı aynen geri göndermek serbest (sıfır hata). Sağlık=0 iken kendi kestirimimizi göndermek ZORUNLU. İlk ~450 kare garanti sağlıklı.
  - Skor: **Denklem 2 = (1/N) · Σ √(Δx² + Δy² + Δz²)** — hizalama YAPILMADAN, mutlak ortalama Öklid hatası. Düşük hata = yüksek puan.
- Monoküler SLAM ölçeksiz ve kendi keyfi koordinat sisteminde çıktı verir; metrik/hizalı çıktıyı **bizim yazacağımız hizalama katmanı** üretecek (FAZ 8.3).

## ÇALIŞMA KURALLARIN (her fazda geçerli)

1. **Faz faz ilerle.** Her fazın sonundaki DOĞRULAMA adımını çalıştırmadan ve geçmeden bir sonraki faza başlama.
2. **SETUP_LOG.md tut.** Çalıştırdığın önemli komutları, kurulan sürümleri, karşılaşılan hataları ve çözümlerini bu dosyaya ekle. Bu dosya yarışma günü offline kurulum rehberimiz olacak.
3. **sudo gerektiren her komuttan önce** ne yapacağını tek cümleyle açıkla.
4. **Yama politikası:** Derleme hatası çıkarsa → hatayı oku → kök nedeni bana bir cümleyle açıkla → mümkün olan en küçük yamayı uygula → yamayı SETUP_LOG.md'ye `## PATCH` başlığıyla (dosya adı + neden + diff özeti) kaydet. Repoda büyük mimari değişiklik yapma.
5. **Reboot/BIOS gerektiren adımlarda DUR** ve bana ne yapacağımı söyle. Oturum yeniden başladığında ilk işin SETUP_LOG.md'yi okuyup kaldığın fazdan devam etmek.
6. Bir indirme linki kırıksa aynı sürümü sağlayan alternatif resmi kaynak bul; sürüm uyumunu bozma.
7. HOME dizini dışında yıkıcı işlem yapma; hiçbir git remote'una push etme.
8. Bir kütüphaneyi kurmadan önce zaten kurulu mu diye kontrol et.

## FAZ 0 — Sistem Keşfi

- `lsb_release -a`, `uname -r`, `df -h` (kök bölümde **en az 40 GB** boş alan olmalı), `free -h`, `lspci | grep -i nvidia`, `mokutil --sb-state`.
- **Secure Boot AÇIKSA DUR:** Bana bildir; BIOS'tan kapatmam ya da sürücü kurulumunda MOK kaydı yapmam gerekecek. Onayım olmadan FAZ 1'e geçme.
- `sudo apt update && sudo apt upgrade -y`, ardından `curl git wget unzip build-essential` kur.
- **DOĞRULAMA:** Disk/RAM yeterli, GPU listede görünüyor, Secure Boot durumu raporlandı.

## FAZ 1 — NVIDIA Sürücü + CUDA Toolkit 12.2

- `ubuntu-drivers devices` ile önerilen sürücüyü bul; `nvidia-driver-535` veya daha yenisini apt ile kur. Reboot gerektiğinde dur, bana söyle.
- Reboot sonrası `nvidia-smi` ile RTX 4060'ın göründüğünü doğrula.
- CUDA Toolkit 12.2'yi NVIDIA'nın **Ubuntu 22.04 (ubuntu2204)** resmi deposundan kur. `cuda-toolkit-12-2` paketini kur; sürücüyü de sürükleyen `cuda` meta-paketini KULLANMA (sürücü zaten kurulu, çakışma yaratır).
- `~/.bashrc`'ye ekle: `PATH=/usr/local/cuda-12.2/bin:$PATH` ve `LD_LIBRARY_PATH=/usr/local/cuda-12.2/lib64:$LD_LIBRARY_PATH`.
- **cuDNN'i ŞİMDİLİK KURMA:** FAZ 4'te indireceğimiz LibTorch "shared-with-deps" paketi kendi cuDNN kopyasını taşır. Çalışma zamanında `libcudnn` hatası görürsek o zaman CUDA 12 uyumlu cuDNN 8.9.x kurarız.
- **DOĞRULAMA:** `nvidia-smi` çalışıyor; `nvcc --version` 12.2 gösteriyor.

## FAZ 2 — APT Bağımlılıkları

```
sudo apt install -y build-essential cmake git pkg-config \
  libopencv-dev libeigen3-dev \
  libboost-serialization-dev libssl-dev \
  libgl1-mesa-dev libglew-dev libpython3-dev \
  python3-venv python3-pip ffmpeg
```
- Not: 22.04'te apt OpenCV **4.5.4** verir; repo 4.2–4.10 aralığında test edilmiş, uyumludur. OpenCV'yi kaynaktan DERLEME.
- **DOĞRULAMA:** `pkg-config --modversion opencv4` → 4.5.x; `dpkg -l | grep eigen` → 3.4.x.

## FAZ 3 — Pangolin

- `stevenlovegrove/Pangolin` reposunu `--recursive` klonla, **v0.8** tag'ine geç (22.04'te temiz derlenir; repo 0.6+ istiyor), `cmake + make -j$(nproc) + sudo make install + sudo ldconfig`.
- 22.04'e özgü derleme hatası çıkarsa yama politikasını uygula.
- **DOĞRULAMA:** `ldconfig -p | grep -i pango` kütüphaneyi listeliyor.

## FAZ 4 — LibTorch 2.3.0 (CUDA 12.1, cxx11 ABI)

- İndir: `https://download.pytorch.org/libtorch/cu121/libtorch-cxx11-abi-shared-with-deps-2.3.0%2Bcu121.zip` → `/usr/local`'e aç (cu121 derlemesi 12.2 sürücüsüyle uyumludur).
- `~/.bashrc`'ye: `export TORCH_DIR=/usr/local/libtorch/share/cmake/Torch`.
- Mini bir CMake test programı yazıp derle: `torch::cuda::is_available()` **true** dönmeli ve bir tensörü GPU'ya taşıyabilmeli.
- **DOĞRULAMA:** Test programı CUDA'yı görüyor.

## FAZ 5 — SP_SLAM3 Klonla ve Derle

- `git clone --recursive https://github.com/kayranecatikara/SP_SLAM3.git ~/SP_SLAM3`
- `chmod +x build.sh && ./build.sh` (gerekirse `TORCH_DIR=... ./build.sh`).
- Bilinen 22.04 risk alanları (çıkarsa yama politikası): GCC 11 ile Thirdparty g2o/DBoW3'te deprecated uyarıları, OpenCV 4.5 API farkları, eksik `#include <thread>/<memory>` satırları, LibTorch–OpenCV ABI karışıklığı (cxx11 ABI'de kaldığımız sürece sorun beklenmez).
- **DOĞRULAMA:** `lib/` altında paylaşımlı kütüphane ve `Examples/Monocular/mono_euroc` binary'si oluştu; `ldd` ile torch/opencv bağları çözülüyor.

## FAZ 6 — EuRoC ile Fonksiyon Testi

- EuRoC **MH_01_easy** sekansını ETH sunucusundan indir (~1.4 GB), `Examples/Monocular/MH_01_easy` altına aç.
- Çalıştır:
```
./Examples/Monocular/mono_euroc Vocabulary/superpoint_voc.dbow3 \
  Examples/Monocular/EuRoC.yaml Examples/Monocular/MH_01_easy \
  Examples/Monocular/EuRoC_TimeStamps/MH01.txt
```
- `CameraTrajectory.txt` üretilmeli. Kaç karenin takip edildiğini raporla.
- Python venv kur (`~/venvs/slam`), içine `evo` kur, `evo_ape tum <GT> CameraTrajectory.txt -as` ile ATE ölç. **Bu sadece fonksiyon testi** — `-as` hizalamalı ATE'dir, yarışma metriği DEĞİLDİR; sonucu yorumlamadan sadece "sistem çalışıyor" kanıtı olarak logla.
- **DOĞRULAMA:** ATE ~0.02–0.10 m bandında ve takip oranı yüksek.

## FAZ 7 — LightGlue Export

- venv içine uygun `torch/torchvision` (cu121) ve `git+https://github.com/cvg/LightGlue.git` kur.
- `python scripts/export_lightglue.py --output lightglue.pt` çalıştır (model ağırlıkları bu aşamada internetten iner — offline pakete gireceği için dosyayı sakla).
- `Examples/Monocular/EuRoC.yaml` içinde `LightGlue.model_path` ve `SuperPoint.useFP16: 1`, `LightGlue.useFP16: 1` ayarla; FAZ 6 testini tekrarla, takip oranı farkını logla.
- **DOĞRULAMA:** LightGlue etkin koşuda takip oranı ≥ önceki koşu.

## FAZ 8 — YARIŞMA ENTEGRASYONU

Çalışma klasörü: `~/teknofest_gorev2/`. Ben şu varlıkları `~/teknofest_gorev2/assets/` altına koyacağım — **eksikse benden iste, uydurma:**
- Yarışmanın kamera kalibrasyon dosyası (Kamera_Kalibrasyon),
- Resmi örnek uçuş videosu + her kareye ait ground-truth pozisyon dosyası,
- Resmi `TAKIM_BAGLANTI_ARAYUZU` istemci kodu.

### 8.1 Headless SLAM sürücüsü (C++)
- `mono_euroc.cc`'yi temel alarak `Examples/Monocular/mono_folder_watch.cc` yaz:
  - Girdi: bir `inbox/` klasörünü izler; `<frame_id>.png/jpg` geldikçe sırayla işler.
  - `ORB_SLAM3::System`'i **bUseViewer=false** ile başlat (Pangolin penceresi yok — yarışmada görselleştirme istemiyoruz).
  - Her karede `TrackMonocular` dönüşünden **kamera→dünya** pozunu çıkar (`Tcw.inverse()`), `outbox/pose.txt`'e satır olarak ekle (flush'lı): `frame_id tx ty tz qx qy qz qw state`. `state` için `GetTrackingState()` kullan (OK / LOST / NOT_INITIALIZED).
- CMakeLists'e ekle, derle.

### 8.2 Yarışma kamera YAML'ı
- assets'teki kalibrasyondan fx, fy, cx, cy, distorsiyon katsayılarını oku.
- Karar: kareleri **genişlik 1280 piksele** küçülteceğiz (4K'yı SLAM'e vermek israf). fx, fy, cx, cy'yi küçültme oranıyla çarp; **distorsiyon katsayıları (k1,k2,p1,p2) değişmez.** `Camera.fps: 7.5`, başlangıç `nFeatures: 800`, FP16 açık. CUDA bellek yetmezliği (OOM) olursa önce genişliği 960'a düşür.
- `teknofest.yaml` olarak kaydet.

### 8.3 Python köprüsü + hizalama (`bridge.py`) — projenin kalbi
- Resmi istemciyi sarmala; istemci yoksa aynı JSON akışını taklit eden `mock_server.py` da yaz (örnek videoyu + GT pozisyonlarını kare kare servis eder, sağlık bayrağını yapılandırılabilir bir aralıkta 0'a düşürür).
- Ana döngü (her kare):
  1. Sunucudan kare + pozisyon + sağlık bilgisini al; kareyi 1280 genişliğe küçültüp `inbox/`'a yaz.
  2. `pose.txt`'te bu frame_id'nin satırını bekle (**timeout 1.2 s**).
  3. **Sağlık=1:** Sunucudan gelen referans (x,y,z)'yi AYNEN geri gönder. Ayrıca (SLAM_pos, ref_pos) çiftini hizalama tamponuna ekle. SLAM her koşulda kare yemeye devam eder — asla durdurma.
  4. **Hizalama:** Tampon ≥ 30 çift olunca **Umeyama** benzerlik dönüşümünü (s, R, t) çöz — scipy'ye bel bağlama, numpy SVD ile kapalı formu kendin yaz. Sağlık=1 sürdükçe kayan pencereyle (son ~300 çift) yeniden çöz. **Dejenerasyon koruması:** ilk 450 karedeki yörünge düz çizgiye yakınsa (en küçük iki tekil değer küçükse) tam 3B dönme belirsizleşir; bu durumda z eksenini dünya-dikey varsay, x-y düzleminde 2B dönme+ölçek çöz, z için ayrı ölçek katsayısı hesapla.
  5. **Sağlık=0:** Gönderilecek değer = `s·R·SLAM_pos + t`.
  6. **Sigorta:** `state != OK` veya poz timeout olursa **sabit-hız ölü hesabı** uygula (son 5 sağlıklı çıktının ortalama hız vektörüyle ekstrapolasyon). Sunucuya ASLA boş/NaN gönderme.
  7. Gönderilen her şeyi `predictions.csv`'ye logla: `frame_id, x, y, z, saglik, kaynak(echo|slam|deadreckon), islem_suresi_s`.

### 8.4 Değerlendirici (`evaluate_denklem2.py`)
- Girdi: `predictions.csv` + GT pozisyon dosyası.
- Çıktı: **Denklem 2** skoru (hizalama YAPMADAN ortalama Öklid hatası), yalnız sağlık=0 dilimi için ayrı skor, ve eksen bazlı hata grafiği (matplotlib, png).

### 8.5 Uçtan uca prova
- `mock_server.py` ile örnek videoyu akıtarak tüm boru hattını çalıştır. Farklı kesinti senaryoları dene (erken/geç başlayan, kısa/uzun sağlıksız pencere).
- Raporla: Denklem 2 skoru, ortalama ve p95 kare işleme süresi (**hedef: ort < 1.6 s**), SLAM'in LOST'a düştüğü kare sayısı ve ölü hesabın devreye girme oranı.
- Provayı **bir kez de Wi-Fi'yi tamamen kapatarak** tekrarla: hiçbir bileşen (torch hub, LightGlue vb.) ağa çıkmaya çalışmamalı.

### 8.6 Offline paket
- `~/teknofest_gorev2/offline_bundle/` altında topla: model dosyaları (`superpoint.pt`, `lightglue.pt`, `Vocabulary/*.dbow3`), derlenmiş binary + `lib/`, `teknofest.yaml`, Python bağımlılıkları için `pip download` ile wheel arşivi, `SETUP_LOG.md` ve "sıfır internetle bu sistem nasıl ayağa kalkar" adımlarını anlatan `OFFLINE_README.md`.

## BAŞARI KRİTERLERİ (hepsi işaretlenmeden iş bitmedi)

- [ ] EuRoC MH_01 çalışıyor, takip oranı > %90
- [ ] Örnek yarışma videosunda uçtan uca Denklem 2 skoru üretiliyor
- [ ] Ortalama işleme süresi < 1.6 s/kare (p95 dahil raporlandı)
- [ ] SLAM LOST olsa bile her kareye geçerli çıktı gidiyor (NaN/boş yok)
- [ ] Wi-Fi kapalı provada sistem ağa çıkmadan çalıştı
- [ ] offline_bundle eksiksiz, OFFLINE_README.md yazıldı

## İLK İŞİN

FAZ 0'ı çalıştır, bulgularını raporla ve SETUP_LOG.md'yi başlat.
