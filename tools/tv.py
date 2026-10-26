#!/usr/bin/env python3
"""Explicit-target access for UnTizen, driven by per-device profiles. See docs/02-access.md."""
import argparse
import asyncio
import base64
import gzip
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "tools"))
import cleanup_groups
import drift
import inventory
from samsung_tv_root.archive_root import probe, _check_target, _capture
from samsung_tv_root.sdb import SdbClient, find_sdb, SDB_PORT

STAGE = "/home/owner/share/tmp/sdk_tools/untizen"
BACKUP_DIR = "/opt/usr/share/untizen-backups"


def script_environment(profile):
    """Recipes read this device's layout from its profile instead of hardcoding another TV's paths."""
    values = {
        "UNTIZEN_CONTAINER": profile["container"],
        "UNTIZEN_SETTINGS_CONTAINER": profile.get("settings_container", ""),
        "UNTIZEN_STAGE": STAGE,
        "UNTIZEN_BACKUP_DIR": BACKUP_DIR,
        "UNTIZEN_REGISTRY": profile["registry"],
    }
    assignments = " ".join(f"{key}={shlex.quote(str(value))}" for key, value in values.items())
    return f"{assignments}; export {' '.join(values)}; "


def load_profiles(directory=None):
    """Every per-device profile keyed by (MODEL, firmware). Two firmwares of one panel may coexist."""
    profiles = {}
    root = Path(directory) if directory else ROOT / "profiles"
    for path in sorted(root.glob("*.json")):
        data = cleanup_groups.load_profile(path)
        key = (data["model"].upper(), data["firmware"])
        if key in profiles:
            raise ValueError(
                f"{path.name} and {profiles[key][0].name} both claim "
                f"{key[0]} firmware {key[1]}.")
        profiles[key] = (path, data)
    return profiles


def resolve_profile(profiles, observed_model, firmware, profile_arg, model_arg):
    """Pick the profile for this device; never guess, never silently accept an unknown pair."""
    if not firmware:
        raise ValueError(
            "Declare --firmware from About This TV; the helper does not read it from the set.")
    if profile_arg:
        data = cleanup_groups.load_profile(profile_arg)
        if firmware != data["firmware"]:
            raise ValueError(
                f"Profile {profile_arg.name} documents firmware {data['firmware']!r} but "
                f"--firmware {firmware!r} was supplied. Read the exact version from About This TV; "
                f"do not guess this value.")
        return profile_arg, data
    model = (model_arg or observed_model or "").upper()
    matches = [(key, value) for key, value in profiles.items() if key[0] == model]
    supported = ", ".join(f"{key[0]}/{key[1]}" for key in sorted(profiles)) or "(none)"
    if not matches:
        raise ValueError(
            f"No profile covers model {model!r}. Supported models: {supported}. "
            f"Add profiles/<model>-<firmware>.json from a read-only inventory (docs/02-access.md), "
            f"or pass --profile <file> explicitly.")
    exact = [value for key, value in matches if key[1] == firmware]
    if not exact:
        variants = ", ".join(key[1] for key, _ in matches)
        raise ValueError(
            f"Model {model} has profiles for {variants}, not firmware {firmware!r}. "
            f"Read the exact version from About This TV; do not guess this value.")
    return exact[0]


