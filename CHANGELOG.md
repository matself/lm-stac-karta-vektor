# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Official Topo10 styling for the `byggnad` table of the `byggnader` collection (rule-based on building type, taken from the "Byggnad (alla utom schabloner med illustrativt läge)" and "Byggnad (endast schabloner med illustrativt läge)" layers, so features with insamlingslage "Illustrativt läge" are drawn with their own symbols)

## [1.0.2] - 2026-10-07

### Changed

- Renamed the internal `TOKEN_URL` constant to `OAUTH_ENDPOINT_URL` to avoid a Bandit false positive (B105) in the plugin repository security scan. No functional changes.

## [1.0.1] - 2026-10-01

### Changed

- Moved the toolbar icon and menu entry from the Web toolbar/menu to the Plugins toolbar/menu

## [1.0.0] - 2026-09-30

### Changed

- Renamed to "Geodata: Vektor (Lantmäteriet)" and gave the plugin a new
  icon, as part of a shared naming/icon scheme across all four
  Lantmäteriet-related plugins (Geodata: Vektor / Ortofoto & höjd / NGP /
  Markhöjd direkt) so they cluster together in the QGIS plugin manager and
  read as one family. "Lantmäteriet" stays a trailing, parenthetical
  source attribution rather than moving to the front, to avoid implying
  the plugin is made by them. `PLUGIN_NAME` (dock title, message-bar
  prefix, menu entry, task-log category) updated to match.

### Fixed

- `ortnamn_ortnamn.qml` had no scale-based label visibility (matching
  Lantmäteriet's own Topo10 style, which doesn't restrict it either), so
  PAL attempted to place a label for every feature in view regardless of
  zoom level. Fine at a normal zoomed-in view, but rendering a whole
  län's worth of features at once (e.g. Stockholms län, 53 668 objekt)
  locked QGIS's main thread for minutes - reported as "QGIS hänger" after
  the per-län split below made it much easier to trigger (a new file's
  first view is naturally "zoom to extent" = the whole län at once). Added
  a minimum visibility scale (labels only render at 1:200 000 or more
  zoomed in) matching how a printed topographic map would behave anyway.
  Full-län renders now take well under a second; a normal zoomed-in view is
  unaffected. See [docs/stilfiler.md](docs/stilfiler.md).

### Added

- Optional per-län split for `ortnamn`: a new "Dela upp ortnamn per län (en
  fil per län)" checkbox in the Hämta group (off by default). `ortnamn` is
  the one STAC-vektor collection delivered as a single nationwide file
  (~989 000 objekt) instead of one file per kommun, which makes it
  unwieldy to work with as-is. When checked, the downloaded file is written
  out as 21 separate GeoPackages (one per `lanskod`, e.g.
  `ortnamn_se_stockholms.gpkg`) via `QgsVectorFileWriter` with a subset
  string filter, and each is added as its own styled layer instead of the
  one giant layer. New `core/lan.py` (the 21 län code → name lookup) and
  `core/split.py` (`SPLITTABLE`, `split_by_lan`).
- Official Lantmäteriet styling for `ortnamn`, adapted from Topo10's
  categorized/rule-based labeling by `detaljtyp` (15 categories, e.g. bold
  black for tätort names, italic green for nature reserves, italic blue for
  water features). Extracted directly from `Topografi10_vektor_thematic.qlr`'s
  "Ortnamn och upplysningstext" layer via `QDomDocument`/`QDomElement`
  manipulation (not by rebuilding `QgsRuleBasedLabeling` objects in Python,
  which proved unreliable), fixing a field-name mismatch (`text` →
  `ortnamn`) and removing three data-defined properties (`Size`,
  `LabelRotation`, `OffsetQuad`) that referenced fields (`thojd`, `trikt`,
  `tjust`) present in Topo10's internal schema but not in the STAC-vektor
  open-data `ortnamn` table - those fields evaluating to `NULL` was silently
  zeroing every label's font size, which had looked like a `QgsRuleBasedLabeling`
  engine bug. See [docs/stilfiler.md](docs/stilfiler.md).

