# Reversible cleanup

Prefer disabling specific components over deleting system packages. A package
can contain several app IDs; disabling an app record is not the same as
uninstalling its package. The tested workaround changes three registry fields:
`app_disable`, `app_onboot` and `app_autorestart`. Normal package activation
commands did not reliably report or retain the intended state on this build.

Do not remove display, HDMI, audio, network, Bluetooth, app-manager or
accessibility services. Keep `org.tizen.menu` available for advanced settings
and Bluetooth pairing. Also keep the container your
profile names in `container` (Bixby Promotion on both tested TVs) enabled once
it hosts Quiet Home.

## Select a group

The [profile](../profiles/un75u8000ffxza-1300.9.json) splits the observed targets:

| Group | Intended effect | Tradeoff |
|---|---|---|
| `advertising` | Disable identified ACR, viewing-analysis, promotion and advertising app records | Recommendations and advertising features change; not a complete network privacy guarantee |
| `voice` | Remove voice assistants, voice UI, wake-word engines and utterance suggestions | Voice control stops working |
| `context` | Disable AI/context suggestions and content-grab helpers | Related smart features stop working |
| `smart-extras` | Reduce SmartThings, health, gaming-hub and ambience helpers | Some integrations become unavailable |
| `light-shell` | Disable native sidebar and browser | Requires a working Quiet Home/settings bridge first |
| `art-store` | Disable the Art Store service, the ambient tile in the stock home, its setup wizards and its support app | Ambient Mode shows a plain black screen instead of art or photos |
| `tv-plus` | Disable Samsung TV Plus startup/app | TV Plus is unavailable until restored |

The first four groups total 51 app IDs from the original cleanup. The
sidebar/browser add two; the later TV Plus change adds one. This is not a
count of 54 independent trackers. Several are ordinary optional features.

`art-store` came from the QN85C's own snapshot. On that panel the artwork
service was the largest single boot cost, so the group is worth checking on any
TV that reports slow power-on. `light-shell` still needs the settings path
verified first. On the QN85C the QuickLaunch bridge was refused, because
`com.samsung.tv.quicklaunch` owns two `XF86More` rows on that firmware (one for
itself, one for `org.tizen.function-osd`), so the group was applied with the
vendor quick-settings panel and `org.tizen.menu` still in place: settings stay
reachable, only the sidebar and browser stop. Read the rows before assuming one
key means one row.

The original owner separately uninstalled ESPN, Sling, Fubo, AMC+, Instagram,
Phynd, Weekend Games, YouTube TV, Peacock and Angel Studios. Those were
personal app choices, not a universal blacklist. Inventory and ask which
subscriptions/apps another owner wants to retain.

## Snapshot, generate, inspect, apply

Start with one group. Use a **new snapshot name for each phase**, so later
restoration does not accidentally erase an earlier desired change.

```sh
tv exec --script recipes/snapshot.sh --arg advertising-01
tv pull /opt/usr/share/untizen-backups/advertising-01/.pkgmgr_parser.db .local/advertising-01-registry.db
python3 tools/plan_cleanup.py \
  --profile profiles/un75u8000ffxza-1300.9.json \
  --snapshot .local/advertising-01-registry.db \
  --groups advertising
```

`--profile` is required. Omit `--output` to print the matched IDs; review them
before writing SQL. Then re-run with `--output .local/plans/advertising-01`.

Inspect `apply.sql`, `restore.sql`, `before.json`, `recovery.json` and
`stop-markers.json`. The planner requires one matching row per selected app
and recognized boolean representations. It refuses missing/duplicate records
and generates guards against state drift. An update to another field/app is
preserved. A change to a selected field causes the plan to stop instead of
silently overwriting it.

`recovery.json` is first-wins: the first write keeps the original field
values. A later run of the same plan may only append app IDs the plan gained.
A sidecar copy is also written under `.local/recovery/`. Do not delete the
first record to make a retry succeed.

