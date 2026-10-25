# Attribution and distribution

UnTizen is a fork and generalization of
[quiet-tizen](https://github.com/jss8649/quiet-tizen/tree/cf518d7a9278dca7990e27756218258e44044a29),
commit `cf518d7a9278dca7990e27756218258e44044a29`, copyright 2026 Quiet Tizen
contributors, under the MIT license in `LICENSE`. The local changes are the
multi-model profile resolution in `tools/tv.py`, the shared bloat catalog in
`data/cleanup-groups.json` with its `keep_active` invariants, the
parameterized recipes, deterministic packaging, this project's branding and the
launcher artwork described below. The upstream chain continues: quiet-tizen
derives its launcher design from Free My TV and its access route from
samsung-tv-root, both credited below and preserved here.

Quiet Home is a native Tizen .NET/NUI implementation. Its layout measurements,
palette, dock proportions and focus treatment adapt
[Free My TV](https://github.com/simbasjungles/free-my-tv/tree/73409804e5085e720dccea9ab95078a515cae098),
commit `73409804e5085e720dccea9ab95078a515cae098`, copyright 2026 FreeMyTV
contributors, under the MIT license in `licenses/FreeMyTV-MIT.txt`.
The Android APK is not used.

The bundled Quiet Inter fonts are static derivatives of Inter, copyright
2016 The Inter Project Authors, renamed after conversion. Medium: weight 500,
optical size 14; Semibold: weight 600, optical size 14; Display: weight 600,
optical size 32. See `licenses/Inter-OFL.txt`. These font files retain the
SIL Open Font License; the repository's MIT license does not replace it.

The Material Symbols PNGs come through Free My TV and retain Apache 2.0:
`licenses/Material-Symbols-Apache-2.txt`.

App, service and console marks in `launcher/assets/` (dock tiles, feature cards
and the `placeholders/card-*.svg` library tiles) were rebuilt as path-only SVG
from publicly documented vector logos, because the NUI SVG renderer has no text
support and a text-based tile renders blank on the TV. Each mark remains the
trademark of its owner; nothing here is relicensed, and no mark implies
endorsement. Gradient cards, backgrounds and the generic input/app tiles were
produced for this launcher. `launcher/artwork-sources.json` records optional
raster sources and transformations, and `tools/fetch_artwork.py` downloads
selected artwork into ignored local files if you prefer your own.

The source subset in `vendor/samsung_tv_root/` and `vendor/payload-source/`
comes from [samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root/tree/4ad2c4d3b0d0e0da4b5b7ebe4a787e94596f416b),
commit `4ad2c4d3b0d0e0da4b5b7ebe4a787e94596f416b`, under the
Unlicense in `licenses/samsung-tv-root-Unlicense.txt`. The local runtime
fallback is described in [provenance](docs/provenance.md).

The UnTizen logo in `logo/` is an original drawing: a tilted ellipse with a
power slash, in homage to the shape language of Samsung TV branding without
reusing any Samsung artwork or wordmark.

No Samsung SDB executable, firmware, SDK/reference assembly, stock app binary,
account database or private backup is distributed. The repository and its
contributors are not affiliated with Samsung, Sony, Nintendo, Microsoft, Amazon
or any streaming service.
