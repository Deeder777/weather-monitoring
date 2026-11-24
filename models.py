"""Question 3: can a model predict next-hour temperature better than persistence?

Follows docs/analysis_plan.md section 5 and robustness check 3. Two separate steps:

  py -3.13 models.py select   uses development days only (1-16 Nov): three forward validation
                              windows choose the model settings, saved to results/q3_selection.json
  (commit that file)
  py -3.13 models.py test     refits on 1-16 Nov with the saved settings and scores ONCE on the
                              final five days (17-21 Nov). Refuses to run until the selection is committed.

The outcome is always the temperature in a later collected reading, exactly 60 minutes after the
input reading for the same city. Forecasts from the original request are never used.
"""
import json
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
DB = ROOT / "weather.sqlite"
RESULTS = ROOT / "results"
SELECTION = RESULTS / "q3_selection.json"
SEED = 2026
CITIES = ["Tashkent", "Samarkand", "Bukhara"]
INPUT_HOURS = range(8, 15)                       # inputs 08:00-14:00 predict 09:00-15:00
DEV_DAYS = [f"2026-11-{d:02d}" for d in range(1, 17)]
TEST_DAYS = [f"2026-11-{d:02d}" for d in range(17, 22)]
WINDOWS = [(range(1, 11), (11, 12)), (range(1, 13), (13, 14)), (range(1, 15), (15, 16))]
RIDGE_ALPHAS = [0.01, 0.1, 1, 10, 100]
RF_DEPTHS, RF_LEAVES = [3, 4, 5], [5, 10, 20]
FEATURE_SETS = ["full", "temperature_history"]   # full is primary; history is robustness check 3


def load_pairs(db):
    """One row per valid prediction pair: input reading at t, outcome reading at t + 60 min."""
    readings = {}
    for city, stamp, temp, hum, wind, pres in db.execute(
            "SELECT city, source_utc, temp_c, humidity_pct, wind_kmh, pressure_hpa FROM weather_readings"):
        utc = datetime.strptime(stamp, "%Y-%m-%dT%H:%MZ")
        readings[(city, utc)] = dict(temp=temp, hum=hum, wind=wind, pres=pres)
    pairs = []
    for (city, utc), r in readings.items():
        later = readings.get((city, utc + timedelta(hours=1)))
        if later is None:
            continue
        local = utc + timedelta(hours=5)
        before = readings.get((city, utc - timedelta(hours=1)))
        pairs.append(dict(
            city=city, day=local.strftime("%Y-%m-%d"), hour=local.hour, minute=local.minute,
            temp=r["temp"], hum=r["hum"], wind=r["wind"], pres=r["pres"],
            change=r["temp"] - before["temp"] if before else 0.0,
            no_previous=0 if before else 1,
            target=later["temp"]))
    return sorted(pairs, key=lambda p: (p["day"], p["hour"], p["minute"], p["city"]))


def features(rows, feature_set):
    """Feature matrix using only values known at the input hour."""
    out = []
    for p in rows:
        x = [p["temp"], p["change"], p["no_previous"]]
        x += [1.0 if p["hour"] == h else 0.0 for h in INPUT_HOURS]
        x += [1.0 if p["city"] == c else 0.0 for c in CITIES]
        if feature_set == "full":
            x += [p["hum"], p["wind"], p["pres"]]
        out.append(x)
    return np.asarray(out, dtype=float)


def target(rows):
    return np.asarray([p["target"] for p in rows], dtype=float)


def make_model(kind, setting):
    if kind == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=setting["alpha"]))
    return RandomForestRegressor(n_estimators=300, max_depth=setting["max_depth"],
                                 min_samples_leaf=setting["min_samples_leaf"], random_state=SEED, n_jobs=-1)


def predict(kind, setting, train, test, feature_set):
    if kind == "persistence":
        return np.asarray([p["temp"] for p in test], dtype=float)
    model = make_model(kind, setting)
    model.fit(features(train, feature_set), target(train))
    return model.predict(features(test, feature_set))


def metrics(rows, pred):
    err = pred - target(rows)
    return dict(n=len(rows), mae=float(np.mean(np.abs(err))), rmse=float(np.sqrt(np.mean(err ** 2))),
                me=float(np.mean(err)))


def days(numbers):
    return {f"2026-11-{d:02d}" for d in numbers}


def candidates():
    yield "persistence", {}
    for a in RIDGE_ALPHAS:
        yield "ridge", {"alpha": a}
    for d in RF_DEPTHS:
        for leaf in RF_LEAVES:
            yield "forest", {"max_depth": d, "min_samples_leaf": leaf}


