# GB overnight electricity demand forecast tracker

Can a fixed correction learned from historical forecast errors improve NESO's day-ahead national demand forecast for the four half-hours between midnight and 02:00 UK time?

## Results so far

| Evaluation | Matched half-hours | NESO MAE | Corrected MAE | Change |
|---|---:|---:|---:|---:|
| January–October 2026 backtest | 1,208 | 518.9 MW | 494.6 MW | 4.7% lower |
| 16 November 2026 reconstructed daily check | 4 | 579.25 MW | 648.16 MW | 11.9% higher |

The backtest figures come from the author's historical notebook run. The complete interval export will be added separately. The [16 November comparison](results/2026-11-16-reconstructed.csv) applies the frozen rule to archived forecasts. It is a retrospective check. Live scoring uses records saved before delivery.

## 16–18 November 2026: week to date

| UK delivery date | Half-hours | NESO MAE (MW) | Corrected MAE (MW) | NESO bias (MW) | Corrected bias (MW) | MAE reduction |
|---|---:|---:|---:|---:|---:|---:|
| 16 Nov | 4 | 579.25 | 648.16 | -486.25 | -611.29 | -11.9% |
| 17 Nov | 4 | 327.75 | 290.00 | +18.75 | -106.29 | +11.5% |
| 18 Nov | 4 | 506.75 | 381.71 | +506.75 | +381.71 | +24.7% |
| **16–18 Nov** | 12 | 471.25 | 439.96 | +13.08 | -111.96 | +6.6% |

MAE measures the average absolute miss. Bias is the average of actual minus forecast, so positive means an underforecast and negative means an overforecast. Across these 12 intervals, v1 lowered MAE by 31.29 MW but increased the magnitude of bias. On 16 November, MAE worsened.

[Download the 12 half-hour comparisons](results/2026-11-16-to-18-reconstructed.csv). The original NESO forecasts were selected from Elexon publications available by 09:15 UK time on the previous day. The corrected values were reconstructed using the frozen v1 offsets, with Elexon Initial National Demand Outturn as actual demand. Coverage is 12 of 28 planned intervals for the week. The reconstruction does not verify that the corrected forecasts were recorded before delivery.

## One night first

From the extracted folder in Command Prompt:

```text
py -m pip install tzdata
py overnight.py 2025-01-01 --output example.csv
```

Open example.csv. Each row shows the latest Elexon National Demand Forecast (NDF) publication for the interval available by 09:15 UK time the previous day, and the matching Initial National Demand Outturn (INDO). The error is actual minus forecast. This decision time defines the weekly project's baseline and differs from the earlier 00:30 cardinal-point analysis and the earliest-publication example. Clock-change dates are excluded to preserve four distinct clock slots.

## Fit once and save before delivery

```text
py overnight.py 2025-01-01 2025-11-30 --output training.csv
py weekly.py freeze training.csv
py weekly.py record
```

The backfill makes up to two requests per day. Cached responses let it resume after a failure by rerunning the same command. It reports how many slots are available for each incomplete date. Freeze writes a versioned model with the mean error for each slot and refuses to overwrite it. Record uses that model and saves tomorrow's four original and corrected forecasts, cutoff and actual save time in predictions/. Run it after 09:15 UK time. Tomorrow's actuals are retrieved only during scoring.

## Score and publish weekly

After a week ends, replace DATE with the Monday of the week:

```text
py weekly.py score DATE
```

The script scores saved forecasts and writes a Markdown report in reports/. It lists gaps and shows original and adjusted errors for exactly the same intervals. An ordinary complete week has 28 intervals. MAE is the average size of the error and bias is the average signed error. Absolute forecast error reduction is the net change across intervals converted into MWh. Keep an audit record for every week. Use the weeks with lower MAE as candidates for LinkedIn case studies and link to the complete record so readers can see mixed results too.

For a retrospective check following training, optionally run:

```text
py overnight.py 2026-01-01 2026-10-15 --training training.csv --output evaluation.csv
```

## Automate on GitHub

The daily recording and Monday scoring commands can be scheduled once the repository and workflow permissions are configured. Until then, use the commands above.

When changing the rule, version it and evaluate it on fresh dates. Saved predictions retain their adjustment and model version. Financial impact needs a separate pricing and decision model.

Data: [Elexon National Demand Forecast](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/NDF) and [Elexon Initial National Demand Outturn](https://bmrs.elexon.co.uk/demand-forecast).
