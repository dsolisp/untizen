# Instructions for an agent working in this repository

## First: which job are you doing?

| You were asked to | Do this |
|---|---|
| Clean up a Tizen TV the owner identifies: inventory, reversible cleanup, install the launcher | Read [PROMPT.md](PROMPT.md) and follow it exactly, on the real TV. Use `tools/tv.py`, `tools/plan_cleanup.py` and `recipes/` rather than writing new ones. The only files you may create are under ignored `.local/` (and an ignored local catalog overlay if the owner asked for one). Do not edit this repo's docs, tests, catalog or profiles, and do not open issues or pull requests unless the person asks you to. |
| Change this repo: a profile, a catalog glob, a recipe, the launcher, docs, tests | Skip the next section and read on from [Repo map](#repo-map). |

### Cleaning a TV: the rules that are not negotiable

[PROMPT.md](PROMPT.md) is the procedure. Its safety rules, in brief:

- **Work only on the TV the owner identifies.** Use the IPv4 they gave you.
  Do not scan the LAN or reuse another person's saved device identity.
- **`--firmware` is required** for every `tools/tv.py` action except
  `profiles`, `port-closed` and `drift`. It is the operator's declaration
  from About This TV; the helper does not read it from the set. Never guess it.
- **`--host` is required** for every action except `profiles` and `drift`.
- **`tv inventory` is the first command on a new TV.** It is read-only, may
  run without a matching profile, and writes only under `.local/inventory/`.
  It never writes `profiles/`.
- **Stop after inventory if no profile matches** the SDB model and the
  declared firmware. Show the draft and the concrete gap. Never run another
  model's data. `doctor`, `root-check`, `exec`, `pull` and `push` still
  require a match. Writing `profiles/<model>-<firmware>.json` is a repo
  change, not a cleaning step. A one-session note goes in
  `docs/devices/README.md` until the TV is exercised end to end.
- **Disable registry flags, never uninstall, never flash.** Only
  `app_disable`, `app_onboot` and `app_autorestart`, from a plan
  `tools/plan_cleanup.py` generated against *this* TV's snapshot.
  `--profile` is required. Omit `--output` to print matches; review them
  with the owner before writing SQL.
- **Back up first.** `recipes/snapshot.sh`, keep the first backup, write the
  inverse before applying. The planner's recovery record is first-wins: a
  retry must not replace the original field values. Compare later snapshots
  with `tv drift`. Do not overwrite the first backup to make a retry succeed.
- **Leave alone what the TV needs:** HDMI, display, audio, networking,
  Bluetooth, package/application management, accessibility, the owner's
  streaming apps, `org.tizen.menu`, and the profile `container` (Quiet Home
  lives there). Voice, SmartThings, health, gaming-hub helpers and TV Plus
  are optional features — ask, do not treat them as malware.
- **`keep_active` is an error, not a warning.** Do not weaken
  `data/cleanup-groups.json` to make a plan succeed.
- **Install the launcher without assigning Home** until the owner has seen
  the UI, remote, HDMI, sound and settings. There is no reliable screenshot
  API; `recipes/status.sh` plus what the owner sees is the proof. Then assign
  Home/startup; settings bridge and `light-shell` later.
- **One SDB/root session at a time**, under the 30-second command budget.
  Do not reboot or stand the TV down inside the temporary root session.
- **Close Developer Mode** when the owner is done. Check with
  `tv port-closed`. Do not leave staging without saying so. If the sandbox
  cannot reach the TV, ask the owner to run `tools/relay.py` in an ordinary
  terminal and pass `--host 127.0.0.1 --callback-host <LAN-IPv4>`; read
  `tools/relay.md`. Do not scan the LAN.
- **Stop and say so** when `inventory`, `doctor` or `root-check` fails after
  one inspect, when a plan would hit `keep_active`, or when the owner asks
  to flash or replace the OS.

The owner's snapshots, plans, session logs and framework assemblies stay
under `.local/` and must never be committed.

## Repo map

| Path | What it is |
|---|---|
| `PROMPT.md` | The prompt people paste into their agent. Brand-neutral; safety rules live here. |
| `README.md` | Front page: what UnTizen does, supported models, quickstart. |
| `CONTRIBUTING.md` | The contributor guide for people. New profiles and catalog globs start here. |
| `AGENTS.md` | This file. Job 1 is cleaning a TV; Job 2 is changing the repo. |
| `docs/01-inventory.md` | Identify the TV; when a matching brand is not compatibility. |
| `docs/02-access.md` | Developer Mode, SDB, `doctor`, `root-check`, transfers. |
| `docs/03-cleanup.md` | Snapshots, planner, one group at a time, restore. |
| `docs/04-launcher.md` | Build, install, verify, then assign Home. |
| `docs/05-controller.md` | Native DualSense pairing. |
| `docs/06-artwork.md` | Path-only SVG; optional local publisher art. |
| `docs/07-performance.md` | What was measured; do not overclaim. |
| `docs/08-privacy.md` | What the privacy work did and did not prove. |
| `docs/09-recovery.md` | Restore the stock experience. |
| `SHOWCASE.md` | Ports, restyles and other-OS work that do not belong in this tree. |
| `docs/provenance.md` | Fork base, vendored access route, validation limits. |
| `docs/devices/README.md` | One-session notes versus end-to-end `profiles/`. |
| `profiles/` | Per-device facts. One exercised model/firmware pair per file. |
| `data/cleanup-groups.json` | Shared glob catalog and `keep_active` invariants. |
| `tools/tv.py` | `profiles`, `doctor`, `inventory`, `root-check`, `exec`, `pull`, `push`, `port-closed`, `drift`. |
| `tools/inventory.py` | Parse a read-only dump into a draft under `.local/inventory/`. |
| `tools/relay.py` | Loopback SDB forward; guide: `tools/relay.md`. |
| `tools/plan_cleanup.py` | Match catalog to a snapshot; emit apply/restore SQL and a first-wins recovery record. |
| `tools/recovery.py` | First-wins recovery records. |
| `tools/drift.py` | Compare a later snapshot to a generated plan. |
| `tools/cleanup_groups.py` | Catalog and profile loaders used by the tools and tests. |
| `tools/build.py` | Access payloads, launcher, deterministic package tarball. |
| `recipes/` | Inventory, snapshot, status, stop-marker, launcher and restore scripts. |
| `launcher/` | Quiet Home (NUI/.NET), app catalog, Probe, settings bridge. |
| `tests/` | Offline unittest and CatalogTests. No live TV. |
| `.github/workflows/checks.yml` | CI: unittest, `tv.py profiles`, payloads, CatalogTests. |

## Where a change goes

| The change | Where it goes |
|---|---|
| A new exercised model/firmware | `profiles/<model>-<firmware>.json` plus a README row. Two firmwares of one panel are two files. See [Add a model](CONTRIBUTING.md#add-a-model). |
| A one-session inventory | `docs/devices/` from the `.local/inventory/` note. Not a profile. |
| A heavy restyle, another OS, or another access route | Its own repository, plus a row in [SHOWCASE.md](SHOWCASE.md). |
| A cleanup glob backed by a real inventory | `data/cleanup-groups.json`. Precise globs only. `coba.*` is refused. |
| A model-specific app ID | That profile's `cleanup.add`, not the shared catalog. |
| A recipe or helper fix | `recipes/` or `tools/`, with a test if the behaviour is offline. |
| Launcher behaviour | `launcher/src/`. Path-only SVG. Validate on a compatible TV before claiming it was tested there. |
| Docs | The numbered guide that already covers the topic. Keep README and `docs/01-inventory.md` tables in step. |

Do not turn the catalog or a profile into an indiscriminate Samsung-wide
debloat list. A matching brand, year or Tizen version is not compatibility.

## Work in phases

These phases apply when changing the repo *and* when the owner has asked you
to add a profile. Cleaning a TV already listed still follows [PROMPT.md](PROMPT.md)
and does not skip inventory.

1. Inventory first (`tv inventory`): record model, firmware, runtime, schemas,
   installed apps, source IDs, root capabilities and current Home/startup
   selectors. The draft stays under `.local/inventory/`.
2. Resolve the profile (`python3 tools/tv.py profiles` lists what this checkout
   covers). If the device is new, write a note under `docs/devices/` from that
   draft; add `profiles/<model>-<firmware>.json` only after the later phases
   and only select cleanup groups whose IDs you actually observed there.
3. Stop before mutation if the model or firmware differs from every profile.
   Explain the concrete gap and investigate a separate profile.
4. Build the source locally. Obtain necessary proprietary assemblies from the
   owner's device or a permitted SDK; do not upload them.
5. Take consistent SQLite snapshots with `.backup`, save original app
   assemblies/metadata, and write the specific inverse operations before
   mutation. Keep a recovery copy both on the TV and under `.local/`.
6. Plan one group at a time (`tools/plan_cleanup.py` without `--output` prints
   what matched), review the matched IDs with the owner, then generate and
   apply. Validate every target, compare rows to the fresh snapshot and
   preserve fields outside the intended scope.
7. Install the launcher without changing the default Home. Verify the visible
   UI, remote, HDMI, sound and settings first. Then assign Home/startup, and
   later install the settings bridge and disable the sidebar/browser.
8. Test a full restart and standby/wake separately. Re-check app-preload
   values, service conditions and Home selectors. A process disappearing once
   is not proof of persistence.
9. Summarize actual evidence, limitations and how to undo the changes.

Run SDB/root sessions sequentially. Keep scripts below the 30-second command
budget. A failed script may have completed earlier filesystem operations;
inspect before retrying. Do not overwrite the first backup to make a retry
succeed. Do not reboot or put the TV in standby inside the temporary root
session; allow its cleanup checks to complete first.

## Implementation constraints

- Do not flash firmware, replace a bootloader, remove partition contents,
  alter `/etc/passwd` or replace Samsung's SDB verification key.
- Do not assume UID 0 defeats SMACK, signed-native-executable enforcement or
  secure boot. No custom OS installation path was established for these models.
- Preserve native advanced/network/Bluetooth settings for functions the new
  UI does not implement. Never globally disable `org.tizen.menu`.
- Private Samsung APIs, HDMI source integers, UID 5001, owner 201:0, package
  containers and app IDs are observations for the tested builds. Inspect them
  before reuse. The profile's `container` is repurposed to host the launcher;
  it must never appear on a disable list. The catalog enforces that, and the
  enforcement must not be weakened to make a plan succeed.
- Catalog globs must come from a read-only inventory of a real device, and
  every `keep_active` entry keeps its reason. Prefer a precise glob over a
  broad one: `com.samsung.tv.coba.adagent` is evidence, `com.samsung.tv.coba.*`
  is the stock home shell and would break the TV.
- Do not replace a live registry wholesale with an old database. Generate
  field-specific rollback; fail on drift instead of overwriting app updates.
- Do not kill every process, clear streaming-app data, log users out, remove
  account credentials or disable updates as a generic speed fix.
- Runtime systemd masks do not survive restart. Cached app-preload settings
  can be overwritten. No hidden watchdog or always-on root daemon is included.
- Do not claim every privacy path is eliminated. No decrypted traffic audit
  of these TVs was performed. See [docs/08-privacy.md](docs/08-privacy.md).
- Launcher artwork must be path-only SVG: the NUI renderer has no text support,
  so a `<text>` tile renders blank on the TV.

## Local data and publication

Use `.local/` for device-specific plans, raw command output, screenshots,
snapshots, builds and extracted framework assemblies. Downloaded publisher art
and a customized catalog stay in ignored overlays next to
`launcher/assets/apps.json`; they are not for public commits. The shipped
catalog is `launcher/assets/apps.json`.

Before any public commit, inspect tracked files for credentials, network
addresses, device/account identifiers, personal filesystem paths, screenshots,
logs, proprietary binaries and original database snapshots. Do not upload
an entire working directory. Keep only sanitized findings and minimal
reproduction examples in reports.

When changing the catalog, the profiles or the SQL generators, run the offline
tests and check apply/restore round trips and concurrent state drift with
synthetic databases. When changing NUI code, compile against matching private
references and validate on a compatible TV before claiming the new build was
tested there. App navigation tests can run without Samsung references. Keep all
third-party license notices and provenance.

## Before opening a PR

| Check | Command or rule |
|---|---|
| Tests, as CI runs them | `python3 -m unittest discover -s tests -v` |
| Supported models | `python3 tools/tv.py profiles` — the listing must match the README table and `docs/01-inventory.md`. |
| Payloads, if you touched access code | `python3 tools/build.py payloads` |
| App catalog, if you touched `launcher/assets/apps.json` or navigation | `dotnet run --project tests/CatalogTests.csproj -- launcher/assets/apps.json` |
| One topic per PR | A new profile does not ride inside a launcher feature. |
| Tested on | Say which model and firmware you exercised, and which phases (inventory / root / cleanup / launcher / reboot / standby). |
| Stray files | Nothing from `.local/`, no IP addresses, no original snapshots. |

## Hard rules

Never do these in a PR:

- **No weakening `keep_active`** to make a group match. Open an issue with evidence instead.
- **No broad `coba.*` glob.** `com.samsung.tv.coba.adagent` is evidence; the rest of `coba` is the stock home shell.
- **No prebuilt Samsung assemblies, TPKs or live registry snapshots** in the tree.
- **No flashing, bootloader, `/etc/passwd` or SDB-key changes** in a recipe.
- **No LAN scan** and no default that applies another model's profile.
- **No always-on root daemon** and no claim that runtime masks survive reboot.
- **No secrets** in commits: no IP addresses, serials, account emails, Wi-Fi names or `.local/` logs.
