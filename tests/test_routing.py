import re
import sqlite3
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.conn = sqlite3.connect(self.directory / "live.db")
        self.conn.executescript("""
          CREATE TABLE key_filter(appid TEXT, key TEXT, target_selector TEXT, args TEXT, other TEXT);
          INSERT INTO key_filter VALUES
            ('com.samsung.tv.quicklaunch','XF86More','package:com.samsung.tv.quicklaunch','original-more','keep'),
            ('org.tizen.menu','XF86SysMenu','package:org.tizen.menu','original-menu','keep'),
            ('unrelated.app','Other','package:unrelated.app','unrelated','keep');
        """)
        with sqlite3.connect(self.directory / ".app-context.db") as snapshot:
            self.conn.backup(snapshot)

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def sql(self, recipe):
        script = (ROOT / "recipes" / recipe).read_text()
        sql = re.search(r"<<SQL\n(.*?)\nSQL", script, re.S).group(1)
        # The recipes read their containers from the profile environment; the
        # synthetic registry stands in for the two containers they name.
        return (sql.replace("$D", str(self.directory))
                   .replace("$K", "com.samsung.tv.quicklaunch")
                   .replace("$C", "com.samsung.tv.bixby-promotion"))

    def test_round_trip_preserves_new_metadata(self):
        self.conn.executescript(self.sql("install-settings-bridge.sh"))
        self.conn.execute("DETACH before")
        self.conn.execute("UPDATE key_filter SET other='updated'")
        self.conn.commit()
        self.conn.executescript(self.sql("restore-settings-bridge.sh"))
        self.assertEqual(self.conn.execute("SELECT target_selector,args,other FROM key_filter "
                         "WHERE appid='org.tizen.menu'").fetchone(),
                         ("package:org.tizen.menu", "original-menu", "updated"))
        self.assertEqual(self.conn.execute("SELECT args FROM key_filter "
                         "WHERE appid='unrelated.app'").fetchone(), ("unrelated",))

    def test_changed_rule_refuses_apply(self):
        self.conn.execute("UPDATE key_filter SET args='vendor-update' WHERE appid='org.tizen.menu'")
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.executescript(self.sql("install-settings-bridge.sh"))
        self.conn.rollback()
        self.assertEqual(self.conn.execute("SELECT args FROM key_filter "
                         "WHERE appid='com.samsung.tv.quicklaunch'").fetchone(), ("original-more",))

    def test_changed_rule_refuses_restore(self):
        self.conn.executescript(self.sql("install-settings-bridge.sh"))
        self.conn.execute("DETACH before")
        self.conn.execute("UPDATE key_filter SET args='new vendor route' WHERE appid='org.tizen.menu'")
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.executescript(self.sql("restore-settings-bridge.sh"))
        self.conn.rollback()


class LauncherUpdateRecipeTests(unittest.TestCase):
    """The update path must never overwrite a launcher without a rollback."""

    def setUp(self):
        self.text = (ROOT / "recipes/update-launcher.sh").read_text()

    def test_it_only_updates_an_existing_launcher(self):
        self.assertIn('test -d "$A/res/quiet-home"', self.text)

    def test_it_refuses_unsafe_snapshot_names(self):
        self.assertIn("*[!A-Za-z0-9_-]*", self.text)

    def test_it_keeps_a_rollback_before_touching_files(self):
        backup = self.text.index('update-previous/BixbyPromotion.dll')
        first_copy = self.text.index('cp "$S/unpacked/BixbyPromotion.dll"')
        self.assertLess(backup, first_copy)
        self.assertIn("update-previous/quiet-home", self.text)

    def test_it_reapplies_owner_and_label(self):
        for fragment in ("chown 201:0", "chmod 644", "chsmack -a User::Pkg::"):
            self.assertIn(fragment, self.text)

    def test_it_verifies_the_archive_before_unpacking(self):
        self.assertIn('test -s "$S/unpacked/BixbyPromotion.dll"', self.text)
        self.assertIn('test -s "$S/unpacked/quiet-home/apps.json"', self.text)
        for downloader in ("curl", "wget"):
            self.assertNotIn(downloader, self.text)


if __name__ == "__main__":
    unittest.main()
