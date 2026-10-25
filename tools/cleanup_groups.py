#!/usr/bin/env python3
"""Shared resolution of the bloat catalog in data/cleanup-groups.json against a per-device profile.

The catalog is model-agnostic: every group is a list of fnmatch globs over registry app IDs.
A profile selects which groups apply to that TV and may add or drop single IDs. Nothing here
touches a device; callers supply the ID list read from their own read-only snapshot.
"""
import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "cleanup-groups.json"
PROFILE_REQUIRED = ("profile_version", "model", "firmware", "kernel", "runtime", "registry", "container")


def load_catalog(path=CATALOG_PATH):
    catalog = json.loads(Path(path).read_text())
    for key in ("catalog_version", "keep_active", "groups"):
        if key not in catalog:
            raise ValueError(f"cleanup-groups.json is missing {key!r}.")
    for entry in catalog["keep_active"]:
        if not entry.get("pattern") or not entry.get("reason"):
            raise ValueError("Every keep_active entry needs a pattern and a reason.")
    for name, group in catalog["groups"].items():
        if not group.get("description"):
            raise ValueError(f"Group {name!r} is missing a description.")
        patterns = group.get("patterns") or []
        if not patterns or not all(isinstance(p, str) and p for p in patterns):
            raise ValueError(f"Group {name!r} needs a non-empty list of app_id globs.")
        for pattern in patterns:
            if any(ch in pattern for ch in "/'\";\n"):
                raise ValueError(f"Group {name!r} has an unsafe glob: {pattern!r}")
    return catalog


def load_profile(path):
    profile = json.loads(Path(path).read_text())
    missing = [key for key in PROFILE_REQUIRED if key not in profile]
    if missing:
        raise ValueError(f"{Path(path).name} is missing {', '.join(missing)}.")
    return profile


def profile_groups(profile):
    """Group names this profile opts into, in the profile's own order."""
    cleanup = profile.get("cleanup", {})
    return list(cleanup.get("groups", []))


def selected_groups(profile, requested=None):
    groups = list(requested) if requested else profile_groups(profile)
    if not groups:
        raise ValueError("No groups selected. Pass --groups or list them in the profile's cleanup section.")
    return groups


def protected_patterns(catalog, profile):
    """Invariants that must stay enabled on every model, plus this profile's own containers."""
    entries = [(item["pattern"], item["reason"]) for item in catalog["keep_active"]]
    entries.append((profile["container"], "Container this profile installs the UnTizen launcher into."))
    settings = profile.get("settings_container")
    if settings:
        entries.append((settings, "Container this profile routes the settings key through."))
    return entries


def protection_reason(entries, app_id):
    for pattern, reason in entries:
        if fnmatch.fnmatchcase(app_id, pattern):
            return f"{pattern} — {reason}"
    return None


def group_patterns(catalog, profile, group):
    """Globs for one group after the profile's per-model overrides."""
    if group not in catalog["groups"]:
        known = ", ".join(sorted(catalog["groups"])) or "(none)"
        raise ValueError(f"Unknown group {group!r}. Catalog groups: {known}.")
    patterns = list(catalog["groups"][group].get("patterns", []))
    cleanup = profile.get("cleanup", {})
    patterns += list(cleanup.get("add", {}).get(group, []))
    dropped = set(cleanup.get("remove", {}).get(group, []))
    return [pattern for pattern in patterns if pattern not in dropped]


def match_group(catalog, profile, group, snapshot_ids):
    """Sorted app IDs installed on this device that the group's globs cover."""
    patterns = group_patterns(catalog, profile, group)
    matched = {app for app in snapshot_ids for pattern in patterns if fnmatch.fnmatchcase(app, pattern)}
    return sorted(matched)


def resolve(catalog, profile, groups, snapshot_ids):
    """Per-group matched IDs plus the flat, de-duplicated target list."""
    entries = protected_patterns(catalog, profile)
    per_group = {}
    for group in groups:
        ids = match_group(catalog, profile, group, snapshot_ids)
        for app in ids:
            reason = protection_reason(entries, app)
            if reason:
                raise ValueError(f"Group {group!r} matched protected app {app!r}: {reason}")
        per_group[group] = ids
    flat = sorted({app for ids in per_group.values() for app in ids})
    return per_group, flat
