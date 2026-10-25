#!/usr/bin/env python3
"""Generate reviewed apply/restore SQL from YOUR fresh, consistent registry snapshot."""
import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import cleanup_groups

FIELDS = ("app_disable", "app_onboot", "app_autorestart")
DISABLED = ("true", "false", "false")


def literal(value):
    if value is None:
        return "NULL"
    if value not in ("true", "false"):
        raise ValueError(f"Unexpected registry boolean representation: {value!r}")
    return "'" + value + "'"


def validate_id(app_id):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", app_id):
        raise ValueError("Invalid application ID.")
    return "'" + app_id + "'"


def read_snapshot(database, ids):
    """Read only. A caller must use SQLite's .backup, never copy a live WAL database."""
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise ValueError("Snapshot integrity check failed.")
        installed = [row[0] for row in conn.execute("SELECT app_id FROM package_app_info")]
        rows = []
        for app_id in ids:
            validate_id(app_id)
            found = conn.execute(
                "SELECT app_disable,app_onboot,app_autorestart FROM package_app_info WHERE app_id=?",
                (app_id,),
            ).fetchall()
            if len(found) != 1:
                raise ValueError(f"{app_id}: expected one row, found {len(found)}. Review this model's inventory.")
            for value in found[0]:
                literal(value)
            rows.append((app_id, tuple(found[0])))
        return installed, rows


def make_sql(rows, restore=False):
    # Guard every observed field before changing anything. SQLite rolls back the
    # transaction if a guard fails and the sqlite3 -bail connection closes.
    lines = ["BEGIN IMMEDIATE;", "CREATE TEMP TABLE untizen_guard(ok INTEGER CHECK(ok=1));"]
    for app_id, original in rows:
        expected = DISABLED if restore else original
        conditions = " AND ".join(f"{key} IS {literal(val)}" for key, val in zip(FIELDS, expected))
        lines.append(f"INSERT INTO untizen_guard SELECT count(*)=1 FROM package_app_info "
                     f"WHERE app_id={validate_id(app_id)} AND {conditions};")
    for app_id, original in rows:
        values = original if restore else DISABLED
        assignments = ",".join(f"{key}={literal(val)}" for key, val in zip(FIELDS, values))
        lines.append(f"UPDATE package_app_info SET {assignments} WHERE app_id={validate_id(app_id)};")
    lines += ["DROP TABLE untizen_guard;", "COMMIT;"]
    return "\n".join(lines) + "\n"


def make_shell(sql, registry):
    return f"""#!/bin/sh
# Generated from the operator's snapshot. Run through tools/tv.py exec --script.
set -eu
test "$(id -u)" = 0
test "$(sqlite3 -readonly {registry} 'PRAGMA quick_check;')" = ok
sqlite3 -bail {registry} <<'UNTIZEN_SQL'
{sql}UNTIZEN_SQL
test "$(sqlite3 -readonly {registry} 'PRAGMA quick_check;')" = ok
echo 'Registry transaction complete. This does not terminate already-running processes.'
"""


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--profile", type=Path, required=True, help="profiles/<model>-<firmware>.json")
    p.add_argument("--groups", nargs="*", help="Defaults to the groups the profile opts into")
    p.add_argument("--output", type=Path, help="New directory below .local/; omit to only print the plan")
    args = p.parse_args()

    catalog = cleanup_groups.load_catalog()
    profile = cleanup_groups.load_profile(args.profile)
    groups = cleanup_groups.selected_groups(profile, args.groups)
    registry = profile["registry"]
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", registry):
        p.error("Profile registry must be an absolute, simple path.")

    with sqlite3.connect(args.snapshot.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
            p.error("Snapshot integrity check failed.")
        installed = [row[0] for row in conn.execute("SELECT app_id FROM package_app_info")]
    try:
        per_group, ids = cleanup_groups.resolve(catalog, profile, groups, installed)
    except ValueError as error:
        p.error(str(error))

    print(f"{profile['model']} / {profile['firmware']}: {len(installed)} installed apps in the snapshot.")
    for group in groups:
        print(f"  {group}: {len(per_group[group])} matched")
    if not ids:
        print("Nothing on this device matches the selected groups; no plan is needed.")
        return

    if not args.output:
        for group in groups:
            for app in per_group[group]:
                print(f"{group}\t{app}")
        print("Re-run with --output to generate reviewed SQL and its inverse.")
        return

    out = args.output.resolve()
    if (ROOT / ".local").resolve() not in out.parents:
        p.error("Plans contain private rollback state; write them below this checkout's .local/.")
    if out.exists():
        p.error("Output directory already exists; preserve previous rollback records.")
    _, rows = read_snapshot(args.snapshot, ids)
    out.mkdir(parents=True, mode=0o700)
    for action in ("apply", "restore"):
        sql = make_sql(rows, restore=action == "restore")
        (out / f"{action}.sql").write_text(sql)
        (out / f"{action}.sh").write_text(make_shell(sql, registry))
    manifest = {"model": profile["model"], "firmware": profile["firmware"], "registry": registry,
                "groups": {group: per_group[group] for group in groups},
                "apps": [{"app_id": app, **dict(zip(FIELDS, vals))} for app, vals in rows]}
    (out / "before.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {len(rows)} targeted changes and inverse operations in {out.relative_to(ROOT)}.")
    print("Review apply.sql and restore.sql. Preserve the snapshot and an on-TV copy of the restore script.")
    print("These plans only edit registry flags; markers, running apps and preferences are separate phases.")


if __name__ == "__main__":
    main()
