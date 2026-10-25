# Diagnose slow menus and streaming apps

The most useful changes were reducing unnecessary background app/service
work and providing small native controls for common actions. This project
does not claim a universal speedup percentage.

## Separate the symptoms

| Symptom | What to inspect |
|---|---|
| Home/sidebar is slow but HDMI works | Launcher/process startup, preload requests, cached native assemblies |
| Common settings are slow | Use quick settings; keep native advanced screens for uncommon controls |
| Both remote and DualSense lag only in Netflix | App/rendering/memory pressure, then input delivery; Bluetooth alone is not an adequate explanation |
| Video buffers but navigation is responsive | Network and streaming diagnostics |
| App images appear late on every visit | Recreated image views, discarded textures, oversized or remote artwork |

Use the same app screen and a similar workload for comparisons. Let the owner
navigate naturally; stop automated button injection while asking about lag.
A successful launch request or a changed process ID is not proof the intended
screen is visible.

## Netflix: what was observed

The owner reported input lag from both the Samsung remote and DualSense.
During diagnosis, background streaming/store/settings processes were closed
and Netflix was relaunched. A full boot later showed Samsung TV Plus starting
with a `backgroundAtStartup` request from `org.tizen.litewebappservice`;
Prime Video and YouTube also reappeared. Both app-preload preferences had
returned to true.

The later mitigation disabled the `HEPsqFNie0.tvplusstandalone` registry row,
created the verified `slive-provider-daemon` stop marker, stopped that service,
reset live/cached preload preferences and closed unused apps. This preserved
Netflix's account and app data. The TV Plus change was checked live, but
**had not yet been checked across another full reboot**.

Sanitized memory snapshots, reported by `/proc/meminfo`:

| Observation | MemAvailable (KiB) | CmaFree (KiB) |
|---|---:|---:|
| Before the first round of background-app closure | 509,032 | 56,048 |
| After a later reboot with background preloads | 537,492 | 544 |
| After the later background-app cleanup | 922,172 | 184,072 |
| Later stable observation | 921,344 | 184,868 |

The later cleanup left roughly **900 MiB available**. These are snapshots
under different uptime/workload conditions, not a controlled benchmark.
CMA is a shared contiguous-memory pool used by graphics/media components,
not a direct measurement of dedicated GPU VRAM.

**The owner had not confirmed that Netflix's perceived input lag was fixed.**
The memory result and visible process changes are evidence for reduced
background pressure, not proof of a completed latency repair.

## Reproduce a useful diagnosis

1. Record what is slow: opening, D-pad response, playback or all of them.
2. Check actual foreground app/processes, `MemAvailable`, swap, CMA and CPU
   use over a short interval. Preserve a sanitized before/after record.
3. Close specific unused applications gracefully by their verified IDs.
   `app_launcher -u 5001 -r APP_ID` can return 1 when the app is already absent;
   handle that state explicitly.
4. Reopen the intended app, verify its screen, stop synthetic input and get
   the owner's observation.
5. Test full boot separately: preload behavior can return.

On the case-study TV, four CPU cores already ran up to 1.35 GHz with the
performance governor; no foreground CPU quota explaining the lag was found.
High load average included driver threads in uninterruptible sleep, so it was
not proof of high CPU utilization. Thermal-zone data was unavailable.
Root agents and screenshots can themselves affect measurements.

The compositor's `enlightenment_info -fps` command hung during investigation.
It is not included in automated recipes. A brief input observation with no
events also does not prove a controller is working correctly.

Do not clear account data, force-stop core display services or kill all
processes as a shortcut. Samsung describes memory-related glitches and cold
booting in [its support guide](https://www.samsung.com/us/support/troubleshoot/TSG10002361/);
Netflix also documents [device restart troubleshooting](https://help.netflix.com/en/node/100242).
Use those ordinary troubleshooting steps when appropriate before escalating
to unsupported registry changes.
