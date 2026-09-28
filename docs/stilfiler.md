# Stilfiler: hur de togs fram

Det här dokumentet beskriver var pluginets bundlade stilfiler
(`lm_stac_karta_vektor/styles/*.qml`) och den bundlade fonten
(`lm_stac_karta_vektor/fonts/lmtopografisymboler.ttf`) kommer ifrån, och hur
man tar fram motsvarande för fler samlingar senare.

## Källa

Lantmäteriet publicerar officiella QGIS-manérfiler (`.qlr`) och en
symbolfont per produkt på respektive produkts dokumentationssida på
Geotorget. Viktigt: **den gamla GEODOK/28-sidan** (`Fastighetsindelning
Nedladdning, vektor`, Produktversion 2021.10, "Utgående") är **inte**
samma produkt som STAC-vektor. Den har ett annat tabellschema
(`fastighetsgrans`, `registerenhet_punkt`, `registerenhet_yta`, ...) och
dess manérfiler matchar därför inte det vi laddar ned.

Den korrekta, aktuella produktsidan hittas via Geotorgets nyare
produktkort, inte via sökmotorträffar på den gamla GEODOK-sidan:

```
https://geotorget.lantmateriet.se/geodataprodukter/fastighetsindelning-nedladdning-vektor-api
  → fliken "Dokumentation" → Version 2025.02 ("Gällande")
  → Åtkomst och leverans → "Utseende på och uppritning av data"
```

Den sidans innehåll ligger i en webbkomponent (`<geotorget-dokumentation>`)
med Shadow DOM, så en vanlig textextraktion av sidan ser bara menyskalet -
man behöver läsa `element.shadowRoot.textContent` (eller motsvarande) för
att se själva dokumentationstexten.

Där anges (2025-09-28):

- Manérfil för QGIS: `Fastighetsindelning_vektor_251127.qlr`
- Manérfil för ArcGIS Pro: `Fastighetsindelning_Vektor_251127.lyrx`
- Symbolfil: `lmtopografisymboler.ttf` (nämnd under "Installation av
  fonter" på motsvarande sida för den äldre produktversionen; den nya
  sidans text nämner inte fonten explicit, men QLR-filen refererar
  `font="LMTopografisymboler"` i flera `FontMarker`-symboler, så den
  behövs fortfarande).

Båda filerna är öppet nedladdningsbara utan inloggning
(`https://geotorget.lantmateriet.se/dokument/projects/fastighetsindelning-nedladdning-vektor/released/2025.02/...`).

Verifierat: `layername`-värdena i QLR:en (`granspunkt`,
`registerenhetsomradespunkt`, `registerenhetsomradeslinje`,
`registerenhetsomradesgrans`, `traktyta`, `registerenhetsomradesyta`)
matchar exakt de tabeller STAC-vektor faktiskt levererar för
`fastighetsindelning`.

## Marktäcke

`Marktäcke_vektor_250203.qlr` (2025-02-03) hämtades av användaren direkt
från Geotorget-dokumentationen för STAC-vektor-produkten "Marktäcke
Nedladdning, vektor" (samma sorts produktkort som ovan, inte den äldre
GEODOK-varianten). Den har bara tre lager: `Markkantlinje`
(`markkantlinje`), `Sankmark` (`sankmark`) och `Mark` (`mark`). Verifierat
mot en riktig nedladdning (redan öppen i användarens QGIS-projekt,
`marktacke_kn1265.gpkg`) - alla tre tabellnamn matchar exakt.
`marktacke_mark.qml` refererar `LMTopografisymboler` (samma font som
fastighetsindelning), de andra två gör det inte.

## Hur QML-filerna togs fram

QLR-filen innehåller alla lager i en enda fil (ett `layer-tree-group` plus
`<maplayers>` med renderer-/label-XML per lager). Pluginet vill ha en
separat `.qml` per tabell (samma mönster som `ngp_downloader/styles/`), så
filerna extraherades genom att låta QGIS själv läsa och skriva om XML:en,
i stället för att tolka den för hand:

```python
from qgis.core import QgsLayerDefinition, QgsReadWriteContext, QgsMapLayer
from qgis.PyQt.QtXml import QDomDocument

with open("Fastighetsindelning_vektor_251127.qlr", encoding="utf-8") as f:
    doc = QDomDocument()
    doc.setContent(f.read(), True)

layers = QgsLayerDefinition.loadLayerDefinitionLayers(doc, QgsReadWriteContext())
categories = QgsMapLayer.StyleCategory.Symbology | QgsMapLayer.StyleCategory.Labeling

for layer in layers:
    table = layer.source().split("layername=")[-1]  # e.g. "granspunkt"
    layer.saveNamedStyle(f"fastighetsindelning_{table}.qml", categories)
```

`loadLayerDefinitionLayers` returns the layers without adding them to a
project and without needing the referenced GeoPackage to actually exist
(the layers come back `isValid() == False` since there's no real data
source, but the renderer/labeling state from the XML is intact, which is
all `saveNamedStyle` needs). Kördes interaktivt mot en riktig QGIS-instans
via MCP-kopplingen, inte gissat fram.

## Fonten

`lmtopografisymboler.ttf` laddades ned direkt från länken på
dokumentationssidan ovan och bundlas i pluginet
(`lm_stac_karta_vektor/fonts/`). Den registreras enbart för den pågående
QGIS-sessionen via `QFontDatabase.addApplicationFont` (`core/fonts.py`) -
den installeras aldrig i operativsystemets typsnittskatalog. Om
registreringen misslyckas (t.ex. trasig bundlad fil) visas en varning i
meddelandefältet i stället för att tyst rendera fel symboler.

## Att lägga till fler samlingar

1. Hitta produktets egna produktkort under `geodataprodukter/` på
   Geotorget (inte den gamla GEODOK-sidan om en sådan finns) och kontrollera
   version/status ("Gällande" vs "Utgående").
2. Under Dokumentation → Åtkomst och leverans, hämta manérfilen för QGIS
   (`.qlr`) och eventuell symbolfont.
3. Ladda ned en riktig fil för samlingen (via pluginet) och jämför dess
   `layername`-värden mot QLR:ens `source="...|layername=..."` för att
   bekräfta att de faktiskt matchar - anta inget.
4. Extrahera per-tabell-QML enligt skriptet ovan och lägg filerna i
   `lm_stac_karta_vektor/styles/` som `{collection_id}_{table}.qml`.
5. `core/styles.apply_style()` hittar dem automatiskt via namnkonventionen.
