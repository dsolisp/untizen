#!/usr/bin/env python3
"""Turn a read-only TV inventory dump into a draft profile under .local/.

Nothing here writes to profiles/ or mutates a device. Callers supply the
operator-declared firmware and the stdout of recipes/inventory.sh.
"""
import fnmatch
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import cleanup_groups

DEFAULT_REGISTRY = "/opt/dbspace/.pkgmgr_parser.db"
DEFAULT_CONTAINER = "com.samsung.tv.bixby-promotion"
DEFAULT_SETTINGS_CONTAINER = "com.samsung.tv.quicklaunch"
SECTION = re.compile(r"^=== ([a-z0-9_-]+) ===\s*$")
SAFE = re.compile(r"[^A-Za-z0-9._-]+")
RUNTIME = re.compile(r"\b(\d+\.\d+\.\d+)\b")
APP_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def inventory_stem(model, firmware):
    """Directory name for one inventory; unique per model/firmware declaration."""
    if not (model or "").strip() or not (firmware or "").strip():
        raise ValueError("Inventory needs a model and a declared firmware.")
    model = SAFE.sub("-", model.strip()).strip("-").lower()
    firmware = SAFE.sub("-", firmware.strip()).strip("-").lower()
    if not model or not firmware:
        raise ValueError("Inventory needs a model and a declared firmware.")
    return f"{model}-{firmware}"


def parse_sections(stdout):
    sections = {}
    current = None
    lines = []
    for line in (stdout or "").splitlines():
        match = SECTION.match(line)
        if match:
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = match.group(1)
            lines = []
            continue
        if current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


def parse_app_ids(text):
    ids = []
    seen = set()
    for line in (text or "").splitlines():
        app_id = line.strip()
        if not app_id or app_id.startswith("#") or not APP_ID.fullmatch(app_id):
            continue
        if app_id not in seen:
            seen.add(app_id)
            ids.append(app_id)
    return ids


def parse_runtime(text):
    matches = RUNTIME.findall(text or "")
    return matches[-1] if matches else ""


def parse_kernel(text):
    line = (text or "").strip().splitlines()
    return line[0].strip() if line else ""


def parse_home(text):
    values = {}
    key = None
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("db/"):
            key = stripped.split(",", 1)[0].strip()
            if "," in stripped:
                values[key] = stripped.split(",", 1)[1].strip()
                key = None
            continue
        if key and stripped:
            values[key] = stripped
            key = None
    return values


def parse_probe(text):
    record = {"raw": (text or "").strip(), "current": None, "hdmi": []}
    if not record["raw"]:
        return record
    sources = []
    for line in record["raw"].splitlines():
        if line.startswith("current_source="):
            try:
                record["current"] = int(line.split("=", 1)[1].strip())
            except ValueError:
                pass
        if line.startswith("sources="):
            sources = re.findall(r"\d+", line.split("=", 1)[1])
    record["hdmi"] = sorted({int(value) for value in sources})
    return record


def match_shipped_apps(catalog_apps, app_ids):
    installed = set(app_ids)
    return [entry for entry in catalog_apps if entry.get("Id") in installed]


def suggest_groups(catalog, app_ids, container=DEFAULT_CONTAINER,
                   settings_container=DEFAULT_SETTINGS_CONTAINER):
    """Match catalog globs against observed IDs. High-risk groups stay deferred."""
    stub = {
        "container": container,
        "settings_container": settings_container,
        "cleanup": {"add": {}, "remove": {}},
    }
    protected = cleanup_groups.protected_patterns(catalog, stub)
    suggested = {}
    deferred = {}
    skipped = {}
    for name, group in catalog["groups"].items():
        matched = cleanup_groups.match_group(catalog, stub, name, app_ids)
        blocked = [app for app in matched if cleanup_groups.protection_reason(protected, app)]
        if blocked:
            skipped[name] = blocked
            continue
        if not matched:
            continue
        if group.get("risk") == "high":
            deferred[name] = matched
        else:
            suggested[name] = matched
    return suggested, deferred, skipped


def infer_container(app_ids, observed_dirs):
    dirs = [name for name in (observed_dirs or []) if APP_ID.fullmatch(name)]
    if DEFAULT_CONTAINER in dirs or DEFAULT_CONTAINER in app_ids:
        return DEFAULT_CONTAINER
    if dirs:
        return dirs[0]
    return DEFAULT_CONTAINER


