# Showcase

This repository stays a Tizen toolkit: one profile per exercised
`(model, firmware)` pair, a shared glob catalog, and Quiet Home on NUI.

Work that does not belong in this tree lives elsewhere. Add a row here when
you publish it. Compatibility reports that are not yet end-to-end use
[.github/ISSUE_TEMPLATE/compatibility.md](.github/ISSUE_TEMPLATE/compatibility.md)
and a note under [docs/devices/](docs/devices/README.md).

## What stays here

| Kind | Where |
|---|---|
| End-to-end model/firmware | `profiles/<model>-<firmware>.json` |
| One-session inventory | `docs/devices/<model>-<firmware>.md` |
| Observed cleanup glob | `data/cleanup-groups.json` |
| Quiet Home behaviour | `launcher/` |

## What goes in its own repository

| Kind | Why not here |
|---|---|
| Heavy restyle of Quiet Home | Different visual contract; keep this launcher small |
| Another access route (kernel, bootloader, custom OS) | This checkout only documents the archive-root route measured on two pairs |
| Fire OS, Android TV, LG webOS, or any non-Tizen port | Different OS, different tools |
| A Samsung-wide copied disable list | The catalog is globs plus per-device profiles, not pasted ID lists |

## Published work

None yet. Open a pull request that adds one row with the repository URL,
the model/firmware you exercised (or the platform, if it is not Tizen),
and a one-line description. Do not attach snapshots or IP addresses.
