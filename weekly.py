"""Freeze a model, save tomorrow's forecasts and score saved forecasts."""
import argparse
import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean

from overnight import UK, UTC, SLOTS, attach_actuals, decision_time, forecast_day, midnight, ordinary_day

CACHE = Path(".cache/cutoff0915")
MODEL = Path("model.json")
VINTAGE = "latest previous-day forecast by 09:15 UK time"


def save_once(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as destination:
        destination.write(content)


def freeze(training_path):
    with Path(training_path).open(newline="", encoding="utf-8") as source:
        training = list(csv.DictReader(source))
    days = {date.fromisoformat(row["date"]) for row in training}
    keys = {(row["date"], int(row["period"])) for row in training}
    if not days or len(keys) != len(training):
        raise ValueError("Training CSV must contain unique date and period pairs.")
    if len(days) < 300 or any(day.year != 2025 or day.month == 12 for day in days):
        raise ValueError("Use at least 300 days from the January–November 2025 backfill.")
    for row in training:
        cutoff = decision_time(date.fromisoformat(row["date"]))
        if datetime.fromisoformat(row["cutoff_utc"]) != cutoff:
            raise ValueError("Training CSV must use the 09:15 UK decision cutoff.")
    corrections = {}
    for slot in SLOTS:
        errors = [float(row["error_mw"]) for row in training if int(row["period"]) == slot]
        if len(errors) < 300:
            raise ValueError(f"Training has only {len(errors)} values for period {slot}.")
        corrections[str(slot)] = mean(errors)
    # This rule is signed-error mean, one value per half-hour.
    model = dict(version="v1", forecast_selection=VINTAGE, training_start=str(min(days)),
                 training_end=str(max(days)), training_rows=len(training), adjustment_mw=corrections)
    save_once(MODEL, json.dumps(model, indent=2) + "\n")
    print(MODEL.read_text())


def record():
    now = datetime.now(UTC)
    target = now.astimezone(UK).date() + timedelta(days=1)
    path = Path("predictions") / f"{target}.json"
    if path.exists():
        print(f"{target} forecast already recorded.")
        return
    if not ordinary_day(target):
        print(f"{target} is a clock-change day and outside the four-slot study.")
        return
    if now < decision_time(target):
        raise ValueError("Run after 09:15 UK time.")
    model = json.loads(MODEL.read_text())
    baseline = forecast_day(target, CACHE)
    if len(baseline) != 4:
        raise ValueError(f"Only {len(baseline)}/4 eligible forecasts for {target}.")
    recorded_at = datetime.now(UTC)
    if recorded_at >= midnight(target):
        raise ValueError("Delivery has started.")
    for row in baseline:
        row["adjustment_mw"] = model["adjustment_mw"][str(row["period"])]
        row["corrected_forecast_mw"] = row["forecast_mw"] + row["adjustment_mw"]
    payload = dict(model_version=model["version"], recorded_at_utc=recorded_at.isoformat(),
                   cutoff_utc=decision_time(target).isoformat(), forecasts=baseline)
    save_once(path, json.dumps(payload, indent=2) + "\n")
    print(f"Saved {path}.")


def score(monday):
    if monday.weekday() != 0 or datetime.now(UK).date() < monday + timedelta(days=7):
        raise ValueError("Supply the Monday of a completed week.")
    rows, coverage, versions = [], [], set()
    expected = 0
    for i in range(7):
        day = monday + timedelta(days=i)
        if not ordinary_day(day):
            coverage.append(f"- {day}: clock-change date excluded.")
            continue
        expected += 4
        path = Path("predictions") / f"{day}.json"
        if not path.exists():
            coverage.append(f"- {day}: no saved forecast.")
            continue
        prediction = json.loads(path.read_text())
        if datetime.fromisoformat(prediction["recorded_at_utc"]) >= midnight(day):
            raise ValueError(f"Forecast saved after delivery began for {day}.")
        versions.add(prediction["model_version"])
        matched = attach_actuals(day, prediction["forecasts"], CACHE)
        rows.extend(matched)
        if len(matched) != 4:
            coverage.append(f"- {day}: {len(matched)}/4 actuals matched.")
            # Allow the next scoring run to request any missing outturns again.
            (CACHE / f"indo_{day}.json").unlink(missing_ok=True)
    lines = [f"# Overnight demand forecast, week of {monday}", "",
             f"**Coverage:** {len(rows)}/{expected} eligible half-hours scored.",
             f"**Model versions:** {', '.join(sorted(versions)) or 'none'}.", ""]
    if coverage:
        lines.extend(coverage + [""])
    if rows:
        lines += ["| Half-hour ending | Intervals | Original MAE (MW) | Corrected MAE (MW) | Original bias (MW) | Corrected bias (MW) | Absolute error reduction (MWh) |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for label, subset in [(f"0{slot // 2}:{'30' if slot % 2 else '00'}",
                                [r for r in rows if r["period"] == slot])
                               for slot in SLOTS] + [("Overall", rows)]:
            if not subset:
                continue
            errors = [r["error_mw"] for r in subset]
            corrected = [r["actual_mw"] - r["corrected_forecast_mw"] for r in subset]
            base, new = mean(map(abs, errors)), mean(map(abs, corrected))
            reduction = (base - new) * len(subset) / 2
            lines.append(f"| {label} | {len(subset)} | {base:.1f} | {new:.1f} | {mean(errors):+.1f} | {mean(corrected):+.1f} | {reduction:+.1f} |")
    path = Path("reports") / f"{monday}.md"
    path.parent.mkdir(exist_ok=True)
    report = "\n".join(lines) + "\n"
    path.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("freeze").add_argument("training")
    sub.add_parser("record")
    sub.add_parser("score").add_argument("monday", type=date.fromisoformat)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.training)
    elif args.command == "record":
        record()
    else:
        score(args.monday)
