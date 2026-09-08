# SIFIRDAN KURULUM REHBERİ (Ubuntu 22.04 + NVIDIA GPU)

Bu rehber, üç görevli yarışma sistemini temiz bir makinede uçtan uca kurar.
Her adım 2026 Temmuz'daki gerçek kurulumun kayıtlarından (SETUP_LOG.md) damıtılmıştır.

> ⚠️ **YOLLAR SABİTTİR** — kodlardaki varsayılanlar bu yolları bekler:
> - Bu repo → `~/Masaüstü/teknofest_gorev2`
> - SLAM     → `~/SP_SLAM3`
> - Resmî istemci → `~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU`
>   (bu repodaki `istemci/TAKIM_BAGLANTI_ARAYUZU` oraya kopyalanır)

## 0) Önkoşullar
- Ubuntu 22.04, NVIDIA GPU (≥6 GB VRAM; RTX 4060'ta doğrulandı) ve çalışan NVIDIA
  sürücüsü (`nvidia-smi` çıktı veriyor olmalı), ~40 GB boş disk, internet.

## 1) Sistem paketleri
```bash
sudo apt update && sudo apt install -y build-essential cmake git pkg-config \
  libopencv-dev libeigen3-dev libboost-serialization-dev libssl-dev \
  libgl1-mesa-dev libglew-dev libpython3-dev python3-venv python3-pip \
  python3-tk ffmpeg git-lfs
git lfs install
```

## 2) Depoları klonla (TAM bu yollara)
```bash
git clone https://github.com/kayranecatikara/SP_SLAM3.git ~/SP_SLAM3
git clone https://github.com/kayranecatikara/thyz2026-hamidiye.git ~/Masaüstü/teknofest_gorev2
mkdir -p ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi
cp -r ~/Masaüstü/teknofest_gorev2/istemci/TAKIM_BAGLANTI_ARAYUZU \
      ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/
```
LFS kontrolü (işaretçi değil gerçek dosya inmiş olmalı):
`du -h ~/SP_SLAM3/lightglue.pt` → ~46 MB (birkaç KB ise: `cd ~/SP_SLAM3 && git lfs pull`).

## 3) Pangolin v0.8
```bash
git clone https://github.com/stevenlovegrove/Pangolin.git ~/Pangolin
cd ~/Pangolin && git checkout v0.8 && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DBUILD_EXAMPLES=OFF
make -j$(nproc) && sudo make install && sudo ldconfig
```

## 4) LibTorch 2.3.0 (cu121, C++)
```bash
mkdir -p ~/Masaüstü/teknofest_gorev2/downloads && cd ~/Masaüstü/teknofest_gorev2/downloads
wget "https://download.pytorch.org/libtorch/cu121/libtorch-cxx11-abi-shared-with-deps-2.3.0%2Bcu121.zip"
unzip -q libtorch-*.zip && sudo mv libtorch /usr/local/libtorch
```
(cuDNN gerekmez; paket kendi bağımlılıklarını taşır. CMake varsayılan olarak
`/usr/local/libtorch`'a bakar; farklı yol için `TORCH_DIR` ortam değişkeni.)

## 5) SP_SLAM3 derle + sözlük
```bash
cd ~/SP_SLAM3 && ./build.sh          # DBoW3 aşaması bellek için -j3 kullanır
# Sözlüğü ikili biçime çevir (LFS'ten gelen yml.gz'den):
./tools/convert_vocab Vocabulary/superpoint_voc.yml.gz Vocabulary/superpoint_voc.dbow3
ls Examples/Monocular/mono_folder_watch && echo "SLAM HAZIR"
```
Sorunda: SETUP_LOG.md FAZ 2-5 bölümleri gerçek kurulumun tüm çözümlerini içerir
(takas alanı, -j3, locale uyarıları vb.).

## 6) Python ortamları (İKİ ayrı ortam!)
**a) Sistem python3 — yarışma istemcisi bununla koşar:**
```bash
pip3 install --user torch --index-url https://download.pytorch.org/whl/cu121
pip3 install --user ultralytics transformers kornia opencv-python pillow numpy \
                     python-decouple requests tqdm
pip3 install --user "git+https://github.com/cvg/LightGlue.git"
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"   # True olmalı
```
**b) `~/venvs/slam` — prova/panel araçları bununla koşar:**
```bash
python3 -m venv ~/venvs/slam
~/venvs/slam/bin/pip install numpy opencv-python matplotlib
```

