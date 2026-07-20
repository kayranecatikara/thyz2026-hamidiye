#!/bin/bash
# video_analiz.sh — 1 dk kalibrasyon + 4 dk kör SLAM analizi (canlı 3-eksen panel).
# İlk 450 karede (1. dk) gerçek veriyle hizalama yapılır; 450'den sonra sistem
# gerçek veriyi HİÇ görmez (--health-drop 450-2249). Saf SLAM: --blend-tau 0.
# Kullanım: ./video_analiz.sh <oturum:1|2|3|4>
set -u
cd "$(dirname "$0")"
OT=${1:?oturum no (1-6)}
DROP="450-2249"
PY=/home/zeylo/venvs/slam/bin/python
case $OT in
  1) FR=prova2025/frames    ; YML=thyz2025_cropA.yaml    ;;
  2) FR=prova2025/frames_o2 ; YML=thyz2025_cropA.yaml    ;;
  3) FR=prova2025/frames_o3 ; YML=thyz2025_cropA.yaml    ;;
  4) FR=prova2025/frames_o4 ; YML=teknofest_termal.yaml  ;;
  5) FR=prova2025/frames_2026rgb ; YML=teknofest_1080p.yaml ;;  # 2026 ornek RGB
  6) FR=prova2025/frames_yarisma ; YML=teknofest_1080p.yaml
     DROP="451-899,1051-1549,1651-2249" ;;  # GERCEK YARISMA karel. + gercek profil
  *) echo "oturum 1-6"; exit 1 ;;
esac
GT=prova2025/oturum${OT}_gt.csv
PORT=$((5950 + OT))
RUN=prova2025/run_analiz_o${OT}
PRED=prova2025/pred_analiz_o${OT}.csv
rm -f "$PRED"

temizle() {
    kill $(jobs -p) 2>/dev/null
    pkill -f "run-dir prova2025/run_analiz" 2>/dev/null
    pkill -f "mono_folder_watch.*run_analiz" 2>/dev/null
    pkill -f "analiz_3eksen.py" 2>/dev/null
    pkill -f "mock_server.py.*mock_analiz" 2>/dev/null
    sleep 1
    pkill -9 -f "mono_folder_watch.*run_analiz" 2>/dev/null
}
trap temizle EXIT INT TERM

$PY mock_server.py --frames-dir $FR --gt $GT --start 0 --limit 2250 \
    --health-drop "$DROP" --paced --fps 4 --port $PORT \
    --out prova2025/mock_analiz_o${OT}.csv &
sleep 2
$PY bridge.py --server 127.0.0.1:$PORT \
    --settings /home/zeylo/SP_SLAM3/Examples/Monocular/$YML \
    --run-dir $RUN --out $PRED --blend-tau 0 --viewer &
BRIDGE=$!
sleep 3
$PY analiz_3eksen.py --gt $GT --pred $PRED --baslik "Oturum $OT" \
    --kaydet analiz_3eksen/oturum${OT}.png &
wait $BRIDGE
echo "Analiz bitti — panel açık kalabilir, kapatınca çıkar (PNG kaydedildi)."
wait
