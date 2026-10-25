"""Keeps AGENTS.md honest: every path it names exists, and its commands match CI.

Coding agents follow AGENTS.md to the letter, so a renamed file or a moved gate
turns into a confident wrong instruction. A path is anything in a link or in
backticks that has a slash or a file extension; templates such as
`profiles/<model>-<firmware>.json` and globs are skipped, and so are the local
folders .gitignore names (`.local/`), which a fresh clone does not have yet.
A bare file name such as `apps.local.json` counts if a file of that name exists
somewhere in the repo.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
PROMPT = ROOT / "PROMPT.md"
README = ROOT / "README.md"
INVENTORY = ROOT / "docs" / "01-inventory.md"
CI = ROOT / ".github" / "workflows" / "checks.yml"

EXTENSION = re.compile(r"\.(md|py|sh|yml|yaml|json|txt|svg|cs|csproj)$")
TEMPLATE = re.compile(r"[<>*{}$=%]")
LINK = re.compile(r"\]\(([^)\s]+)\)")
CODE = re.compile(r"(`+)(.+?)\1")
SKIP_DIRS = {".git", ".local", "__pycache__", "bin", "obj"}


def text():
    return AGENTS.read_text(encoding="utf-8")


def ignored_entries():
    """Paths .gitignore names: they exist on a contributor's machine, not in a clone."""
    directories = []
    files = []
    for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if line.endswith("/"):
            directories.append(line.rstrip("/"))
        else:
            files.append(line)
    return directories, files


def file_names():
    names = set()
    for path in ROOT.rglob("*"):
        if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            names.add(path.name)
    return names


def named_paths():
    """(source, path) for every link target outside code and every path-like word in backticks."""
    body = text()
    found = []
    for target in LINK.findall(CODE.sub("", body)):
        if not re.match(r"(https?:|mailto:|#)", target):
            found.append(("link", target.split("#")[0]))
    for _, span in CODE.findall(body):
        for word in span.split():
            word = word.strip("'\"(),;:")
            if word.startswith("./"):
                word = word[2:]
            if not word or TEMPLATE.search(word) or word.startswith(("~", "/", "-", "http")):
                continue
            if "/" in word or EXTENSION.search(word):
                found.append(("code", word))
    return found


class AgentsPathsTest(unittest.TestCase):
    def test_every_named_path_exists(self):
        ignored_directories, ignored_files = ignored_entries()
        names = file_names()
        for source, path in named_paths():
            with self.subTest(path=path, source=source):
                if path in ignored_files:
                    continue
                if any(path == prefix or path.startswith(prefix + "/") for prefix in ignored_directories):
                    continue
                if "/" not in path.rstrip("/"):
                    self.assertTrue(
                        (ROOT / path).exists() or path.rstrip("/") in names,
                        f"AGENTS.md names {path}, and no file in the repo has that name")
                else:
                    self.assertTrue((ROOT / path).exists(),
                                    f"AGENTS.md names {path}, which does not exist")

    def test_it_names_paths_at_all(self):
        paths = [path for _, path in named_paths()]
        for expected in ("PROMPT.md", "tools/tv.py", "tools/plan_cleanup.py",
                         "data/cleanup-groups.json", "docs/02-access.md",
                         ".github/workflows/checks.yml"):
            self.assertIn(expected, paths)


class AgentsNumbersTest(unittest.TestCase):
    def test_commands_are_the_ones_ci_runs(self):
        ci = CI.read_text(encoding="utf-8")
        body = text()
        for command in ("python3 -m unittest discover -s tests -v",
                        "python3 tools/tv.py profiles",
                        "python3 tools/build.py payloads",
                        "dotnet run --project tests/CatalogTests.csproj -- launcher/assets/apps.json"):
            with self.subTest(command=command):
                self.assertIn(command, ci, "checks.yml changed; update AGENTS.md and this test")
                self.assertIn(command, body, "AGENTS.md no longer gives the command CI runs")

    def test_tv_helper_subcommands_match_the_parser(self):
        helper = (ROOT / "tools" / "tv.py").read_text(encoding="utf-8")
        for command in ("profiles", "doctor", "inventory", "root-check", "exec",
                        "pull", "push", "port-closed", "drift"):
            with self.subTest(command=command):
                self.assertIn(f'"{command}"', helper)
                self.assertIn(f"`{command}`", text())


class AgentsEntryPointsTest(unittest.TestCase):
    def test_claude_and_gemini_import_agents_md(self):
        for name in ("CLAUDE.md", "GEMINI.md"):
            with self.subTest(file=name):
                lines = (ROOT / name).read_text(encoding="utf-8").split("\n")
                self.assertIn("@AGENTS.md", [line.strip() for line in lines],
                              f"{name} must import AGENTS.md")

    def test_people_docs_point_at_it(self):
        for name in ("README.md", "CONTRIBUTING.md"):
            with self.subTest(file=name):
                self.assertIn("](AGENTS.md)", (ROOT / name).read_text(encoding="utf-8"))

    def test_cleaning_a_tv_comes_first(self):
        body = text()
        self.assertLess(
            body.index("PROMPT.md"),
            body.index("## Repo map"),
            "an agent cleaning a TV must be sent to PROMPT.md before the contributor sections")

    def test_prompt_is_the_operator_playbook(self):
        prompt = PROMPT.read_text(encoding="utf-8")
        self.assertIn("tools/tv.py", prompt)
        self.assertIn("--firmware", prompt)
        self.assertIn("plan_cleanup.py", prompt)
        self.assertIn("--profile", prompt)
        self.assertIn("Do not scan", prompt)
        self.assertIn("inventory", prompt)
        self.assertIn("port-closed", prompt)

    def test_readme_and_inventory_list_the_same_models(self):
        readme = README.read_text(encoding="utf-8")
        inventory = INVENTORY.read_text(encoding="utf-8")
        listing = subprocess_profiles()
        for token in ("UN75U8000FFXZA", "QN55QN85CAPXPA",
                      "T-KSU2EFAKUC-0090-1300.9", "T-PTMCUABC-0090-2220.4"):
            with self.subTest(token=token):
                self.assertIn(token, readme)
                self.assertIn(token, inventory)
                self.assertIn(token, listing)


def subprocess_profiles():
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/tv.py"), "profiles"],
        check=True, capture_output=True, text=True,
    )
    return result.stdout


if __name__ == "__main__":
    unittest.main()
