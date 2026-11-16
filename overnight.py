"""Fetch and compare GB national demand forecasts for four overnight slots."""
import argparse
import csv
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import mean
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")
BASE = "https://data.elexon.co.uk/bmrs/api/v1/"
SLOTS = range(1, 5)


def midnight(day):
    return datetime.combine(day, time.min, UK).astimezone(UTC)


def fetch(endpoint, params, cache_file):
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    with urlopen(BASE + endpoint + "?" + urlencode(params), timeout=45) as response:
        payload = json.load(response)
    rows = payload if isinstance(payload, list) else payload["data"]
    if rows:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(rows), encoding="utf-8")
        temporary.replace(cache_file)
    return rows


def decision_time(day):
    return datetime.combine(day - timedelta(days=1), time(9, 15), UK).astimezone(UTC)


def ordinary_day(day):
    return midnight(day + timedelta(days=1)) - midnight(day) == timedelta(hours=24)


def matches(record, day, slot):
    return (
        record["settlementDate"] == day.isoformat()
        and record["settlementPeriod"] == slot
        and datetime.fromisoformat(record["startTime"])
        == midnight(day) + timedelta(minutes=30 * (slot - 1))
    )


def forecast_day(day, cache):
    if not ordinary_day(day):
        return []
    earliest = midnight(day - timedelta(days=1))
    cutoff = decision_time(day)
    forecasts = fetch("datasets/NDF/stream", {
        "publishDateTimeFrom": earliest.isoformat(),
        "publishDateTimeTo": cutoff.isoformat(),
    }, cache / f"ndf_{day}.json")
    rows = []
    for slot in SLOTS:
        eligible = [
            r for r in forecasts
            if matches(r, day, slot) and r["boundary"] == "N" and r["demand"] is not None
            and earliest <= datetime.fromisoformat(r["publishTime"]) <= cutoff
        ]
        if not eligible:
            continue
        latest = max(datetime.fromisoformat(r["publishTime"]) for r in eligible)
        values = {
            r["demand"] for r in eligible if datetime.fromisoformat(r["publishTime"]) == latest
        }
        if len(values) != 1:
            raise ValueError(f"Conflicting forecasts for {day}, period {slot}")
        rows.append(dict(date=day.isoformat(), period=slot, published_utc=latest.isoformat(), cutoff_utc=cutoff.isoformat(),
                         forecast_mw=values.pop()))
    return rows


def attach_actuals(day, rows, cache):
    if not rows:
        return []
    actuals = fetch("demand/outturn", {
        "settlementDateFrom": day.isoformat(), "settlementDateTo": day.isoformat(),
    }, cache / f"indo_{day}.json")
    matched = []
    for row in rows:
        slot = row["period"]
        values = {
            r["initialDemandOutturn"] for r in actuals
            if matches(r, day, slot) and r["initialDemandOutturn"] is not None
        }
        if not values:
            continue
        if len(values) != 1:
            raise ValueError(f"Conflicting actuals for {day}, period {slot}")
        actual = values.pop()
        matched.append(dict(row, actual_mw=actual, error_mw=actual - row["forecast_mw"]))
    return matched


def compare_day(day, cache):
    return attach_actuals(day, forecast_day(day, cache), cache)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start", type=date.fromisoformat)
    parser.add_argument("end", type=date.fromisoformat, nargs="?")
    parser.add_argument("--output", type=Path, default=Path("overnight.csv"))
    parser.add_argument("--training", type=Path, help="Separate, earlier comparison CSV")
    args = parser.parse_args()
    end = args.end or args.start
    if end < args.start:
        parser.error("end must be on or after start")
    adjustment = None
    if args.training:
        with args.training.open(newline="", encoding="utf-8") as source:
            training = list(csv.DictReader(source))
        if any(date.fromisoformat(row["date"]) >= args.start for row in training):
            parser.error("training dates must precede the evaluation period")
        adjustment = {
            slot: mean(float(r["error_mw"]) for r in training if int(r["period"]) == slot)
            for slot in SLOTS
        }
    rows = []
    for offset in range((end - args.start).days + 1):
        day = args.start + timedelta(days=offset)
        day_rows = compare_day(day, Path(".cache/analysis"))
        if len(day_rows) != len(SLOTS):
            print(f"{day}: {len(day_rows)}/4 slots matched")
        rows.extend(day_rows)
    if not rows:
        raise SystemExit("No matching forecast and actual rows.")
    if adjustment:
        for row in rows:
            correction = adjustment[row["period"]]
            row.update(adjustment_mw=correction, corrected_error_mw=row["error_mw"] - correction)
        for label, subset in [(f"SP{slot}", [r for r in rows if r["period"] == slot])
                              for slot in SLOTS] + [("Overall", rows)]:
            if not subset:
                continue
            original = mean(abs(r["error_mw"]) for r in subset)
            corrected = mean(abs(r["corrected_error_mw"]) for r in subset)
            bias = mean(r["error_mw"] for r in subset)
            corrected_bias = mean(r["corrected_error_mw"] for r in subset)
            print(f"{label}: n={len(subset)}, MAE {original:.2f} → {corrected:.2f} MW, "
                  f"bias {bias:+.2f} → {corrected_bias:+.2f} MW, "
                  f"absolute error reduction {(original - corrected) * len(subset) / 2:+.2f} MWh")
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Matched {len(rows)} intervals. Saved {args.output}.")


if __name__ == "__main__":
    main()
