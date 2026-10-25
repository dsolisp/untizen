import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import cleanup_groups
import tv


class ProfileSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = cleanup_groups.load_catalog()
        cls.profiles = tv.load_profiles()

    def test_every_profile_carries_the_fields_recipes_and_plans_need(self):
        for key, (path, profile) in sorted(self.profiles.items()):
            with self.subTest(path.name):
                self.assertEqual(key, profile["model"].upper())
                self.assertEqual(profile["profile_version"], 1)
                for field in ("firmware", "kernel", "runtime", "registry", "container"):
                    self.assertTrue(profile.get(field), f"{path.name} is missing {field}")
                self.assertTrue(profile["registry"].startswith("/"), f"{path.name}: registry must be absolute")
                self.assertRegex(profile["container"], r"^[A-Za-z0-9_.-]+$")
                self.assertRegex(profile["model"], r"^[A-Z0-9]+$")
                self.assertRegex(profile["firmware"], r"^[A-Za-z0-9_.-]+$")

    def test_selected_groups_and_overrides_only_reference_catalog_groups(self):
        for path, profile in self.profiles.values():
            cleanup = profile.get("cleanup", {})
            self.assertTrue(cleanup.get("groups"), f"{path.name} selects no cleanup groups")
            for group in cleanup["groups"]:
                self.assertIn(group, self.catalog["groups"], f"{path.name}: unknown group {group}")
            for section in ("add", "remove"):
                for group in cleanup.get(section, {}):
                    self.assertIn(group, self.catalog["groups"], f"{path.name}: {section} names {group}")

    def test_no_group_glob_covers_a_keep_active_app(self):
        for path, profile in self.profiles.values():
            protected = [pattern for pattern, _ in cleanup_groups.protected_patterns(self.catalog, profile)]
            _, flat = cleanup_groups.resolve(
                self.catalog, profile, cleanup_groups.profile_groups(profile), protected)
            self.assertEqual(flat, [], f"{path.name} would disable a keep-active container")

    def test_an_app_id_glob_never_belongs_to_two_groups(self):
        for path, profile in self.profiles.values():
            groups = cleanup_groups.profile_groups(profile)
            patterns = [pattern for group in groups
                        for pattern in cleanup_groups.group_patterns(self.catalog, profile, group)]
            per_group, flat = cleanup_groups.resolve(self.catalog, profile, groups, patterns)
            self.assertEqual(sum(len(ids) for ids in per_group.values()), len(flat),
                             f"{path.name}: two groups claim the same app id")

    def test_catalog_invariants_carry_reasons(self):
        for entry in self.catalog["keep_active"]:
            self.assertTrue(entry["pattern"])
            self.assertTrue(entry["reason"].strip())


class ProfileResolutionTests(unittest.TestCase):
    def setUp(self):
        self.profiles = tv.load_profiles()
        self.path, self.profile = next(iter(sorted(self.profiles.values())))

    def test_unknown_model_is_guided_instead_of_silent(self):
        with self.assertRaises(ValueError) as caught:
            tv.resolve_profile(self.profiles, "UN99ZZ9999XX", None, None, None)
        message = str(caught.exception)
        self.assertIn("Supported models", message)
        self.assertIn("profiles/", message)

    def test_declared_firmware_must_match_the_profile(self):
        with self.assertRaises(ValueError):
            tv.resolve_profile(self.profiles, self.profile["model"], "0000.0", None, None)
        _, resolved = tv.resolve_profile(self.profiles, self.profile["model"], self.profile["firmware"], None, None)
        self.assertEqual(resolved["model"], self.profile["model"])

    def test_explicit_profile_and_model_arguments_win_over_observation(self):
        self.assertEqual(tv.resolve_profile(self.profiles, "IGNORED", None, self.path, None)[0], self.path)
        _, resolved = tv.resolve_profile(self.profiles, None, None, None, self.profile["model"].lower())
        self.assertEqual(resolved["model"], self.profile["model"])

    def test_script_environment_exports_every_recipe_variable(self):
        env = tv.script_environment(self.profile)
        for name in ("UNTIZEN_CONTAINER", "UNTIZEN_SETTINGS_CONTAINER", "UNTIZEN_STAGE",
                     "UNTIZEN_BACKUP_DIR", "UNTIZEN_REGISTRY"):
            self.assertIn(f"{name}=", env)
        self.assertIn("export UNTIZEN_CONTAINER", env)

    def test_profiles_listing_names_every_supported_model(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            tv.print_profiles(self.profiles)
        listing = buffer.getvalue()
        for key, (_, profile) in self.profiles.items():
            self.assertIn(profile["model"], listing)
            self.assertIn(profile["firmware"], listing)
            self.assertGreaterEqual(len(key), 10)


if __name__ == "__main__":
    unittest.main()
