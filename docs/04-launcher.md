# Build and install Quiet Home

Quiet Home is a native NUI/.NET application, with Home/startup and remote-key
routing adjusted to make it act as the launcher. It does not replace the
kernel or the whole Tizen shell. Samsung's settings, app framework and media
stack remain available underneath.

The design follows Free My TV: light background, wide feature card, two
portrait cards, colorful tiles, rounded controls and a translucent dock.
All UI text here is English. See [attribution](../NOTICE.md).

## Obtain matching private framework references

Build against the TV's own compatible `Tizen.NUI.dll`,
`Tizen.Applications.Common.dll`, `Tizen.System.dll` and `Tizen.dll`.
The shipped project files use `Private=false`, so those references are not
copied into the app package.

Find the paths on the target:

```sh
tv exec --command 'find /usr/share/dotnet.tizen -name Tizen.NUI.dll -o -name Tizen.Applications.Common.dll -o -name Tizen.System.dll -o -name Tizen.dll'
```

Inspect the results and pull the four matching runtime assemblies individually
with `tv pull REMOTE_PATH .local/tv-framework/NAME.dll`. Do not use a random
desktop/mobile SDK version just because it has a file with the same name.
Do not commit the resulting assemblies.

```sh
python3 tools/build.py launcher --framework .local/tv-framework
```

This builds `BixbyPromotion.dll`, `QuickLaunch.dll` and `Probe.dll`, then
assembles `.local/package/`. The shipped library cards are path-only SVG brand
marks, which the NUI renderer can draw without font support; [optional publisher
artwork](06-artwork.md) can be fetched and selected before rebuilding.

## Adapt inputs and apps

The original UI uses HDMI 2 as the wide PlayStation 5 card, HDMI 3 as the
Switch card, and HDMI 1 as the third card. Source IDs 14, 15 and 13 were observed
on the tested TV. They are example wiring, not auto-discovery.

Upload and run Probe to inspect sources and the current main-operation handler:

```sh
tv push .local/build/Probe/Probe.dll Probe.dll
tv exec --command '/usr/bin/dotnet /home/owner/share/tmp/sdk_tools/untizen/Probe.dll'
```

Copy the integers Probe printed into `launcher/assets/sources.json` (or an
ignored overlay next to it). Quiet Home loads that file from the same resource
root as `apps.json`; `DiscoverRoot` prefers the installed package resource
directory and falls back to the container's `quiet-home/` path. Do not reuse
another panel's HDMI mapping. The library is read from `apps.json`; verify
all app IDs against the TV. See [app configuration](06-artwork.md). Rebuild
after source changes.

## Two app lists: your apps and all apps

The Apps page keeps two lists. **Your Apps** is the menu you curate; **All
Apps** is everything the TV reports as installed. The launcher merges them at
startup from two optional files next to `apps.json`:

- `apps-installed.json` — the installed catalog, generated from the TV (below).
  When it is absent the menu behaves exactly like the curated `apps.json`.
- `/var/tmp/untizen-menu.json` — the hidden list (app IDs you removed from Your
  Apps). It lives outside the package so toggling never rewrites resources.

`MenuCatalog.Visible` puts curated entries first (skipping hidden ones and,
when a catalog exists, curated apps that are not installed), then appends the
remaining installed apps alphabetically. The Store/Utility tile always stays.
An **All apps** tile at the end of Your Apps opens the full list; there, Select
toggles an app's membership and a small accent dot marks apps already in Your
Apps. Back returns to Your Apps.

## The doors that close Your Apps

The last tiles of Your Apps are not apps. **All apps** reaches the installed
catalog, and **Samsung home** launches `com.samsung.tv.csfs`, the shell Samsung
ships. That second door is not decoration: once `home_appid` and `startup_appid`
point at this launcher, nothing else brings the stock shell up, and some
surfaces exist only inside it.

The QN85C (QN55QN85CAPXPA, 2220.4) showed why. Its registry has no Developer
Mode package at all, so the developer-mode panel is reachable only by focusing
**App Settings** in the shell's Apps strip and typing `12345`. With Home owned by
the launcher and no tile for the shell, the panel was unreachable by any route:
the store (`org.volt.apps`, package `com.samsung.tv.store`) has no App Settings
entry, and the launcher's own gear is Quick Settings, not Samsung's.
`AppLibrary.TileCount`, `IsAllAppsTile` and `IsStockHomeTile` hold that index
math, checked offline by `tests/CatalogTests.cs`; the stock-home tile stays
present even when no installed catalog has been generated.

Generate the installed catalog from the TV's package registry (read-only):

```sh
tv catalog                      # writes launcher/assets/apps-installed.json
tv catalog --no-icons           # skip pulling per-app icons
```

The command opens one read-only root session, dumps the registry schema and
app IDs, pulls a bounded set of icons into
`launcher/assets/app-icons/installed/`, and writes the catalog. Review the
printed names before rebuilding; `humanize` only guesses a display name when
the registry has no label column. Apps installed after the last `tv catalog`
run stay invisible until you regenerate — that is the deliberate ceiling, and
the upgrade path is a runtime registry read once permissions are confirmed.
Rebuild and redeploy after regenerating.

