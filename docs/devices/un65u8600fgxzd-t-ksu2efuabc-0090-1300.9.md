# UN65U8600FGXZD / T-KSU2EFUABC-0090-1300.9

Brazilian UN65U8600F (65", 2025), Tizen 9.0. Kernel `Linux 5.4.261 armv7l`
and runtime `Microsoft.NETCore.App 6.0.9` — identical to the tested
UN75U8000FFXZA. Doctor reports the archive-route capability family
(`cap_setgid,cap_sys_admin=ei` on dotnet, `cap_setgid,cap_setuid=eip` on
sdbd-tarlauncher). Temporary root verified (UID/EUID 0) during inventory;
passwd and SDB key hashes unchanged afterwards.

This note is **not** an end-to-end profile: cleanup, the launcher and full
restarts were exercised, standby/wake was not tested separately, and one
boot limitation below is unresolved. Do not apply another model's profile
to this pair.

## Container

- `com.samsung.tv.bixby-promotion` is **not present** on this model. The
  only writable app directory observed under `/opt/usr/apps` is
  `com.samsung.tv.quicklaunch`, which hosts Quiet Home here (entry
  assembly renamed to `QuickLaunch.dll`); it is also the settings
  container. The stock QuickLaunch payload is Samsung's quick panel
  (quick settings, channel list, source list) — replacing the container
  replaces that panel. Stock key routing confirms this: `XF86More`
  launches `package:com.samsung.tv.quicklaunch`, while `XF86SysMenu`
  launches `package:org.tizen.menu`. The system IME keyboards used by
  Settings text fields (Wi-Fi password, manual DNS) are a separate
  component and keep working.
- Registry `/opt/dbspace/.pkgmgr_parser.db`, table `package_app_info`,
  schema as on the tested panel. Stock Home `com.samsung.tv.csfs`,
  stock startup `org.tizen.tv-viewer`.

## Cleanup (exercised)

493 app IDs observed. Seven groups matched without hitting `keep_active`
and were applied one at a time against fresh snapshots: advertising (13),
tv-plus (2), voice (18), context (13), smart-extras (15), hotel-b2b (16)
and gaming-hub (4 of 5 — the owner kept the Xbox cloud app via
`cleanup.remove = {"gaming-hub": ["*.XboxGamePass"]}`). 81 IDs verified
disabled against a fresh registry pull, no collateral; the kept app's
row was byte-identical. `light-shell` was not exercised (owner declined;
the stock sidebar/browser remain).

Preferences were applied and read back: `db/was/preload_by_country`
false (vconf and the WAS cache `RESERVED_18` JSON), voice activation /
recognition and multi-assistant prelaunch off.

## Stop markers (inspected and exercised on this TV)

Each pair below was read from the unit's own
`ConditionPathExists=!/opt/usr/share/systemd/system/<marker>` line on
this TV before applying, and all were verified blocked after a full
restart (`ActiveState=inactive`, `ConditionResult=no`):

| Unit | Marker | Group |
|---|---|---|
| pisa-service.service | pisa-service | advertising |
| canalysis-service.service | canalysis-daemon | advertising |
| com.samsung.tv.bixby-prov.service | com.samsung.tv.bixby-prov | voice |
| com.samsung.tv.ondevice-voice.service | com.samsung.tv.ondevice-voice | voice |
| org.tizen.voice-app.service | org.tizen.voice-app | voice |
| org.tizen.voice-client.service | org.tizen.voice-client | voice |
| com.samsung.tv.context-aware-agent.service | com.samsung.tv.context-aware-agent | context |
| com.samsung.tv.context-aware-service.service | com.samsung.tv.context-aware-service | context |
| com.samsung.tv.AICompanionAgent.service | com.samsung.tv.AICompanionAgent | context |
| com.samsung.tv.ghdaemon.service | com.samsung.tv.ghdaemon | smart-extras |

Notes: `adagent-service.service` shares the `pisa-service` marker (same
condition line) and is blocked by the same file. Most of these units are
also path-activated; the path triggers fire and are blocked by the
condition. `slive-provider-daemon.service` has a marker
(`slive-provider-daemon`, group tv-plus) but was deliberately **left
active** — the household watches Samsung TV Plus.
`contents-recognition-service.service`, `org.tizen.tv.sp-kpi.service`
and `data-service.service` have no negated condition and were left
alone. `samsunghealth-service-tv.service` does not exist on this model.

## Launcher (exercised, one limitation)

Quiet Home runs hosted in quicklaunch: UI, remote navigation, app
launching, volume, the settings page and return from a streaming app
(Back and Home) all verified after Home assignment. The vendor preload
starts the package at boot, so the launcher is resident and the Home key
raises it instantly. Real app icons were pulled with `tv catalog`
(27 of 32).

**Known limitation — automatic startup does not persist on this
firmware.** All three selectors were set and read back (main-operation
home, `db/appfw/home_appid`, `db/appfw/startup_appid` =
`com.samsung.tv.quicklaunch`), but `db/appfw/startup_appid` is reverted
to `org.tizen.tv-viewer` during every boot, so the TV powers on to the
last source (TV Plus / last channel) instead of the launcher. The
revert happens in the boot path; the tv-viewer binary does not
reference the key, no systemd unit references it, and both Start Screen
options (Smart Hub Home, TV Plus autorun) were already off. Home
assignment itself persists. Not yet root-caused.

HDMI source integers were not mapped (only source 0, TV, was probed);
do not copy another panel's `sources.json`.
