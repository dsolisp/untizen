from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

from tv import (build_entries, catalog_command, humanize, save_icon,
                table_column, tile_background, CATALOG_DENY, ICON_COLUMNS,
                LABEL_COLUMNS)

SCHEMA = (
    'CREATE TABLE package_info (pkg_id VARCHAR(255), version TEXT);\n'
    'CREATE TABLE package_app_info (app_id VARCHAR(255) PRIMARY KEY, '
    'pkg_id VARCHAR(255), label TEXT, icon_path VARCHAR(255), noupdate INT);\n'
)


class CatalogToolTests(unittest.TestCase):
    def test_recipe_is_read_only(self):
        text = (ROOT / "recipes/catalog.sh").read_text()
        self.assertIn("-readonly", text)
        self.assertIn("=== apps ===", text)
        self.assertNotIn("rm ", text)
        self.assertIn('test "$(id -u)" = 0', text)

    def test_catalog_command_embeds_recipe(self):
        command = catalog_command(None)
        self.assertIn("UNTIZEN_REGISTRY", command)
        self.assertIn("base64 -d | /bin/sh -s", command)

    def test_table_column_detection(self):
        self.assertEqual(table_column(SCHEMA, "package_app_info", set(LABEL_COLUMNS)), "label")
        self.assertEqual(table_column(SCHEMA, "package_app_info", set(ICON_COLUMNS)), "icon_path")
        self.assertEqual(table_column(SCHEMA, "package_info", set(ICON_COLUMNS)), "")
        self.assertEqual(table_column(SCHEMA, "missing", set(ICON_COLUMNS)), "")
        self.assertEqual(table_column("", "package_app_info", set(LABEL_COLUMNS)), "")

    def test_humanize(self):
        self.assertEqual(humanize("com.liteweb.iptvsmarterspro"), "iptvsmarterspro")
        self.assertEqual(humanize("org.tizen.netflix-app"), "netflix app")
        self.assertEqual(humanize("Crunchyroll"), "Crunchyroll")

    def test_build_entries(self):
        ids = list(CATALOG_DENY) + ["b.app", "a.app"]
        entries = build_entries(ids, {"a.app": "Zed"})
        # Sorted by display name, not by id: "app" (b.app) precedes "Zed" (a.app).
        self.assertEqual([entry["Id"] for entry in entries], ["b.app", "a.app"])
        self.assertEqual(entries[0]["Name"], "app")
        self.assertEqual(entries[1]["Name"], "Zed")

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
