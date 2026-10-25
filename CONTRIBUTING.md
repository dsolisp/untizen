# Contributing

Read [AGENTS.md](AGENTS.md) first if you are using a coding agent: cleaning a
TV follows [PROMPT.md](PROMPT.md) and must not edit this repo.

Useful contributions are new device profiles, corrections to observed behavior,
new catalog groups backed by an inventory, small reviewed recipes and
improvements to the native launcher.

## Add a model

Start from `python3 tools/tv.py --host … --firmware … inventory`. That writes
a draft under `.local/inventory/` only. A one-session observation goes in
[docs/devices/](docs/devices/README.md). Promote it to
`profiles/<model>-<firmware>.json` only after cleanup, the launcher, a full
restart and standby/wake were exercised on that TV.

Use a separate profile rather than widening an existing one's model gate.
The profile records facts read from that TV:

```json
{
  "profile_version": 1,
  "model": "QN55QN85CAPXPA",
  "firmware": "T-PTMCUABC-0090-2220.4",
  "os": "Tizen (estimated 7.5-8.0)",
  "kernel": "Linux 5.4.77 armv7l",
  "runtime": "6.0.9",
  "registry": "/opt/dbspace/.pkgmgr_parser.db",
  "container": "com.samsung.tv.bixby-promotion",
  "settings_container": "com.samsung.tv.quicklaunch",
  "cleanup": { "groups": ["advertising", "tv-plus"], "add": {}, "remove": {} },
  "stop_markers": []
}
```

One profile per **(model, firmware)** pair. Two firmwares of the same panel
are two files; `tools/tv.py` only refuses two files that claim the same
model *and* firmware. An empty `stop_markers` list means those unit/marker
pairs were not inspected — do not copy another TV's. Report which steps were
exercised, what was checked after a full boot and after standby/wake, and how
restoration was verified. A successful preflight is not a successful root
session; a root session is not a validated launcher install. Preserve the
owner-selected features and take fresh rollback state.

A heavy restyle, a port to another OS, or another access route belongs in its
own repository with a row in [SHOWCASE.md](SHOWCASE.md). Compatibility
reports that are not yet end-to-end use
[.github/ISSUE_TEMPLATE/compatibility.md](.github/ISSUE_TEMPLATE/compatibility.md)
and a note under `docs/devices/`.

## Add or correct a cleanup group

Groups live in `data/cleanup-groups.json` and are matched with `fnmatch` globs
against the app IDs in the contributor's own snapshot, so one catalog serves
every model. Rules:

- Every glob must come from a read-only inventory of a real device. Say which
  model and firmware in the pull request.
- Be precise. `com.samsung.tv.coba.adagent` is evidence; `com.samsung.tv.coba.*`
  is the stock home shell and the catalog loader refuses it.
- Never weaken a `keep_active` invariant to make a group match. If you believe
  one is wrong, open an issue with the evidence instead.
- Model-specific IDs (the ten-character publisher prefixes, for example) belong
  in that profile's `cleanup.add`, not in the shared catalog.
- Describe the tradeoff in plain language: what stops working.

## Local checks

```sh
python3 -m unittest discover -s tests -v
python3 tools/tv.py profiles
python3 tools/build.py payloads
python3 tools/build.py package
dotnet run --project tests/CatalogTests.csproj -- launcher/assets/apps.json
```

NUI changes also need a build against matching private references and a clearly
stated hardware-test status. Launcher artwork must be path-only SVG — the NUI
renderer has no text support, so a `<text>` tile renders blank on the TV.

## Do not attach

Serial numbers, MAC or IP addresses, device/account IDs, original app
assemblies, SDK binaries, database snapshots or raw session logs. Review
screenshots for viewing history, profile names, Wi-Fi names and other personal
information before sharing them. Keep attribution and license files with any
derived asset or code.
