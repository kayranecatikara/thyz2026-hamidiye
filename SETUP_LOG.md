# SETUP_LOG — SP-SLAM3 + TEKNOFEST Görev 2

> Bu dosya yarışma günü offline kurulum rehberidir. Her faz, çalıştırılan önemli komutlar,
> kurulan sürümler, hatalar ve çözümleri buraya işlenir.

## FAZ 0 — Sistem Keşfi (2026-07-12)

### Bulgular
| Öğe | Değer | Durum |
|---|---|---|
| OS | Ubuntu 22.04.5 LTS (jammy) | ✓ hedefle uyumlu |
| Kernel | 6.8.0-134-generic (HWE) | ✓ |
| Kök disk | 98 GB toplam, **71 GB boş** (%24 dolu) | ✓ ≥ 40 GB şartı sağlandı |
| RAM | 15 Gi + 2 Gi takas | ✓ |
| GPU | NVIDIA 01:00.0 VGA, PCI ID 28a0 rev a1 (AD107 → RTX 4060 Laptop, sm_89) | ✓ listede görünüyor |
| Secure Boot | **disabled** (`mokutil --sb-state`) | ✓ MOK kaydı GEREKMİYOR, sürücü kurulumu engelsiz |

### Komutlar
```bash
lsb_release -a          # Ubuntu 22.04.5
uname -r                # 6.8.0-134-generic
df -h /                 # 71G boş
free -h                 # 15Gi RAM
lspci | grep -i nvidia  # 01:00.0 NVIDIA 28a0
mokutil --sb-state      # SecureBoot disabled
```

