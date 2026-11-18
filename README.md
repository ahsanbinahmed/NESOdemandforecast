# GB Overnight Demand Correction

A fixed adjustment to NESO's day-ahead national demand forecast, evaluated against Elexon Initial National Demand Outturn for midnight to 02:00 UK time.

Developed by **Ahsan bin Ahmed** as part of an energy forecasting portfolio.

## Historical evaluation through 18 November 2026

| Forecast | Matched half-hours | MAE MW | Bias MW |
|---|---:|---:|---:|
| NESO original | 1,248 | 509.0 | +215.8 |
| NESO plus fixed correction | 1,248 | 483.5 | +90.8 |

The fixed correction reduced average absolute forecast error by **25.5 MW, or 5.0%**, across these matched intervals.

The adjustment was estimated separately for the four overnight slots using January–November 2025 forecast errors. Its settings remain fixed during the 2026 comparison.

## November 2026 reconstruction

| Scope | Half-hours | Original MAE MW | Corrected MAE MW | Original bias MW | Corrected bias MW |
|---|---:|---:|---:|---:|---:|
| All nights from 1–18 November | 72 | 547.3 | 489.1 | +336.4 | +211.3 |
| Dates matched to Demand Lab | 64 | 556.8 | 487.7 | +416.1 | +291.1 |

The all-night correction comparison includes every overnight half-hour from 1–18 November. The 64-interval subset supports comparison with the separate Demand Lab model.

These corrected forecasts were reconstructed from archived issues after delivery. Prospective recording and historical reconstruction have different evidential status.

[Daily November results](reports/november-2026.md)

## Interpretation

MAE measures the average size of the miss. Bias averages actual demand minus forecast, so a positive value indicates underforecasting on average. Individual nights can worsen after applying the correction.

The figures describe forecast accuracy. Electricity, financial and carbon savings would require evidence of changed operational decisions and outcomes.

## Method

The benchmark selects the latest NESO National Demand Forecast issued by 09:15 UK time on the previous day. A fixed slot-specific adjustment is added to it. Actual demand is Elexon's Initial National Demand Outturn. Comparison periods and matched coverage are stated alongside every summary.

The wider [Demand Lab](https://github.com/ahsanbinahmed/GB-Demand-Forecast-Lab) project develops a separate demand forecast using historical demand, weather, calendar information and public embedded-generation forecasts.

## Sources

[Elexon National Demand Forecast](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/NDF) · [Elexon demand outturn](https://bmrs.elexon.co.uk/demand-forecast)