def private_path(path):
    path = Path(path).expanduser().resolve()
    private = (ROOT / ".local").resolve()
    if path == private or private not in path.parents:
        raise ValueError("Private files must be inside this checkout's .local/ directory.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def save_private(path, data):
    path = private_path(path)
    path.write_bytes(data)
    path.chmod(0o600)


def observed_model(client):
    client.connect()
    client.require_device()
    rows = [line.split() for line in client.run(("devices",), check=True).stdout.splitlines()]
    rows = [row for row in rows if row and row[0] == client.serial]
    if len(rows) != 1 or len(rows[0]) < 3:
        raise ValueError("Cannot identify the explicitly selected device from SDB.")
    return rows[0][-1]


def pull_command(remote):
    if not remote.startswith("/") or "\0" in remote or "\n" in remote:
        raise ValueError("Use an absolute, single-line TV file path.")
    # The upstream command channel captures at most 1 MiB per stream.
    # A compressed transfer is bounded before emitting any base64.
    return f"""set -eu
test -f {shlex.quote(remote)}
test "$(stat -c %s {shlex.quote(remote)})" -le 33554432
t=$(mktemp /run/untizen-pull.XXXXXX)
trap 'rm -f "$t"' EXIT HUP INT TERM
gzip -c {shlex.quote(remote)} > "$t"
test "$(wc -c < "$t")" -le 760000 || {{ echo 'File too large; split a snapshot into smaller files first.' >&2; exit 1; }}
sha256sum {shlex.quote(remote)} | cut -d ' ' -f 1
base64 "$t"
"""


def decode_pull(stdout):
    digest, encoded = stdout.split("\n", 1)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Missing transfer digest.")
    compressed = base64.b64decode("".join(encoded.split()), validate=True)
    data = gzip.decompress(compressed)
    if len(data) > 33554432 or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Transfer size or digest mismatch; file was not saved.")
    return data


ROOT_ACTIONS = {"root-check", "exec", "pull", "inventory", "catalog"}


def require_callback_host(host, callback_host):
    """Loopback SDB (a relay) cannot be the TV's root callback address."""
    if ipaddress.IPv4Address(host).is_loopback and not callback_host:
        raise ValueError(
            "--host is loopback, so SDB is probably going through tools/relay.py. "
            "Pass --callback-host <this-computer-LAN-IPv4> so the TV can call back; "
            "127.0.0.1 is unreachable from the panel.")


def check_port_closed(host, port, timeout=3.0):
    """Return ('closed'|'open'|'failed', message). Does not use SDB."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except ConnectionRefusedError:
        return "closed", f"{host}:{port} is closed: the TV refused the connection."
    except (TimeoutError, socket.timeout):
        return "closed", (
            f"{host}:{port} did not answer in {timeout:.0f}s: treated as closed, "
            "unless the TV is off or not at this address.")
    except OSError as error:
        return "failed", f"could not check {host}:{port} ({error}). Is the TV on this LAN?"
    return "open", (
        f"{host}:{port} is still open: Developer Mode / SDB is reachable. "
        "Turn Developer Mode off on the TV, reboot, and check again.")


def run_inventory(args, model, profile, profile_path):
    """Read-only root dump; write a draft under .local/inventory/ only."""
    script = (ROOT / "recipes/inventory.sh").read_bytes()
    encoded = base64.b64encode(script).decode()
    fallback = {
        "container": inventory.DEFAULT_CONTAINER,
        "settings_container": inventory.DEFAULT_SETTINGS_CONTAINER,
        "registry": inventory.DEFAULT_REGISTRY,
    }
    command = (
        script_environment(profile or fallback)
        + f"printf '%s' {shlex.quote(encoded)} | base64 -d | /bin/sh -s"
    )
    result = asyncio.run(probe(
        args.host, model=model, callback_host=args.callback_host,
        payloads=ROOT / ".local/build/payloads", commands=(command,), command_timeout=30,
    ))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    save_private(ROOT / ".local/sessions" / f"{stamp}.json",
                 (json.dumps(result, indent=2) + "\n").encode())
    if result.get("uid") != 0 or result.get("euid") != 0:
        raise ValueError("The callback did not prove UID/EUID 0.")
    if not result.get("system_files_unchanged") or not result.get("staging_cleaned"):
        raise ValueError("Root session cleanup checks failed; inspect the private session log.")
    response = result["commands"][0]
    if response["stderr"]:
        print(response["stderr"], file=sys.stderr, end="")
    if response["exit_code"] or response["timed_out"]:
        raise RuntimeError(
            f"Inventory command failed ({response['exit_code']}, timeout={response['timed_out']}).")
    catalog = cleanup_groups.load_catalog()
    shipped = json.loads((ROOT / "launcher/assets/apps.json").read_text())
    match_name = profile_path.name if profile_path else None
    record = inventory.compile_record(
        model, args.firmware, response["stdout"], catalog, shipped, match_name)
    if args.name:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", args.name):
            raise ValueError("Use a simple --name without directory components.")
        directory = ROOT / ".local/inventory" / args.name
    else:
        directory = inventory.inventory_directory(ROOT / ".local", model, args.firmware)
    directory.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    written = inventory.write_inventory(directory, record)
    if not str(written.resolve()).startswith(str((ROOT / ".local").resolve())):
        raise ValueError("Inventory must stay under .local/.")
    print(f"Observed {len(record['app_ids'])} app IDs; "
          f"{len(record['suggested'])} catalog groups matched.")
    print(f"Draft written to {written.relative_to(ROOT)} "
          "(app-ids.txt, draft-profile.json, apps-overlay.json, sources.json, note.md).")
    print("This did not write profiles/ and did not change registry flags or Home.")
    if match_name:
        print(f"A profile already covers this TV: {match_name}. Review the draft, then continue.")
    else:
        print("No profile matches. Stop here. Promote the note under docs/devices/ "
              "only if the owner asked to change this repo; do not mutate the TV.")
    print("UID/EUID 0 verified; root staging cleaned; passwd and SDB key hashes unchanged.")


def matched_profile(profiles, model, firmware, profile_arg, model_arg):
    """Resolve if possible; inventory may continue when nothing matches."""
    try:
        path, data = resolve_profile(profiles, model, firmware, profile_arg, model_arg)
        return path, data, None
    except ValueError as error:
        return None, None, str(error)


def run_drift(args):
    plan = drift.load_plan(args.plan)
    rows = drift.read_rows(args.snapshot)
    result = drift.compare(rows, plan)
    print(drift.report(result, args.plan), end="")
    if args.fix:
        apply_sh = Path(args.plan) / "apply.sh"
        print("Re-apply the original plan; the first recovery record is not rewritten.")
        if apply_sh.is_file():
            print(f"tv exec --script {apply_sh}")
        else:
            print(f"Missing {apply_sh}; keep the generated apply.sh next to before.json.")
    if result["drifted"] or result["missing"]:
        raise SystemExit(1)


def print_profiles(profiles):
    if not profiles:
        print("No profiles yet. Add profiles/<model>-<firmware>.json (docs/02-access.md).")
        return
    print(f"{'MODEL':<18} {'FIRMWARE':<28} {'RUNTIME':<8} GROUPS")
    for key in sorted(profiles):
        _, data = profiles[key]
        cleanup = data.get("cleanup", {})
        groups = cleanup.get("groups", [])
        print(f"{data['model']:<18} {data['firmware']:<28} {data.get('runtime','?'):<8} {len(groups)}")


CATALOG_DENY = {
    "com.samsung.tv.bixby-promotion",
    "com.samsung.tv.quicklaunch",
}
ICON_COLUMNS = ("icon", "icon_path", "iconpath", "icon_file", "icon_uri")
LABEL_COLUMNS = ("label", "name", "app_name", "display_name", "alias")


def catalog_command(profile):
    """The read-only registry dump behind `tv.py catalog`."""
    script = (ROOT / "recipes/catalog.sh").read_bytes()
    encoded = base64.b64encode(script).decode()
    fallback = {
        "container": inventory.DEFAULT_CONTAINER,
        "settings_container": inventory.DEFAULT_SETTINGS_CONTAINER,
        "registry": inventory.DEFAULT_REGISTRY,
    }
    return (
        script_environment(profile or fallback)
        + f"printf '%s' {shlex.quote(encoded)} | base64 -d | /bin/sh -s"
    )


def run_readonly_root(args, model, command, timeout=60):
    """One read-only root command; same session guarantees as inventory."""
    result = asyncio.run(probe(
        args.host, model=model, callback_host=args.callback_host,
        payloads=ROOT / ".local/build/payloads", commands=(command,), command_timeout=timeout,
    ))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    save_private(ROOT / ".local/sessions" / f"{stamp}.json",
                 (json.dumps(result, indent=2) + "\n").encode())
    if result.get("uid") != 0 or result.get("euid") != 0:
        raise ValueError("The callback did not prove UID/EUID 0.")
    if not result.get("system_files_unchanged") or not result.get("staging_cleaned"):
        raise ValueError("Root session cleanup checks failed; inspect the private session log.")
    response = result["commands"][0]
    if response["stderr"]:
        print(response["stderr"], file=sys.stderr, end="")
    if response["exit_code"] or response["timed_out"]:
        raise RuntimeError(
            f"Catalog command failed ({response['exit_code']}, timeout={response['timed_out']}).")
    return response["stdout"]


def table_column(schema_text, table, wanted):
    """First column of `table` whose name is in `wanted`; '' when absent."""
    match = re.search(
        r"CREATE TABLE (?:IF NOT EXISTS )?[\"'`\[]?" + re.escape(table) + r"[\"'`\]]?\s*\(([^;]*?)\)\s*;",
        schema_text or "", re.S | re.I)
    if not match:
        return ""
    for column in re.findall(r"[\"'`\[]?(\w+)[\"'`\]]?\s+\w", match.group(1)):
        if column.lower() in wanted:
            return column
    return ""


def registry_pairs(args, model, column):
    """app_id -> column value for every row; one more read-only root command."""
    query = f"SELECT app_id, {column} FROM package_app_info;"
    stdout = run_readonly_root(
        args, model,
        f"sqlite3 -readonly {shlex.quote(inventory.DEFAULT_REGISTRY)} {shlex.quote(query)}")
    pairs = {}
    for line in stdout.splitlines():
        if "|" in line:
            key, value = line.split("|", 1)
            if key.strip():
                pairs[key.strip()] = value.strip()
    return pairs


def humanize(app_id):
    """Best-effort display name when the registry has no label column."""
    tail = re.split(r"[._]", app_id)[-1]
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", tail.replace("-", " ").replace("_", " "))
    return words.strip() or app_id


def build_entries(app_ids, labels, deny=CATALOG_DENY):
    """Catalog rows sorted by display name; launcher containers stay out."""
    entries = []
    for app_id in app_ids:
        if app_id in deny:
            continue
        entries.append({"Id": app_id, "Name": labels.get(app_id) or humanize(app_id)})
    entries.sort(key=lambda entry: entry["Name"].lower())
    return entries


def tile_background(rgb):
    """Tile colour from an icon's mean colour, clamped into a readable range."""
    r, g, b = (max(0, min(255, int(value))) for value in rgb)
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if luma > 86:
        scale = 86 / luma
        r, g, b = int(r * scale), int(g * scale), int(b * scale)
    elif luma < 24:
        r, g, b = (int(v * 0.4 + t * 0.6) for v, t in zip((r, g, b), (42, 45, 54)))
    return f"#{r:02x}{g:02x}{b:02x}"


def save_icon(data, dest):
    """Validate, downscale and save one pulled icon; returns its tile colour."""
    import io
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("RGBA")
        image.thumbnail((256, 256))
        out = io.BytesIO()
        image.save(out, format="PNG")
        mean = image.resize((1, 1)).getpixel((0, 0))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(out.getvalue())
    return tile_background(mean[:3])


def run_catalog(args, model, profile):
    """Regenerate launcher/assets/apps-installed.json from this TV. Read-only.

    Ceiling: apps installed after this run stay invisible until it runs again,
    and each icon costs one bounded root read; --icon-limit caps that."""
    stdout = run_readonly_root(args, model, catalog_command(profile))
    parsed = inventory.parse_sections(stdout)
    app_ids = inventory.parse_app_ids(parsed.get("apps", ""))
    if not app_ids:
        raise RuntimeError("The registry returned no app IDs; refusing to write an empty catalog.")
    schema = parsed.get("schema", "")
    labels = {}
    label_column = table_column(schema, "package_app_info", set(LABEL_COLUMNS))
    if label_column:
        labels = {k: v for k, v in registry_pairs(args, model, label_column).items() if v}
    entries = build_entries(app_ids, labels)
    print(f"Observed {len(app_ids)} app IDs; catalog keeps {len(entries)}.")
    icon_column = "" if args.no_icons else table_column(schema, "package_app_info", set(ICON_COLUMNS))
    icons = registry_pairs(args, model, icon_column) if icon_column else {}
    if icons:
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            icons = {}
            print("Pillow is unavailable; skipping icons (install it in a local venv to pull them).")
    assets = ROOT / "launcher/assets/app-icons/installed"
    pulled = 0
    for entry in entries:
        remote = icons.get(entry["Id"], "")
        if pulled >= args.icon_limit:
            break
        if not remote.startswith("/") or not remote.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        safe = re.sub(r"[^A-Za-z0-9._-]", "-", entry["Id"])
        dest = assets / f"{safe}.png"
        try:
            data = decode_pull(run_readonly_root(args, model, pull_command(remote)))
            entry["Background"] = save_icon(data, dest)
            entry["Asset"] = f"app-icons/installed/{dest.name}"
            pulled += 1
        except Exception as error:
            print(f"  icon skipped ({entry['Id']}): {error}")
    catalog_path = ROOT / "launcher/assets/apps-installed.json"
    catalog_path.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"Wrote {catalog_path.relative_to(ROOT)} ({len(entries)} apps, {pulled} icons).")
    print("Review it, then rebuild: python3 tools/build.py all")
    print("UID/EUID 0 verified; root staging cleaned; nothing on the TV was modified.")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="The owner's TV IPv4 address; never auto-discovered")
    parser.add_argument(
        "--firmware",
        help="Required except for profiles, port-closed and drift. Operator-verified About This TV value",
    )
    parser.add_argument("--model", help="Override the SDB-reported model when selecting a profile")
    parser.add_argument("--profile", type=Path, help="Use one explicit profile file instead of matching")
    parser.add_argument("--sdb", help="Path to Samsung's separately installed SDB")
    parser.add_argument("--callback-host", help="This computer's LAN IPv4 if route detection is wrong")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("profiles", help="List the per-device profiles this checkout supports; no TV needed")
    closed = sub.add_parser(
        "port-closed",
        help="Check that SDB refuses connections after Developer Mode is off; no firmware needed",
    )
    closed.add_argument("--port", type=int, default=SDB_PORT, help="SDB port to probe (default 26101)")
    drift_cmd = sub.add_parser(
        "drift",
        help="Compare a snapshot to a plan's before.json; no TV, no firmware",
    )
    drift_cmd.add_argument("--snapshot", type=Path, required=True)
    drift_cmd.add_argument("--plan", type=Path, required=True)
    drift_cmd.add_argument(
        "--fix", action="store_true",
        help="Print how to re-apply the original plan; does not rewrite recovery",
    )
    sub.add_parser("doctor", help="Read SDB identity and archive-route capabilities; does not obtain root")
    inv = sub.add_parser(
        "inventory",
        help="Read-only dump: draft profile under .local/inventory/; does not write profiles/",
    )
    inv.add_argument("--name", help="Override the inventory directory name under .local/inventory/")
    cat = sub.add_parser(
        "catalog",
        help="Regenerate launcher/assets/apps-installed.json from this TV; read-only on the device",
    )
    cat.add_argument("--no-icons", action="store_true",
                     help="Skip icon pulls; entries use the neutral tile")
    cat.add_argument("--icon-limit", type=int, default=40,
                     help="Maximum icons to pull, one bounded read each (default 40)")
    sub.add_parser("root-check", help="Temporarily obtain root and run id; no configuration changes")
    run = sub.add_parser("exec", help="Execute one reviewed command or short script using temporary root")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--command")
    source.add_argument("--script", type=Path)
    run.add_argument("--arg", action="append", default=[], help="Positional argument passed to --script")
    pull = sub.add_parser("pull", help="Read and verify one bounded file into ignored .local/")
    pull.add_argument("remote")
    pull.add_argument("local", type=Path)
    push = sub.add_parser("push", help="Upload one file to the SDK staging directory, not to system paths")
    push.add_argument("local", type=Path)
    push.add_argument("name", help="Simple staging filename")
    args = parser.parse_args()

    profiles = load_profiles()
    if args.action == "profiles":
        print_profiles(profiles)
        return
    if args.action == "drift":
        run_drift(args)
        return
    if not args.host:
        parser.error("--host is required for every action except 'profiles' and 'drift'.")
    ipaddress.IPv4Address(args.host)
    if args.action == "port-closed":
        if not (1 <= args.port <= 65535):
            parser.error("--port must be in 1..65535")
        status, message = check_port_closed(args.host, args.port)
        if status == "closed":
            print(message)
            return
        print(message, file=sys.stderr)
        sys.exit(1 if status == "open" else 2)
    if not args.firmware:
        parser.error(
            "--firmware is required for every action except 'profiles', 'port-closed' and 'drift'. "
            "Read it on About This TV; do not guess.")
    if args.callback_host:
        ipaddress.IPv4Address(args.callback_host)
    if args.sdb:
        os.environ["SDB"] = str(Path(args.sdb).expanduser().resolve())
    if args.action in ROOT_ACTIONS:
        require_callback_host(args.host, args.callback_host)
    client = SdbClient(find_sdb(), args.host, timeout=15)
    model = observed_model(client)
    print("SDB model:", model)
    if args.action == "doctor":
        assessment = _check_target(client)
        print("Archive-route runtime family:", assessment.runtime)
        print(assessment.capabilities)
        print(_capture(client, "uname -srmo; readlink -f /usr/share/dotnet.tizen/netcoreapp"))
        profile_path, profile = resolve_profile(profiles, model, args.firmware, args.profile, args.model)
        print(f"Profile: {profile_path.name} (model {profile['model']}, firmware {profile['firmware']}, "
              f"runtime {profile.get('runtime','?')}, kernel {profile.get('kernel','?')})")
        print("Preflight only. Firmware was operator-declared; root is not yet confirmed.")
        return
    if args.action == "inventory":
        assessment = _check_target(client)
        print("Archive-route runtime family:", assessment.runtime)
        profile_path, profile, mismatch = matched_profile(
            profiles, model, args.firmware, args.profile, args.model)
        if profile_path:
            print(f"Profile: {profile_path.name} (model {profile['model']}, firmware {profile['firmware']})")
        else:
            print(f"No end-to-end profile: {mismatch}")
            print("Continuing with a read-only inventory. Nothing will be written under profiles/.")
        run_inventory(args, model, profile, profile_path)
        return
    if args.action == "catalog":
        assessment = _check_target(client)
        print("Archive-route runtime family:", assessment.runtime)
        profile_path, profile, mismatch = matched_profile(
            profiles, model, args.firmware, args.profile, args.model)
        if profile_path:
            print(f"Profile: {profile_path.name} (model {profile['model']}, firmware {profile['firmware']})")
        else:
            print(f"No end-to-end profile: {mismatch}")
            print("Continuing read-only; the catalog does not depend on cleanup groups.")
        run_catalog(args, model, profile)
        return
    profile_path, profile = resolve_profile(profiles, model, args.firmware, args.profile, args.model)
    print(f"Profile: {profile_path.name} (model {profile['model']}, firmware {profile['firmware']}, "
          f"runtime {profile.get('runtime','?')}, kernel {profile.get('kernel','?')})")
    if args.action == "push":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", args.name):
            raise ValueError("Use a simple staging filename without directory components.")
        if not args.local.is_file():
            raise ValueError("Upload source must be a file.")
        _capture(client, f"mkdir -p {STAGE}")
        remote = PurePosixPath(STAGE) / args.name
        client.push(args.local.resolve(), remote)
        digest = hashlib.sha256(args.local.read_bytes()).hexdigest()
        actual = _capture(client, f"sha256sum {shlex.quote(str(remote))}").split()[0]
        if digest != actual:
            raise ValueError("Uploaded file digest mismatch.")
        print(f"Verified staging file: {remote}. Remove it after deployment.")
        return
    if args.action == "root-check":
        command = "id"
    elif args.action == "pull":
        private_path(args.local)
        command = pull_command(args.remote)
    elif args.script:
        script = args.script.read_bytes()
        if len(script) > 45000:
            raise ValueError("Script too large for the bounded command channel; split into phases.")
        encoded = base64.b64encode(script).decode()
        command = (script_environment(profile)
                   + f"printf '%s' {shlex.quote(encoded)} | base64 -d | /bin/sh -s -- "
                   + shlex.join(args.arg))
    else:
        if args.arg:
            raise ValueError("--arg requires --script.")
        command = args.command
    result = asyncio.run(probe(
        args.host, model=model, callback_host=args.callback_host,
        payloads=ROOT / ".local/build/payloads", commands=(command,), command_timeout=30,
    ))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    log = ROOT / ".local/sessions" / f"{stamp}.json"
    save_private(log, (json.dumps(result, indent=2) + "\n").encode())
    if result.get("uid") != 0 or result.get("euid") != 0:
        raise ValueError("The callback did not prove UID/EUID 0.")
    if not result.get("system_files_unchanged") or not result.get("staging_cleaned"):
        raise ValueError("Root session cleanup checks failed; inspect the private session log.")
    response = result["commands"][0]
    if response["stderr"]:
        print(response["stderr"], file=sys.stderr, end="")
    if response["exit_code"] or response["timed_out"]:
        raise RuntimeError(f"Command failed ({response['exit_code']}, timeout={response['timed_out']}). "
                           f"Private log: {log.relative_to(ROOT)}")
    if args.action == "pull":
        save_private(args.local, decode_pull(response["stdout"]))
        print("Verified file saved inside .local/.")
    else:
        print(response["stdout"], end="")
    print("UID/EUID 0 verified; root staging cleaned; passwd and SDB key hashes unchanged.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as error:
        print(f"Stopped: {error}", file=sys.stderr)
        sys.exit(1)
