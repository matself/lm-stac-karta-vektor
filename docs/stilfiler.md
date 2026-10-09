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

## Byggnader - Topo10:s byggnadsstil

`byggnader_byggnad.qml` är lagret **"Byggnad (alla utom schabloner med
illustrativt läge)"** ur `Topografi10_vektor_thematic.qlr`
(`byggnadsverk_ln12.gpkg|layername=byggnad`). Regelbaserad renderare på
`objekttypnr` (2061 Bostad, 2062 Industri, 2063 Samhällsfunktion,
2064 Verksamhet, 2065 Ekonomibyggnad, 2066 Komplementbyggnad,
2067 Övrig byggnad). Varje regel har filtret
`NOT "insamlingslage" = 'Illustrativt läge'`, så objekt med det läget
ritas inte; QLR:en har ett separat lager för dem som inte tagits med.
Fältnamnen verifierades mot en riktig `byggnadsverk_*.gpkg` (tabell
`byggnad` med `objekttypnr` och `insamlingslage`). `renderer-v2` kopierades
direkt ur QLR-XML:en (ingen etikettsättning i detta lager). Övriga tabeller
i samlingen (`byggnadspunkt`, `byggnadsanlaggningspunkt`,
`byggnadsanlaggningslinje`) saknar stil.

## Kommun, län och rike - egen stil (inget officiellt manér finns)

Till skillnad från de två ovan finns **ingen** officiell manérfil för
`kommun-lan-rike`. Undersökt grundligt innan detta drogs som slutsats:

- Den gamla (2021.10, utgående) GEODOK/28-sidan för Fastighetsindelning
  hade lagren "Kommuner" (`kommunyta`) och "Län" (`lansyta`) inbakade, men
  det är ett annat, numera avvecklat schema (se ovan) - inte samma data.
- `Topografi10_vektor_260605.qlr` (användarens fråga: "hade topo10
  kommungränser?") innehåller 44 lager (vägar, byggnader, hydrografi,
  terräng, marktäcke ...) men **inget** kommun-/län-/rikeslager alls.
- Produktsidan för `Kommun, Län och Rike Nedladdning`
  (`geotorget.lantmateriet.se/geodataprodukter/kommun-lan-rike-nedladdning-api`)
  nämner varken manérfil, QLR eller symbolfil någonstans i sin
  dokumentation. Den är en **Nationella geodataplattformen (NGP)**-produkt
  med specifikationsstatus "Test" - en annan, nyare produktfamilj än de
  klassiska "Nedladdning"-produkterna (som Fastighetsindelning/Marktäcke)
  som kommer med ett fullständigt manérpaket (QLR + LYR/LYRX + symbolfont).

Stilen i `kommun-lan-rike_{kommun,lan,rike}.qml` är därför **självbyggd**,
inte extraherad ur ett Lantmäteriet-manér. Verifierad mot en riktig
nedladdning (`kommun-lan-rike_aktuell.gpkg`, tre tabeller: `kommun` 290
objekt, `lan` 21 objekt, `rike` 1 objekt - stämmer med Sveriges faktiska
antal). Utseendet är inspirerat av hur Lantmäteriets egen webbvisare Min
Karta ritar administrativa gränser (skärmdump från användaren:
heldragen linje med tvärstreck = riksgräns, streckad = länsgräns,
streck-prick-prick = kommungräns) men är en förenklad approximation, inte
en pixelexakt kopia:

- Genomgående magenta/rosa kontur (`#c500a1`), ingen fyllning.
- `rike`: heldragen linje, 0.6 mm.
- `lan`: streckad linje, 0.4 mm.
- `kommun`: streck-prick-linje, 0.3 mm.
- Etikett med `namnkortform`-attributet för `lan` och `kommun` (inte
  `rike`, eftersom det bara är ett enda polygon-objekt).

Byggdes direkt i QGIS via `QgsSimpleFillSymbolLayer`/`QgsFillSymbol`/
`QgsPalLayerSettings` och `saveNamedStyle()`, inte genom att tolka en
extern fil - se `DRAW_ORDER["kommun-lan-rike"]` i `core/styles.py` för
skiktordningen (mindre enheter ovanpå större: kommun, sedan län, sedan
rike underst).

