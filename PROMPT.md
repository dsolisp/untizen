# The prompt

Paste this into Cursor, Claude Code, Codex or Gemini CLI on a computer that is
on the same Wi-Fi as the TV. This repository is for **Samsung Tizen** sets that
can use Developer Mode and SDB. It will not work on Android TV, Google TV, Fire
TV or LG webOS.

If you cloned this repo, say so: the assistant must reuse `tools/` and
`recipes/` instead of writing new ones. The only local files it may create are
under ignored `.local/` (plans, snapshots, session logs) and, if you ask for
custom artwork, `launcher/assets/apps.local.json`.

Before you start, on the TV: Settings → Support → About This TV. Write down the
exact **model** and **software version**. Then Settings → Network → your
connection, and write down the TV's IPv4 address. Keep the TV on.

---

I want to make my Samsung Tizen TV quieter: reversible cleanup of advertising
and optional smart extras, then a native launcher, on a TV I own. Work on the
real device, one phase at a time. Ask me before anything that depends on my
preferences. Do not invent extra approval steps for reversible work I already
asked for.

My TV
- Model (from About This TV, not a retailer name): <MODEL>
- Firmware / software version (from About This TV; never guessed): <FIRMWARE>
- TV IPv4 on this LAN: <TV_IP>
- This computer's SDB path, if I have one: <SDB or "not installed yet">

Connect
- Use that IPv4. Do not scan the LAN, do not guess the IP, do not reuse another
  person's saved device identity.
- List what this checkout covers first: `python3 tools/tv.py profiles`.
- If SDB is missing, tell me to install Tizen Studio and set `SDB` to the
  absolute path of `tizen-studio/tools/sdb`. This repo does not redistribute it.
- On the TV I will turn Developer Mode on (Smart Hub → Apps → App Settings,
  enter `12345`), set Host PC IP to this computer's LAN address, and restart.
  Tell me when the TV should show that prompt. Samsung's notes:
  https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/tv-device.html
- Then: `"$SDB" connect <TV_IP>:26101` and `"$SDB" devices`.
- Wrap the helper so every TV command declares host and firmware:

```sh
export SDB=/absolute/path/to/tizen-studio/tools/sdb
export TV_IP=<TV_IP>
export TV_FIRMWARE='<FIRMWARE>'
tv() { python3 tools/tv.py --host "$TV_IP" --firmware "$TV_FIRMWARE" "$@"; }
```

- `--firmware` is my declaration from the About screen. The helper does not
  read it from the set. It is required for `doctor`, `inventory`,
  `root-check`, `exec`, `pull` and `push`. `profiles`, `port-closed` and
  `drift` do not need it. `drift` also does not need `--host`.
- If your sandboxed shell cannot reach the TV while the same command works in
  an ordinary terminal, ask me to run `python3 tools/relay.py <TV_IP>` in an
  ordinary terminal and leave it running (`tools/relay.md`). Then use
  `--host 127.0.0.1 --callback-host <this-computer-LAN-IPv4>`. Do not scan,
  do not change Host PC IP, do not disable the sandbox yourself.
- `sdb shell` returning `closed` on retail firmware is expected. Do not replace
  `/etc/passwd` or Samsung's SDB key to "fix" it.

Identify, then stop if this checkout has no profile
- `python3 tools/build.py payloads` once, then `tv inventory`.
- `inventory` is read-only: SDB preflight plus a temporary root dump of kernel,
  runtime, app IDs and current Home. It writes a draft under
  `.local/inventory/` (`draft-profile.json`, `app-ids.txt`,
  `apps-overlay.json`, `sources.json`, `note.md`). It never writes `profiles/`.
- If a profile already matches, show me the draft and continue.
- If the model is unknown or the firmware does not match a profile: **stop**.
  Show me the draft, the concrete gap and the supported list. Do not write a
  profile unless I ask you to change this repo. A one-session note belongs
  under `docs/devices/`, not in `profiles/`. Never run another model's data.
  Never fake `--firmware` to make a match succeed.
- `doctor` remains a lighter preflight (no root) once a profile matches.

Checklist (ask once, before any mutation)
Keep HDMI, display, audio, networking, Bluetooth, package management,
accessibility and the streaming apps I name. Ask me, as a single checklist,
which optional features to keep:

