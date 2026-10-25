"""First-wins recovery, post-apply drift, forbidden globs and firmware-variant keys."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import cleanup_groups
import drift
import recovery
import tv


FIXTURE = json.loads((ROOT / "tests/fixtures/observed-ids.json").read_text())


def observed_ids():
    return sorted({*FIXTURE["keep_active"], *FIXTURE["streaming"],
                   *FIXTURE["profile_overrides"], *FIXTURE["groups"]})


def write_profile(directory, model, firmware, stem=None):
    data = {
        "profile_version": 1,
        "model": model,
        "firmware": firmware,
        "kernel": "Linux 5.4.0",
        "runtime": "6.0.9",
        "registry": "/opt/dbspace/.pkgmgr_parser.db",
        "container": "com.samsung.tv.bixby-promotion",
        "cleanup": {"groups": ["advertising"], "add": {}, "remove": {}},
        "stop_markers": [],
    }
    name = stem or f"{model.lower()}-{firmware}"
    path = Path(directory) / f"{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def snapshot_with(path, rows):
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE package_app_info (
              app_id TEXT, app_disable TEXT, app_onboot TEXT, app_autorestart TEXT
            );
        """)
        for app_id, values in rows.items():
            conn.execute(
                "INSERT INTO package_app_info VALUES (?,?,?,?)",
                (app_id, *values))
    return path


