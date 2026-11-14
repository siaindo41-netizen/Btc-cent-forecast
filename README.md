# BTC cent forecast — entry

Forecast Bitcoin's price 240 minutes after each checkpoint, from the 4,320
one-minute closes in the case. One number per case, scored by mean absolute
error in cents against the house persistence baseline.

## Model

48-hour regime drift, heavily shrunk and capped:

```
forecast = last_close * exp(clip(0.5 * mean_log_return(last 2880 min) * 240,
                                 -0.01, +0.01))
```

i.e. take the average per-minute log-return of the last 48 hours, extrapolate
it 4 hours ahead, shrink it by half, and cap the move at ±1%.

Why this, and not a shorter window: on the practice kit every short-window
drift model (last 30–240 min) beat persistence on the 5 measurable official
cases but *lost* to it on 16 hourly checkpoints cut from the merged practice
recording, which include a trend reversal — short-window drift was regime
luck. The 48-hour drift was the only candidate that beat persistence on all
three evaluation sets (see REPORT.md). The ±1% cap keeps the worst case close
to persistence if the final's regime flips.

## Run

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13, standard library only, no network. Reads every `*.in` in the
input dir (in name order), writes `<id>.out` JSON exactly
`{"forecasts":[{"case": <id>, "price": <number>}]}` per case. Deterministic:
same input bytes give byte-identical output (verified, two runs). About
50 ms per case, far under the 8 s cap.

## Practice score

Measured on the 5 practice cases whose target is known (target of p00–p04 =
checkpoint close of the next case; p05's target is outside the kit):

| case | forecast | target | error (cents) | persistence (cents) |
|------|----------|--------|---------------|---------------------|
| p00 | 74,725.65 | 74,447.80 | 27,784 | 31,711 |
| p01 | 74,389.88 | 73,680.84 | 70,904 | 76,697 |
| p02 | 73,592.17 | 73,210.50 | 38,167 | 47,033 |
| p03 | 73,108.52 | 73,777.35 | 66,883 | 56,685 |
| p04 | 73,759.30 | 73,545.88 | 21,342 | 23,147 |
| **MAE** | | | **45,016** | **47,055** |

4.3% below the baseline on the measurable cases. The house baseline's
published 6-case practice score is 44,521.58 cents (includes p05, whose
target is not in the kit). A practice score is no guide to the final — the
final is scored on 12 unseen checkpoints over 48 hours.