An icon already in `app-icons/installed/` is reused by every later run, even
`--no-icons` or a machine without Pillow: reuse costs nothing, and an entry
written without `Asset` makes the launcher fall back to its placeholder tile.
`--icon-limit` caps the pulls, never the reuse, and Pillow only decides whether
new icons can be fetched. The generated catalog is gitignored, so CI cannot see
it; `build.py launcher` checks it instead and refuses a tree where a referenced
PNG is missing or no installed app has artwork at all.

## Install without changing Home yet

The tested native-app container is **`com.samsung.tv.bixby-promotion`**.
Its `BixbyPromotion.dll` is replaced with our assembly, while the package's
existing identity, metadata and framework integration are retained. This
replaces Bixby Promotion's function. It is not a store-signed standalone TPK.

Inspect the installed package, its owner/labels, original entry assembly and
current registry flags first. This release's recipe requires the observed
owner `201:0`. If the layout differs, stop and adapt the profile.

```sh
tv exec --script recipes/snapshot.sh --arg home-01
python3 tools/build.py package   # deterministic archive, files at its root
tv push .local/package.tar.gz package.tar.gz
tv exec --script recipes/install-launcher.sh --arg home-01
```

The recipe backs up the original package before replacing the assembly,
moves the cached native image out of the execution path, installs resources,
applies the package's observed SMACK label and requests a manual launch.
It does not change Home/startup.

`install-launcher.sh` refuses to run when `res/quiet-home` already exists. Every
later change goes through the update path, which first copies the running
assembly and resources to `update-previous/` inside the snapshot folder:

```sh
tv catalog                      # regenerate the installed list when apps changed
python3 tools/build.py all
tv push .local/package.tar.gz package.tar.gz
tv exec --script recipes/update-launcher.sh --arg home-02
tv exec --script recipes/status.sh   # the kill can drop the channel; confirm here
```

Stage with `tv push`, not with a raw relative `sdb push`. `tv push` resolves the
SDK staging folder the recipe reads; `sdb push .local/package.tar.gz package.tar.gz`
writes into sdb's own working directory and leaves the previous tarball in place, so
the recipe unpacks an old build, reports `Updated`, relaunches, and nothing changed
except the timestamp. Found the hard way on 2026-11-13: after three apps were
uninstalled, `tv catalog` plus `build.py all` produced a clean catalog, the update
ran twice, and the TV still listed the removed apps because the stage still held the
tarball from earlier that day. Both recipes now print the digest and mtime of the
stage they are about to apply, plus the digest of the catalog they installed; compare
those with `md5 -q .local/package.tar.gz` and `md5 -q launcher/assets/apps-installed.json`
before believing the update.

The new release recipes are a generalized form of the operations used on the
original TV. Filesystem steps are not a single atomic transaction. If a step
fails, inspect the saved state and use recovery; do not rerun by deleting
the original backup. The snapshot and backup folder is
`/opt/usr/share/untizen-backups/home-01`.

Verify visibly:

- All pages render; the D-pad, Select and Back behave correctly.
- HDMI cards switch the intended input, with picture and audio.
- Volume/mute and applicable quick settings work.
- Native Advanced and Network settings still open.
- Chosen app shortcuts launch the correct installed apps.
- The Controllers shortcut reaches the Bluetooth device list.

The `build_ms` value in `/tmp/untizen-state.txt` (or a leftover
`/tmp/quiet-home-state.txt`) measures scene construction, not
input-to-photon latency or complete rendering time. Recents and theme files
are written to `/var/tmp/untizen-recents.json` and
`/var/tmp/untizen-theme.conf`; the previous `quiet-home-*` paths are still
read if the new files are absent.

## Make it open on Home and startup

Save the **three original values** privately first: the main-operation Home
handler printed by Probe, `db/appfw/home_appid`, and
`db/appfw/startup_appid`. They all happened to be `com.samsung.tv.csfs` on the
case-study device; restoration must use the actual saved values.

Only after the visible verification above:

Both commands below use the profile's `container` value,
`com.samsung.tv.bixby-promotion` on the tested TVs. Substitute your own.

```sh
tv exec --command '/usr/bin/dotnet /opt/usr/share/untizen-backups/home-01/Probe.dll set-home com.samsung.tv.bixby-promotion'
tv exec --command 'vconftool set -f -t string db/appfw/home_appid com.samsung.tv.bixby-promotion; vconftool set -f -t string db/appfw/startup_appid com.samsung.tv.bixby-promotion'
```

Read all three selectors back. Let temporary root cleanup finish, then
restart with the remote. Check full boot, the Home button, standby/wake
and return from a streaming app separately. Automatic startup was verified
on the original TV; an OS update can change routing.

## When a cold boot leaves a black screen

Home and startup both point at the launcher, so the firmware is expected to put
Quiet Home on screen by itself. When it starts the process and never maps the
window, the panel stays black until the remote's Home key sends the launch
request that raises the running instance.

`/var/tmp/untizen-boot.log` is the record of that: `/tmp` is wiped by a power
cut, `/var/tmp` is not. One line per lifecycle event, newest first, capped at
200 lines, timestamps in UTC. A healthy start reads

