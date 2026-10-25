# Provenance and verification scope

## Original device work

The findings were compiled from local inspection, build/deployment records,
registry snapshots, post-restart checks and owner feedback collected
2026-10-19 through 2026-10-20. Private originals remain outside this repository.
No serial, network address, account identity, original application binary,
raw TV log or screen photo is needed to reproduce the findings.

The upstream repository keeps a deliberately small sanitized record at
[`evidence/observations.json`](https://github.com/jss8649/quiet-tizen/blob/cf518d7a9278dca7990e27756218258e44044a29/evidence/observations.json).
It is an observation summary, not an independently reproducible benchmark
dataset. This fork does not re-ship that directory: the device facts it records
live in `profiles/` and in the guides.

## Access tooling

Source: [chris-ritsen/samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root/tree/4ad2c4d3b0d0e0da4b5b7ebe4a787e94596f416b),
commit `4ad2c4d3b0d0e0da4b5b7ebe4a787e94596f416b`, Unlicense.

Only the archive-route support modules and two .NET payload projects are
vendored. The QN90B/QN90F kernel exploits, continuous host controller,
firmware-key tooling and unrelated payloads are not bundled.
`resources.py` retains upstream profile names, but this toolkit explicitly
builds and selects only the two common .NET 6 payloads.

The one local change to the copied access code is in `archive_root.py`:
if Samsung's host returns the exact `Unknown option --list-runtimes` error,
resolve `/usr/share/dotnet.tizen/netcoreapp`, require `libcoreclr.so` and
`System.Private.CoreLib.dll`, then derive the runtime version from that path.
Other preflight errors still fail. This fallback was used on the actual TV.

The new `tools/tv.py` wrapper adds explicit model/declared-firmware gating,
private local storage, bounded checksum-verified file transfer and reviewed
single-command execution. Those generalized conveniences were locally
tested; they are not a claim of end-to-end testing on additional hardware.

## Launcher and design

The C# launcher, app catalog, native settings bridge and Probe were developed
for the tested Tizen device. The public source retains the tested native
architecture, with a streaming-app dock shortcut and redistributable
placeholders in the public catalog.

Visual reference: [simbasjungles/free-my-tv](https://github.com/simbasjungles/free-my-tv/tree/73409804e5085e720dccea9ab95078a515cae098),
commit `73409804e5085e720dccea9ab95078a515cae098`, MIT. The port adapts layout,
palette, font treatment and focus/dock proportions. It does not run Android
code on Tizen. Inter and Material Symbols licenses are included separately.

Publisher logos remain optional local downloads. High resolution was preferred
over invented vectors for artwork such as the translucent Xbox mark. The
download manifest is an attribution/source record, not a license grant.

## What local validation establishes

- Native launcher, bridge, Probe and root payload source compile with the
  matching locally held references/SDK.
- Synthetic registry tests verify targeted apply/restore behavior, preservation
  of unrelated fields and refusal of missing, duplicate or changed target rows.
- Catalog tests exercise navigation across page boundaries and malformed input.
- Shell recipes receive syntax checks; selected SQL blocks are tested against
  synthetic tables.
- Public files receive a review for accidental private/binary artifacts.

These checks do not substitute for visual/controller verification, firmware
compatibility testing or measurement of real input latency on each target.

## UnTizen derivation and the second device

UnTizen starts from quiet-tizen commit
`cf518d7a9278dca7990e27756218258e44044a29` and generalizes it rather than
adding features: profile resolution by model in `tools/tv.py` (with a `profiles`
subcommand and no silent fallback), the shared glob catalog and `keep_active`
invariants in `data/cleanup-groups.json`, recipes parameterized by the resolved
profile instead of one TV's paths, and deterministic packaging in
`tools/build.py package`. Launcher artwork was rebuilt as path-only SVG brand
marks because the NUI renderer has no text support.

A second device was exercised on 2026-10-25: **QN55QN85CAPXPA**, firmware
`T-PTMCUABC-0090-2220.4`, Linux 5.4.77 armv7l, .NET runtime 6.0.9, registry
build `e2371440`. Its 555 app records were inventoried read-only; 60 packages
were disabled in six staged groups with a `.backup` snapshot and generated
restore scripts kept on the TV and under `.local/`; the owner power-cycled the
set and confirmed normal operation. The Quiet Home launcher was built against
that TV's own framework assemblies, installed into the Bixby Promotion
container and used as the daily home, verified after each deployment by process
state, the launcher's own diagnostic file and the rendered assets, with HDMI,
audio, Wi-Fi, Bluetooth, the streaming apps and the stock settings still
reachable. No serial, MAC address or IP address is recorded here.
