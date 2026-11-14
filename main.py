# btc-cent-forecast-01 entry: forecast BTC's price 240 minutes ahead.
#
# Model: 48-hour regime drift, heavily shrunk and capped.
#   forecast = last_close * exp(clip(0.5 * mean_log_return(last 2880 min) * 240,
#                                    -0.01, +0.01))
# Rationale (measured on the practice kit, 5 measurable cases p00-p04 whose
# target is the next case's checkpoint close, plus 16 hourly checkpoints cut
# from the merged practice recording):
#   * pure persistence (the house baseline) is hard to beat at a 4h horizon:
#     every short-window drift model tested (W=30..240 min, shrink 0.15..1.0)
#     beat persistence on the 5 official cases but LOST to it on the 16
#     hourly checkpoints, which include a trend reversal. Short-window drift
#     is regime luck, not skill.
#   * the 48h drift is the only candidate that beat persistence on ALL THREE
#     evaluation sets (official 5: 45,195 vs 47,055; merged 4h: 50,705 vs
#     52,742; hourly 16: 53,920 vs 54,020 cents MAE). The edge is small
#     (~4% on the official cases) and the cap keeps the worst case close to
#     persistence, so the downside if the final's regime flips is bounded.
#   * no network, stdlib only, fully deterministic (pure arithmetic on the
#     input prices, fixed iteration order, no randomness, no time, no dict
#     ordering dependence).
#
# I/O contract (RULES.txt): read every <id>.in in $MAKEFUN_INPUT_DIR
# (fallback /input/), write /output/<id>.out JSON exactly
# {"forecasts":[{"case": <id>, "price": <number>}]}, price in (0, 10^7),
# rounded to the grid's 5 decimals. One case per run in the grader; locally
# all *.in files found are processed in name order.

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999

# Model constants (fitted only on the practice kit, see header).
LONG_WINDOW = 2880          # minutes of history for the regime drift (48 h)
DRIFT_SHRINK = 0.5          # shrink the extrapolated 48 h drift by half
MAX_LOG_MOVE = 0.01         # cap the forecast move at +/-1% in log terms
HORIZON_MINUTES = 240


def price5(x):
    """Clamp to the scorer's (0, 10_000_000) range, on the 5-decimal grid."""
    x = min(MAX_PRICE, max(MIN_PRICE, x))
    return round(x * 100000) / 100000


def forecast(prices):
    """One price forecast from 4,320 one-minute closes (last = checkpoint)."""
    if not prices:
        raise ValueError("empty price series")
    last = prices[-1]
    if not (isinstance(last, (int, float)) and math.isfinite(last) and last > 0):
        raise ValueError("last price is not a finite positive number")

    window = prices[-LONG_WINDOW:]
    if len(window) < 2:
        return price5(last)

    # Mean log-return per minute over the window, extrapolated to the horizon.
    total = 0.0
    for i in range(len(window) - 1):
        a, b = window[i], window[i + 1]
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
            raise ValueError("non-numeric price in series")
        if a <= 0 or b <= 0 or not (math.isfinite(a) and math.isfinite(b)):
            raise ValueError("non-positive or non-finite price in series")
        total += math.log(b / a)
    mean_return = total / (len(window) - 1)
    log_move = mean_return * HORIZON_MINUTES * DRIFT_SHRINK
    if log_move > MAX_LOG_MOVE:
        log_move = MAX_LOG_MOVE
    elif log_move < -MAX_LOG_MOVE:
        log_move = -MAX_LOG_MOVE
    return price5(last * math.exp(log_move))


def main():
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Every case file, in name order, so two runs write the same bytes.
    inputs = sorted(p for p in input_dir.iterdir()
                    if p.is_file() and p.name.endswith(".in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        with path.open("r", encoding="utf-8") as fh:
            case = json.load(fh)
        markets = case.get("markets")
        if not isinstance(markets, list) or len(markets) != 1:
            raise ValueError(f"{path.name} does not hold exactly one market")
        prices = markets[0].get("prices")
        if not isinstance(prices, list):
            raise ValueError(f"{path.name} has no prices list")
        guess = forecast(prices)
        payload = {"forecasts": [{"case": case_id, "price": guess}]}
        out_path = output_dir / f"{case_id}.out"
        with out_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(payload) + "\n")


if __name__ == "__main__":
    main()
