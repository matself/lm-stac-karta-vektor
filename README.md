# Geodata Downloader – Karta/Vektor (Lantmäteriet)

Ett fristående QGIS-plugin (inte utvecklat av Lantmäteriet) för att söka och
ladda ned öppna geodata från Lantmäteriets STAC-tjänster:

- **STAC-vektor** — vektordata (Byggnader, Marktäcke, Fastighetsindelning,
  Belägenhetsadresser, Ortnamn, Kommun/län/rike).
- **STAC-karta** — avstängd tills vidare, se
  [STAC-karta är avstängd](#stac-karta-är-avstängd) nedan.

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
GET  https://api.lantmateriet.se/stac-vektor/v1/collections   -> 200, inget Authorization-huvud krävs
GET  https://api.lantmateriet.se/stac-vektor/v1/search?...    -> 200, inget Authorization-huvud krävs
GET  https://dl1.lantmateriet.se/byggnadsverk/byggnad_*.zip    -> 401 Unauthorized (utan uppgifter)
```

Det vill säga: **att bläddra i kataloger och söka fungerar utan inloggning**
(`/collections` och `/search` svarar publikt). Det är först **den faktiska
filnedladdningen** (`dl1.lantmateriet.se`) som kräver autentisering. Sökning
kan alltså göras utan att ha skapat en inloggning i pluginet; ladda ned genom
att först klicka **Ny Lantmäteriet-inloggning…** och ange Consumer Key/Secret
för ett systemkonto som beställt rätt nedladdningsprodukt på
[Geotorget](https://geotorget.lantmateriet.se/).

Live-verifierat med riktiga nycklar: ett konto med STAC-vektor beställt fick
`403 Forbidden` (autentiserat men inte behörigt) på `byggnader` men lyckades
hämta, packa upp och lägga till `belagenhetsadresser` som lager — dvs.
entitlement kontrolleras per samling, inte bara per tjänst.

## STAC-karta är avstängd

STAC-karta erbjuds inte i gränssnittet just nu (`SERVICES` i
[`config.py`](lm_stac_karta_vektor/config.py) utesluter den uttryckligen) —
ingen av dess tre samlingar går att hämta meningsfullt genom pluginet:

- **`nmk50`/`nmk250`** (Nationell militär karta) är behörighetsskyddade och
  kräver ett systemkonto med särskild beställning — samma sak som gör att
  de aldrig visas i samlingslistan även om STAC-karta slås på igen
  (`RESTRICTED_COLLECTIONS`).
- **`topowebb`** (CC-BY-4.0, den enda öppna samlingen) är **inte indelad i
  rutor**: `GET /collections/topowebb` rapporterar hela jordklotet som
  utbredning, och en sökning på en bbox i Kiruna gav exakt samma fyra träffar
  som en sökning i Skåne — samma fyra hela-Sverige-filer (145–175 GB var,
  en per stil-/projektionsvariant) oavsett var man söker. Lantmäteriets egen
  Geotorget-sida för produkten säger uttryckligen att den inte går att
  beställa där och hänvisar i stället till en FTP-plats
  (`ftp://download-opendata.lantmateriet.se/`) — dvs. den är inte tänkt att
  hämtas via API:et i nuläget.

Slå på den igen genom att ta bort filtreringen i `config.py`
(`SERVICES = {k: v for k, v in _ALL_SERVICES.items() if k != "stac-karta"}`)
om Lantmäteriet börjar dela upp `topowebb` i rutor eller på annat sätt gör
STAC-karta lämplig för ett sök-och-hämta-gränssnitt.

## Katalogstruktur (STAC)

Båda tjänsterna följer STAC/OGC API - Features (även STAC-karta, som
tillsvidare är avstängd i gränssnittet, se ovan):

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