After a restart or an update, compare a fresh snapshot to the plan without
touching the TV:

```sh
tv drift --snapshot .local/advertising-01-after.db --plan .local/plans/advertising-01
```

`--fix` prints how to re-apply the original `apply.sh`. It does not rewrite
recovery. If the profile's `stop_markers` is an empty list, do not invent
unit/marker pairs from another model.

Save the generated restore script on the TV **before** applying:

```sh
tv push .local/plans/advertising-01/restore.sh advertising-01-restore.sh
tv exec --command 'cp /home/owner/share/tmp/sdk_tools/untizen/advertising-01-restore.sh /opt/usr/share/untizen-backups/advertising-01/restore-registry.sh'
tv exec --script .local/plans/advertising-01/apply.sh
```

This updates only the registry flags. It does not terminate existing
processes, set preferences or install service stop conditions.

## Uninstall an application package

Disabling an app record keeps the package on the store list and reuses its
storage. When an owner wants a package gone, `pkgcmd` can uninstall it. The
launcher offers no delete gesture for sideloaded or root-registered apps, so
[recipes/uninstall-app.sh](../recipes/uninstall-app.sh) is the recipe.

```sh
tv exec --script recipes/uninstall-app.sh --arg list
```

`list` prints the packages that are removable, not system and not preloaded,
plus `MONTADO` next to any package whose widget is currently loop-mounted. That
mount is the live app container, so the row is a hard protect: on this TV the
Smarters package hosts Marea TV's `res/wgt`, and deleting it would delete the
project. The guard reads `/sys/block/loop*/loop/backing_file` rather than the
`.tmg` name, because almost every store app ships a `res/*.tmg` too.

Then uninstall exactly one package, with a snapshot taken first:

```sh
tv exec --script recipes/snapshot.sh --arg uninstall-01
tv exec --script recipes/uninstall-app.sh --arg <package> --arg confirm
```

Owners do not think in ten-character ids, so the same recipe answers to the name:

```sh
tv exec --script recipes/uninstall-app.sh --arg find --arg ego
tv exec --script recipes/uninstall-app.sh --arg remove --arg ego
tv exec --script recipes/uninstall-app.sh --arg remove --arg ego --arg confirm
```

`find` lists every removable package whose id or app id contains the text.
`remove` without `confirm` prints the single match and changes nothing; with
`confirm` it uninstalls. A text that matches two packages is refused with both
candidates rather than guessing, and a package that is loop-mounted (the Smarters
container that carries Marea TV) is refused before even the preview.

The second argument must be the literal `confirm`; the package name is
whitelisted to `[A-Za-z0-9_.-]`; the container in the profile `container` and
`settings_container` keys is refused. The recipe calls `pkgcmd -u -n` and
re-queries `package_info` instead of deleting directories by hand, so a failed
uninstall reports the running processes rather than leaving a half-removed
registry row. Restart the TV and rebuild the launcher afterwards: a removed
package can still be referenced by the home catalog.

Uninstalling is not reversible by restoring a registry snapshot: the package
files are gone. Reinstall from the store, or with `pkgcmd -i` for a `.wgt` you
still hold. Start with the apps the owner named; do not bulk-remove from the
list.

Not every package can be removed this way. A widget registered outside the store
answers `pkgcmd -u` with `General error [-1]` at 20 percent and keeps its row: on
2026-11-13 three store apps left cleanly (Ego IPTV, Infinite IPTV Player, Net
ipTV) while `MareaTv001`, the 2026-11-04 sideload that we later abandoned for the
Smarters container, refused from root and refused the same way through `sdb
uninstall`, which calls the same pkgmgr. The files are complete, nothing runs, no
loop holds it. `remove` reports that outcome instead of pretending success. What
is left is either hiding the tile from the launcher list, or deleting
`/opt/usr/apps/<package>` plus its registry rows by hand, which is surgery on the
package manager's database and only worth it for a package the owner insists on.

