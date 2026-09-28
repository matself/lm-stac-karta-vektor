# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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

### Fixed

- Träffar (hits) kept showing the previous service's results after
  switching service, since only the collection list was reloaded. Now
  cleared immediately, and any in-flight collections/search task for the
  old service is cancelled so a late response can't repopulate it.

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
