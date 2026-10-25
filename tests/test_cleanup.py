import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import cleanup_groups
from plan_cleanup import read_snapshot, make_sql


def synthetic_snapshot(path, ids):
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE package_app_info (
              app_id TEXT, app_disable TEXT, app_onboot TEXT, app_autorestart TEXT,
              unrelated TEXT
            );
        """)
        for app_id in ids:
            conn.execute("INSERT INTO package_app_info VALUES (?,'false','true','false','keep')", (app_id,))
    return path


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "synthetic.db"
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript("""
            CREATE TABLE package_app_info (
              app_id TEXT, app_disable TEXT, app_onboot TEXT, app_autorestart TEXT,
              unrelated TEXT
            );
            INSERT INTO package_app_info VALUES ('example.optional','false','true','false','keep');
            INSERT INTO package_app_info VALUES ('example.core','false','true','true','keep');
        """)
        self.rows = read_snapshot(self.path, ["example.optional"])[1]

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_round_trip_preserves_unrelated_changes(self):
        self.conn.executescript(make_sql(self.rows))
        self.assertEqual(self.conn.execute("SELECT app_disable,app_onboot,app_autorestart "
                         "FROM package_app_info WHERE app_id='example.optional'").fetchone(),
                         ("true", "false", "false"))
        self.conn.execute("UPDATE package_app_info SET unrelated='new app metadata'")
        self.conn.execute("UPDATE package_app_info SET app_onboot='false' WHERE app_id='example.core'")
        self.conn.commit()
        self.conn.executescript(make_sql(self.rows, restore=True))
        self.assertEqual(self.conn.execute("SELECT app_disable,app_onboot,app_autorestart,unrelated "
                         "FROM package_app_info WHERE app_id='example.optional'").fetchone(),
                         ("false", "true", "false", "new app metadata"))
        self.assertEqual(self.conn.execute("SELECT app_onboot FROM package_app_info "
                         "WHERE app_id='example.core'").fetchone(), ("false",))

    def test_apply_refuses_target_field_drift(self):
        self.conn.execute("UPDATE package_app_info SET app_autorestart='true' WHERE app_id='example.optional'")
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.executescript(make_sql(self.rows))
        self.conn.rollback()
        self.assertEqual(self.conn.execute("SELECT app_disable FROM package_app_info "
                         "WHERE app_id='example.optional'").fetchone(), ("false",))

    def test_restore_refuses_target_field_drift(self):
        self.conn.executescript(make_sql(self.rows))
        self.conn.execute("UPDATE package_app_info SET app_onboot='true' WHERE app_id='example.optional'")
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.executescript(make_sql(self.rows, restore=True))
        self.conn.rollback()

    def test_all_guards_run_before_any_update(self):
        rows = read_snapshot(self.path, ["example.optional", "example.core"])[1]
        self.conn.execute("DELETE FROM package_app_info WHERE app_id='example.core'")
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.executescript(make_sql(rows))
        self.conn.rollback()
        self.assertEqual(self.conn.execute("SELECT app_disable FROM package_app_info").fetchone(), ("false",))

    def test_missing_and_duplicate_rows_fail(self):
        with self.assertRaises(ValueError):
            read_snapshot(self.path, ["missing.app"])
        self.conn.execute("INSERT INTO package_app_info SELECT * FROM package_app_info WHERE app_id='example.optional'")
        self.conn.commit()
        with self.assertRaises(ValueError):
            read_snapshot(self.path, ["example.optional"])

    def test_unknown_boolean_and_sql_injection_fail(self):
        self.conn.execute("UPDATE package_app_info SET app_disable='yes'")
        self.conn.commit()
        with self.assertRaises(ValueError):
            read_snapshot(self.path, ["example.optional"])
        with self.assertRaises(ValueError):
            read_snapshot(self.path, ["example'; DROP TABLE package_app_info;--"])

    def test_null_original_value_round_trip(self):
        self.conn.execute("UPDATE package_app_info SET app_onboot=NULL WHERE app_id='example.optional'")
        self.conn.commit()
        rows = read_snapshot(self.path, ["example.optional"])[1]
        self.conn.executescript(make_sql(rows))
        self.conn.executescript(make_sql(rows, restore=True))
        self.assertIsNone(self.conn.execute("SELECT app_onboot FROM package_app_info "
                          "WHERE app_id='example.optional'").fetchone()[0])


class CatalogPlanTests(unittest.TestCase):
    """The catalog resolves against the operator's snapshot, and plans are reproducible."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = cleanup_groups.load_catalog()
        cls.profile = cleanup_groups.load_profile(ROOT / "profiles/qn55qn85capxpa-2220.4.json")
        cls.groups = cleanup_groups.profile_groups(cls.profile)
        # One literal installed id per glob (every '*' realised as 'a'): each group
        # must match its own patterns, and keep-active ids must never be matched.
        literal = lambda pattern: pattern.replace("*", "a")
        cls.ids = sorted({literal(pattern) for group in cls.groups
                          for pattern in cleanup_groups.group_patterns(cls.catalog, cls.profile, group)})
        cls.ids += [literal(pattern) for pattern, _ in cleanup_groups.protected_patterns(cls.catalog, cls.profile)]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        synthetic_snapshot(Path(self.temp.name) / "snapshot.db", self.ids)
        self.snapshot = Path(self.temp.name) / "snapshot.db"

    def tearDown(self):
        self.temp.cleanup()

    def test_resolution_is_stable_and_protected_ids_stay_out(self):
        first = cleanup_groups.resolve(self.catalog, self.profile, self.groups, self.ids)
        second = cleanup_groups.resolve(self.catalog, self.profile, self.groups, self.ids)
        self.assertEqual(first, second)
        per_group, flat = first
        protected = {pattern for pattern, _ in cleanup_groups.protected_patterns(self.catalog, self.profile)}
        self.assertFalse(protected & set(flat))
        for group in self.groups:
            self.assertTrue(per_group[group], f"group {group} matched nothing in its own patterns")

    def test_a_glob_that_would_hit_a_keep_active_app_is_refused(self):
        hostile = dict(self.profile)
        hostile["cleanup"] = dict(self.profile["cleanup"],
                                  add={"advertising": [self.profile["container"][:12] + "*"]})
        with self.assertRaises(ValueError):
            cleanup_groups.resolve(self.catalog, hostile, self.groups, self.ids)

    def test_generated_plans_are_byte_identical_across_runs(self):
        outputs = []
        for run in ("first", "second"):
            out = ROOT / ".local" / f"plan-determinism-{run}"
            if out.exists():
                shutil.rmtree(out)
            try:
                subprocess.run([sys.executable, str(ROOT / "tools/plan_cleanup.py"),
                                "--snapshot", str(self.snapshot),
                                "--profile", str(ROOT / "profiles/qn55qn85capxpa-2220.4.json"),
                                "--output", str(out)],
                               check=True, capture_output=True)
                outputs.append({path.name: path.read_bytes()
                                for path in out.iterdir()})
            finally:
                shutil.rmtree(out, ignore_errors=True)
        self.assertEqual(outputs[0].keys(), outputs[1].keys())
        for name in outputs[0]:
            self.assertEqual(outputs[0][name], outputs[1][name], name)
        self.assertIn("apply.sql", outputs[0])
        self.assertIn("restore.sql", outputs[0])
        self.assertIn("before.json", outputs[0])
        self.assertIn("recovery.json", outputs[0])
        self.assertIn("stop-markers.json", outputs[0])

    def test_plans_must_stay_inside_the_private_directory(self):
        outside = Path(self.temp.name) / "plan"
        result = subprocess.run([sys.executable, str(ROOT / "tools/plan_cleanup.py"),
                                 "--snapshot", str(self.snapshot),
                                 "--profile", str(ROOT / "profiles/qn55qn85capxpa-2220.4.json"),
                                 "--output", str(outside)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".local", result.stderr)


if __name__ == "__main__":
    unittest.main()
