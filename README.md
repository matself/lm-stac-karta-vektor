# Geodata Downloader – Karta/Vektor (Lantmäteriet)

Ett fristående QGIS-plugin (inte utvecklat av Lantmäteriet) för att söka och
ladda ned öppna geodata från Lantmäteriets STAC-tjänster:

- **STAC-karta** — rasterkartor (Topografisk webbkarta m.fl. — se
  [Behörighetsskyddade kartor](#behörighetsskyddade-kartor) nedan).
- **STAC-vektor** — vektordata (Byggnader, Marktäcke, Fastighetsindelning,
  Belägenhetsadresser, Ortnamn, Kommun/län/rike).

Systerplugin till [`matself/LM-STAC-Downloader`](https://github.com/matself/LM-STAC-Downloader)
("Geodata Downloader (Lantmäteriet)"), som täcker ortofoto och höjddata
(STAC-bild/STAC-hojd). Arkitekturen och gränssnittet är medvetet lika: samma
sorts autentiseringsgrupp, samma `QgsFileDownloader`-baserade nedladdningskö,
samma sätt att spara/återläsa inställningar. En redan skapad
autentiseringskonfiguration i QGIS ("Lantmäteriet STAC") kan återanvändas
mellan de två pluginen, eftersom båda pratar med samma API-hanterare.

## Auktorisering

Lantmäteriets STAC-API:er använder **OAuth2 client credentials** via
`https://apimanager.lantmateriet.se/oauth2/token` — samma mönster som
Lantmäteriets övriga distributions-API:er (jfr `stac-bild`/`stac-hojd` i
systerpluginet, och Markhöjd Direkt i Hajk-forkens bakände). Pluginet
lagrar inga uppgifter själv: klientnyckel/hemlighet sparas krypterat i QGIS
egen autentiseringsdatabas (`QgsAuthMethodConfig`, typ OAuth2), och QGIS
hämtar/förnyar token automatiskt via `authcfg`.

Verifierat mot de faktiska produktions-URL:erna (2026-09-28):

```
GET  https://api.lantmateriet.se/stac-karta/v1/collections    -> 200, inget Authorization-huvud krävs
GET  https://api.lantmateriet.se/stac-karta/v1/search?...     -> 200, inget Authorization-huvud krävs
GET  https://dl1.lantmateriet.se/.../nmk250_61_4.tif           -> 401 Unauthorized (utan uppgifter)
```

Det vill säga: **att bläddra i kataloger och söka fungerar utan inloggning**
(både `/collections` och `/search` svarar publikt på båda tjänsterna). Det är
först **den faktiska filnedladdningen** (`dl1.lantmateriet.se`) som kräver
autentisering — och det gäller i första hand skyddade produkter (se nedan).
Sökning kan alltså göras utan att ha skapat en inloggning i pluginet; ladda
ned genom att först klicka **Ny Lantmäteriet-inloggning…** och ange Consumer
Key/Secret för ett systemkonto som beställt rätt nedladdningsprodukt på
[Geotorget](https://geotorget.lantmateriet.se/).

## Behörighetsskyddade kartor

**Nationell militär karta** (samlingarna `nmk50` och `nmk250` i STAC-karta)
är behörighetsskyddad och kräver ett systemkonto med särskild beställning.
Pluginet filtrerar bort dessa två samlingar helt (`RESTRICTED_COLLECTIONS` i
[`config.py`](lm_stac_karta_vektor/config.py)) — de visas varken i
samlingslistan eller i sökresultat, så att man inte råkar försöka ladda ned
data man inte har åtkomst till. Övriga samlingar i STAC-karta (t.ex.
Topografisk webbkarta) och samtliga i STAC-vektor är öppna data.

## Katalogstruktur (STAC)

Båda tjänsterna följer STAC/OGC API - Features:

- `GET /collections` — listar samlingar.
- `POST /search` — sök objekt (`collections`, `bbox`, `datetime`, `limit`),
  paginerar via `links[rel=next]` som klienten följer automatiskt.
- Varje träff (`Feature`) har en tillgång (`assets.data`) som är själva
  nedladdningsfilen: `.tif`/`.jp2` för raster, `.zip` (innehåller
  GeoPackage m.m.) för vektor.

## Installation (utveckling)

Länka eller kopiera in `lm_stac_karta_vektor/`-mappen i din QGIS-profils
plugin-katalog, t.ex. på Windows:

```powershell
Copy-Item -Recurse `
  "C:\GITHUB\lm-stac-karta-vektor\lm_stac_karta_vektor" `
  "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\lm_stac_karta_vektor"
```

Starta QGIS, öppna **Insticksprogram → Hantera och installera
insticksprogram → Installerade** och aktivera "Geodata Downloader –
Karta/Vektor (Lantmäteriet)". Panelen öppnas från Webb-menyn eller
verktygsfältet.

Kräver QGIS 3.44 eller senare (OAuth2 Client Credentials-flödet i
`QgsBlockingNetworkRequest`/`QgsFileDownloader`).

## Användning

1. **Anslutning**: klicka **Ny Lantmäteriet-inloggning…** och ange Consumer
   Key/Secret (krävs bara för nedladdning, inte för sökning).
2. **Sökning**: välj tjänst, kryssa i en eller flera samlingar, ställ in
   utbredningen (kartvyn, ett lager, rita på kartan eller manuella
   koordinater) och eventuellt ett tidsfilter. Klicka **Sök**.
3. **Träffar**: kryssa i önskade rader.
4. **Hämta**: välj målmapp, klicka **Hämta valda**. Om "Lägg till i
   projektet när klart" är ikryssad läggs raster-/vektorfiler (även sådana
   som packas upp ur `.zip`) till i projektet automatiskt.

## Kända begränsningar

- En `.zip`-tillgång antas innehålla en enda GeoPackage/lager per fil (så
  som Lantmäteriets vektorprodukter är paketerade idag). Ett flerlagers-GPKG
  i zip-arkivet öppnas bara med sitt första lager av `QgsVectorLayer`.
- Sökning är begränsad till 1000 träffar; snäva in området eller
  tidsfiltret vid trunkering.
- Inget automatiserat testramverk är uppsatt — verifiering sker genom
  manuell körning i QGIS (se `docs/` för anteckningar, om sådana läggs till).

## Licens

GPL-3.0-or-later, se [LICENSE](LICENSE).
