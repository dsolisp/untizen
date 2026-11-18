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

## Quiet Home power-on on the QN85C: what the numbers said

The owner reported the new home screen felt slow right after power-on. The
launcher was not the cost: `/tmp/untizen-state.txt` measured `build_ms=24` with
all 43 artwork images ready, 39 catalogue entries and no load error, on a
process that lived from the first seconds of boot at 0.6% CPU and 36 MB.

Everything around it was the cost, read at ~19 minutes of uptime:

| Measurement | Value |
|---|---|
| Load average on 4 cores | 7.9 / 8.1 / 6.4, still climbing at 240 s and never settling |
| MemAvailable | 410-460 MB of 1,817 MB |
| Swap | 1,020 MB of 1,181 MB used, only ~160 MB free |
| Paging | `pswpin` rising ~20,000 pages per minute, 235,764 major faults, `kswapd0` resident |
| Resident .NET app processes | 11, 362 MB RSS combined |
| `org.tizen.art-app` (Art Store) | 28-32% CPU sustained, 46 threads, 43 MB RSS plus 70 MB swapped, live sockets to three external hosts |
| `ffv-service` (far-field voice) | 16-17% CPU sustained; owner keeps voice, so it stayed |

That is a memory-bound boot paging on eMMC, not a slow scene build. Both web-app
preload preferences were back on after the previous cleanup, exactly as
[the preference note](03-cleanup.md#preferences-and-the-web-app-preload-cache)
warns, and 347 registry records still carry `app_preload=true`.

Applied from a fresh `boot-slow-01` snapshot: the `art-store` and `light-shell`
groups (8 IDs), the graceful close of the four still-running processes, and
both web-app preload preferences set to `false`. Within a minute, MemAvailable
went 456 to 529 MB and SwapFree 137 to 294 MB. **No cold-boot comparison has
been taken yet**, so the power-on claim stays unproven until the TV is powered
off with the remote and measured from uptime zero.

Ceiling: the Samsung catalog refresh restores both preload preferences, and
`app_preload=true` still sits on 347 registry records here. Turning that count
down would need a planner field the tool does not touch yet, not another
hand-written UPDATE.

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
