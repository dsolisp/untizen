#!/usr/bin/env python3
"""Compare a registry snapshot to a plan's before.json (post-apply expectation)."""
from pathlib import Path
import json
import sqlite3

FIELDS = ("app_disable", "app_onboot", "app_autorestart")
DISABLED = ("true", "false", "false")


def read_rows(database):
    path = Path(database)
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise ValueError("Snapshot integrity check failed.")
        rows = {}
        for app_id, disable, onboot, autorestart in conn.execute(
            "SELECT app_id,app_disable,app_onboot,app_autorestart FROM package_app_info"
        ):
            rows[app_id] = (disable, onboot, autorestart)
    return rows


def load_plan(plan_dir):
    before = Path(plan_dir) / "before.json"
    if not before.is_file():
        raise ValueError(f"{plan_dir} has no before.json; it is not a generated plan.")
    return json.loads(before.read_text(encoding="utf-8"))


def compare(snapshot_rows, plan):
    drifted, missing, stable = [], [], []
    for app in plan.get("apps", []):
        app_id = app["app_id"]
        if app_id not in snapshot_rows:
            missing.append(app_id)
            continue
        current = snapshot_rows[app_id]
        if current != DISABLED:
            drifted.append({
                "app_id": app_id,
                "current": dict(zip(FIELDS, current)),
                "expected": dict(zip(FIELDS, DISABLED)),
            })
        else:
            stable.append(app_id)
    return {"drifted": drifted, "missing": missing, "stable": stable}


def report(result, plan_dir):
    lines = [
        f"Plan {plan_dir}: {len(result['stable'])} still applied, "
        f"{len(result['drifted'])} drifted, {len(result['missing'])} missing.",
    ]
    for item in result["drifted"]:
        lines.append(f"  drifted\t{item['app_id']}\t{item['current']}")
    for app_id in result["missing"]:
        lines.append(f"  missing\t{app_id}")
    return "\n".join(lines) + "\n"
