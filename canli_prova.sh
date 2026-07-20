#!/bin/bash
# canli_prova.sh — Görselli prova: Pangolin (SLAM noktaları/haritası) +
# canlı karşılaştırma paneli + gerçek zamanlı mock.
# Kullanım: ./canli_prova.sh <oturum:1|2|3|4> [start] [limit] [drop]
#   ör: ./canli_prova.sh 2              # Oturum 2, tamamı, Q&A profili
#       ./canli_prova.sh 2 0 800 300-799
set -u
cd "$(dirname "$0")"
OT=${1:?oturum no (1-4)}
START=${2:-0}
LIMIT=${3:-2250}
DROP=${4:-450-1199,1260-2249}
PY=/home/zeylo/venvs/slam/bin/python
case $OT in
  1) FR=prova2025/frames    ; YML=thyz2025_cropA.yaml    ;;
  2) FR=prova2025/frames_o2 ; YML=thyz2025_cropA.yaml    ;;
  3) FR=prova2025/frames_o3 ; YML=thyz2025_cropA.yaml    ;;
  4) FR=prova2025/frames_o4 ; YML=teknofest_termal.yaml  ;;
  *) echo "oturum 1-4"; exit 1 ;;
esac
GT=prova2025/oturum${OT}_gt.csv
PORT=$((5900 + OT))
RUN=prova2025/run_canli
PRED=prova2025/pred_canli.csv
rm -f "$PRED"

temizle() {
    # torunlar dahil herkesi indir (Pangolin = mono_folder_watch'un penceresi)
    kill $(jobs -p) 2>/dev/null
    pkill -f "run-dir prova2025/run_canli" 2>/dev/null
    pkill -f "mono_folder_watch.*run_canli" 2>/dev/null
    pkill -f "canli_panel.py" 2>/dev/null
    pkill -f "mock_server.py.*mock_canli" 2>/dev/null
    sleep 1
    pkill -9 -f "mono_folder_watch.*run_canli" 2>/dev/null
}
trap temizle EXIT INT TERM

$PY mock_server.py --frames-dir $FR --gt $GT --start $START --limit $LIMIT \
    --health-drop "$DROP" --paced --fps 4 --port $PORT \
    --out prova2025/mock_canli.csv &
sleep 2
$PY bridge.py --server 127.0.0.1:$PORT \
    --settings /home/zeylo/SP_SLAM3/Examples/Monocular/$YML \
    --run-dir $RUN --out $PRED --viewer &
BRIDGE=$!
sleep 3
$PY canli_panel.py --gt $GT --pred $PRED --run-dir $RUN \
    --frames-dir $FR --start $START &
wait $BRIDGE
echo "Prova bitti — panel açık kalabilir, kapatınca çıkar."
wait