- Voice (Bixby / Alexa / wake word)
- SmartThings and health extras
- Samsung TV Plus
- Gaming-hub / cloud-gaming helpers
- Hotel / B2B signage leftovers (usually unused on a home panel)

Those are optional features, not automatically malware. Disable only what I
do not tick. Streaming apps I use stay enabled.

Root check, still no mutation
- `tv root-check` — temporary UID/EUID 0, then staging cleaned. No config
  changes. If it fails, inspect; do not retry in a loop and do not overwrite
  the first session log.

Cleanup, one group at a time
- Use `tools/plan_cleanup.py` and `recipes/snapshot.sh`. Do not write a new
  disable tool. Do not uninstall packages, do not delete partitions, do not
  flash firmware.
- New snapshot name per phase so a later restore cannot erase an earlier
  wanted change. Keep the first backup; never overwrite it to make a retry
  succeed.
- Dry-run first (`plan_cleanup.py` without `--output` prints matches). `--profile`
  is required. Example:

```sh
tv exec --script recipes/snapshot.sh --arg advertising-01
tv pull /opt/usr/share/untizen-backups/advertising-01/.pkgmgr_parser.db \
        .local/advertising-01-registry.db
python3 tools/plan_cleanup.py \
  --profile profiles/<the-resolved-profile>.json \
  --snapshot .local/advertising-01-registry.db \
  --groups advertising
```

- Show me the matched IDs. After I agree, re-run with
  `--output .local/plans/advertising-01`, push `restore.sh` onto the TV, then
  apply. Only three registry fields change (`app_disable`, `app_onboot`,
  `app_autorestart`). Drift aborts the transaction. `recovery.json` is
  first-wins: a retry after a half-applied plan must not replace the original
  values. Later, `tv drift --snapshot <fresh.db> --plan .local/plans/advertising-01`
  compares a new snapshot to `before.json`. `--fix` prints how to re-apply;
  it does not rewrite recovery. If the profile's `stop_markers` is empty, do
  not invent unit/marker pairs from another TV.
- Never disable `org.tizen.menu` or the profile `container` (Quiet Home lives
  there). `data/cleanup-groups.json` `keep_active` is an error if a group hits
  it, not a warning — do not weaken it.
- Runtime `systemctl mask` does not survive restart. Do not add a watchdog.
- One SDB/root session at a time. Keep scripts under the 30-second command
  budget. Do not reboot or stand the TV down inside the root session; let
  cleanup checks finish first.

Launcher, after cleanup you and I are happy with
- Build locally. Pull the four Tizen reference assemblies from **this** TV
  into `.local/tv-framework`. Do not upload them. Follow `docs/04-launcher.md`.
- Install Quiet Home **without** changing the default Home. I will look at the
  TV: remote, HDMI, sound, settings. There is no reliable screenshot API on
  these sets — `recipes/status.sh` plus what I see is the proof. An injected
  guess is not proof.
- Only then assign Home/startup. Settings bridge and sidebar/browser
  (`light-shell`) come later, after Home works.
- Test a full restart and a standby/wake **separately**. Re-check Home
  selectors. A process disappearing once is not persistence.

Close the session
- Remind me to turn Developer Mode off when we are done. Then
  `tv port-closed` (no firmware needed) must report the SDB port closed.
  Stop `tools/relay.py` if we used it. Do not leave staging files in
  `/home/owner/share/tmp/sdk_tools/untizen` without saying so.
- Summarize what you changed, what you did not prove (see `docs/08-privacy.md`
  and `docs/07-performance.md`), and the exact restore commands.

Hard stops
- No profile match, or I refuse to declare firmware.
- `doctor` / `root-check` fails after one careful inspect.
- A plan would hit a `keep_active` pattern or the launcher container.
- I ask you to flash, replace the bootloader, or install a custom OS — refuse.
- Do not claim every privacy path is gone or that apps will feel faster.

---

Expect a short checklist (apps, voice, SmartThings, TV Plus). Everything you
disable has a generated inverse. If this TV is not in `python3 tools/tv.py
profiles`, we stop and talk; we do not improvise a Samsung-wide list.