## Ortnamn - Topo10:s regelbaserade stil, fungerar nu fullt ut

Fråga: "kan ortnamn stilsättas enligt Topo10?" `Topografi10_vektor_thematic.qlr`
(och den äldre `Topografi10_vektor_260605.qlr`, identiskt innehåll för detta
lager) har ett lager **"Ortnamn och upplysningstext"**
(`text_ln12.gpkg|layername=textobjekt`) med en kategoriserad rendering på
attributet `detaljtyp` (15 kategorier, t.ex. `BEBTX`="Bebyggelsenamn",
`VATTTX`="Namn på sjö") och regelbaserad etikettsättning per kategori -
olika färg, kursivering och fetstil per kategori (t.ex. grön kursiv för
naturreservat, blå kursiv för vattendrag, fet svart för tätortsnamn). Vår
riktiga `ortnamn`-samling (`ortnamn_se.gpkg|layername=ortnamn`, ~989 000
objekt) har fältet `detaljtyp` med 13 distinkta värden, varav 11 finns
direkt bland Topo10:s 15 kategorier (`KULTURTX` och `TRAKTTX` saknas där,
utan motsvarande regel - de får ingen etikett, vilket är korrekt eftersom
Topo10:s eget schema inte har dem heller).

**Tre saker hittades, alla lösta:**

1. Symbolerna i Topo10:s lager är avsiktligt osynliga (`color`-alpha = 0,
   `outline_style="no"`) - punkten är bara en etikettankare, inte tänkt att
   synas. Förväntat, inget fel.
2. Etikettreglerna pekar på fältet `"text"` (Topo10:s egen generiska
   textkolumn i `textobjekt`), inte `"ortnamn"` (vårt fältnamn). Rättades med
   ett enkelt textbyte i XML:en: `fieldName="text"` → `fieldName="ortnamn"`
   på alla 17 `<text-style>`-element.
3. **Den riktiga boven bakom "ingenting renderas":** varje regel har en
   data-definierad `Size`-egenskap kopplad till fältet `thojd`
   (textstorleksklass), plus `LabelRotation`→`trikt` och `OffsetQuad`→`tjust`.
   De fälten finns i Topo10:s egna `textobjekt`-tabell men **inte** i
   STAC-vektor-produktens öppna `ortnamn`-tabell (som bara har `fid`,
   `ortnamn`, `kvartsruta`, `nkoordinat`, `ekoordinat`, `lanskod`,
   `kommunkod`, `detaljtyp`, `sprak`, `lopnummer`, `sockenstadkod`,
   `sockenstadnamn`). När ett data-definierat uttryck pekar på ett fält som
   inte finns evalueras det till NULL, och `Size`-transformerns
   `nullOutput="0"` satte då textstorleken till 0 för *alla* etiketter -
   PAL (etikettmotorn) placerar aldrig en etikett med storlek 0, så resultatet
   blev noll placerade etiketter, oavsett om man körde
   `QgsRuleBasedLabeling` eller `QgsVectorLayerSimpleLabeling` med samma
   inställningar. Det här såg ut som och misstogs länge för ett motorfel i
   `QgsRuleBasedLabeling` (se git-historik för den ursprungliga, felaktiga
   slutsatsen) - det var det inte. Lösning: ta bort de tre
   data-definierade `Option`-noderna (`Size`, `LabelRotation`, `OffsetQuad`)
   ur varje regels `dd_properties` innan filen sparas, eftersom de fält de
   pekar på helt enkelt inte finns i den här produkten.

**Vad det betyder i praktiken:** `thojd`/`trikt`/`tjust` är inte generiska
QGIS-inställningar - de är per-objekt kartografisk produktionsmetadata
(textstorleksklass, textriktning, vilken av de nio kvadranterna runt
ankarpunkten etiketten ska placeras i) som hör till Topo10:s fullständiga
databas, inte till den öppna STAC-vektor-produkten "**Ortnamn
Nedladdning, vektor**". Ortnamnsnedladdningen är ett förenklat,
allmänt namnregister (namn + `detaljtyp` + grundläggande geografi), inte
samma produktionsdata som ligger bakom en tryckt/renderad Topo10-karta.
Manérfilen är alltså fullt avsedd för kartografi - bara för en rikare
datamängd än den som faktiskt publiceras öppet. Det som går att överföra
till ortnamnsnedladdningen är den del av stilen som bara beror på
`detaljtyp` (färg, kursivering, fetstil per kategori - det finns i båda),
inte den del som beror på per-objekt-placeringsdata som ortnamnsnedladdningen
saknar.

