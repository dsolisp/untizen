# Contributing

Useful contributions are new device profiles, corrections to observed behavior,
new catalog groups backed by an inventory, small reviewed recipes and
improvements to the native launcher.

## Add a model

Use a separate profile rather than widening an existing one's model gate.
`profiles/<model>-<firmware>.json` records facts read from that TV:

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
  "cleanup": { "groups": ["advertising", "tv-plus"], "add": {}, "remove": {} }
}
```

One profile per model code: `tools/tv.py` refuses two files that claim the same
model. Report which steps were exercised, what was checked after a full boot and
after standby/wake, and how restoration was verified. A successful preflight is
not a successful root session; a root session is not a validated launcher
install. Preserve the owner-selected features and take fresh rollback state.

## Add or correct a cleanup group

Groups live in `data/cleanup-groups.json` and are matched with `fnmatch` globs
against the app IDs in the contributor's own snapshot, so one catalog serves
every model. Rules:

- Every glob must come from a read-only inventory of a real device. Say which
  model and firmware in the pull request.
- Be precise. `com.samsung.tv.coba.adagent` is evidence; `com.samsung.tv.coba.*`
  is the stock home shell.
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