## 7) Görev 3 ağırlıkları — **indirme YOK**
Ağırlıklar depoyla birlikte geliyor:
`gorev3_v2/agirliklar/` (DINOv3-S/16, 82 MB) ve `FastSAM-s.pt` (23 MB).
Paket, yanındaki `agirliklar/` klasörünü Hugging Face önbelleği olarak **kendisi**
kullanır; ev dizinine kopyalamak da gerekmez. Yalnız doğrula:
```bash
cd ~/Masaüstü/teknofest_gorev2 && python3 -m gorev3_v2.onkontrol
```
Çıktıda `modeller yüklendi` görmelisin. Paket ayrıca `HF_HUB_OFFLINE=1`'i içe
aktarılırken kendisi açar — sahada ağa çıkmayı hiç denemez.

## 8) İstemci kimlik bilgileri
```bash
cd ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU
cp config/example.env config/.env && nano config/.env
```
`TEAM_NAME` / `PASSWORD` → TEKNOFEST'in e-postasındaki takım bilgileri;
`EVALUATION_SERVER_URL` → duyurudaki adres, **sonu `/` ile bitecek**.
(.env ASLA git'e girmez.)

## 9) Veri setleri (provalar için; yarışma koşusuna gerekmez)
- 2025 THYZ oturumları + 2026 örnek videolar: TEKNOFEST resmî repo/Drive
  bağlantıları → SETUP_LOG.md "FAZ 1" bölümü ve resmî repo:
  https://github.com/TEKNOFEST-YARISMALAR/havacilikta-yapay-zeka-yarismasi
- İndirilen 2025 oturum kareleri `prova2025/frames_oN` adlarıyla beklenir
  (GT csv'leri zaten bu repoda: `prova2025/oturum*_gt.csv`).
- 2026 örnek videoyu kare dizisine çevirme (oturum 5):
  `ffmpeg -i THYZ_2026_Ornek_Veri_1.MP4 -vf "select='not(mod(n\,4))'" -vsync vfr \
   -f image2 -c:v libwebp -quality 90 -start_number 0 prova2025/frames_2026rgb/frame_%06d.webp`

## 10) DOĞRULAMA SIRASI (hepsi geçmeli)
```bash
cd ~/Masaüstü/teknofest_gorev2
~/venvs/slam/bin/python alignment.py        # T1..T5 öz-testleri "tamam"
python3 - <<'EOF'                            # Görev 1 yükleme + sınıf sırası
import sys; sys.path.insert(0,'gorev_1')
from yarisma_pipeline import model_yukle
assert model_yukle('gorev_1/birincil_run7_26l.pt').names == {0:'tasit',1:'insan',2:'uap',3:'uai'}
print("G1 OK")
EOF
# Uçtan uca yerel prova (resmî protokol taklidi; 2025 O2 kareleri gerekir):
python3 resmi_mock.py --limit 300 --drop 200-299 &   # Terminal 1
cd ~/Masaüstü/test/havacilikta-yapay-zeka-yarismasi/TAKIM_BAGLANTI_ARAYUZU && \
EVALUATION_SERVER_URL="http://127.0.0.1:5580/" HF_HUB_OFFLINE=1 python3 main.py
```
Son satır "Session complete" ile biterse **sistem yarışmaya hazırdır.**
Yarışma günü akışı için: `YARISMA_GUNU.md`.
