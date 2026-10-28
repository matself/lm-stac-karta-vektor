<img src="lm_stac_karta_vektor/icon.png" alt="" width="72" align="right">

# Geodata: Vektor (Lantmäteriet)

An independent QGIS plugin (not developed by Lantmäteriet, the Swedish
mapping, cadastral and land registration authority) for searching and
downloading open vector data from Lantmäteriet's **STAC-vektor** service:
Byggnader (buildings), Marktäcke (land cover), Fastighetsindelning (cadastral
boundaries), Belägenhetsadresser (addresses), Ortnamn (place names) and
Kommun/lan/rike (municipality/county/country). Covers Sweden only.

It also offers the open **topowebb** raster map from STAC-karta
(*Topografisk webbkarta Nedladdning, raster*). Those files are 140-175 GB each,
so the plugin cuts out just the extent you choose instead of downloading
everything - see [Topowebb raster map](#topowebb-raster-map) below.

Downloaded layers are automatically styled with Lantmäteriet's own official
QGIS symbology where a style has been extracted for that collection's
tables (currently `fastighetsindelning`) - see
[Official styling](#official-styling) below.

Sibling plugin to [`matself/LM-STAC-Downloader`](https://github.com/matself/LM-STAC-Downloader)
("Geodata: Ortofoto & höjd (Lantmäteriet)"), which covers orthophoto and elevation
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
| Tjänst | Service | Service picker: STAC-vektor (vector data, default) or STAC-karta (the topowebb raster map, see below) |
| Samlingar | Collections | Checkable list of the service's collections, e.g. Byggnader, Marktäcke |
| Utbredning | Extent | Standard QGIS extent widget (`QgsExtentGroupBox`): current map view, a layer's extent, drawing a box, or manual coordinates |
| Tidsfilter | Time filter | Optional checkable date-from/date-to range |
| Från / Till | From / To | The two date fields in the time filter |
| Sök | Search | Runs the STAC search for the selected collections and area |
| Träffar | Hits | Group listing the search results as a table (name, collection, type, date, size). The "name" column shows the kommun name and code (e.g. "Skellefteå (2482)") when the item's STAC title follows Lantmäteriet's "... för `<kommun>` kommun" phrasing, otherwise just the item id |
| Markera alla | Select all | Checks every hit |
| Avmarkera alla | Deselect all | Unchecks every hit |
| Rasterkarta (topowebb) | Raster map (topowebb) | Group shown only when the hits are topowebb items (STAC-karta); see [Topowebb raster map](#topowebb-raster-map) |
| Läge | Mode | "Klipp ut området i Utbredning" (clip the extent out of the remote file, default) or "Hämta hela filen (140-175 GB)" (download the whole file) |
| Upplösning | Resolution | Pixel size of the clip, from full resolution (0.5 m for EPSG:3006) down in powers of two; coarser output is read from the file's overview levels and is much faster |
| Format | Format | Output format of the clip: GeoTIFF (default, compressed) or GeoPackage |
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
| Klipper ut {n} av {N}: {id} ({p} %) | Cutting out {n} of {N}: {id} ({p} %) | Progress while clipping a topowebb extent |
| {n} utklipp klara. | {n} clips done. | Clipping finished successfully |
| {id}: {c} × {r} px är för stort. Minska utbredningen eller välj en lägre upplösning. | {id}: {c} × {r} px is too large. Reduce the extent or pick a lower resolution. | The requested clip exceeds 4 billion pixels |
| Utklippet blir som mest {size} okomprimerat och kan ta lång tid. Fortsätta? | The clip will be at most {size} uncompressed and may take a long time. Continue? | Confirmation before a clip larger than 2 GB uncompressed |
| Området ligger utanför kartans utbredning. | The area is outside the map's extent. | The clip extent does not overlap the topowebb file |
| Kunde inte öppna kartfilen på distans... | Could not open the map file remotely... | The remote GeoPackage could not be opened, usually because the authentication has no access to STAC-karta |
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

## Topowebb raster map

STAC-karta has three collections:

- **`nmk50`/`nmk250`** (Nationell militär karta, national military map) are
  access-restricted and require a system account with a separate order, so
  they are hidden from the collection list (`RESTRICTED_COLLECTIONS`).
- **`topowebb`** (*Topografisk webbkarta Nedladdning, raster*, CC-BY-4.0) is
  the one open collection. It is **not tiled by area**: it has four items
  (colour or greyscale, each in EPSG:3006 and EPSG:3857), and a search on any
  bbox returns those same four. Each item is one GeoPackage of raster tiles of
  140-175 GB covering all of Sweden (EPSG:3857: the whole world).

Because the files are so large, the **Rasterkarta (topowebb)** group offers
two modes:

1. **Klipp ut området i Utbredning** (default): cut the chosen extent out of
   the remote file. The download server answers HTTP Range requests, so GDAL
   can open the GeoPackage through `/vsicurl/` and read only the tiles that
   the extent needs. `core/clip.py` does this with
   `QgsRasterLayer("/vsicurl/<href> authcfg='<id>'")` and `QgsRasterFileWriter`
   in a `QgsTask`. The auth config's HTTP headers (Basic or OAuth2 Bearer,
   from `QgsAuthManager.updateNetworkRequest`) are handed to GDAL through the
   thread-local `GDAL_HTTP_HEADERS` option, because `authcfg` in a `/vsicurl/`
   URI works for Basic but not for OAuth2. The result is a local, compressed GeoTIFF (or GeoPackage) with
   4 bands (RGBA) in the item's CRS. The resolution can be lowered in powers
   of two; coarser output is read from the file's overview levels.
2. **Hämta hela filen**: the ordinary download queue, with the usual
   confirmation for anything over 2 GB.

Verified with both the plugin's usual OAuth2 login (Consumer Key/Secret) and
a Basic-authentication config. Measured against the production service
(2026-10-28): a 2 × 2 km extent at the full 0.5 m resolution
(4000 × 4000 px) took about 10 s; 100 × 100 km at 2000 × 2000 px took about
10 s; a 0.9 km square at full resolution took under a second. Clips larger
than 4 billion pixels are refused, and anything over 2 GB uncompressed asks
for confirmation first.

EPSG:3006 files have a full resolution of 0.5 m. EPSG:3857 files have
2^25 pixels across the world, about 1.19 map units per pixel (roughly 0.6 m
at Swedish latitudes), and their resolution is shown in map units.

## Styling

When "Lägg till i projektet när klart" is checked, downloaded layers are
styled from a bundled `.qml` per collection/table
(`lm_stac_karta_vektor/styles/{collection}_{table}.qml`, applied via
`core/styles.py`, matching the sibling plugin's approach). Only symbology
and labeling are applied, not fields/forms, and the style is also saved
into the GeoPackage's own `layer_styles` table so the file stays styled
even opened without this plugin later.

For `fastighetsindelning`, `marktacke` and the `byggnad` table of
`byggnader` this is Lantmäteriet's own
official QGIS symbology, extracted from the `.qlr` manér file published on
each product's Geotorget documentation page (for `byggnad`, the layer
"Byggnad (alla utom schabloner med illustrativt läge)" and
"Byggnad (endast schabloner med illustrativt läge)" of
`Topografi10_vektor_thematic.qlr`: rule-based on `objekttypnr`, seven
building types, features with `insamlingslage` = "Illustrativt läge"
are drawn with the QLR's separate "(illustrativt läge)" symbols). No such file exists for
`kommun-lan-rike` (it's a newer NGP "Test"-status product without a
published style package - see [docs/stilfiler.md](docs/stilfiler.md) for
what was checked before concluding that), so its style is a simple
self-designed one instead: magenta outline-only polygons differentiated by
line pattern per level (solid/dashed/dash-dot for rike/lan/kommun), loosely
matching how Lantmäteriet's own Min Karta viewer draws administrative
boundaries, with `lan`/`kommun` labelled by name.

Each download also gets its own group in the layer tree (e.g.
`marktacke_kn1270`), with its layers ordered inside that group to match
Lantmäteriet's own cartographic draw order from the QLR - points on top,
then lines, then polygon fills at the bottom (`core/styles.DRAW_ORDER`).
Lantmäteriet documents this order explicitly ("en föreslagen ritordning av
skikten"); previously all layers landed flat and unordered at the project
root.

Currently covers:

- `fastighetsindelning` (all 6 geometry tables: `granspunkt`,
  `registerenhetsomradespunkt`, `registerenhetsomradeslinje`,
  `registerenhetsomradesgrans`, `traktyta`, `registerenhetsomradesyta`) -
  official Lantmäteriet style
- `marktacke` (all 3 tables: `mark`, `markkantlinje`, `sankmark`) -
  official Lantmäteriet style
- `kommun-lan-rike` (all 3 tables: `kommun`, `lan`, `rike`) - self-designed,
  no official style exists
- `ortnamn` - official Lantmäteriet style, adapted from Topo10's
  categorized/rule-based labeling by `detaljtyp` (15 categories, e.g. bold
  black for tätort names, italic green for nature reserves, italic blue for
  water features) - see [docs/stilfiler.md](docs/stilfiler.md) for how the
  field-name and data-defined-property mismatches against the STAC-vektor
  schema were resolved

Other collections fall back to QGIS' default style until a matching QML is
added - see [docs/stilfiler.md](docs/stilfiler.md) for where the current
files came from, how they were produced, and how to add more.

Some of Lantmäteriet's symbols (e.g. fastighetsgränspunkter in
`granspunkt`, and some `mark` categories) use a custom font,
**LMTopografisymboler**, bundled at
`lm_stac_karta_vektor/fonts/lmtopografisymboler.ttf` (downloaded from the
same Geotorget documentation page as the style files) and registered for
the running QGIS session only via `QFontDatabase.addApplicationFont`
(`core/fonts.py`) - never installed into the OS font directory. The check
is scoped to the styles actually being applied (`core/fonts.font_referenced_in`),
so downloading a collection whose style doesn't use the font never shows
the warning; if registration does fail for a style that needs it, a
warning is shown once instead of silently rendering the wrong symbols.

## Catalog structure (STAC)

Both services follow STAC/OGC API - Features:

- `GET /collections` - lists collections.
- `POST /search` - search items (`collections`, `bbox`, `datetime`,
  `limit`), paginating via `links[rel=next]`, which the client follows
  automatically.
- Each hit (`Feature`) has an asset (`assets.data`) that is the actual
  download file: `.tif`/`.jp2` for raster, `.zip` (containing a GeoPackage
  etc.) for vector.

## Install

Download the zip from
[Releases](https://github.com/matself/lm-stac-karta-vektor/releases) and
use *Plugins → Manage and Install Plugins → Install from ZIP*.

For development, link or copy the `lm_stac_karta_vektor/` folder into your
QGIS profile's plugin directory instead, e.g. on Windows:

```powershell
Copy-Item -Recurse `
  "C:\GITHUB\lm-stac-karta-vektor\lm_stac_karta_vektor" `
  "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\lm_stac_karta_vektor"
```

Requires QGIS 3.44 or later (the OAuth2 Client Credentials flow in
`QgsBlockingNetworkRequest`/`QgsFileDownloader`).

## New release

1. Bump `version` in `lm_stac_karta_vektor/metadata.txt`, update
   `changelog=` there and in `CHANGELOG.md`, and commit.
2. `python build.py` - builds `dist/lm_stac_karta_vektor.<version>.zip`
   and updates `plugins.xml`.
3. Commit `plugins.xml`, push and create the release:
   ```
   gh release create v<version> dist/lm_stac_karta_vektor.<version>.zip --title "v<version>"
   ```

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

GPL-3.0-or-later, see [LICENSE](LICENSE), for the plugin's own code.

`lm_stac_karta_vektor/fonts/lmtopografisymboler.ttf` is not covered by that
license: it's Lantmäteriet's own symbol font, downloaded from their
Geotorget product documentation page and bundled here so the official
styling in [Official styling](#official-styling) renders correctly without
a separate manual install step. See
[docs/stilfiler.md](docs/stilfiler.md) for its exact source.
