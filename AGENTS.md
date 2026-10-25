# Instructions for an agent working in this repository

## Start with the owner's device and goals

Read README.md and docs/01-inventory.md through docs/04-launcher.md, plus
docs/09-recovery.md. UnTizen is generalized across several exact
model/firmware pairs, but it is still a case study with measured limits:
`profiles/` holds per-device facts and `data/cleanup-groups.json` holds the
shared bloat catalog. Do not turn either into an indiscriminate Samsung-wide
debloat list.

Work only on the TV the owner identifies. Use its explicit IP address; do not
scan the whole network or reuse another person's saved device identity.
Discover the installed app IDs and schemas on that TV. Read firmware from
About This TV; the helper's `--firmware` value is an operator declaration,
not a value it has independently read. SDB's reported model is checked and
selects the profile; `--model` is only for a regional variant of a panel that
already has one, and `--profile` only for an explicit file the operator chose.

If no profile matches, stop and write one from a read-only inventory. Never
run another model's data against this TV, and never fake the firmware argument
to make a match succeed.

Use the owner's current authorization and feature preferences. Ask only for
missing decisions or observations that matter. Do not invent extra approval
steps for reversible work already requested. Default preservation: HDMI,
display, audio, networking, Bluetooth, package/application management,
accessibility and the owner's streaming apps. Voice, SmartThings, health,
gaming-hub helpers and TV Plus are optional features, not automatically malware.

## Work in phases

1. Inventory first; record model, firmware, runtime, schemas, installed apps,
   source IDs, root capabilities and current Home/startup selectors.
2. Resolve the profile (`tools/tv.py profiles` lists what this checkout
   covers). If the device is new, add `profiles/<model>-<firmware>.json` and
   only select cleanup groups whose IDs you actually observed there.
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
  of these TVs was performed. See docs/08-privacy.md.
- Launcher artwork must be path-only SVG: the NUI renderer has no text support,
  so a `<text>` tile renders blank on the TV.

## Local data and publication

Use `.local/` for device-specific plans, raw command output, screenshots,
snapshots, builds and extracted framework assemblies. Use the ignored
`launcher/assets/app-icons/` and `apps.local.json` for downloaded publisher art
and customized catalogs; the shipped catalog is `launcher/assets/apps.json`.
These paths are not for public commits.

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
