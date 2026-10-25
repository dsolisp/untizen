#!/usr/bin/env python3
"""Optional local publisher-artwork fetcher. No images are downloaded at TV startup."""
import argparse
import hashlib
import html
import io
import json
from pathlib import Path
import re
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "launcher/assets"
LIMIT = 64 * 1024 * 1024


def download(url):
    if not url.startswith("https://"):
        raise ValueError("Artwork sources must use HTTPS.")
    request = urllib.request.Request(url, headers={"User-Agent": "QuietTizenArtwork/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if not response.url.startswith("https://"):
            raise ValueError("Refusing a redirect to an insecure URL.")
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("Artwork download exceeds the size limit.")
    return data


def destination(asset):
    p = (ASSETS / asset).resolve()
    if (ASSETS / "app-icons").resolve() not in p.parents:
        raise ValueError("Artwork destination must be below app-icons/.")
    return p


def convert(data, entry):
    catalog = entry["catalog"]
    suffix = Path(entry["asset"]).suffix
    if entry.get("archive_member"):
        # Read a named member directly; never extract archive paths onto disk.
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo(entry["archive_member"])
            if info.file_size > 4 * 1024 * 1024:
                raise ValueError("Archive member exceeds the SVG size limit.")
            data = archive.read(info)
    if entry["name"] == "Spotify":
        text = data.decode("utf-8")
        candidates = re.findall(r"<svg\b[\s\S]*?</svg>", text)
        matches = [svg for svg in candidates if re.search(
            r'viewBox=["\']0 0 823\.46 225\.25["\']', svg)]
        if not matches:
            raise ValueError("Spotify changed its page; update the source after inspecting the publisher page.")
        data = matches[0].encode()
    if suffix == ".svg":
        text = data.decode("utf-8")
        if re.search(r"<!DOCTYPE|<!ENTITY|<script|<foreignObject|\bon\w+\s*=|(?:href|url)\s*[=(]\s*['\"]?(?:https?:|//|data:)", text, re.I):
            raise ValueError("SVG contains active content or external resources.")
        # Inline SVGs copied from an HTML page can omit the namespace.
        root = ET.fromstring(text)
        if root.tag.split("}")[-1] != "svg":
            raise ValueError("Expected an SVG document.")
        root.set("width", str(catalog["Width"]))
        root.set("height", str(catalog["Height"]))
        if "}" not in root.tag:
            root.set("xmlns", "http://www.w3.org/2000/svg")
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        if entry["name"] == "Prime Video":
            for node in root.iter():
                if node.tag.split("}")[-1] in ("path", "polygon", "circle", "rect"):
                    node.set("fill", "#ffffff")
                    if node.get("style"):
                        node.set("style", re.sub(r"fill:[^;]+", "fill:#ffffff", node.get("style")))
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)
    try:
        from PIL import Image
    except ImportError as error:
        raise ValueError("Install Pillow in a local venv to validate and convert raster artwork.") from error
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.size != (catalog["Width"], catalog["Height"]):
            raise ValueError(f"Publisher dimensions changed to {image.size}; inspect and update the manifest.")
        out = io.BytesIO()
        if suffix == ".jpg":
            image.convert("RGB").save(out, format="JPEG", quality=95)
        else:
            image.save(out, format="PNG")
        return out.getvalue()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    select = p.add_mutually_exclusive_group(required=True)
    select.add_argument("--all", action="store_true")
    select.add_argument("--app", action="append", help="Exact app name; repeat as needed")
    args = p.parse_args()
    entries = json.loads((ROOT / "launcher/artwork-sources.json").read_text())["apps"]
    names = {entry["name"] for entry in entries}
    if args.app and set(args.app) - names:
        p.error("Unknown app name: " + ", ".join(sorted(set(args.app) - names)))
    local = ASSETS / "apps.local.json"
    catalog = json.loads((local if local.exists() else ASSETS / "apps.json").read_text())
    receipts_path = ROOT / ".local/artwork-receipts.json"
    receipts = json.loads(receipts_path.read_text()) if receipts_path.exists() else {}
    failures = []
    for entry in entries:
        if not args.all and entry["name"] not in args.app:
            continue
        try:
            raw = download(entry["source_path"])
            data = convert(raw, entry)
            dest = destination(entry["asset"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            # Preserve local app IDs/labels selected by the operator.
            matching = [a for a in catalog if a["Name"] == entry["name"]]
            for app in matching:
                for key in ("Asset", "Fit", "Background", "Width", "Height", "Crop"):
                    if key in entry["catalog"]:
                        app[key] = entry["catalog"][key]
                    else:
                        app.pop(key, None)
            receipts[entry["name"]] = {
                "source": entry["source_path"],
                "download_sha256": hashlib.sha256(raw).hexdigest(),
                "asset_sha256": hashlib.sha256(data).hexdigest(),
            }
            print("Fetched:", entry["name"])
        except Exception as error:
            failures.append(entry["name"])
            print(f"{entry['name']}: {error}; previous catalog artwork retained.")
    local.write_text(json.dumps(catalog, indent=2) + "\n")
    receipts_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipts_path.write_text(json.dumps(receipts, indent=2) + "\n")
    if failures:
        raise SystemExit(1)
    print("Local artwork catalog saved. Review it, then rebuild the launcher package.")


if __name__ == "__main__":
    main()