## Prevent selected services from starting

The vendor units on this build have stop-file conditions. Use the profile's
exact unit/marker pair and inspect it first. For example:

```sh
tv exec --script recipes/stop-marker.sh \
  --arg apply --arg pisa-service.service --arg pisa-service --arg advertising-01
tv exec --script recipes/stop-marker.sh \
  --arg apply --arg canalysis-service.service --arg canalysis-daemon --arg advertising-01
tv exec --command 'systemctl stop adagent-service.service'
```

The script verifies the exact negated `ConditionPathExists`, saves whether
the marker already existed and whether the unit was active, then stops it.
It refuses to overwrite that record. Do the same only for selected voice,
context or smart-extra units listed in the profile.

Four other services were masked **only for the running boot**:

```sh
tv exec --command 'systemctl mask --runtime --now ipa.service contents-recognition-service.service org.tizen.tv.sp-kpi.service data-service.service'
```

These concern predictive app preload, recognition, performance reporting and
logging. Inspect their units and decide if they belong in the owner's setup.
Record existing mask/enabled/active states before using the command. Their
firmware-backed definitions were not writable, so no persistent masking was
attempted. A later restart can bring them back.

## Preferences and the web-app preload cache

The profile records the six preferences changed in the case study. Save
the actual old values from `preferences-before.txt` and prepare the inverse
`vconftool set -f -t TYPE KEY OLD_VALUE` commands first.

For the selected features, apply the corresponding entries, for example:

```sh
tv exec --command 'vconftool set -f -t string db/was/preload_by_country false'
tv exec --command 'vconftool set -f -t bool db/menu/autorun_tv_plus 0'
```

Voice preferences are `db/menu/voice/voice_activated` (bool),
`db/menu/voice/wakeupless_status` (int),
`db/si_service/voice_recog_enable` (bool), and
`db/multi-assistant/prelaunch_mode` (bool), all set to `0` in the voice-free
setup. Do not change them if voice features are retained.

For the cached preload preference, inspect the schema and **only** the relevant
JSON field; the larger record may contain device details:

```sql
SELECT name,json_type(value,'$.rsp.preloadByCountry'),
       json_extract(value,'$.rsp.preloadByCountry')
FROM WASConfigTable
WHERE name='RESERVED_18' AND json_valid(value);
```

On this firmware it was a JSON string `"true"`, not a JSON boolean. After
backing up `.webappservice.db`, a reviewed transaction can use:

```sql
BEGIN IMMEDIATE;
CREATE TEMP TABLE guard(ok INTEGER CHECK(ok=1));
INSERT INTO guard SELECT count(*)=1 FROM WASConfigTable
WHERE name='RESERVED_18' AND json_valid(value)
AND json_type(value,'$.rsp.preloadByCountry')='text'
AND json_extract(value,'$.rsp.preloadByCountry')='true';
UPDATE WASConfigTable
SET value=json_set(value,'$.rsp.preloadByCountry','false')
WHERE name='RESERVED_18';
COMMIT;
```

Run SQL with `sqlite3 -bail`, in a short reviewed script. If the value is
already false, no change is needed. Rollback should restore only this JSON
field, preserving the rest of the record. Do not copy the old WAS database
over the live one.

**Samsung catalog refreshes restored both cached and live preload flags in
later testing.** Recheck them after restart/update. Do not describe this as
a permanent fix or silently add a background enforcement loop.

## Verify the result

Read the affected registry rows, unit `ActiveState`/`ConditionResult`,
preference values and actual processes. Test HDMI, volume, mute, remote,
controller, network and chosen streaming apps. Then perform a full restart
after the root session has ended and check again.

The user confirmed picture, Home and remote operation after an early restart.
No controlled native-settings latency benchmark was obtained. Lightweight
quick settings bypass frequent trips through Samsung's larger settings UI;
they do not make every advanced settings screen instantaneous.
