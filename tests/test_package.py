import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build
from fetch_artwork import convert, destination


class PackageTests(unittest.TestCase):
    def test_catalog_assets_exist_and_ids_are_unique(self):
        catalog = json.loads((ROOT / "launcher/assets/apps.json").read_text())
        self.assertEqual(len({a["Id"] for a in catalog}), len(catalog))
        for entry in catalog:
            asset = entry["Asset"]
            self.assertNotIn("..", asset)
            self.assertTrue((ROOT / "launcher/assets" / asset).is_file(), asset)
        self.assertEqual(sum(bool(a.get("Utility")) for a in catalog), 1)

    def test_sources_json_assets_exist_and_hdmi_ids_are_unique(self):
        sources = json.loads((ROOT / "launcher/assets/sources.json").read_text())
        self.assertGreaterEqual(len(sources), 1)
        self.assertEqual(len({item["Source"] for item in sources}), len(sources))
        for item in sources:
            self.assertIsInstance(item["Source"], int)
            for key in ("Hero", "Portrait"):
                asset = item[key]
                self.assertNotIn("..", asset)
                self.assertTrue((ROOT / "launcher/assets" / asset).is_file(), asset)

    def test_shell_syntax(self):
        for path in (ROOT / "recipes").glob("*.sh"):
            subprocess.run(["sh", "-n", str(path)], check=True, capture_output=True)

    def test_artwork_destinations_and_active_svg_rejected(self):
        with self.assertRaises(ValueError):
            destination("../elsewhere.svg")
        entry = {"name": "Example", "asset": "app-icons/example.svg",
                 "catalog": {"Width": 100, "Height": 50}}
        valid = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><path d="M0 0"/></svg>'
        self.assertEqual(ET.fromstring(convert(valid, entry)).get("width"), "100")
        for data in [
            b'<svg><script>alert(1)</script></svg>',
            b'<svg><image href="https://example.com/image.png"/></svg>',
            b'<svg onload="alert(1)"/>',
            b'<!DOCTYPE svg [<!ENTITY x "x">]><svg/>',
        ]:
            with self.assertRaises(ValueError):
                convert(data, entry)

    def test_relative_document_links_resolve(self):
        for doc in [ROOT / "README.md", ROOT / "NOTICE.md",
                    *sorted((ROOT / "docs").glob("*.md")),
                    *sorted((ROOT / "docs").glob("**/*.md"))]:
            for link in re.findall(r"\[[^\]]*\]\(([^ )]+)(?: [^)]*)?\)", doc.read_text()):
                if "://" in link or link.startswith("#"):
                    continue
                path = link.split("#", 1)[0]
                self.assertTrue((doc.parent / path).exists(), f"{doc.name}: {link}")


class PackagingTests(unittest.TestCase):
    """build.py package must produce the same tarball twice and never ship bin/."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.stage = Path(self.temp.name)
        self.package = self.stage / "package"
        (self.package / "quiet-home").mkdir(parents=True)
        (self.package / "BixbyPromotion.dll").write_bytes(b"managed assembly")
        (self.package / "quiet-home/apps.json").write_text("[]")
        self.archive = self.stage / "package.tar.gz"
        self._saved = (build.PACKAGE, build.ARCHIVE, build.ROOT)
        build.PACKAGE, build.ARCHIVE, build.ROOT = self.package, self.archive, self.stage

    def tearDown(self):
        build.PACKAGE, build.ARCHIVE, build.ROOT = self._saved
        self.temp.cleanup()

    def digest(self):
        parser = argparse.ArgumentParser()
        build.stage_package(parser)
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def test_package_is_deterministic_and_rooted(self):
        import tarfile
        first = self.digest()
        second = self.digest()
        self.assertEqual(first, second)
        with tarfile.open(self.archive) as tar:
            names = sorted(tar.getnames())
        self.assertEqual(names, ["BixbyPromotion.dll", "quiet-home/apps.json"])

    def test_bin_directories_are_refused(self):
        (self.package / "bin").mkdir()
        (self.package / "bin/stray.dll").write_bytes(b"x")
        with self.assertRaises(SystemExit):
            self.digest()

    def test_operator_catalog_overrides_the_shipped_one_when_staged(self):
        fake = self.stage / "repo"
        for folder, dll in (("Home", "BixbyPromotion.dll"), ("QuickLaunch", "QuickLaunch.dll"),
                            ("Probe", "Probe.dll")):
            (fake / ".local/build" / folder).mkdir(parents=True)
            (fake / ".local/build" / folder / dll).write_bytes(b"dll")
        assets = fake / "launcher/assets"
        assets.mkdir(parents=True)
        (assets / "apps.json").write_text('[{"Id":"shipped"}]')
        (assets / "apps.local.json").write_text('[{"Id":"operator"}]')
        build.ROOT = fake
        build.PACKAGE = fake / ".local/package"
        build.stage_launcher()
        staged = build.PACKAGE / "quiet-home"
        self.assertEqual(json.loads((staged / "apps.json").read_text()), [{"Id": "operator"}])
        self.assertFalse((staged / "apps.local.json").exists())
        self.assertTrue((build.PACKAGE / "BixbyPromotion.dll").is_file())


if __name__ == "__main__":
    unittest.main()