### Notlar
- Sistem temiz kurulum; `~/` altında yalnız standart klasörler var, geliştirme aracı yok.
- Çalışma klasörü: `/home/zeylo/Masaüstü/teknofest_gorev2` (MASTER_PROMPT.md burada).
- Temel araç kontrolü (Kural 8): `curl 7.81`, `git 2.34`, `wget 1.21`, `unzip 6.0`,
  `build-essential 12.9` (gcc 11.4.0) **zaten kurulu**; `cmake` eksik (FAZ 2'de kurulacak).

### Engel: sudo şifresi → ÇÖZÜLDÜ
- Claude'un kabuk oturumu terminalsiz olduğundan `sudo` şifre soramıyor.
- Çözüm: kuruluma özel geçici NOPASSWD kuralı yazıldı (`/etc/sudoers.d/99-claude-setup`,
  0440, `visudo -c` ile doğrulandı). Kurulum bitince kaldırılacak:
  `sudo rm /etc/sudoers.d/99-claude-setup`. (Yarışma günü rehberi için not: offline
  kurulumda da sudo gerekir; ya aynı kural ya da elle şifre.)

### apt update/upgrade + temel araçlar
```bash
sudo apt update    # Tüm paketler güncel çıktı (22.04.5 imajı taze)
sudo apt install -y curl git wget unzip build-essential   # hepsi zaten kuruluydu
```

### FAZ 0 DOĞRULAMA ✓
- Disk 71 GB boş (≥40 GB) ✓ | RAM 15 Gi ✓ | GPU lspci'de görünüyor ✓
- Secure Boot: disabled (raporlandı) ✓ | apt güncel, temel araçlar kurulu ✓

## FAZ 1 — NVIDIA Sürücü + CUDA Toolkit 12.2 (2026-07-12)

### Sürücü: ZATEN KURULUYDU (Kural 8)
- `dpkg -l` → `nvidia-driver-580` 580.159.03-0ubuntu0.22.04.1 kurulu, modüller yüklü.
  (Muhtemelen Ubuntu kurulumundaki "üçüncü taraf sürücüler" seçeneğiyle gelmiş.)
- `nvidia-smi` ✓: **RTX 4060 Laptop GPU, 8188 MiB VRAM, sürücü 580.159.03, CUDA 13.0'a
  kadar destek** → CUDA 12.2 toolkit ile geriye dönük uyumlu. 580 ≥ 535 şartı sağlandı.
- `ubuntu-drivers devices` önerisi 595-open idi; çalışan 580'e DOKUNULMADI (risk yok).
- **Reboot GEREKMEDİ** (sürücü zaten aktif).

### CUDA Toolkit 12.2 kurulumu
```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb && sudo apt update
sudo apt install -y cuda-toolkit-12-2   # 'cuda' meta-paketi DEĞİL (sürücüye dokunmaz)
```
- NVIDIA deposu 23 paket için upgrade önerdi → sürücü bileşenlerini değiştirmemek için
  YÜKSELTİLMEDİ; yalnız cuda-toolkit-12-2 (aday 12.2.2-1) kuruldu.

### Paralel indirmeler (build yok, sadece fetch — faz sırası korunuyor)
- LibTorch 2.3.0+cu121 zip → `~/Masaüstü/teknofest_gorev2/downloads/` ✓ 2,4 GB indi
  (offline paket için saklanacak)
- Pangolin klon + v0.8 checkout ✓ → `~/Pangolin` (git describe: v0.8)
- SP_SLAM3 --recursive klon ✓ → `~/SP_SLAM3` (98 MB)
- EuRoC MH_01_easy.zip → indirme sürüyor (ETH sunucusu yavaş; FAZ 6'ya kadar vakit var)

### SP_SLAM3 repo keşfi (FAZ 5–8 için kritik notlar)
1. **`Vocabulary/superpoint_voc.yml.gz` bir Git-LFS İŞARETÇİSİ** (134 B; gerçek boyut
   122.487.857 B ≈ 122 MB). `superpoint_voc.dbow3` repoda HİÇ YOK.
   → Gerekecek: `apt install git-lfs` + `git lfs pull`, sonra
   `./tools/convert_vocab Vocabulary/superpoint_voc.yml.gz Vocabulary/superpoint_voc.dbow3`
   (tools/convert_vocab derlemeyle birlikte oluşuyor olmalı).
2. `superpoint.pt` (5 MB TorchScript zip) GERÇEK dosya, repoda hazır ✓.
3. **`Examples/Monocular/mono_teknofest.cc` ZATEN VAR** (takım arkadaşı eklemiş):
   düz klasör + WebP/PNG/JPG, esnek timestamp, kalibrasyon çözünürlüğüne otomatik
   resize, `SLAM_NO_VIEWER` env ile headless. Ama poz akışlı yazılmıyor (sonda toplu
   SaveTrajectory) → FAZ 8.1 `mono_folder_watch.cc` yine gerekli (kare-kare flush).
4. **`Examples/Monocular/THYZ.yaml` ZATEN VAR**: THYZ 2025 kalibrasyonu, 960×540
   (4K'dan küçültme), fx=670.13 fy=503.14 cx=477.12 cy=281.20, k1=0.0798 k2=-0.1867,
   fps 7.5, nFeatures 800, nLevels 1. FAZ 8.2'de resmi asset ile karşılaştırılacak.
5. **FP16 UYARISI (takım arkadaşının notu, THYZ.yaml içinde):** "FP16 KAPALI: her
   frame model->to(kFloat16) kararsızlık/çökme yapıyor, kazanç minimal." → FAZ 7'de
   FP16 denenecek ama çökerse FP32'de kalınıp raporlanacak.
6. Git geçmişinde işe yarar düzeltmeler zaten var: MapPoint depth-invariance fix
   (nadir uçuş için önemli), CLAHE ön-işleme, relocalization aday sınırı, loop-closing
   boş covisibility koruması, WebP desteği.
7. `mono_euroc.cc` da `SLAM_NO_VIEWER` env değişkenini destekliyor (headless test kolay).
8. build.sh: apt bağımlılıkları kurar; Pangolin yoksa /tmp'ye v0.6 klonlar (BİZ v0.8'i
   FAZ 3'te kuracağız → bu adımı atlar); /usr/local/libtorch yoksa 2.2.2 İNDİRİR
   (biz 2.3.0'ı FAZ 4'te kuracağız → atlar); Sophus/DBoW3/g2o Thirdparty'den derlenir;
   `-DTorch_DIR` cmake'e geçilir. DBoW3 `make -j3` (linker OOM önlemi).
9. CMakeLists.txt: örnek eklemek 2 satır (add_executable + target_link_libraries);
   `tools/convert_vocab` ana derlemeyle geliyor; `-march=native` kullanılıyor
   (binary bu makineye özgü — yarışma makinesi de bu makine, sorun değil);
   USE_ORBFEATURES=0 (SuperPoint modu); realsense2 opsiyonel (yoksa sorun çıkmaz).

### FAZ 1 DOĞRULAMA ✓ (2026-07-12)
- `nvidia-smi` ✓ RTX 4060, sürücü 580.159.03
- `nvcc --version` ✓ release 12.2, V12.2.140 (`/usr/local/cuda-12.2`)
- `~/.bashrc`'ye PATH + LD_LIBRARY_PATH eklendi
- cuDNN kurulmadı (talimat: LibTorch shared-with-deps kendi kopyasını taşıyor)

## FAZ 2 — APT Bağımlılıkları (2026-07-12)

```bash
sudo apt install -y build-essential cmake git pkg-config \
  libopencv-dev libeigen3-dev libboost-serialization-dev libssl-dev \
  libgl1-mesa-dev libglew-dev libpython3-dev python3-venv python3-pip ffmpeg git-lfs
```
- Listeye ek: `git-lfs` (Vocabulary/superpoint_voc.yml.gz LFS işaretçisini çekmek için).

### FAZ 2 DOĞRULAMA ✓
- `pkg-config --modversion opencv4` → **4.5.4** ✓ (beklenen 4.5.x; kaynaktan derlenmedi)
- `libeigen3-dev` → **3.4.0-2ubuntu2** ✓
- cmake 3.22.1, git-lfs 3.0.2, Python 3.10.12

## FAZ 3 — Pangolin v0.8 (2026-07-12)

```bash
cd ~/Pangolin && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DBUILD_EXAMPLES=OFF
make -j$(nproc)
sudo make install && sudo ldconfig
```
- Paralelde: `cd ~/SP_SLAM3 && git lfs install --local && git lfs pull` (122 MB sözlük).

### FAZ 3 DOĞRULAMA ✓
- `ldconfig -p | grep pango` → tüm `libpango_*.so` `/usr/local/lib`'de ✓
- `/usr/local/lib/cmake/Pangolin/PangolinConfig.cmake` mevcut ✓ (build.sh bunu görüp
  kendi Pangolin v0.6 kurulumunu atlayacak)
- LFS sözlüğü çekildi: `superpoint_voc.yml.gz` artık 117 MB gerçek gzip ✓

## FAZ 4 — LibTorch 2.3.0 cu121 (2026-07-12)

```bash
sudo unzip -q downloads/libtorch-cxx11-abi-shared-with-deps-2.3.0+cu121.zip -d /usr/local/
echo "/usr/local/libtorch/lib" | sudo tee /etc/ld.so.conf.d/libtorch.conf && sudo ldconfig
echo 'export TORCH_DIR=/usr/local/libtorch/share/cmake/Torch' >> ~/.bashrc
```
- `/usr/local/libtorch` 4,3 GB; kendi cuDNN 8 kopyasını taşıyor (libcudnn_*.so.8) →
  sistem cuDNN'i kurulmadı (plana uygun).
- ld.so.conf.d kaydı build.sh'ın kendi yaklaşımıyla birebir aynı.

### FAZ 4 DOĞRULAMA ✓
- Mini test: `~/Masaüstü/teknofest_gorev2/tests/torch_cuda_test/` (yarışma günü hızlı
  sağlık kontrolü olarak yeniden kullanılabilir):
  LibTorch 2.3.0, **CUDA available: true**, cuDNN true, GPU sayısı 1,
  tensör `cuda:0`'a taşındı, matmul sonucu sonlu → `TORCH_CUDA_TEST_OK`.

## FAZ 5 — SP_SLAM3 Derlemesi (2026-07-12)

- `./build.sh` çalıştırıldı (repo zaten klonluydu). Not: RAM 15 GB + `make -j$(nproc)`
  torch başlıklı TU'larda OOM riski taşıyor; OOM olursa düşük -j ile tekrar denenecek.
- build.sh adımları: apt bağımlılıkları ✓, Pangolin atlandı (bizimki görüldü) ✓,
  LibTorch atlandı (bizimki görüldü) ✓, Sophus ✓, DBoW3 ✓, g2o ✓, ana derleme → OOM.

## PATCH — OOM: ana derlemede cc1plus öldürüldü (kod yaması DEĞİL, prosedür düzeltmesi)
- **Dosya:** yok (repo koduna dokunulmadı). **Aşama:** build.sh 6. adım (ana kütüphane).
- **Hata:** `c++: fatal error: Süreç durduruldu signal terminated program cc1plus`
  (Tracking.cc.o derlenirken). dmesg teyidi: `Out of memory: Killed process (cc1plus),
  anon-rss ≈ 1.28 GB`.
- **Kök neden:** `make -j20` (nproc=20) × ~1,3-1,6 GB/derleyici süreci ≈ 26-30 GB talep
  > 15 GB RAM + 2 GB takas. LibTorch başlıkları TU başına bellek kullanımını şişiriyor.
- **Çözüm (1. deneme, YETMEDİ):** `make -j6` → yine OOM. İkinci dmesg kaydı öğretici:
  cc1plus tek başına **2,85 GB RSS**'e çıktı (Tracking.cc; torch+g2o+opencv başlıkları,
  -O3 -march=native). Optimizer/G2oTypes gibi diğer dev TU'larla yan yana gelince
  -j6 bile taşıyor.
- **Çözüm (kalıcı):** (a) geçici 8 GB takas dosyası:
  `sudo fallocate -l 8G /swapfile-claude && sudo chmod 600 /swapfile-claude &&
   sudo mkswap /swapfile-claude && sudo swapon /swapfile-claude`
  (fstab'a YAZILMADI — reboot'ta gider; gerekirse aynı komutlarla yeniden aç),
  (b) `make -j4`. **Yarışma günü notu:** SP_SLAM3'ü bu makinede derlerken önce takası
  aç, sonra `make -j4`; build.sh sıfırdan koşarsa 6. adım OOM'lar → build/ içinde
  `make -j4` ile devam.

### EuRoC indirme aksaklığı → ÇÖZÜM: Research Collection API (Kural 6)
- robotics.ethz.ch **TCP seviyesinde ölü** (129.132.38.186:80'e bağlantı kurulamıyor);
  8 denemeli wget de exit=4 ile düştü.
- Ders: `pkill -f "wget.*MH_01"` deseni, komut satırında aynı metni taşıyan kendi bash
  sarmalayıcısını da öldürüyor (kendine ateş). pkill'e tam süreç adı vermeli.
- Resmi alternatif bulundu: ETH Research Collection (DOI 10.3929/ethz-b-000690084).
  Web UI (`/bitstreams/<uuid>/download`) Express SSR katmanında HTTP 500 veriyor,
  fakat **DSpace REST API sağlam**:
  `https://www.research-collection.ethz.ch/server/api/core/bitstreams/<uuid>/content`
  → HTTP 206, gerçek zip (PK imzası), ~9,6 MB/s, resume destekli.
- Sekanslar tek tek yok; `machine_hall.zip` (12,7 GB, MH_01–MH_05 hepsi) indiriliyor:
  bitstream UUID `7b2419c1-62b5-4714-b7f8-485e5fe3e5fe`. Sadece MH_01_easy açılacak.
- Paralel: `~/venvs/slam` venv + `evo` kurulumu (FAZ 6 ölçümü için).
- machine_hall.zip 12 GB indi ✓; içinden yalnız MH_01_easy.zip çıkarılıp
  `Examples/Monocular/MH_01_easy/` altına açıldı (3682 kare + mav0 GT) ✓.

## FAZ 6 — EuRoC MH_01 Fonksiyon Testi (2026-07-12)

### Ön hazırlık
- Sözlük dönüşümü: `./tools/convert_vocab Vocabulary/superpoint_voc.yml.gz
  Vocabulary/superpoint_voc.dbow3` → 113 MB dbow3 ✓ (~7 dk sürdü).
- `superpoint.pt` GÖRELİ yolla yükleniyor (SPextractor.cc:91) → **binary'yi daima
  repo kökünden çalıştır** (yarışma günü de geçerli).
- lightglue.pt / cosplace.pt yokken kod catch'leyip L2/DBoW3'e düşüyor (çökme yok) ✓.

### Koşu
```bash
cd ~/SP_SLAM3
SLAM_NO_VIEWER=1 ./Examples/Monocular/mono_euroc Vocabulary/superpoint_voc.dbow3 \
  Examples/Monocular/EuRoC.yaml Examples/Monocular/MH_01_easy \
  Examples/Monocular/EuRoC_TimeStamps/MH01.txt
```

### FAZ 6 DOĞRULAMA ✓
- **Takip: 3644/3682 poz = %99,0** (hedef >%90) ✓
- Kare işleme: medyan 46 ms / ort. 47 ms (GPU SuperPoint, FP16=1 sorunsuz — bu koşuda)
- ATE ölçümü (SADECE fonksiyon testi, `-as` Sim3 hizalı, yarışma metriği DEĞİL):
  GT: `evo_traj euroc mav0/.../data.csv --save_as_tum`;
  yörünge ns→s çevrimi: `LC_ALL=C awk 'NF==8 {printf "%.9f ...", $1/1e9, ...}'`
  → `evo_ape tum GT traj -as` = **RMSE 0,0447 m** (ort 0,0405, medyan 0,0398,
  maks 0,219) — 0,02–0,10 m bandında ✓. Koşu LightGlue'SUZ baseline'dı.

## FAZ 7 — LightGlue Export (2026-07-12)

- venv'e `torch==2.3.0+cu121`, `torchvision==0.18.0+cu121`,
  `git+https://github.com/cvg/LightGlue.git` kuruldu.
- `python scripts/export_lightglue.py --output lightglue.pt` → 46 MB TorchScript ✓.
- **Offline paket için ağırlık dosyası:** `~/.cache/torch/hub/checkpoints/
  superpoint_lightglue_v0-1_arxiv.pth` (46 MB) — 8.6'da kopyalanacak.

## PATCH — LightGlue FP16 çökmesi → FP32'de bırakıldı
- **Dosya:** `Examples/Monocular/EuRoC.yaml` (yalnız ayar; kod değişikliği yok).
- **Hata:** `LightGlue.useFP16: 1` ile koşu ~ilk karede SIGABRT (exit 134):
  `RuntimeError: expected mat1 and mat2 to have the same dtype: float != c10::Half`.
- **Kök neden:** lightglue.pt `torch.jit.trace` ile üretildi; trace, dtype'ları grafiğe
  gömer. C++ tarafı FP16 istayınca ağırlıklar Half'e çevriliyor ama grafikteki işlemler
  float bekliyor → dtype çarpışması. (Takım arkadaşının THYZ.yaml'daki "FP16 kararsız"
  notunun teknik açıklaması.)
- **Çözüm:** `LightGlue.useFP16: 0` (LightGlue ETKİN kalıyor, FP32'de; SuperPoint FP16=1
  sorunsuz çalışıyor). Yarışma YAML'ında da böyle olacak. MASTER_PROMPT 8.2'deki
  "FP16 açık" hedefi SuperPoint için geçerli, LightGlue için değil.

### FAZ 7 DOĞRULAMA ✓
| Metrik | Baseline L2 (FAZ 6) | LightGlue FP32 (FAZ 7) |
|---|---|---|
| Takip | 3644/3682 = %99,0 | **3681/3682 = %99,97** (≥ şartı ✓) |
| ATE RMSE (-as) | 0,0447 m | **0,0411 m** (ort 0,0324, medyan 0,0284) |
| Kare süresi | 47 ms | 56 ms |

## FAZ 8 — Yarışma Entegrasyonu (2026-07-12, sürüyor)

### Yol düzeni
- `~/teknofest_gorev2` → `~/Masaüstü/teknofest_gorev2` sembolik bağı kuruldu
  (MASTER_PROMPT'un beklediği yol da çalışıyor; assets/ hangisine konursa görünür).

### 8.1 mono_folder_watch.cc ✓
- `Examples/Monocular/mono_folder_watch.cc` yazıldı + CMakeLists'e eklendi + derlendi.
- inbox/<id>.png|jpg|webp izler, sırayla işler; `outbox/pose.txt`'e flush'lı satır:
  `frame_id tx ty tz qx qy qz qw state`; `outbox/READY` işareti; `inbox/STOP` ile kapanır.
- **PATCH (API farkı):** Bu repo TrackMonocular'ı ESKİ API ile `cv::Mat` (4×4 Tcw)
  döndürüyor (Sophus değil — System.h:119). Twc = [Rᵀ | −Rᵀt] elle kuruldu,
  kuaterniyon Eigen'le. Boş Mat (izleme yok) → `0 0 0 0 0 0 1 <state>` satırı.
- İzleme durumu enum eşlemesi: -1 NOT_READY, 0 NO_IMAGE, 1 NOT_INITIALIZED, 2 OK,
  3 RECENTLY_LOST, 4 LOST.

### 8.3 çekirdek modüller ✓ (resmi asset'ler beklenirken)
- `alignment.py`: Umeyama sim3 (numpy SVD) + düz-çizgi dejenerasyon koruması
  (σ2/σ1 < 0.05 → xy'de 2B dönme+ölçek [gerekirse yansımalı] + z'de ayrı 1B ölçek).
  Öz-testler: sim3 geri kazanım 3.6e-3 m, dejenere+z-ters 2e-14 m, n<30→None ✓.
- `mock_server.py`: newline-JSON TCP; kare+ref+sağlık servis eder, sağlık=0
  aralıkları `--health-drop 700-850` gibi; sağlık=0'da ref GÖNDERMEZ (gerçekçi);
  `--paced` ile gerçek-zaman 7.5fps modu; sunucu tarafı log csv.
- `bridge.py`: SLAM'i spawn eder (READY bekler), PoseReader thread pose.txt tail,
  sağlık=1→echo + çift biriktir (kayan pencere 300), ≥30 çiftte Umeyama refit,
  sağlık=0→s·R·slam+t, sigorta=sabit-hız ölü hesabı (son 5 güvenilir çıktı),
  NaN sigortası, predictions.csv logu. Kareler daima SLAM'e akar (durdurma yok).
- `evaluate_denklem2.py`: hizalamasız Denklem2 + sağlık=0 dilimi + kaynak kırılımı
  + süre istatistiği + eksen bazlı hata grafiği (png).

### 8.5 ön-prova (EuRoC verisiyle — resmi video gelene dek)
- 1000 kare (MH_01 #400–1399), sağlık=0: kare 700–850, lockstep mock.
- Sonuç (1. tur): boru hattı sorunsuz; echo dilimi hata=0.0000 ✓, NaN yok ✓,
  süre ort 0.030 s (p95 0.049) ✓. Denklem2(tümü)=0.207 m; sağlık=0 dilimi 1.372 m:
  kaynak=slam ort 1.54 m (kesinti başında 0.79 m hazır sapma + drift ile 2.18 m'ye),
  deadreckon (ilk 17 kare, SLAM kuyruk yakalarken) 0.044 m.
- **İyileştirme (2. tur):** çapa düzeltmesi — son sağlıklı çiftte `ref − tf(slam)`
  artığı kesinti boyunca sabit eklenir → kesinti başı hatası ~0'a iner, yalnız
  göreli drift kalır.
- **2. tur sonuç (çapalı):** Denklem2(tümü) 0.207→**0.031 m**, sağlık=0 dilimi
  1.372→**0.205 m**, slam kaynak ort 1.540→**0.226 m** (6.8×). Süre ort 0.030 s ✓.
  Grafikler: prova/denklem2_axes.png, prova/denklem2_r2_axes.png.
- Lockstep mock'ta SLAM kuyruğu birikiyor (echo anında yanıtlıyor) → kesinti başında
  17 kare TIMEOUT/deadreckon. Gerçekçi `--paced` (7.5fps) provası resmi videoyla
  yapılacak; SLAM EuRoC 752×480'de ~0.06 s/kare işliyor (7.5fps=0.133 s bütçesinin
  yarısı). 1280 genişlikte yeniden ölçülecek.

### 8.6 offline paket (kısmen — asset'ler beklenirken)
- `offline_bundle/` oluşturuldu: models (superpoint.pt, lightglue.pt,
  superpoint_voc.dbow3, ham .pth), binaries (mono_folder_watch, mono_euroc,
  libORB_SLAM3/DBoW3/g2o.so), wheels (torch cu121 + evo + opencv-headless +
  matplotlib + numpy), OFFLINE_README.md (sıfır-internet kurulum + sağlık kontrolü
  + yarışma koşusu talimatı).
- Disk temizliği: machine_hall.zip (12 GB) silindi; MH_01_easy.zip (1,5 GB) ve
  açılmış sekans duruyor.

### Resmi asset'ler GELDİ (2026-07-12 akşam) — kaynak: resmi GitHub repo + Drive
- Repo: TEKNOFEST-YARISMALAR/havacilikta-yapay-zeka-yarismasi →
  `assets/resmi_repo/` klonlandı. İçerik: Kamera_Kalibrasyon (2024/2025/2026),
  TAKIM_BAGLANTI_ARAYUZU (Python istemci), README (Drive veri seti bağlantısı).
- Veri seti: Drive'dan `assets/veri_seti/` → THYZ 2025 Oturum 1–4 (kare zip +
  Translation.csv + etiket) + Soru-Cevap PDF'leri. Oturum: 2250 kare, 4K
  3840×2160 webp, `frame_XXXXXX.webp`; Translation.csv: x,y,z,frame_numbers
  (ilk kare ≈ 0 referans).
- Takım kimlik bilgileri → `TAKIM_BAGLANTI_ARAYUZU/config/.env` (600 izin;
  EVALUATION_SERVER_URL sunucu açılınca doldurulacak). Şifre bu loga YAZILMADI.

### İstemci mimarisi (kılavuz + kod okuması)
- Lockstep HTTP: login→token, GET current frame (webp indirir), GET translation
  (health_status '0'/'1'/None + gt_translation_x/y/z), detect() çağrısı,
  POST prediction; sunucu tahmin gelmeden SONRAKİ KAREYİ VERMEZ.
- MIN_FRAME_INTERVAL=0.25 s (istemci tabanı, rate limit koruması).
- **Kare başına TEK tahmin hakkı** (tekrar=406) → puanlı oturumda model hazır
  olmadan main.py ÇALIŞTIRMA.
- Payload: DetectedTranslation str(float) — locale güvenli (nokta) ✓.
- Entegrasyon SADECE src/object_detection_model.py'de (resmi kural).

### Soru-Cevap PDF'lerinden kritik kurallar
1. Koordinatlar İLK KAREYE göre mutlak (drone merkezi).
2. İlk 450 kare health=1 + GT; sonrası yarışma sonuna kadar HİÇ gelmeyebilir ya da
   50–100 karelik pencerelerle anlık gelebilir → çok uzun kesinti senaryosu esas.
3. Skorlama Sim3 hizalamasız, doğrudan RMSE (Denklem 2 anlayışı teyit).
4. Kare başına süre limiti YOK; yalnız toplam oturum süresi.
5. İlk 10 kare null gönderilebilir (değerlendirilmez); bozuk kare boş JSON'la geçilir.
6. Sağlık=0 iken sunucu translation'da none gönderir (istemcide health None yolu).
7. Paylaşılan örnek verinin TAMAMI sağlıklı → kesinti mock ile simüle edilir (bizim yol).
8. Q&A'da termal kameradan söz ediliyor — 2025 verisi RGB 4K çıktı; termal ihtimaline
   karşı kalibrasyon dosyasında termal intrinsics de var (512×640).

### 8.2 teknofest.yaml ✓ (resmi 2026 kalibrasyonundan)
- RGB 4K 2026: fx=2792.2 fy=2795.2 cx=1988.0 cy=1562.2, k1=0.0798 k2=-0.1867,
  sensör 4000×3000. 1280 genişlik (ölçek 0.32) → fx=893.504 fy=894.464
  cx=636.160 cy=499.904, 1280×960. Distorsiyon değişmedi. fps 7.5, SP FP16=1,
  LG FP32. → `~/SP_SLAM3/Examples/Monocular/teknofest.yaml`
- **KALİBRASYON MUAMMASI:** 2025 örnek verisi 3840×2160 ama kalibrasyon 4000×3000.
  İki hipotez: (A) üniform merkez-kırpma (fx,fy aynı; cx−80, cy−420), (B) anamorfik
  ölçek (fx×0.96, fy×0.72 — takım arkadaşının THYZ.yaml varsayımı). 700 karelik
  yarış koşuluyor; kazananı transform_rms + takip oranı belirleyecek.
  Yarışma 2026 kamerası 4000×3000 native ise teknofest.yaml doğrudan doğru.

### 8.3 resmi istemci entegrasyonu ✓ (kod düzeyinde)
- Çekirdek `gorev2_engine.py`'ye ayrıldı (Gorev2Engine: SLAM spawn, PoseReader,
  Umeyama+çapa, ölü hesap, csv log). bridge.py (mock) ve resmi
  object_detection_model.py AYNI motoru kullanıyor.
- object_detection_model.py: Görev 2 tam entegre (health None/0/1 yolları);
  Görev 1/3 için sahte örnek tahminler KALDIRILDI (boş liste geçerli; yanlış kutu
  MAP düşürür) — takım modelleri için şablon yorumda.
- Regresyon (EuRoC, motor bazlı): Denklem2 0.019 m, sağlık=0 dilimi 0.126 m —
  önceki elle yazılmış köprüyle uyumlu/daha iyi ✓.

### 8.5 THYZ 2025 verisiyle bulgular (2026-07-12 gece)
- **Oturum içerikleri:** O1 = kıyı (kare 0–~650 AÇIK SU, ~700–1900 kara, son su);
  O2 ve O3 = baştan sona dokulu (kentsel; SLAM dostu); **O4 = TERMAL kamera**
  (512×640, kalibrasyon dosyasındaki termal intrinsics ile eşleşiyor).
- **SU GERÇEĞİ:** su üstünde SuperPoint ~300 zayıf/oynak nokta buluyor; monoküler
  init İMKANSIZ (700 kare hep NOT_INITIALIZED; eşik düşürme de çare değil —
  fiziksel sınır). O1 profilinde "ilk 450 sağlıklı" penceresi su üstünde →
  hizalama ancak karada sağlık dönerse kurulur; dönmezse su bacağı ölü hesap.
  (Mimari buna hazır: SLAM sürekli beslenir, çapa son sağlıklı çifte güncellenir.)
- **Kare içerik metriği:** 1280px gri Laplacian varyansı — su ~3–8, O1 karası
  250–1000, O2/O3 kentsel 2000–19000. (Runtime su tespiti için kullanılabilir.)

## PATCH/OLAY — Disk doldu (kök %100) → kurtarma
- **Belirti:** Bash çıktı yakalama ENOSPC ("temp filesystem full"); ev dizinine
  yazma bile başarısız.
- **Kök neden:** gdown, Drive klasöründeki İLGİSİZ eski yarışma verilerini de
  indirdi: TEKNOFEST UYZ 2021 (1,9 GB) + **UYZ 2022 (20 GB)** → kök tıka basa.
- **Kurtarma:** (1) acil alan: `swapoff && rm /swapfile-claude` (+8 GB anında);
  (2) teşhis: `du -xsh` zinciri; (3) UYZ 2021+2022 SİLİNDİ (gerekirse aynı Drive
  bağlantısından geri indirilebilir — Görev 1 eğitimi içindi, Görev 2'ye gereksiz);
  (4) eski prova run klasörleri silindi. Sonuç: 34 GB boş.
- **Kalıcı önlem:** Gorev2Engine'e `keep_frames=False` — SLAM pozunu üretir üretmez
  inbox PNG'si silinir (2250×4K oturum ≈ 3 GB birikiyordu).
- **Not:** takas dosyası ŞU AN YOK; bir sonraki derlemeden önce OFFLINE_README'deki
  komutla yeniden oluştur.

### THYZ kara segmenti — kalibrasyon yarışı ve geometri teşhisi (2026-07-12 gece)
- Kara yarışı (kare 700–1700, tüm sağlıklı): **cropA** (üniform merkez-kırpma
  varsayımı) kazandı: 464 OK / init ~95 kare / 0 LOST — anamB: 419 OK / ~138 / 1.
  → THYZ 2025 verisi için thyz2025_cropA.yaml esas alındı. (2026 4K native
  4000×3000 gelirse teknofest.yaml zaten doğrudan doğru.)
- **Geometri teşhisi:** küresel Sim3 artığı ~63 m; 100-çift pencere İÇİ artık bile
  ~17 m; hata ekseni x≈46/y≈43/z≈5 m (uçuş sabit irtifa, GT z-açıklığı 5 m).
  Zaman-kayması taraması düz (senkron sorunu DEĞİL). İmza: **yaw drifti** —
  nadir kentselde mono VO rotası bükülüyor; benzerlik dönüşümü büküleni açamaz.
- Koşularda **0 döngü kapatma** (DBoW3 tetiklenmemiş, CosPlace yoktu).
  → `cosplace.pt` export edildi (44 MB; offline_bundle/models'a kopyalandı).
- Çevrimdışı tekrar aracı: `replay_analiz.py` (pose.txt+GT → her kesinti noktası
  için W-pencere+çapa simülasyonu). cropA: W=100 H=75 medyan 38 m; H=250 69 m.
- **Lockstep tuzağı:** canlı lockstep provada echo fazı SLAM'den ~5× hızlı akınca
  ~300 kare backlog oluştu → kesintide pozlar bayat → 415 m (gerçek dışı kötü).
  Gerçek istemcide MIN_FRAME_INTERVAL=0.25 s var → prova artık `--paced --fps 4`
  ile koşuluyor. Motor PNG→**JPEG q95** yazacak şekilde hızlandırıldı.
- Deney kuyruğu: E1 = CosPlace etkin; E2 = 1920 px + nFeatures 1600 (yaw driftine
  karşı daha zengin geometri); ölçüm = replay_analiz + paced senaryo Denklem2.

### Paced senaryo bulguları (O1 kara, kesinti fid 450–699, 4 fps)
- **JPEG hipotezi YANLIŞLANDI:** PNG'ye dönüşte de 14 harita sıfırlaması. Gerçek
  neden: lockstep yarış diziyi yarıda kesmişti (564/1000) — zorlu segmentlere
  (orij. ~1265–1700: çatı/ağaçlık) hiç girmemişti. Kayıplar İÇERİK kaynaklı.
- **Harita-sıfırlama koruması ÇALIŞTI:** bayat dönüşüm uygulanmıyor →
  scen2 (korumasız) maks 528 m / ort 486 m → scen3 (korumalı) maks 364 / ort 280.
- **E1 CosPlace: sıfırlamaları AZALTMADI** (yine 14) — relocalization tekrar
  ziyaret gerektirir; doğrusal keşif uçuşunda işe yaramıyor. (Yine de zararsız;
  offline_bundle'da duruyor, tekrar-ziyaretli rotalarda faydalı olabilir.)
- Motor iyileştirmesi: **sönümlü ölü hesap** `p(Δ)=p1+v·τ(1−e^(−Δ/τ))`, τ=40 kare
  (dr_tau parametresi) — uzun kesintide savrulma sınırlı (E1 sonrası koşularda).
- **E2 (1920 px + nFeatures 1600) REDDEDİLDİ:** SLAM hiç initialize olamadı
  (kesintide 250/250 NOT_INITIALIZED). Muhtemel neden: LightGlue trace'i 200
  noktayla alınmıştı — 1600 noktada davranış bozuluyor ve/veya init eşleşme
  dağılımı bozuluyor. → **NİHAİ KONFİG: cropA @1280, nFeatures 800, sıfırlama
  korumalı motor + sönümlü ölü hesap (τ=40).** LightGlue'yu yüksek nokta
  sayısıyla yeniden trace etmek gelecek işi olarak not edildi.

### 8.5 O2 TAM PROVA (Q&A profili: 450 sağlıklı → 750 kesinti → 60 sağlıklı → 990 kesinti)
- paced 4 fps, 2250 kare, nihai konfig (cropA@1280, sıfırlama koruması, sönümlü DR):
  **Denklem2 (tümü) = 40,2 m**; sağlık=0 (1740 kare): ort 52 / medyan 30 / p90 144 m;
  kesinti1 ort 29,4 m; kesinti2 (uzun) ort 69,2 m.
- İşlem süresi: **ort 0,173 s/kare, p95 0,240 s** (bütçe 1,6 s) ✓; NaN=0 ✓.
- Kaynak: echo 510 / slam 593 / deadreckon 1147; 6 harita sıfırlaması (korumalı).
- İyileştirme alanı (16 Temmuz'a kadar): SLAM'in geç init'i (healthy pencerede
  init olamadı — O2 başı zor olabilir); LightGlue'yu ≥800 noktayla yeniden trace;
  sıfırlama sonrası pseudo-pair araştırması.

### 8.5 Wi-Fi KAPALI PROVA ✓
- Tek arka plan zinciri: `nmcli radio wifi off` → curl doğrulaması (AG_KAPALI_OK)
  → 400 karelik mock+bridge+SLAM koşusu → `nmcli radio wifi on` (trap garantili).
- Sonuç: **OFFLINE_PROVA_EXIT=0**, loglarda ağ girişimi YOK, Wi-Fi ilk denemede döndü.
- Kanıt: tüm modeller/sözlük yerel; torch hub/pip'e çıkan bileşen yok.

### 8.6 offline_bundle FİNAL (3,1 GB)
- models: superpoint.pt, lightglue.pt, cosplace.pt, superpoint_voc.dbow3, ham .pth
- binaries: mono_folder_watch, mono_euroc + lib (ORB_SLAM3/DBoW3/g2o)
- config: teknofest.yaml (RGB 4K 2026), teknofest_termal.yaml (YENİ — termal 512×640,
  düşük eşikli), thyz2025_cropA.yaml (2025 verisi), object_detection_model.py.entegre
  (resmi istemciye entegre sürümün yedeği)
- python: gorev2_engine.py, bridge.py, mock_server.py, alignment.py,
  evaluate_denklem2.py, replay_analiz.py + wheels/ (54 paket, torch cu121 dahil)
- OFFLINE_README.md + SETUP_LOG.md

## İYİLEŞTİRME TURU (2026-07-14)
- **4 oturum tam prova tablosu** (aynı senaryo): O2=40,2 / O3=56,6 / O1=135,7 /
  O4=44,6 m. SLAM kapsaması sadece O2'de anlamlı (%34); DR ana taşıyıcı.
  Kullanıcı kararı: su oturumu (O1) öncelik DIŞI (herkes orada kötü).
- **R1 (dönüş-farkındalı DR) ÇÖP:** çevrimdışı yarışta kazanç %1-6 (30+ sn
  ufukta anlık dönüş hızı anlamını yitiriyor). dr_deney.py ile kanıtlandı.
- **R3 (DR-çapa ile hizasız blok bağlama) ÇÖP:** sönümlü DR bir noktaya
  yakınsayınca sözde-referanslar durağan → fit ölçeği ~0 → DR'ye çöküyor.
  Beş blokta test: hepsi DR ile bire bir aynı. (Ders: durağan hedefe fit = tuzak.)
- **Zaman çizelgesi teşhisi (asıl bulgu):** sağlıklı pencereler ile SLAM-OK
  pencereleri birbirini ıskalıyor. O3 init=484. karede (yavaş hareket: 0,37
  m/kare → paralaks kıtlığı); O4 sağlıklı patlamada durum çırpıntısı → 15 çift
  < 30 eşik → 716 karelik OK bloğu hizasız kaldı. O2 reset 385 / O4 reset 379:
  yavaşlama + 14°/sn manevra kaynaklı (içerik, parametreyle düzelmez).
- **v2 DENEY SONUÇLARI (pred_O{2,3,4}v2.csv):** init-atlama ETKİSİZ (O3 init
  484→482; O3 D2 hafif kötü) → GERİ ALINDI. min_pairs 30→10 pratikte etkisiz
  (O4 patlaması ~5 çift üretiyor, 10'un altında; 3-5'e inmek dejenere fit
  riski — çevrimdışı test o blokta fit 41 m > DR 33 m gösterdi) → 10'da
  bırakıldı, zararsız. **MOTOR DONDURULDU:** kalıcı kazanımlar = sıfırlama
  koruması + sönümlü DR + çapa + kayan pencere. Koşudan koşuya varyans ~3 m;
  bundan küçük "iyileştirme" iddiaları gürültü.
- **GÖRSELLEŞTİRME TAKIMI:** mono_folder_watch'a [viewer] argümanı (Pangolin;
  yeniden derlendi), bridge --viewer bayrağı, canli_panel.py (6 gözlü canlı
  panel: kuşbakışı/hata/yönelim/kare/z(t)/durum+doku), canli_prova.sh
  başlatıcı (trap torunları da öldürür). Kullanım: ./canli_prova.sh <1-4>.

## BÜYÜK KIRILMA — init ölü bölgesinin kökü + bayat çift zehirlenmesi (2026-07-14)
- **Kullanıcı Pangolin'de canlı gördü:** noktalar kesildi, init'e düştü, çıkamadı.
- **Kök neden 1 (C++):** Tracking.cc:788 initializer **5*nFeatures** ile kurulur
  → 4000 hedef, logda 1714-3638 nokta ("mCurrentFrame.mvKeys"). Trace'li
  LightGlue ~1600 nokta üstünde bozulur (E2 kanıtı) → init eşleşmeleri hep <100
  → 815 karelik ölü bölge. **FIX:** init çıkarıcısı ≤1200'e sınırlandı
  (Tracking.cc, yeniden derleme takas dosyası + make -j2 ile sorunsuz).
  Sonuç (O2v3): 0 reset, 33→2249 kesintisiz OK, SLAM kapsaması %100.
- **Kök neden 2 (Python):** kapsama %100 olunca skor KÖTÜLEŞTİ (40→61) çünkü
  kesinti-2 dönüşümü 240 bayat + 60 taze çift karışımından çözülüyordu →
  driftli eski geometri (canlı 122 m vs taze-çiftli sim 42 m; kesinti-1'de
  canlı=sim=22.1 birebir doğrulandı). **FIX:** çiftlere fid damgası; dönüşüm
  yalnız son pair_age_frames=450 karedeki çiftlerle çözülür.
- Harman testi (SLAM↔DR ufka bağlı blend): gereksiz — taze çiftlerle saf SLAM
  en iyi (sim D2≈26). DR yalnız poz yokken devrede kalır.
- v4 doğrulaması: pred_O{2,3,4}v4.csv (beklenti: O2 D2 ~26).

## v4/v5/v6 CANLI DOĞRULAMA + NİHAİ DONDURMA (2026-07-15)
- **v4 (taze çift + saf SLAM):** O2 28.0 / O3 73.1 / O4 23.0. O3 regresyonu:
  yavaş uçuşta mono drift, kesinti-2 (990 kare) k2=149.7 m.
- **v5 (harman blend_tau=600, İLK sürüm):** v4 ile birebir aynı (O2 28.1 /
  O3 73.5 / O4 20.9) → harman NO-OP çıktı. Sebep: sent_hist'e slam çıktıları
  da yazılıyor; kesintide _dead_reckon son 5 SLAM noktasından hız çıkarınca
  "SLAM ⊕ SLAM'in 1-kare uzantısı" oluyor. Sim'de işe yarayıp canlıda
  yaramamasının açıklaması bu (sim DR'yi kesinti başı çapasından donmuş
  hızla hesaplıyordu).
- **FIX (dr_snapshot):** sağlıklı karede sent_hist dondurulur; harman DR'si
  bu donmuş görüntüden hesaplanır (gorev2_engine.py). Birim testli.
- **v6 (düzeltilmiş harman, blend_tau=600) — NİHAİ:**
  | Oturum | v4 D2 | v6 D2 | v6 k1 | v6 k2 | maks |
  |--------|-------|-------|-------|-------|------|
  | O2     | 28.0  | 30.7  | 21.8  | 53.2  | 103@1850 |
  | O3     | 73.1  | **57.7** | 18.2 | 117.5 | 209@1868 |
  | O4     | 23.0  | 28.0  | 51.9  | 24.3  | 113@2243 |
  Ortalama 41.4→38.8; en-kötü-durum 73→58. Tüm koşularda 0 reset,
  kesintide SLAM OK 1740/1740.
- **KARAR: blend_tau=600 DONDURULDU** (motor varsayılanı; resmi istemci
  GOREV2_DIR'den motoru yüklediği için otomatik geçerli). Gerekçe: en kötü
  oturum tipini (yavaş uçuş/uzun kesinti) 15 m iyileştiriyor, bedeli
  O2/O4'te 3-5 m. Risk profili düzleşti (23-73 → 28-58 bandı).
  Geri dönüş tek bayrak: `--blend-tau 0` (bridge) / blend_tau=0 (motor).
- Bilinen taviz: O4 k1 23→52 (hızlı uçuşta duran-nokta DR'si kötü; toplam
  D2 yine 28). İleri fikir (denenmedi, gerek yok): harmanı yalnız
  fid-a_fid>600 için açmak.
- **offline_bundle senkron (2026-07-15):** gorev2_engine/bridge/canli_panel/
  canli_prova/alignment/mock_server + YENİ libORB_SLAM3.so (init-cap fix'li,
  md5 doğrulandı) + mono_folder_watch (viewer arg'lı) + 3 yaml → bundle güncel.

## Z-AYNASI KEŞFİ VE DÜZELTMESİ (2026-07-15, kullanıcı canlıda fark etti)
- **Belirti:** O2 canlı koşuda tahmin z'si GT z'nin aynadaki görüntüsü gibi
  (korelasyon −1.00); 1260'taki sağlıklı patlamada kendiliğinden düzeldi.
- **Kök neden:** kalibrasyon dakikasında sabit irtifa uçuş → SLAM nokta bulutu
  düzlemsel (sv3/sv1=0.0069). Tam sim3 Umeyama'da düzlemi kendine eşleyen
  180° uygun dönme z'yi ters çevirir, artık aynı kalır → z işareti yazı-tura.
  alignment.py'de çizgi dejenerasyonu korunuyordu, DÜZLEM dejenerasyonu yoktu.
- **FIX (alignment.py):** plane_ratio=0.05 (sv3/sv1) → planar moda düş;
  ayrıca z lstsq yalnız std(Xz) > %2·sv1 iken (gürültüye işaret uydurma
  yasak), aksi halde sz=s2d pozitif (nadir önseli: SLAM +z ≈ yere doğru,
  GT z aşağı-pozitif/NED — kullanıcı gözlemi: yere yaklaşırken GT z artıyor).
  Öz-test T5 eklendi (düzlem+ayna → planar, sz>0).
- **Gerçek veri kanıtı (run_canli O2 tekrar oynatma):** kesinti-1 ort. Öklid
  23.1 → 9.4 m; z-MAE 22.7 → 7.7 m; z-korelasyon −1.00 → +0.96.
- Not: GT z konvansiyonu aşağı-pozitif görünüyor (NED) — hata değil,
  konvansiyon; puanlama GT çerçevesinde, uyum bizden.
- **Yapılacak:** v7 canlı doğrulama zinciri (yarışma profili, blend 600) +
  offline_bundle'a alignment.py yeniden senkron.

## EL-YÖNÜ (YANSIMA) KEŞFİ — SİM3'ÜN TOPYEKÛN TERKİ (2026-07-15)
- 3-eksen kör analiz (1 dk kalibrasyon + 4 dk kör, video_analiz.sh) O3/O4'te
  z yine tersti; ama plane_ratio eşiği değil: kalibrasyonda 26-42 m gerçek
  irtifa değişimi vardı ve sim3 yine z'yi ters eşledi (R·ẑ→−z: O2 −0.97,
  O3 −0.84, O4 −0.70). Ham SLAM z'si GT ile POZİTİF korelasyonda (+0.78..+1.00).
- **Kök neden:** SLAM çerçevesi ile GT çerçevesi arasında el-yönü uyumsuzluğu —
  gerçek ilişki YANSIMA içeriyor. det=+1 kısıtlı Umeyama bunu temsil edemez;
  varyansı büyük xy'yi eşleyip z'yi feda ediyor. Yapısal sorun, eşikle çözülmez.
- **FIX (gorev2_engine.py):** solve_alignment'a plane_ratio=1.0 → HER ZAMAN
  planar (xy 2B yansımalı Procrustes + z 1B ölçek/öteleme). Kör bölge kanıtı
  (kayıtlı pozlardan): O3 48.0→7.1, O4 20.7→6.9, O2 23.2→19.8 m (çapasız);
  çapa dahil O3 tam analiz: ort 5.1 m (x 1.3 / y 2.7 / z 3.4 MAE).
- Kör analiz canlı sonuçları (450'den sonra GT yok, saf SLAM):
  O2 16.2 m (canlı, planar) / O3 5.1 / O4 ~7 (çevrimdışı yeniden hizalama).
- v7 doğrulaması (yarışma profili + blend 600 + her-zaman-planar) başlatıldı.

## v7→v8: ESKİ YAMALARIN TEMİZLİĞİ + NİHAİ DONDURMA (2026-07-15 gece)
- v7 (planar + eski harman/tazelik ayarları): O2 25.3 / O3 35.5 / O4 29.0.
  Kayıt ayrıştırması: kalan hata iki sim3-dönemi yamasından geliyordu.
  1) HARMAN: harmansız k2 11-15 m iken harman 44-73 m'ye çekiyor → varsayılan 0
     (motor + bridge). Bayrak acil dönüş için duruyor.
  2) ÇİFT TAZELİK FİLTRESİ: patlama sonrası yalnız-60-taze-çift çözümü O4'te
     74.9 m; tüm geçmişle 4.5 m → pair_age_frames=None (filtre kapalı).
     "Bayat çift zehirlenmesi" sim3 aynasının belirtisiymiş.
- **v8 NİHAİ SONUÇLAR (yarışma profili, 0 reset, SLAM 1740/1740):**
  | Oturum | v1 | v6 | **v8** | k1 | k2 | maks |
  |--------|----|----|----|----|----|----|
  | O2 | 40.2 | 30.7 | **8.8** | 8.1 | 13.9 | 22.8@2249 |
  | O3 | 56.6 | 57.7 | **4.3** | 3.8 |  6.8 | 11.6@1641 |
  | O4 | 44.6 | 28.0 | **4.7** | 7.8 |  4.9 | 15.9@542 |
  Ortalama 5.9 m (v1: 47.1) — ~8 kat iyileşme.
- **DONDURULAN KONFİGÜRASYON:** her-zaman-planar hizalama (plane_ratio=1.0,
  xy yansımalı 2B + z 1B, z-lstsq std eşiği), pair_age=None, blend=0,
  init-cap 1200 (Tracking.cc), min_pairs=10, window=300, PNG+otomatik silme,
  paced besleme. Üç kök neden zinciri: init nokta limiti → z aynası →
  el-yönü/yansıma. offline_bundle bu commit'le senkron.

## YARIŞMA GÜNÜ KALAN İŞLER (sunucu açılınca)
1. `TAKIM_BAGLANTI_ARAYUZU/config/.env` → EVALUATION_SERVER_URL doldur.
2. Kamera seçimi ARTIK OTOMATİK (aşağıdaki 2026 kalibrasyon bölümü):
   ilk karenin genişliğinden yaml seçilir; GOREV2_SETTINGS verilirse elle
   geçersiz kılınır. Yine de logdaki "Gorev2 kamera tespiti" satırını doğrula.
3. Puanlı oturumda `python main.py` çalıştırmadan önce test oturumunda dene
   (kare başına TEK tahmin hakkı!).
4. İlk 10 kareye null gönderilebilir (değerlendirilmez) — istemci zaten yönetiyor.

## 3-GÖREV BİRLEŞİK ENTEGRASYON + CANLI SUNUCU DOĞRULAMASI (2026-07-16 gecesi)
- OTORİTER İSTEMCİ: ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/
  TAKIM_BAGLANTI_ARAYUZU (gerçek .env burada; yedekler assets/resmi_repo ve
  offline_bundle/resmi_istemci'de). Yorumlayıcı: SİSTEM python3
  (torch 2.13 cu130 + ultralytics 8.4.96; venv DEĞİL).
- Görev 1 (gorev_1/yarisma_pipeline, YOLO26l): sınıf sırası constants ile birebir;
  hareket/inis → str() ile moving/landing kodları; hız p95=70 ms (4K, 55 kare).
  isit() __init__'te; video_name değişiminde oturum_sifirla().
- Görev 3 (Masaüstü/hyz_gorev3 klonu): transformers+kornia pip --user kuruldu;
  lightglue paketi slam venv'den ~/.local'e kopyalandı; HF ağırlıkları indirildi
  (test_offline.py ✅). Çalıştırmada HF_HUB_OFFLINE=1.
- KRİTİK API TUZAĞI: DetectedObject.create_payload cls[0] indeksler → sınıf
  TUPLE ((sinif,),) verilmek zorunda; sınıf URL'si 1-tabanlı (classes/1/=Tasit).
- Sağlamlaştırmalar: health_status str'e normalize; kare bir kez okunup G1+G2
  paylaşır; run_yarisma varsa zaman damgasıyla kenara taşınır (bayat pose.txt
  zehirlenmesi); her görev try/except'li — kare her durumda ilerletilir.
- Canlı test sunucusu (16 Tem ~09:33): login ✅, progress ✅ (test oturumu
  2250/2250 zaten dolu — önceki denemeden), referans uç noktası ✅ (5 referans).
  10 karelik çevrimdışı kuru koşu: 3 görev aynı GPU'da, payload doğru, OOM yok.
- Kullanım rehberi: YARISMA_GUNU.md (tek komut + kontrol listesi + arıza tablosu).

## 2026 RESMİ KAMERA KALİBRASYONLARI (2026-07-15, kullanıcı paylaştı)
- TERMAL 640×512: fx 731.7965 fy 732.0172 cx 319.2367 cy 251.2424
  k1 −0.3507 k2 0.1137 → teknofest_termal.yaml BİREBİR AYNIYDI (değişiklik yok;
  640<1280 olduğundan motor kareyi ölçeklemez, native beslenir).
- RGB 4K 4000×3000: fx 2792.2 fy 2795.2 cx 1988.0 cy 1562.2 k1 0.0798
  k2 −0.1867 → teknofest.yaml zaten bunun 0.32 ölçeklisiydi (1280×960) ✓.
- RGB 1080p 1920×1080: fx 1389.7 fy 1387.1 cx 954.007 cy 558.896 k1 0.1378
  k2 −0.2564 (4K'dan FARKLI distorsiyon!) → YENİ teknofest_1080p.yaml
  (2/3 ölçek → 1280×720: fx 926.467 fy 924.733 cx 636.005 cy 372.597).
- **Otomatik kamera seçimi** (object_detection_model.py::_auto_settings —
  kurallara uygun, yalnız bu dosya değişti): ilk kare genişliği
  ≥3900→teknofest.yaml | ≥2500→thyz2025_cropA.yaml (3840 kırpma) |
  ≥1500→teknofest_1080p.yaml | <1500→teknofest_termal.yaml; okunamazsa 4K
  varsayılan; GOREV2_SETTINGS her zaman öncelikli. 4 çözünürlük + hata yolu
  test edildi (HEPSI OK). Bundle: config/teknofest_1080p.yaml +
  resmi_istemci/object_detection_model.py eklendi.

## ⚠ GENEL DERS — TÜRKÇE LOCALE TUZAĞI (tüm fazlar için kritik)
- Sistem tr_TR.UTF-8: `awk`/`printf` ondalık ayracı **virgül** basıyor
  (`1403636581,66` gibi) → evo/parser'lar bozuluyor.
- Kural: sayı üreten/işleyen HER kabuk komutunda `LC_ALL=C` kullan.
- FAZ 8 notu: bridge.py/mock_server.py'de Python locale bağımsızdır (nokta basar),
  ama C++ tarafında `std::to_string`/`printf` varsayılan "C" locale kullanır — yine de
  `mono_folder_watch.cc`'de iostream'e locale enjekte ETME; float yazarken
  `std::setprecision` + varsayılan classic locale ile yaz.