def select(pairs):
    dev = [p for p in pairs if p["day"] in DEV_DAYS]
    lines = ["Question 3 - model selection on development days only (1-16 Nov)",
             f"Development pairs: {len(dev)}. Test days are not read for selection.", ""]
    chosen = {}
    for fs in FEATURE_SETS:
        lines.append(f"== Feature set: {fs}{' (primary)' if fs == 'full' else ' (robustness check 3)'} ==")
        lines.append("model | setting | MAE window 1 | window 2 | window 3 | mean MAE")
        best = {}
        for kind, setting in candidates():
            maes = []
            for train_days, val_days in WINDOWS:
                train = [p for p in dev if p["day"] in days(train_days)]
                val = [p for p in dev if p["day"] in days(val_days)]
                maes.append(metrics(val, predict(kind, setting, train, val, fs))["mae"])
            mean = float(np.mean(maes))
            lines.append(f"{kind} | {json.dumps(setting)} | " + " | ".join(f"{m:.3f}" for m in maes) + f" | {mean:.3f}")
            if kind not in best or mean < best[kind][1]:
                best[kind] = (setting, mean)
        chosen[fs] = {kind: {"setting": s, "mean_validation_mae": round(m, 4)} for kind, (s, m) in best.items()}
        lines.append("Chosen: " + "; ".join(f"{k} {json.dumps(v['setting'])} (mean MAE {v['mean_validation_mae']:.3f})"
                                             for k, v in chosen[fs].items()))
        lines.append("")
    RESULTS.mkdir(exist_ok=True)
    selection = dict(created=datetime.now().isoformat(timespec="seconds"), seed=SEED,
                     development_days=[DEV_DAYS[0], DEV_DAYS[-1]], windows=[
                         dict(train=[f"2026-11-{min(t):02d}", f"2026-11-{max(t):02d}"],
                              validate=[f"2026-11-{v[0]:02d}", f"2026-11-{v[1]:02d}"]) for t, v in WINDOWS],
                     chosen=chosen)
    SELECTION.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    (RESULTS / "q3_validation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("saved results/q3_selection.json and results/q3_validation.txt")
    print("NEXT: commit results/ before running 'test'.")


def selection_is_committed():
    """True if q3_selection.json is tracked by git and has no uncommitted changes."""
    try:
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(SELECTION)], cwd=ROOT,
                                 capture_output=True).returncode == 0
        clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(SELECTION)], cwd=ROOT).returncode == 0
        return tracked and clean
    except FileNotFoundError:
        return False


def record_runs(rows):
    """Store each test evaluation in a model_runs table (results/model_runs.sqlite)."""
    db = sqlite3.connect(RESULTS / "model_runs.sqlite")
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS model_runs(id INTEGER PRIMARY KEY, run_utc TEXT NOT NULL,
            feature_set TEXT NOT NULL, model TEXT NOT NULL, setting TEXT NOT NULL, train_days TEXT NOT NULL,
            test_days TEXT NOT NULL, n INTEGER NOT NULL, mae REAL, rmse REAL, mean_error REAL)""")
        db.executemany("INSERT INTO model_runs VALUES(NULL,?,?,?,?,?,?,?,?,?,?)", rows)
    db.close()


def test(pairs):
    if not SELECTION.exists():
        print("No results/q3_selection.json. Run 'py -3.13 models.py select' first.")
        return 1
    if not selection_is_committed():
        print("results/q3_selection.json is not committed. Commit it first, so the settings are fixed:\n"
              "  git add results\n  git commit -m \"Question 3: model settings chosen on development days\"")
        return 1
    chosen = json.loads(SELECTION.read_text(encoding="utf-8"))["chosen"]
    train = [p for p in pairs if p["day"] in DEV_DAYS]
    held = [p for p in pairs if p["day"] in TEST_DAYS]
    now = datetime.now().isoformat(timespec="seconds")
    lines = ["Question 3 - final evaluation on the held-out test days (17-21 Nov), run once",
             f"Training pairs (1-16 Nov): {len(train)}   Test pairs: {len(held)}",
             "Error = prediction - actual. Five test days cannot support inference about model differences;",
             "results are observed values only (exploratory).", ""]
    runs = []
    for fs in FEATURE_SETS:
        lines.append(f"== Feature set: {fs}{' (primary)' if fs == 'full' else ' (robustness check 3)'} ==")
        preds = {kind: predict(kind, v["setting"], train, held, fs) for kind, v in chosen[fs].items()}
        base = metrics(held, preds["persistence"])["mae"]
        lines.append("model | MAE | RMSE | mean error | MAE change vs persistence")
        for kind, pred in preds.items():
            m = metrics(held, pred)
            change = "" if kind == "persistence" else f"{(base - m['mae']) / base * 100:.1f}% better" if m["mae"] < base \
                else f"{(m['mae'] - base) / base * 100:.1f}% worse"
            lines.append(f"{kind} | {m['mae']:.3f} | {m['rmse']:.3f} | {m['me']:+.3f} | {change}")
            runs.append((now, fs, kind, json.dumps(chosen[fs][kind]["setting"]), "2026-11-01..2026-11-16",
                         "2026-11-17..2026-11-21", m["n"], m["mae"], m["rmse"], m["me"]))
        for group, key in [("city", "city"), ("day", "day")]:
            lines.append(f"MAE by {group}:")
            lines.append(f"  {group} | n | " + " | ".join(preds))
            for value in sorted({p[key] for p in held}, key=lambda v: CITIES.index(v) if v in CITIES else v):
                idx = [i for i, p in enumerate(held) if p[key] == value]
                rows = [held[i] for i in idx]
                cells = [f"{metrics(rows, preds[k][idx])['mae']:.3f}" for k in preds]
                lines.append(f"  {value} | {len(idx)} | " + " | ".join(cells))
        lines.append("")
    record_runs(runs)
    (RESULTS / "q3_test.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("saved results/q3_test.txt and results/model_runs.sqlite")
    return 0


def main(argv):
    if len(argv) != 1 or argv[0] not in ("select", "test"):
        print("Usage: py -3.13 models.py select   |   py -3.13 models.py test")
        return 1
    if not DB.exists():
        print("weather.sqlite not found. Get it first:\n"
              "  git fetch origin data\n  git restore --source=origin/data -- weather.sqlite")
        return 1
    db = sqlite3.connect(DB)
    try:
        pairs = load_pairs(db)
    finally:
        db.close()
    if argv[0] == "select":
        select(pairs)
        return 0
    return test(pairs)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
