# Device notes versus end-to-end profiles

`profiles/` is only for model/firmware pairs that were exercised through
cleanup, the launcher, a full restart and standby/wake. A successful
`tv inventory` or `tv doctor` is not that.

A one-session inventory belongs here as `docs/devices/<model>-<firmware>.md`,
copied from the `note.md` that `tv inventory` writes under `.local/inventory/`.
Do not publish IP addresses, serials or the raw app-ID dump.

| Kind | Path | What it means |
|---|---|---|
| End-to-end | `profiles/<model>-<firmware>.json` | Listed in the README and `docs/01-inventory.md`. `tools/tv.py` will resolve it. |
| Notes | `docs/devices/<model>-<firmware>.md` | Observed, not yet daily-driven. Agents must not apply another profile to it. |

Promote a note to a profile only after the phases in [CONTRIBUTING.md](../../CONTRIBUTING.md#add-a-model).
The two current end-to-end pairs stay in `profiles/`; they do not get a notes
file here.