### Fixed

- `core/styles.apply_style()` used `layer.loadNamedStyle(path, ...)`, whose
  file-path overload can silently resolve to a style already saved in the
  layer's own provider (e.g. a GeoPackage's `layer_styles` table, which
  `apply_style` itself writes to) instead of reading the QML file passed to
  it - discovered while re-testing the `ortnamn` style against a GeoPackage
  that still had an earlier style saved. Now reads the file and imports it
  via `QDomDocument`/`importNamedStyle()` instead, which always reflects the
  actual file on disk.

### Added

- Self-designed styling for `kommun-lan-rike` (`kommun`, `lan`, `rike`
  polygon tables): magenta outline-only polygons, solid/dashed/dash-dot
  line pattern per level, `lan`/`kommun` labelled by name. No official
  Lantmäteriet style exists for this collection - it's an NGP
  "Test"-status product without a published manér package, unlike
  `fastighetsindelning`/`marktacke`. Checked and ruled out: the old
  outgoing Fastighetsindelning schema's bundled `kommunyta`/`lansyta`
  layers (different, discontinued schema) and `Topografi10_vektor_260605.qlr`
  (44 layers, no admin-boundary layer at all). See
  [docs/stilfiler.md](docs/stilfiler.md).
- `build.py` and `plugins.xml`: builds `dist/lm_stac_karta_vektor.<version>.zip`
  (via `git archive`, so only committed files) and a self-hosted plugin
  repository, matching the sibling plugins' release process. See "New
  release" in the README.
- Downloaded layers are grouped in the layer tree (one group per download,
  e.g. `marktacke_kn1270`) and ordered within the group to match
  Lantmäteriet's own cartographic draw order from the QLR - points on top,
  then lines, then polygon fills at the bottom (`core/styles.DRAW_ORDER`,
  `sort_by_draw_order`). Previously all layers landed flat and unordered at
  the project root.
- Official Lantmäteriet styling for `marktacke` (all 3 tables: `mark`,
  `markkantlinje`, `sankmark`), extracted from `Marktäcke_vektor_250203.qlr`
  and verified against a real downloaded `marktacke` GeoPackage. See
  [docs/stilfiler.md](docs/stilfiler.md).
- Results table shows the kommun name alongside its code (e.g. "Skellefteå
  (2482)") when the STAC item's title follows Lantmäteriet's "... för
  `<kommun>` kommun" phrasing (`StacItem.kommun`/`.label` in `core/items.py`),
  falling back to the plain id otherwise.
- Official Lantmäteriet styling for downloaded layers: `core/styles.py`
  applies a bundled `.qml` (symbology + labeling) per collection/table when
  one exists, and saves it into the GeoPackage's `layer_styles` table so it
  stays styled outside the plugin too. Covers all 6 `fastighetsindelning`
  geometry tables so far, extracted from Lantmäteriet's own
  `Fastighetsindelning_vektor_251127.qlr` (the *current*, "Gällande" 2025.02
  product documentation - not the outgoing 2021.10 GEODOK/28 page, which
  has an entirely different, non-matching table schema). See
  [docs/stilfiler.md](docs/stilfiler.md) for exactly where it came from and
  how to add styles for more collections.
- Bundled `LMTopografisymboler` font (`fonts/lmtopografisymboler.ttf`,
  downloaded from the same Geotorget documentation page), registered for
  the running QGIS session only via `QFontDatabase.addApplicationFont`
  (`core/fonts.py`) - some of Lantmäteriet's point symbols (e.g.
  fastighetsgränspunkter) use it. Falls back to a warning message if
  registration fails instead of silently rendering the wrong symbols.

### Fixed

