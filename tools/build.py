#!/usr/bin/env python3
"""Build locally; never redistribute Samsung reference assemblies."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / ".local/package"
ARCHIVE = ROOT / ".local/package.tar.gz"


def stage_launcher():
    """Assemble the deployable tree: two managed assemblies, the probe and the launcher assets."""
    PACKAGE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / ".local/build/Home/BixbyPromotion.dll", PACKAGE / "BixbyPromotion.dll")
    shutil.copyfile(ROOT / ".local/build/QuickLaunch/QuickLaunch.dll", PACKAGE / "QuickLaunch.dll")
    shutil.copyfile(ROOT / ".local/build/Probe/Probe.dll", PACKAGE / "Probe.dll")
    assets = PACKAGE / "quiet-home"
    if assets.exists():
        shutil.rmtree(assets)
    shutil.copytree(ROOT / "launcher/assets", assets)
    # apps.local.json is the operator's own catalog; the TV only ever reads apps.json.
    local_catalog = ROOT / "launcher/assets/apps.local.json"
    if local_catalog.exists():
        shutil.copyfile(local_catalog, assets / "apps.json")
    (assets / "apps.local.json").unlink(missing_ok=True)
    print(f"Deployable files: {PACKAGE.relative_to(ROOT)}/. Review the catalog and input mapping before use.")


def stage_package(parser):
    """Deterministic tarball with the files at its root; the on-TV layout adds bin/ itself."""
    if not PACKAGE.is_dir():
        parser.error("Nothing to package. Run 'build.py launcher' (or 'all') first.")
    entries = sorted(path.relative_to(PACKAGE) for path in PACKAGE.rglob("*") if path.is_file())
    if not entries:
        parser.error(f"{PACKAGE.relative_to(ROOT)}/ is empty.")
    for entry in entries:
        if "bin" in entry.parts:
            parser.error(f"Refusing to package a bin/ directory ({entry}); the container already owns that path.")
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with tarfile.open(ARCHIVE, "w:gz", format=tarfile.GNU_FORMAT) as tar:
        for entry in entries:
            info = tar.gettarinfo(PACKAGE / entry, arcname=entry.as_posix())
            info.uid, info.gid, info.uname, info.gname = 0, 0, "root", "root"
            info.mtime, info.mode = 0, 0o644
            with open(PACKAGE / entry, "rb") as handle:
                tar.addfile(info, handle)
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    print(f"Wrote {ARCHIVE.relative_to(ROOT)} ({len(entries)} files, sha256 {digest[:16]}...).")
    print("Stage it with: tv.py push .local/package.tar.gz package.tar.gz")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=["payloads", "launcher", "package", "all"])
    parser.add_argument("--dotnet", default=os.environ.get("DOTNET", "dotnet"))
    parser.add_argument("--framework", type=Path, default=ROOT / ".local/tv-framework")
    args = parser.parse_args()
    jobs = []
    if args.target in ("payloads", "all"):
        for name in ("SamsungTvArchiveRoot", "SamsungTvRootAgent"):
            jobs.append((ROOT / f"vendor/payload-source/{name}.csproj", "payloads", name, []))
    if args.target in ("launcher", "all"):
        for name in ("Tizen.NUI", "Tizen.Applications.Common", "Tizen.System", "Tizen"):
            if not (args.framework / f"{name}.dll").is_file():
                parser.error(f"Missing {name}.dll. Read docs/04-launcher.md; these are not bundled.")
        for name in ("Home", "QuickLaunch"):
            jobs.append((ROOT / f"launcher/src/{name}.csproj", name, name,
                         [f"-p:TV_FRAMEWORK_DIR={args.framework.resolve()}"]))
        jobs.append((ROOT / "launcher/probe/Probe.csproj", "Probe", "Probe", []))
    for project, output, intermediate, extra in jobs:
        subprocess.run([
            args.dotnet, "build", str(project), "-c", "Release", "--nologo",
            "-o", str(ROOT / ".local/build" / output),
            f"-p:BaseIntermediateOutputPath={ROOT / '.local/obj' / intermediate}/",
            "-p:Deterministic=true",
            f"-p:PathMap={ROOT}=/_/untizen", *extra,
        ], check=True, env={**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1"})
    if args.target in ("launcher", "all"):
        stage_launcher()
    if args.target in ("package", "all"):
        stage_package(parser)


if __name__ == "__main__":
    main()
