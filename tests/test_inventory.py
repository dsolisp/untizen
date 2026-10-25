import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))
import cleanup_groups
import inventory
import tv


SAMPLE = """=== kernel ===
Linux 5.4.77 armv7l GNU/Linux
=== runtime ===
/usr/share/dotnet.tizen/netcoreapp
Microsoft.NETCore.App 6.0.9
=== registry ===
/opt/dbspace/.pkgmgr_parser.db
=== schema ===
CREATE TABLE package_app_info(app_id TEXT);
=== apps ===
com.samsung.tv.acr
com.samsung.tv.tvplus
org.tizen.netflix-app
com.samsung.tv.bixby-promotion
com.samsung.tv.coba.newhome
com.samsung.tv.home.sidebar
# not an id
=== home ===
db/appfw/home_appid
com.samsung.tv.coba.newhome
=== containers ===
com.samsung.tv.bixby-promotion
com.samsung.tv.quicklaunch
=== probe ===
home_result=0 home=com.samsung.tv.bixby-promotion
sources=13,14,15
current_source=14
"""


class InventoryParseTests(unittest.TestCase):
    def setUp(self):
        self.catalog = cleanup_groups.load_catalog()
        self.apps = json.loads((ROOT / "launcher/assets/apps.json").read_text())

    def test_stem_is_stable_and_rejects_empty(self):
        self.assertEqual(
            inventory.inventory_stem("QN55QN85CAPXPA", "T-PTMCUABC-0090-2220.4"),
            "qn55qn85capxpa-t-ptmcuabc-0090-2220.4")
        with self.assertRaises(ValueError):
            inventory.inventory_stem("", "fw")

    def test_compile_record_suggests_groups_and_keeps_high_risk_deferred(self):
        record = inventory.compile_record(
            "QN55QN85CAPXPA", "T-PTMCUABC-0090-2220.4", SAMPLE,
            self.catalog, self.apps, profile_match=None)
        self.assertIn("com.samsung.tv.acr", record["app_ids"])
        self.assertIn("advertising", record["suggested"])
        self.assertIn("tv-plus", record["suggested"])
        self.assertIn("light-shell", record["deferred"])
        self.assertNotIn("light-shell", record["profile"]["cleanup"]["groups"])
        self.assertEqual(record["profile"]["container"], "com.samsung.tv.bixby-promotion")
        self.assertEqual(record["profile"]["runtime"], "6.0.9")
        self.assertEqual(record["profile"]["stop_markers"], [])
        self.assertEqual(record["sources"]["current"], 14)
        self.assertEqual(record["sources"]["hdmi"], [13, 14, 15])
        names = {entry["Name"] for entry in record["apps_overlay"]}
        self.assertIn("Netflix", names)
        self.assertIn("docs/devices/", record["note"])
        self.assertNotIn("profiles/qn", record["note"])

    def test_keep_active_hits_are_skipped_not_suggested(self):
        record = inventory.compile_record(
            "QN55QN85CAPXPA", "T-PTMCUABC-0090-2220.4", SAMPLE,
            self.catalog, self.apps)
        self.assertNotIn("com.samsung.tv.coba.newhome",
                         [app for ids in record["suggested"].values() for app in ids])

    def test_first_inventory_wins(self):
        record = inventory.compile_record(
            "QN55QN85CAPXPA", "T-PTMCUABC-0090-2220.4", SAMPLE,
            self.catalog, self.apps)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "qn55qn85capxpa-t-ptmcuabc-0090-2220.4"
            written = inventory.write_inventory(directory, record)
            self.assertTrue((written / "draft-profile.json").is_file())
            self.assertTrue((written / "apps-overlay.json").is_file())
            with self.assertRaises(ValueError) as caught:
                inventory.write_inventory(directory, record)
            self.assertIn("first dump", str(caught.exception))

    def test_draft_is_not_a_profiles_path(self):
        directory = inventory.inventory_directory(ROOT / ".local", "QN55QN85CAPXPA",
                                                 "T-PTMCUABC-0090-2220.4")
        self.assertEqual(directory.parts[-2], "inventory")
        self.assertNotEqual(directory.parent.name, "profiles")


class InventoryGateTests(unittest.TestCase):
    def test_loopback_root_requires_a_lan_callback(self):
        with self.assertRaises(ValueError) as caught:
            tv.require_callback_host("127.0.0.1", None)
        self.assertIn("--callback-host", str(caught.exception))
        tv.require_callback_host("127.0.0.1", "192.0.2.10")
        tv.require_callback_host("192.0.2.50", None)

    def test_port_closed_reports_refused_as_closed(self):
        import socket
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        # Not listening: connect is refused.
        port = server.getsockname()[1]
        server.close()
        status, message = tv.check_port_closed("127.0.0.1", port)
        self.assertEqual(status, "closed")
        self.assertIn("closed", message)

    def test_port_closed_reports_an_open_listener(self):
        import socket
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        try:
            status, message = tv.check_port_closed("127.0.0.1", port)
            self.assertEqual(status, "open")
            self.assertIn("still open", message)
        finally:
            server.close()


class RelaySafetyTests(unittest.TestCase):
    def test_relay_listens_on_loopback_only(self):
        source = (ROOT / "tools/relay.py").read_text(encoding="utf-8")
        self.assertIn('LISTEN = "127.0.0.1"', source)
        self.assertNotIn("0.0.0.0", source)
        self.assertIn("26101", source)


if __name__ == "__main__":
    unittest.main()