def draft_profile(model, firmware, parsed, suggested_groups, container):
    runtime = parse_runtime(parsed.get("runtime", ""))
    kernel = parse_kernel(parsed.get("kernel", ""))
    return {
        "profile_version": 1,
        "model": model,
        "firmware": firmware,
        "os": "Tizen (inventory draft; confirm on the TV)",
        "kernel": kernel or "unknown",
        "runtime": runtime or "unknown",
        "registry": DEFAULT_REGISTRY,
        "container": container,
        "settings_container": DEFAULT_SETTINGS_CONTAINER,
        "cleanup": {
            "groups": list(suggested_groups),
            "add": {},
            "remove": {},
            "evidence": (
                "Draft from a read-only inventory. Promote to profiles/ only after "
                "cleanup, launcher, reboot and standby/wake were exercised on this TV."
            ),
        },
        "stop_markers": [],
        "notes": "One-session inventory. Not an end-to-end profile. Do not invent unit/marker pairs.",
    }


def inventory_directory(root, model, firmware):
    return Path(root) / "inventory" / inventory_stem(model, firmware)


def write_inventory(directory, record):
    """First write wins. A retry must not overwrite the first dump."""
    directory = Path(directory)
    marker = directory / "draft-profile.json"
    if marker.exists():
        raise ValueError(
            f"{directory} already holds an inventory; the first dump is kept. "
            "Inspect it or choose a new --name.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    (directory / "raw.txt").write_text(record["raw"], encoding="utf-8")
    (directory / "app-ids.txt").write_text(
        "".join(f"{app}\n" for app in record["app_ids"]), encoding="utf-8")
    marker.write_text(json.dumps(record["profile"], indent=2) + "\n", encoding="utf-8")
    (directory / "apps-overlay.json").write_text(
        json.dumps(record["apps_overlay"], indent=2) + "\n", encoding="utf-8")
    (directory / "sources.json").write_text(
        json.dumps(record["sources"], indent=2) + "\n", encoding="utf-8")
    (directory / "note.md").write_text(record["note"], encoding="utf-8")
    for path in directory.iterdir():
        path.chmod(0o600)
    return directory


def build_note(model, firmware, profile_match, app_count, suggested, deferred, shipped):
    status = (
        f"A profile already covers this pair: `{profile_match}`."
        if profile_match else
        "No end-to-end profile covers this pair yet. Keep this note under "
        "`docs/devices/` until cleanup, launcher, reboot and standby/wake "
        "have been exercised; only then add `profiles/<model>-<firmware>.json`."
    )
    groups = ", ".join(suggested) or "(none matched)"
    shipped_names = ", ".join(app["Name"] for app in shipped) or "(none of the shipped catalog)"
    deferred_names = ", ".join(deferred) or "(none)"
    return (
        f"# {model} / {firmware}\n\n"
        f"{status}\n\n"
        f"- Observed app IDs: {app_count}\n"
        f"- Catalog groups that matched without hitting `keep_active`: {groups}\n"
        f"- High-risk groups deferred (need a working launcher first): {deferred_names}\n"
        f"- Shipped launcher apps present: {shipped_names}\n"
        f"- HDMI source integers belong in `sources.json` from Probe; "
        f"do not copy another panel's mapping.\n"
    )


def compile_record(model, firmware, stdout, catalog, shipped_apps, profile_match=None):
    parsed = parse_sections(stdout)
    app_ids = parse_app_ids(parsed.get("apps", ""))
    containers = [line.strip() for line in parsed.get("containers", "").splitlines() if line.strip()]
    container = infer_container(app_ids, containers)
    suggested, deferred, skipped = suggest_groups(catalog, app_ids, container)
    probe = parse_probe(parsed.get("probe", ""))
    if not probe["raw"]:
        probe["note"] = "Probe.dll was not on the TV; HDMI integers were not read."
    else:
        probe["note"] = "Integers observed on this panel. Do not reuse them on another model."
    overlay = match_shipped_apps(shipped_apps, app_ids)
    profile = draft_profile(model, firmware, parsed, suggested, container)
    note = build_note(model, firmware, profile_match, len(app_ids), suggested, deferred, overlay)
    return {
        "raw": stdout,
        "parsed": parsed,
        "app_ids": app_ids,
        "home": parse_home(parsed.get("home", "")),
        "suggested": suggested,
        "deferred": deferred,
        "skipped": skipped,
        "apps_overlay": overlay,
        "sources": probe,
        "profile": profile,
        "note": note,
        "profile_match": profile_match,
    }
