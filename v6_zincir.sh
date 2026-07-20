#!/bin/bash
# v6 doğrulama zinciri: harman (blend_tau=600) — O2, O3, O4 sıralı.
set -u
cd "$(dirname "$0")"
PY=/home/zeylo/venvs/slam/bin/python
DROP="450-1199,1260-2249"

kos() {
    local OT=$1 FR=$2 YML=$3 PORT=$4
    echo "=== Oturum $OT (v6) basliyor: $(date +%H:%M:%S) ==="
    rm -rf prova2025/run_O${OT}v6
    rm -f prova2025/pred_O${OT}v6.csv prova2025/mock_O${OT}v6.csv
    $PY mock_server.py --frames-dir $FR --gt prova2025/oturum${OT}_gt.csv \
        --start 0 --limit 2250 --health-drop "$DROP" --paced --fps 4 \
        --port $PORT --out prova2025/mock_O${OT}v6.csv &
    local MOCK=$!
    sleep 2
    $PY bridge.py --server 127.0.0.1:$PORT \
        --settings /home/zeylo/SP_SLAM3/Examples/Monocular/$YML \
        --run-dir prova2025/run_O${OT}v6 --out prova2025/pred_O${OT}v6.csv
    wait $MOCK 2>/dev/null
    echo "=== Oturum $OT (v6) bitti: $(date +%H:%M:%S) ==="
}

kos 2 prova2025/frames_o2 thyz2025_cropA.yaml   5871
kos 3 prova2025/frames_o3 thyz2025_cropA.yaml   5872
kos 4 prova2025/frames_o4 teknofest_termal.yaml 5873
echo "=== v6 zinciri tamam ==="
