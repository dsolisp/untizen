# Identify the TV before changing it

Two devices are documented, one per profile:

| Model | Panel | Firmware | Profile |
|---|---|---|---|
| `UN75U8000FFXZA` | 2025 Crystal UHD 75" (U8000F) | `T-KSU2EFAKUC-0090-1300.9` | [profile](../profiles/un75u8000ffxza-1300.9.json) |
| `QN55QN85CAPXPA` | 2023 Neo QLED 4K 55" (QN85C) | `T-PTMCUABC-0090-2220.4` | [profile](../profiles/qn55qn85capxpa-2220.4.json) |

In both cases the model code came from the television's About screen, not a
retailer listing or an inferred marketing name. That is the authoritative
starting point for any other TV too.

Open Settings → Support → About This TV. Record model and software version
privately. Do not publish the serial number, MAC address, device ID or QR code
from that screen. Write down the TV's local IP from its network settings and
the computer's current LAN IPv4 address.

The U8000F runs Tizen 9.0, Linux 5.4.261, ARMv7 softfloat and .NET 6.0.9; the
QN85C runs Linux 5.4.77 armv7l with the same .NET 6.0.9 runtime. Two panels
three years apart shared the runtime and the access route, and still differed in
kernel, home shell (`com.samsung.tv.coba.*` on the QN85C) and installed app IDs.
Similar year/model names can have different chipsets, framework assemblies, APIs
and app containers.

Ask which features matter if the owner has not already said. Our setup
prioritized HDMI, streaming shortcuts and native Bluetooth. Voice assistants,
context suggestions and several background smart features were unwanted.
Another owner may need them.

After [access setup](02-access.md), collect a private inventory:

```sh
tv exec --command 'uname -srmo; readlink -f /usr/share/dotnet.tizen/netcoreapp'
tv exec --command 'sqlite3 -readonly /opt/dbspace/.pkgmgr_parser.db ".schema package_app_info"'
tv exec --command 'sqlite3 -readonly -header -csv /opt/dbspace/.pkgmgr_parser.db "SELECT app_id,app_disable,app_onboot,app_autorestart FROM package_app_info ORDER BY app_id;"'
tv exec --command 'sqlite3 -readonly /opt/dbspace/.app-context.db ".schema key_filter"'
tv exec --script recipes/status.sh
```

`tv` is the shell helper defined in the access guide. Raw command results
are automatically stored in ignored `.local/sessions/`.

Record current Home/startup preferences, then use the compiled Probe described
in the launcher guide to read the main-operation Home handler and actual input
source list. On the U8000F, HDMI 1/2/3 mapped to 13/14/15. **Do not infer that mapping for
another model.** The shipped dock carries PS5, Xbox, Switch, Netflix, Prime
Video and YouTube tiles; edit `launcher/assets/apps.json` and the input labels
to match the owner's connected devices.

Inventory service unit definitions before creating stop markers:

```sh
tv exec --command 'systemctl cat pisa-service.service canalysis-service.service'
```

A stop marker works only if the exact vendor unit contains the corresponding
negated `ConditionPathExists`. Guessing a path based on a process name is not
enough. A [profile](../profiles) and the shared
[catalog](../data/cleanup-groups.json) describe observed targets, not
authorization to change every entry.

Samsung's product pages
([U8000F](https://www.samsung.com/us/tvs/uhd-4k-tv/u8000f-75-inch-crystal-uhd-4k-smart-tv-un75u8000ffxza/))
provide consumer specifications only. Inspect the real device for
firmware-specific implementation details, and record what you find in a new
profile rather than editing an existing one.
