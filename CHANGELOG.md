# Changelog

Format baserat på [Keep a Changelog](https://keepachangelog.com/sv/1.0.0/).

## [Unreleased]

### Added

- Initial version of the QGIS plugin "Geodata Downloader – Karta/Vektor
  (Lantmäteriet)": search and download from Lantmäteriet's STAC-karta and
  STAC-vektor open data services. Architecture mirrors the sibling plugin
  `matself/LM-STAC-Downloader` (stac-bild/stac-hojd): OAuth2 client
  credentials via QGIS' own authentication manager (`QgsAuthConfigSelect` +
  a "Ny Lantmäteriet-inloggning…" dialog), background `QgsTask`-based search
  through `QgsBlockingNetworkRequest`, and a `QgsFileDownloader`-based
  sequential download queue with progress reporting. Adds a collection
  picker (STAC-karta/STAC-vektor expose several collections each) and
  extracts vector `.zip` assets into GeoPackage/Shapefile/GML layers after
  download.
- Nationell militär karta (`nmk50`, `nmk250`) is access-restricted and is
  filtered out of the collection list and search results.

### Changed

- Reworked from an initial flat single-package scaffold (unauthenticated
  `urllib` downloads, no auth UI) after live-testing against the real API
  showed `/collections` and `/search` are public but the actual file
  download host (`dl1.lantmateriet.se`) requires OAuth2 credentials for
  restricted products.