**Skalbegränsning tillagd i efterhand (QGIS hängde sig):** varken Topo10:s
originalstil eller den första versionen av `ortnamn_ortnamn.qml` hade någon
skalbaserad synlighet på etiketterna (`scaleVisibility="0"` på alla regler,
även i Lantmäteriets egen fil). Det märks inte vid en normal inzoomad vy
(några hundra objekt), men blir ett akut prestandaproblem när man zoomar ut
till en hel läns utbredning - t.ex. Stockholms län med 53 668 objekt tog
QGIS main-tråden i anspråk i flera minuter (upplevdes av användaren som att
"QGIS hänger", vilket det praktiskt taget gjorde: `QgsMapRendererParallelJob`
för hela länets utbredning tog över två minuter innan PAL:s
platsplaceringsalgoritm var klar). Detta fanns latent redan i den
ostyckade `ortnamn`-filen också, men blev mycket lättare att råka ut för
med länsfiler, eftersom "zooma till lagrets utbredning" på en ny fil då
visar hela länet på en gång.

Löst genom att sätta en skalbegränsning per regel
(`s.minimumScale = 200000`, `s.maximumScale = 1` - i XML:en motsvarar det
`scaleMax="200000"` respektive `scaleMin="1"`, **omvänt** mot vad
attributnamnen antyder; QGIS namnger dessa XML-attribut och sina egna
Python-egenskaper `minimumScale`/`maximumScale` åt olika håll av historiska
skäl, verifierat empiriskt genom att rendera samma vy med olika
värdekombinationer snarare än att gissa). Etiketter visas nu bara vid skala
1:200 000 eller mer inzoomat - motsvarande hur en tryckt topografisk karta
aldrig visar alla ortnamn på en översiktskarta över ett helt län heller.
Full läns-utbredning renderas nu på under en sekund (tidigare >2 minuter),
och en normal inzoomad vy är opåverkad.

**Hur den slutgiltiga `ortnamn_ortnamn.qml` togs fram** (skiljer sig från
metoden i avsnittet nedan, eftersom `QgsRuleBasedLabeling`s Python-API visade
sig vara opålitligt att bygga om för hand - se varning nedan): `renderer-v2`-
och `labeling`-XML-noderna kopierades **direkt** ur QLR:en via
`QDomDocument`/`QDomElement` (inte via `QgsRuleBasedLabeling`-objekt i
Python), fixades enligt punkt 2-3 ovan genom att manipulera DOM-trädet
(aldrig regex på XML-text - nästlade `<Option>`-element med samma namn gör
enkel textersättning opålitlig, se nedan), och skrevs ut som en fristående
`.qml`. Verifierat mot riktig nedladdad `ortnamn_se`-data (Höör/Hörby-området,
83 placerade etiketter, matchar exakt Lantmäteriets egen visuella stil).

**Varning för framtida stilextraktion:** att bygga om `QgsRuleBasedLabeling`
regel för regel i Python (t.ex. `QgsRuleBasedLabeling.Rule(settings)` +
`rootRule.appendChild(rule)`) är känsligt - ett tidigt försök på det sättet
gav till synes identiska regler (rätt filter, rätt `fieldName`) men renderade
ändå ingenting, av skäl som aldrig klarlades. Direkt DOM-manipulation av den
redan fungerande QLR-XML:en (byt attribut, ta bort noder) och sedan
`layer.importNamedStyle(QDomDocument)` är den tillförlitliga vägen. Undvik
också `layer.loadNamedStyle(path, ...)` (filsökvägsvarianten) - den kan tyst
läsa en stil som redan sparats i lagrets egen `layer_styles`-tabell (t.ex. i
en GeoPackage) i stället för filen man faktiskt pekar på; `core/styles.py`
läser nu filen själv och importerar via `QDomDocument`/`importNamedStyle()`
för att undvika det.

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
