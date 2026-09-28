# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

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
