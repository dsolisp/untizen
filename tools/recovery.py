#!/usr/bin/env python3
"""First-wins recovery records for a cleanup plan.

The record is written from the snapshot *before* apply. A retry after a
half-applied plan must not replace those original field values. Later runs
may only append app IDs the plan gained.
"""
import hashlib
import json
import re
from pathlib import Path


def sidecar_name(model, firmware, groups):
    raw = f"{model}-{firmware}-{'-'.join(groups)}"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-").lower()
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"{safe[:80]}-{digest}.json"


def save_first_wins(path, record):
    """Write record unless one exists; then only append newly named apps."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    incoming = json.loads(json.dumps(record))
    if not path.exists():
        path.write_text(json.dumps(incoming, indent=2) + "\n", encoding="utf-8")
        path.chmod(0o600)
        return incoming, True
    existing = json.loads(path.read_text(encoding="utf-8"))
    known = {app["app_id"] for app in existing.get("apps", [])}
    added = False
    for app in incoming.get("apps", []):
        if app["app_id"] not in known:
            existing.setdefault("apps", []).append(app)
            known.add(app["app_id"])
            added = True
    if added:
        path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return existing, False