class ForbiddenGlobTests(unittest.TestCase):
    def test_coba_star_and_menu_globs_are_refused_at_load(self):
        catalog = json.loads((ROOT / "data/cleanup-groups.json").read_text())
        catalog["groups"]["hostile"] = {
            "description": "must not load",
            "patterns": ["com.samsung.tv.coba.*"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                cleanup_groups.load_catalog(path)
            self.assertIn("coba.*", str(caught.exception))

    def test_a_glob_that_covers_keep_active_is_refused_at_load(self):
        catalog = json.loads((ROOT / "data/cleanup-groups.json").read_text())
        catalog["groups"]["hostile"] = {
            "description": "must not load",
            "patterns": ["org.tizen.m*"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                cleanup_groups.load_catalog(path)
            self.assertIn("org.tizen.menu", str(caught.exception))

    def test_profile_add_cannot_smuggle_a_forbidden_glob(self):
        catalog = cleanup_groups.load_catalog()
        profile = cleanup_groups.load_profile(ROOT / "profiles/qn55qn85capxpa-2220.4.json")
        hostile = dict(profile)
        hostile["cleanup"] = dict(profile["cleanup"],
                                  add={"advertising": ["com.samsung.tv.coba.*"]})
        with self.assertRaises(ValueError) as caught:
            cleanup_groups.group_patterns(catalog, hostile, "advertising")
        self.assertIn("coba.*", str(caught.exception))


class ObservedFixtureTests(unittest.TestCase):
    def test_keep_active_ids_from_the_fixture_never_resolve(self):
        catalog = cleanup_groups.load_catalog()
        ids = observed_ids()
        protected = set(FIXTURE["keep_active"])
        for path in sorted((ROOT / "profiles").glob("*.json")):
            profile = cleanup_groups.load_profile(path)
            _, flat = cleanup_groups.resolve(
                catalog, profile, cleanup_groups.profile_groups(profile), ids)
            self.assertFalse(protected & set(flat), f"{path.name} targeted keep_active")
            self.assertFalse(set(FIXTURE["streaming"]) & set(flat),
                             f"{path.name} targeted a streaming app")


class FirmwareVariantTests(unittest.TestCase):
    def test_two_firmwares_of_one_model_coexist(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_profile(tmp, "UN99TEST", "1000.0", "un99test-1000.0")
            write_profile(tmp, "UN99TEST", "2000.0", "un99test-2000.0")
            profiles = tv.load_profiles(tmp)
            self.assertEqual(len(profiles), 2)
            _, first = tv.resolve_profile(profiles, "UN99TEST", "1000.0", None, None)
            _, second = tv.resolve_profile(profiles, "UN99TEST", "2000.0", None, None)
            self.assertEqual(first["firmware"], "1000.0")
            self.assertEqual(second["firmware"], "2000.0")
            with self.assertRaises(ValueError) as caught:
                tv.resolve_profile(profiles, "UN99TEST", "9999.0", None, None)
            self.assertIn("1000.0", str(caught.exception))
            self.assertIn("2000.0", str(caught.exception))

    def test_duplicate_model_and_firmware_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_profile(tmp, "UN99TEST", "1000.0", "one")
            write_profile(tmp, "UN99TEST", "1000.0", "two")
            with self.assertRaises(ValueError) as caught:
                tv.load_profiles(tmp)
            self.assertIn("1000.0", str(caught.exception))


class RecoveryFirstWinsTests(unittest.TestCase):
    def test_retry_keeps_original_fields_and_only_appends_new_ids(self):
        first = {
            "model": "UN99TEST", "firmware": "1000.0",
            "apps": [{"app_id": "com.samsung.tv.acr",
                      "app_disable": "false", "app_onboot": "true",
                      "app_autorestart": "false"}],
        }
        retry = {
            "model": "UN99TEST", "firmware": "1000.0",
            "apps": [
                {"app_id": "com.samsung.tv.acr",
                 "app_disable": "true", "app_onboot": "false",
                 "app_autorestart": "false"},
                {"app_id": "com.samsung.tv.tvplus",
                 "app_disable": "false", "app_onboot": "true",
                 "app_autorestart": "false"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recovery.json"
            written, created = recovery.save_first_wins(path, first)
            self.assertTrue(created)
            kept, created = recovery.save_first_wins(path, retry)
            self.assertFalse(created)
            by_id = {app["app_id"]: app for app in kept["apps"]}
            self.assertEqual(by_id["com.samsung.tv.acr"]["app_disable"], "false")
            self.assertIn("com.samsung.tv.tvplus", by_id)

    def test_sidecar_name_is_stable(self):
        self.assertEqual(
            recovery.sidecar_name("UN75U8000FFXZA", "T-KSU2EFAKUC-0090-1300.9",
                                  ["advertising"]),
            recovery.sidecar_name("UN75U8000FFXZA", "T-KSU2EFAKUC-0090-1300.9",
                                  ["advertising"]))


class DriftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.plan = Path(self.temp.name) / "plan"
        self.plan.mkdir()
        (self.plan / "before.json").write_text(json.dumps({
            "apps": [
                {"app_id": "com.samsung.tv.acr",
                 "app_disable": "false", "app_onboot": "true",
                 "app_autorestart": "false"},
                {"app_id": "com.samsung.tv.tvplus",
                 "app_disable": "false", "app_onboot": "true",
                 "app_autorestart": "false"},
            ],
        }), encoding="utf-8")
        (self.plan / "apply.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_stable_snapshot_exits_zero(self):
        snap = snapshot_with(Path(self.temp.name) / "ok.db", {
            "com.samsung.tv.acr": ("true", "false", "false"),
            "com.samsung.tv.tvplus": ("true", "false", "false"),
        })
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/tv.py"), "drift",
             "--snapshot", str(snap), "--plan", str(self.plan)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 still applied", result.stdout)
        self.assertNotIn("--firmware", result.stderr)
        self.assertNotIn("--host", result.stderr)

    def test_drift_and_missing_exit_one_and_fix_does_not_rewrite(self):
        snap = snapshot_with(Path(self.temp.name) / "drift.db", {
            "com.samsung.tv.acr": ("false", "true", "false"),
        })
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/tv.py"), "drift",
             "--snapshot", str(snap), "--plan", str(self.plan), "--fix"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("drifted", result.stdout)
        self.assertIn("missing", result.stdout)
        self.assertIn("not rewritten", result.stdout)
        self.assertIn("apply.sh", result.stdout)
        compared = drift.compare(drift.read_rows(snap), drift.load_plan(self.plan))
        self.assertEqual(len(compared["drifted"]), 1)
        self.assertEqual(compared["missing"], ["com.samsung.tv.tvplus"])


if __name__ == "__main__":
    unittest.main()