```text
2026-11-18T05:31:17+00:00 up=2537s pid=8525 home created foreground-launch visible=True library=28+29
2026-11-18T05:31:17+00:00 up=2538s pid=8525 home resumed visible=True
```

`created` with neither `resumed` nor `paused` after it means the app manager
told the launcher nothing about its own state, and that is what a cold boot does
here. Measured on the QN85C on 2026-11-17, after a standby/wake:

```text
up=20s pid=435 home created bg-launch+standalone visible=True library=28+29
up=23s pid=435 home paint-nudge 1 visible=True->True
up=26s pid=435 home paint-nudge 2 visible=True->True
up=29s pid=435 home paint-nudge 3 visible=True->True raise=0
up=29s pid=435 home resumed visible=True
```

Two facts in that trace. The boot unit starts the startup app as a **background
preload** (`bg-launch`), so nothing ever asks Quiet Home to paint, and
`Window.IsVisible()` stays `True` the whole time: it reports the app's own
window, not what the compositor is showing. And `Show`/`Raise`/`Activate`
bought nothing, while the default launch request for our own app id, the same
request the Home key sends, was answered with a `resumed` in the same second.

So the first-paint nudge sends that request, once 1.2 seconds after the scene
exists and again every 1.2 seconds while the app manager still has said nothing,
for at most twelve tries and only while the system has been up less than 60
seconds. Any `resumed` or `paused` disarms it for good, so an app the firmware
legitimately put in front keeps the foreground. The floor is not the launcher's:
the boot unit does not start the process until roughly 20 seconds after
power-on. A `bg-launch` flag is normal here, not a routing failure.

Read this file after a standby/wake before changing anything else.

## Replace the slow settings/sidebar path

The quick settings page handles volume, mute, brightness, Game Mode and
sleep timer with native APIs. Availability is checked for the current input.
Advanced settings, network setup and Bluetooth pairing still use Samsung's
native menu on demand.

The small QuickLaunch bridge exits on vendor `launch_type=preload` requests.
For interactive requests it opens Quiet Home's settings page and exits.
It does not keep a second heavy settings process running.

After quick settings work, take a new snapshot and install the bridge:

```sh
tv exec --script recipes/snapshot.sh --arg shell-01
tv exec --script recipes/install-settings-bridge.sh --arg shell-01
```

This replaces `/opt/usr/apps/com.samsung.tv.quicklaunch/bin/QuickLaunch.dll`
and updates two `key_filter` rules:

| Rule owner / key | New destination |
|---|---|
| `com.samsung.tv.quicklaunch` / `XF86More` | Quiet Home, `quiet_page:settings` |
| `org.tizen.menu` / `XF86SysMenu` | Quiet Home, `quiet_page:settings` |

The recipe selects semantic keys and checks the saved values. It does not
copy another TV's row numbers. It notifies
`memory/appfw/app_context_db_change` after the transaction.

The recipe refuses a panel where one app ID owns more than one row for the same
key, and it is right to. On the QN85C `XF86More` has three rows:
`com.samsung.tv.quicklaunch` to itself, `com.samsung.tv.quicklaunch` to
`org.tizen.function-osd`, and `org.tizen.remote-management` to itself. Narrowing
the `UPDATE` by `target_selector` would let the bridge install there, but it has
to keep the vendor OSD row alive, so that change needs a real panel test before
anyone ships it. Until then the QN85C keeps Samsung's own QuickLaunch assembly
(~60 MB resident from boot) and Quiet Home's quick settings only inside the
launcher.

Test both settings buttons, then generate/apply the **`light-shell`** cleanup
group from the `shell-01` registry snapshot. That disables the native sidebar
and browser. Keep the QuickLaunch bridge and `org.tizen.menu` enabled.

Retain rollback files and remove only the known staged files after verification:

```sh
tv exec --command 'rm -f /home/owner/share/tmp/sdk_tools/untizen/package.tar.gz /home/owner/share/tmp/sdk_tools/untizen/Probe.dll; rm -rf /home/owner/share/tmp/sdk_tools/untizen/unpacked'
```

## Performance choices in the launcher

App art is local. Real `ImageView` objects are created ahead of use and moved
between the hidden cache parent and visible cards. `ReleasePolicy=Destroyed`
keeps decoded textures alive while those views live. The cache is bounded
by catalog size and the grid/dock variants, not an ever-growing screenshot
cache. Image loading is asynchronous, so a first launch still needs loading
time; subsequent page visits avoid recreating image views.

The settings bridge exits when nothing asks it anything: the vendor boot unit
can start the assembly without ever sending an app-control request, and an idle
timer (3 s) closes it instead of leaving a hidden window resident. This build is
in `.local/package/` but is not installed on the QN85C, which still runs the
vendor assembly.

The clock updates every 30 seconds and stops while the launcher is paused.
There is no always-running controller-poll loop. The 180 ms repeat filter
applies inside Quiet Home only; changing it cannot fix input lag inside Netflix.
Local diagnostic files retain only current launcher state and are overwritten;
the launcher has no telemetry/network client.
