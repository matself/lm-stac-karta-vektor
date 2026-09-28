# Geodata Downloader (Lantmäteriet) - STAC-vektor

An independent QGIS plugin (not developed by Lantmäteriet, the Swedish
mapping, cadastral and land registration authority) for searching and
downloading open vector data from Lantmäteriet's **STAC-vektor** service:
Byggnader (buildings), Marktäcke (land cover), Fastighetsindelning (cadastral
boundaries), Belägenhetsadresser (addresses), Ortnamn (place names) and
Kommun/lan/rike (municipality/county/country). Covers Sweden only.

STAC-karta (raster maps) is not offered - see
[STAC-karta is disabled](#stac-karta-is-disabled) below.

Sibling plugin to [`matself/LM-STAC-Downloader`](https://github.com/matself/LM-STAC-Downloader)
("Geodata Downloader (Lantmäteriet)"), which covers orthophoto and elevation
data (STAC-bild/STAC-hojd). The architecture and interface intentionally
match: the same kind of authentication group, the same
`QgsFileDownloader`-based download queue, the same settings persistence. An
authentication configuration already created in QGIS ("Lantmäteriet STAC")
can be reused between the two plugins, since both talk to the same API
manager.

The user interface is in Swedish. This section explains it in English so the
plugin can be reviewed and tested without knowing Swedish; the full Swedish
walkthrough is in [docs/anvandning.md](docs/anvandning.md).

## User interface

Opened from the Web menu or the web toolbar (button "Geodata Downloader
(Lantmäteriet) - STAC-vektor"). The dock panel has four groups: Anslutning
(connection), Sökning (search), Träffar (hits) and Hämta (download).

### Main dock panel

| Swedish label | English meaning | What it does |
|---|---|---|
| Anslutning | Connection | Group with the authentication picker |
| Autentisering | Authentication | QGIS' own auth config picker (`QgsAuthConfigSelect`); configs can also be created/edited here directly |
| Ny Lantmäteriet-inloggning... | New Lantmäteriet login... | Opens the login dialog (see below) |
| Sökning | Search | Group with the search controls |
| Tjänst | Service | Service picker (currently only STAC-vektor, see below) |
| Samlingar | Collections | Checkable list of the service's collections, e.g. Byggnader, Marktäcke |
| Utbredning | Extent | Standard QGIS extent widget (`QgsExtentGroupBox`): current map view, a layer's extent, drawing a box, or manual coordinates |
| Tidsfilter | Time filter | Optional checkable date-from/date-to range |
| Från / Till | From / To | The two date fields in the time filter |
| Sök | Search | Runs the STAC search for the selected collections and area |
| Träffar | Hits | Group listing the search results as a table (name, collection, type, date, size) |
| Markera alla | Select all | Checks every hit |
| Avmarkera alla | Deselect all | Unchecks every hit |
| Hämta | Download | Group with the download controls |
| (file picker) | Target folder | `QgsFileWidget` for the output directory |
| Lägg till i projektet när klart | Add to project when done | Adds the downloaded layers to the QGIS project once finished (extracting vector `.zip` assets first) |
| Hämta valda | Download selected | Starts downloading the checked hits |
| Avbryt | Cancel | Cancels an ongoing download |
| Fristående plugin, inte utvecklat av Lantmäteriet. | Independent plugin, not developed by Lantmäteriet. | Disclaimer label shown in the panel |

### Login dialog ("Ny inloggning för Lantmäteriet" / New Lantmäteriet login)

Opened by "Ny Lantmäteriet-inloggning...". Creates an OAuth2 (client
credentials) authentication configuration in QGIS' own Authentication
Manager; the key and secret are stored encrypted by QGIS, not by the plugin.

| Swedish label | English meaning | What it does |
|---|---|---|
| Namn | Name | Name of the QGIS authentication configuration (defaults to "Lantmäteriet STAC") |
| Consumer Key | Consumer Key | The OAuth2 client id from Lantmäteriet's API manager |
| Consumer Secret | Consumer Secret | The OAuth2 client secret from Lantmäteriet's API manager |

### Messages

| Swedish message | English meaning | When it appears |
|---|---|---|
| Välj eller skapa en autentisering först. | Choose or create an authentication first. | Download was started without a valid auth config selected |
| Kunde inte hämta samlingar: ... | Could not fetch collections: ... | The collections request failed |
| Välj minst en samling. | Select at least one collection. | Search was started with no collection checked |
| Ange en giltig utbredning. | Enter a valid extent. | Search was started with an empty/invalid extent |
| {n} träffar. | {n} hits. | Search completed |
| Markera minst en rad att hämta. | Check at least one row to download. | Download was started with nothing checked |
| Välj en målmapp. | Choose a target folder. | Download was started with no output folder set |
| Du är på väg att hämta ... ungefär ... Fortsätta? | You are about to download ... approximately ... Continue? | Confirmation before a download larger than 2 GB |
| Fil {n} av {N}: {namn} (...) | File {n} of {N}: {name} (...) | Progress while downloading |
| Avbryter... | Cancelling... | Shown while a download is being cancelled |
| {n} filer hämtade. | {n} files downloaded. | Download finished successfully |
| åtkomst nekad. Sökningen fungerade, men... | Access denied. The search worked, but... | The download host returns HTTP 403 (Forbidden): the account is authenticated but not entitled to that collection |
| Ange både Consumer Key och Consumer Secret. | Enter both Consumer Key and Consumer Secret. | One of the two login fields is empty |

## Authorization

Lantmäteriet's STAC API uses **OAuth2 client credentials** via
`https://apimanager.lantmateriet.se/oauth2/token`, the same pattern as
Lantmäteriet's other distribution APIs (compare `stac-bild`/`stac-hojd` in
the sibling plugin). The plugin stores no credentials itself: the client
key/secret is saved encrypted in QGIS' own authentication database
(`QgsAuthMethodConfig`, type OAuth2), and QGIS fetches/refreshes the token
automatically via `authcfg`.

Verified against the actual production URLs (2026-09-28):

```
GET  https://api.lantmateriet.se/stac-vektor/v1/collections   -> 200, no Authorization header required
GET  https://api.lantmateriet.se/stac-vektor/v1/search?...    -> 200, no Authorization header required
GET  https://dl1.lantmateriet.se/byggnadsverk/byggnad_*.zip    -> 401 Unauthorized (without credentials)
```

In other words: **browsing catalogs and searching works without logging
in** (both `/collections` and `/search` respond publicly). It is only **the
actual file download** (`dl1.lantmateriet.se`) that requires authentication.
Search can therefore be used without having created a login in the plugin;
download by first clicking **Ny Lantmäteriet-inloggning...** and entering
Consumer Key/Secret for a system account that has ordered the right download
product on [Geotorget](https://geotorget.lantmateriet.se/).

Live-verified with real keys: an account with STAC-vektor ordered got
`403 Forbidden` (authenticated but not entitled) on `byggnader` but
successfully downloaded, unzipped and added `belagenhetsadresser` as a
layer - i.e. entitlement is checked per collection, not just per service.

## STAC-karta is disabled

STAC-karta is not offered in the interface right now (`SERVICES` in
[`config.py`](lm_stac_karta_vektor/config.py) excludes it explicitly) -
none of its three collections can be usefully fetched through the plugin:

- **`nmk50`/`nmk250`** (Nationell militär karta, national military map) are
  access-restricted and require a system account with a separate order -
  the same thing that keeps them out of the collection list even if
  STAC-karta is turned back on (`RESTRICTED_COLLECTIONS`).
- **`topowebb`** (CC-BY-4.0, the only open collection) is **not tiled by
  area**: `GET /collections/topowebb` reports the whole globe as its
  extent, and a search on a bbox in Kiruna returned the exact same 4 hits
  as a search in Skåne - the same 4 whole-of-Sweden files (145-175 GB each,
  one per style/projection variant) regardless of where you search.
  Lantmäteriet's own Geotorget product page for it explicitly says it
  can't be ordered there and points to an FTP mirror instead
  (`ftp://download-opendata.lantmateriet.se/`) - i.e. it isn't meant to be
  fetched through the API right now.

Turn it back on by removing the filter in `config.py`
(`SERVICES = {k: v for k, v in _ALL_SERVICES.items() if k != "stac-karta"}`)
if Lantmäteriet starts tiling `topowebb` or otherwise makes STAC-karta
suitable for a search-and-download interface.

## Catalog structure (STAC)

Both services follow STAC/OGC API - Features (including STAC-karta, which
is currently disabled in the interface, see above):

- `GET /collections` - lists collections.
- `POST /search` - search items (`collections`, `bbox`, `datetime`,
  `limit`), paginating via `links[rel=next]`, which the client follows
  automatically.
- Each hit (`Feature`) has an asset (`assets.data`) that is the actual
  download file: `.tif`/`.jp2` for raster, `.zip` (containing a GeoPackage
  etc.) for vector.

## Install

1. Link or copy the `lm_stac_karta_vektor/` folder into your QGIS profile's
   plugin directory, e.g. on Windows:

   ```powershell
   Copy-Item -Recurse `
     "C:\GITHUB\lm-stac-karta-vektor\lm_stac_karta_vektor" `
     "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\lm_stac_karta_vektor"
   ```

2. Start QGIS, open **Plugins -> Manage and Install Plugins -> Installed**
   and enable "Geodata Downloader (Lantmäteriet) - STAC-vektor". The panel
   opens from the Web menu or the toolbar.

Requires QGIS 3.44 or later (the OAuth2 Client Credentials flow in
`QgsBlockingNetworkRequest`/`QgsFileDownloader`).

## Getting started

1. Get access keys (Consumer Key and Consumer Secret) from Lantmäteriet's
   API manager, for a system account that has ordered the right STAC-vektor
   download product on Geotorget.
2. Open the panel and click **Ny Lantmäteriet-inloggning...**, enter the
   keys (only needed for download, not for search).
3. Pick one or more collections, set the search area, optionally a time
   filter, and click **Sök**.
4. Check the wanted hits, choose a target folder, click **Hämta valda**.

## Known limitations

- Search is capped at 1000 hits; narrow the area or the time filter if
  truncated.
- No automated test framework is set up; verification is done by running
  the plugin manually in QGIS.

## Development

The code lives in `lm_stac_karta_vektor/`. Hook it into a QGIS profile by
linking or copying the folder into the profile's `python/plugins`.

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
