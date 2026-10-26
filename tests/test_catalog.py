from pathlib import Path
import base64
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
try:
    from PIL import Image  # noqa: F401
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

from tv import (CATALOG_DENY, build_entries, catalog_command, curated_apps,
                curated_ids, humanize, is_usable, parse_app_rows, save_icon,
                tile_background)


def decode_recipe(command):
    """The base64 payload `catalog_command` pipes into /bin/sh."""
    match = re.search(r"printf '%s' (\S+) \| base64 -d", command)
    assert match, command
    return base64.b64decode(match.group(1)).decode()


class CatalogToolTests(unittest.TestCase):
    def test_recipe_is_read_only(self):
        text = (ROOT / "recipes/catalog.sh").read_text()
        self.assertIn("-readonly", text)
        self.assertIn("=== apps ===", text)
        self.assertNotIn("rm ", text)
        self.assertIn('test "$(id -u)" = 0', text)

    def test_recipe_filters_to_user_apps(self):
        text = (ROOT / "recipes/catalog.sh").read_text()
        self.assertIn("app_package_system='false'", text)
        self.assertIn("component_type='uiapp'", text)
        self.assertIn("__CURATED_IDS__", text)

    def test_catalog_command_embeds_recipe(self):
        command = catalog_command(None)
        self.assertIn("UNTIZEN_REGISTRY", command)
        self.assertIn("base64 -d | /bin/sh -s", command)
        self.assertIn("IN (''", decode_recipe(command))

    def test_catalog_command_quotes_curated_ids(self):
        recipe = decode_recipe(catalog_command(None, ["a.app", "b.app"]))
        self.assertIn("IN ('a.app','b.app')", recipe)
        # Anything that is not a plain app id never reaches the SQL.
        recipe = decode_recipe(catalog_command(None, ["ok.app", "bad'; drop", ""]))
        self.assertIn("IN ('ok.app')", recipe)
        self.assertNotIn("drop", recipe)

    def test_parse_app_rows(self):
        rows = parse_app_rows("a.app|Netflix|/opt/a/icon.png\nb.app||\n\nbroken line\n")
        self.assertEqual(rows, [("a.app", "Netflix", "/opt/a/icon.png"), ("b.app", "", "")])

    def test_is_usable(self):
        self.assertFalse(is_usable("com.samsung.tv.quickpanel"))
        self.assertFalse(is_usable("com.samsung.tv.coba.newhome"))
        self.assertFalse(is_usable("org.tizen.primevideo-dummy"))
        self.assertTrue(is_usable("OGLLvqej7u.CrunchyrollWebApp"))
        self.assertTrue(is_usable("rKpKZvmSog.IPTVSmartersPro"))
        # Curated ids survive the vendor prefix filter but never the hard deny.
        self.assertTrue(is_usable("com.samsung.tv.cobalt-yt", curated=True))
        for denied in CATALOG_DENY:
            self.assertFalse(is_usable(denied, curated=True))

    def test_curated_apps_reads_repo_catalog(self):
        apps = curated_apps()
        self.assertIn("org.tizen.netflix-app", curated_ids(apps))
        self.assertTrue(any(entry.get("Name") for entry in apps))
        self.assertEqual(curated_apps(ROOT / ".local/missing.json"), [])

    def test_prefix_deny_ignores_case(self):
        self.assertFalse(is_usable("com.samsung.tv.CSAccount"))
        self.assertFalse(is_usable("com.samsung.tv.CSBilling"))
        self.assertFalse(is_usable("com.samsung.tv.SecurityCenter"))
        self.assertFalse(is_usable("com.samsung.SelfDiagnosis"))
        self.assertFalse(is_usable("com.samsung.tv.CinemaGraphApp"))
        self.assertFalse(is_usable("com.samsung.tv.MultiControlApp"))

    def test_humanize(self):
        self.assertEqual(humanize("com.liteweb.iptvsmarterspro"), "iptvsmarterspro")
        self.assertEqual(humanize("org.tizen.netflix-app"), "netflix app")
        self.assertEqual(humanize("Crunchyroll"), "Crunchyroll")

    def test_build_entries(self):
        rows = [(denied, "Denied", "") for denied in CATALOG_DENY]
        rows += [
            ("a.app", "Zed", "/icons/a.png"),
            ("b.app", "", ""),
            ("a.app", "Duplicate", ""),
            ("c.app", "Crunchyroll", ""),
            ("org.tizen.primevideo-dummy", "Prime Video", ""),
        ]
        entries = build_entries(rows)
        # Sorted by display name, de-duplicated by id, deny list and dummies dropped.
        self.assertEqual([entry["Id"] for entry in entries], ["b.app", "c.app", "a.app"])
        self.assertEqual([entry["Name"] for entry in entries], ["app", "Crunchyroll", "Zed"])
        self.assertEqual(entries[-1]["Icon"], "/icons/a.png")
        self.assertNotIn("Icon", build_entries([("x.app", "X", "")])[0])

    def test_non_curated_duplicate_name_drops(self):
        curated = [{"Id": "com.samsung.tv.cobalt-yt", "Name": "Youtube"}]
        rows = [("com.samsung.tv.cobalt-yt", "Youtube", ""),
                ("9Ur5IzDKqV.TizenYouTube", "YouTube", "")]
        entries = build_entries(rows, curated)
        self.assertEqual([entry["Id"] for entry in entries], ["com.samsung.tv.cobalt-yt"])

    def test_duplicate_names_keep_one_stable_tile(self):
        rows = [("org.volt.apps", "Apps", ""), ("com.samsung.tv.store", "Apps", "")]
        entries = build_entries(rows)
        self.assertEqual([entry["Id"] for entry in entries], ["com.samsung.tv.store"])

    def test_build_entries_keeps_curated_system_app(self):
        entries = build_entries([("com.samsung.tv.cobalt-yt", "YouTube", "")],
                                [{"Id": "com.samsung.tv.cobalt-yt", "Name": "Youtube"}])
        self.assertEqual([entry["Id"] for entry in entries], ["com.samsung.tv.cobalt-yt"])

    def test_tile_background_clamps(self):
        self.assertEqual(tile_background((255, 255, 255)), "#565656")
        self.assertEqual(tile_background((0, 0, 0)), "#191b20")
        self.assertEqual(tile_background((244, 117, 33)), "#984814")

    @unittest.skipUnless(HAVE_PIL, "Pillow not installed")
    def test_save_icon_roundtrip(self):
        import io
        from PIL import Image
        out = io.BytesIO()
        Image.new("RGB", (512, 512), (244, 117, 33)).save(out, format="PNG")
        dest = ROOT / ".local/test-icon/installed/icon.png"
        background = save_icon(out.getvalue(), dest)
        try:
            self.assertTrue(dest.is_file())
            with Image.open(dest) as saved:
                self.assertLessEqual(max(saved.size), 256)
            self.assertEqual(background, "#984814")
        finally:
            dest.unlink(missing_ok=True)
            dest.parent.rmdir()

    def test_gitignore_covers_generated_catalog(self):
        text = (ROOT / ".gitignore").read_text()
        self.assertIn("launcher/assets/apps-installed.json", text)
        self.assertIn("launcher/assets/app-icons/", text)


if __name__ == "__main__":
    unittest.main()
