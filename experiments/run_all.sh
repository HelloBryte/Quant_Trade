#!/usr/bin/env bash
# Re-run every experiment behind RESULTS.md from recorded data.
#
#   experiments/run_all.sh                  # uses the default file names below
#   BTC=data/x.jsonl.gz SOL=data/y.jsonl.gz experiments/run_all.sh
#
# Protocol: the first 20 minutes of each raw recording are the calibration
# window (signal research, parameter choice). Minutes 20-60 and the separate
# live paper sessions are out of sample.
set -euo pipefail
cd "$(dirname "$0")/.."

BTC=${BTC:-data/binance_BTCUSDT_60m.jsonl.gz}
SOL=${SOL:-data/binance_SOLUSDT_60m.jsonl.gz}
LIVE_BTC=${LIVE_BTC:-data/live_BTCUSDT.jsonl.gz}
LIVE_SOL=${LIVE_SOL:-data/live_SOLUSDT.jsonl.gz}
OUT=${OUT:-runs/experiments}
CALIB_MIN=20

# Shared quoting parameters (chosen on the calibration window).
COMMON=(-p k=1 -p gamma=0.05 -p fixed.half_spread_bps=1)
# Signal betas: joint regression at the 1 s horizon on the calibration window.
BTC_BETAS=(-p as_signal.beta_gap=0 -p as_signal.beta_imb=0.25)
SOL_BETAS=(-p as_signal.beta_gap=0.08 -p as_signal.beta_imb=0.6)

run() { echo "+ python -m mmsim $*" >&2; python -m mmsim "$@" 2>&1 | grep -v -E "findfont|truncated" || true; }

for sym in BTC SOL; do
  data=${!sym}
  betas_var="${sym}_BETAS[@]"
  # 1. signal research: calibration window vs the rest
  run research --data "$data" --max-minutes $CALIB_MIN --out "$OUT/$sym/research_calibration"
  run research --data "$data" --skip-minutes $CALIB_MIN --out "$OUT/$sym/research_out_of_sample"
  # 2. latency x strategy on the out-of-sample window
  run sweep --data "$data" --skip-minutes $CALIB_MIN --latencies 5,50,200,500 --reports \
      "${COMMON[@]}" "${!betas_var}" --out "$OUT/$sym/latency"
done

# 3. live paper sessions: replay must reproduce them exactly
for f in "$LIVE_BTC" "$LIVE_SOL"; do
  [ -f "$f" ] && run reproduce --data "$f" --out "$OUT/reproduce_$(basename "$f" .jsonl.gz)"
done
echo "done: $OUT"
