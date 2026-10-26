#!/usr/bin/env python3
"""Render docs/media screenshots and demo.gif from demo/harness.html.

The harness is a static mirror of launcher/src/Home.cs layout constants, so the
pictures below match what the TV draws. Rendering needs headless Chrome (for
layout + the shipped SVG/PNG assets) and Pillow (downscale + GIF assembly);
everything runs offline against file:// URLs.

    python3 demo/render.py            # screenshots + gif
    python3 demo/render.py shots      # only docs/media/*.png
    python3 demo/render.py gif        # only docs/media/demo.gif

Frames land in .local/demo-frames/ (gitignored) so re-runs never dirty the tree.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
HARNESS = REPO / "demo/harness.html"
FRAMES = REPO / ".local/demo-frames"
MEDIA = REPO / "docs/media"
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

FRAMES.mkdir(parents=True, exist_ok=True)
MEDIA.mkdir(parents=True, exist_ok=True)


def chrome():
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    sys.exit("headless Chrome not found; install Chrome or edit CHROME_CANDIDATES")


def render(query, out, scale=2):
    out = Path(out)
    cmd = [
        chrome(), "--headless=new", f"--user-data-dir={FRAMES / 'chrome-profile'}",
        "--allow-file-access-from-files", "--hide-scrollbars",
        "--force-color-profile=srgb", "--disable-lcd-text",
        f"--force-device-scale-factor={scale}",
        "--window-size=1920,1080",
        f"--screenshot={out}",
        "--virtual-time-budget=6000",
        f"file://{HARNESS}?{query}",
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def downscale(src, dst, width):
    with Image.open(src) as im:
        im = im.convert("RGB")
        ratio = width / im.width
        im = im.resize((width, int(im.height * ratio)), Image.LANCZOS)
        im.save(dst)
    return dst


# README gallery: one shot per theme, the two secondary pages, and the
# recents-driven home (Xbox hero because the journal says the household
# played on Xbox last while the TV sits on no featured input).
SHOTS = [
    ("home-original", "page=home&theme=original&focus=0"),
    ("home-glass", "page=home&theme=glass&focus=3"),
    ("home-dark", "page=home&theme=dark&focus=0"),
    ("library", "page=apps&theme=glass&focus=0"),
    ("library-all",
     "page=apps&theme=glass&focus=0&allview=1"
     "&installed=com.crunchyroll:Crunchyroll,com.iptv.smarters:IPTV Smarters,"
     "org.tizen.netflix-app:Netflix,org.tizen.primevideo:Prime Video,"
     "com.samsung.tv.cobalt-yt:YouTube&hidden=com.iptv.smarters"),
    ("settings", "page=settings&theme=original&focus=8"),
    ("home-recents", "page=home&theme=glass&focus=0&live=0&recents=hdmi:13,app:com.samsung.tv.cobalt-yt"),
]

# GIF storyline: walk the dock focus, open the library, then flip themes.
SEQUENCE = [
    "page=home&theme=original&focus=0",
    "page=home&theme=original&focus=1",
    "page=home&theme=original&focus=2",
    "page=home&theme=original&focus=3",
    "page=home&theme=original&focus=4",
    "page=home&theme=original&focus=5",
    "page=home&theme=original&focus=6",
    "page=home&theme=original&focus=7",
    "page=home&theme=original&focus=8",
    "page=home&theme=original&focus=0&live=0&recents=hdmi:13,app:com.samsung.tv.cobalt-yt",
    "page=home&theme=original&focus=3&live=0&recents=hdmi:13,app:com.samsung.tv.cobalt-yt",
    "page=apps&theme=original&focus=0",
    "page=apps&theme=original&focus=5",
    "page=settings&theme=original&focus=0",
    "page=settings&theme=glass&focus=8",
    "page=settings&theme=dark&focus=8",
]

which = sys.argv[1] if len(sys.argv) > 1 else "all"

if which in ("all", "shots"):
    for name, query in SHOTS:
        raw = render(query, FRAMES / f"{name}-raw.png")
        print("wrote", downscale(raw, MEDIA / f"{name}.png", 1920))

if which in ("all", "gif"):
    paths = []
    for i, query in enumerate(SEQUENCE):
        raw = render(query, FRAMES / f"gif-{i:02d}-raw.png")
        paths.append(str(downscale(raw, FRAMES / f"gif-{i:02d}.png", 960)))
    with Image.open(paths[0]) as first:
        first.save(
            MEDIA / "demo.gif",
            save_all=True,
            append_images=[Image.open(p) for p in paths[1:]],
            duration=125,  # 8 fps
            loop=0,
            optimize=True,
        )
    print("wrote", MEDIA / "demo.gif", f"({len(paths)} frames)")