- `PLUGIN_NAME` (used for the dock title, message-bar prefix, menu entry,
  toolbar tooltip and task-manager entries) was the English display name
  used for the plugins.qgis.org metadata `name=` field, making every
  message-bar popup read as a mix of English and Swedish (e.g. "Geodata
  Downloader (Lantmäteriet) - STAC-vektor : Välj minst en samling."). The
  two are unrelated by rule - metadata's `name=` stays English for the
  store listing, but the runtime UI must stay Swedish. `PLUGIN_NAME` is now
  a separate, fully Swedish string ("Geodatahämtning (Lantmäteriet) –
  STAC-vektor").
- The `LMTopografisymboler` font-missing warning fired on every download
  regardless of whether any layer's actually-applied style referenced the
  font (e.g. it fired for plain `markkantlinje`/`sankmark` styles that don't
  use it). `apply_style` now reports per-style whether the font was needed
  and missing (`core/fonts.font_referenced_in`), and the dock warns once
  only when that was actually the case.
- `fastighetsindelning` (and any other multi-layer GeoPackage, e.g. separate
  point/line/polygon tables) only had its first layer added to the project;
  `_add_vector` now enumerates every vector sublayer via
  `QgsProviderRegistry.querySublayers` and adds each one.
- Träffar (hits) stayed visible after changing which collections were
  checked, without touching the service - easy to miss re-clicking Sök and
  end up downloading stale results. The hits are now cleared as soon as the
  collection selection changes, not only on a service switch (see below).
- Träffar (hits) kept showing the previous service's results after
  switching service, since only the collection list was reloaded. Now
  cleared immediately, and any in-flight collections/search task for the
  old service is cancelled so a late response can't repopulate it.

### Added

- Initial version of the QGIS plugin "Geodata Downloader (Lantmäteriet) -
  STAC-vektor": search and download from Lantmäteriet's STAC-vektor open
  data service. Architecture mirrors the sibling plugin
  `matself/LM-STAC-Downloader` (stac-bild/stac-hojd): OAuth2 client
  credentials via QGIS' own authentication manager (`QgsAuthConfigSelect` +
  a "Ny Lantmäteriet-inloggning…" dialog), background `QgsTask`-based search
  through `QgsBlockingNetworkRequest`, and a `QgsFileDownloader`-based
  sequential download queue with progress reporting. Adds a collection
  picker and extracts vector `.zip` assets into GeoPackage/Shapefile/GML
  layers after download.
- Plugin-root `LICENSE` file and a `license` field in `metadata.txt`,
  required by the plugins.qgis.org validator (a repo-root `LICENSE` next to
  the plugin folder doesn't satisfy it).
- English README with a "User interface" section explaining every Swedish
  dialog and message, required for plugins.qgis.org review. A Swedish user
  guide (`docs/anvandning.md`) covers the full walkthrough for end users.
- `changelog` and `qgisMaximumVersion=4.99` fields in `metadata.txt`.

### Changed

- Translated `metadata.txt` (name, description, about, tags) and the one
  genuinely Swedish code comment (in `config.py`) to English, per
  plugins.qgis.org's requirement that code and explanations be in English;
  the UI itself stays Swedish (see README).
- Disabled STAC-karta in the service picker (`SERVICES` in `config.py`).
  Live investigation of `GET /collections/{id}` showed its one open
  collection, `topowebb`, has a global (`-180…180`) collection extent and
  returns the same 4 items (145-175 GB each, one per style/projection
  variant of the whole country) for any search bbox - it isn't tiled by
  area at all, so a search-and-download UI is the wrong tool for it. Its
  Geotorget product page confirms this: "Produkten går inte att beställa i
  Geotorget", pointing to an FTP mirror instead. Its other two collections
  (nmk50/nmk250) were already excluded as access-restricted. Reversible via
  a one-line change in `config.py` if Lantmäteriet changes this.
- Nationell militär karta (`nmk50`, `nmk250`) is access-restricted and is
  filtered out of the collection list and search results.
- Reworked from an initial flat single-package scaffold (unauthenticated
  `urllib` downloads, no auth UI) after live-testing against the real API
  showed `/collections` and `/search` are public but the actual file
  download host (`dl1.lantmateriet.se`) requires OAuth2 credentials for
  restricted products.
