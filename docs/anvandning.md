# Användarhandledning: Geodata Downloader (Lantmäteriet) - STAC-vektor

Den här guiden går igenom hela flödet i pluginet på svenska: installation,
inloggning, sökning, nedladdning och felsökning. För en kort teknisk
sammanfattning på engelska, se [README.md](../README.md) i förrådets rot.

## Vad gör pluginet?

Pluginet söker och laddar ned öppna vektordata från Lantmäteriets
**STAC-vektor**-tjänst direkt i QGIS: Byggnader, Marktäcke,
Fastighetsindelning, Belägenhetsadresser, Ortnamn samt Kommun, län och rike.
Data är indelad per kommun, så en sökning ger normalt en eller ett fåtal
träffar per samling och kommun ni söker inom.

STAC-karta (rasterkartor som Topografisk webbkarta) erbjuds **inte** just
nu. Anledningen finns förklarad i README under "STAC-karta is disabled":
i korthet är den enda öppna samlingen där (`topowebb`) inte indelad i
rutor, utan varje sökning ger samma fyra 145-175 GB-filer för hela Sverige
oavsett var man söker, och Lantmäteriets egen produktsida för den hänvisar
till en FTP-plats i stället för API-beställning.

Pluginet är fristående och inte utvecklat av Lantmäteriet. Det är
systerplugin till [Geodata Downloader (Lantmäteriet)](https://github.com/matself/LM-STAC-Downloader),
som på samma sätt täcker ortofoto och höjddata.

## 1. Installation

1. Länka eller kopiera mappen `lm_stac_karta_vektor/` in i din QGIS-profils
   plugin-katalog. På Windows:

   ```powershell
   Copy-Item -Recurse `
     "C:\GITHUB\lm-stac-karta-vektor\lm_stac_karta_vektor" `
     "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\lm_stac_karta_vektor"
   ```

2. Starta QGIS och öppna **Insticksprogram → Hantera och installera
   insticksprogram → Installerade**.
3. Kryssa i "Geodata Downloader (Lantmäteriet) - STAC-vektor" för att
   aktivera det.
4. En ny panel-ikon dyker upp i verktygsfältet, och pluginet läggs även
   till under **Webb**-menyn.

Kräver QGIS 3.44 eller senare.

## 2. Skaffa inloggningsuppgifter (krävs endast för nedladdning)

Sökning fungerar utan inloggning - pluginet frågar Lantmäteriets katalog
och söktjänst helt öppet. Det är först när ni faktiskt vill **ladda ned**
en fil som inloggning krävs.

1. Logga in på [Geotorget](https://geotorget.lantmateriet.se/) och
   kontrollera att ert systemkonto har beställt rätt produkt för
   STAC-vektor (nedladdning).
2. Gå till Lantmäteriets API-hanterare (apimanager.lantmateriet.se) och
   skapa en applikation som prenumererar på STAC-vektor-API:et, om ni inte
   redan har en.
3. Under applikationen genererar ni ett **Consumer Key** och **Consumer
   Secret** - det är dessa två värden pluginet behöver.

Behörigheten kontrolleras per samling, inte bara per tjänst: ett konto kan
till exempel ha åtkomst till `belagenhetsadresser` men inte till
`byggnader`, även om båda ingår i STAC-vektor. Om en nedladdning ger
"åtkomst nekad" (se avsnittet Felsökning nedan) är det oftast just detta
som är orsaken.

## 3. Logga in i pluginet

1. Öppna panelen (Webb-menyn eller verktygsfältsikonen).
2. I gruppen **Anslutning**, klicka **Ny Lantmäteriet-inloggning…**.
3. Fyll i:
   - **Namn**: valfritt namn på inloggningen i QGIS (förvalt: "Lantmäteriet
     STAC"). Om ni redan har skapat en inloggning för systerpluginet
     (Geodata Downloader för ortofoto/höjddata) kan ni återanvända samma
     namn/nycklar här, eftersom båda pratar med samma API-hanterare.
   - **Consumer Key** och **Consumer Secret** från steg 2 ovan.
4. Klicka OK. Nyckel och hemlighet sparas krypterat i QGIS egen
   autentiseringsdatabas (via QGIS huvudlösenord, om ni har satt ett) -
   pluginet självt lagrar aldrig uppgifterna. QGIS hämtar och förnyar
   åtkomsttoken automatiskt när det behövs.
5. Inloggningen väljs nu automatiskt i rullistan **Autentisering**. Ni kan
   när som helst byta till en annan sparad inloggning där, eller skapa
   ytterligare en.

## 4. Sök data

1. Under **Sökning**, kontrollera att tjänsten **STAC-vektor** är vald
   (det är för närvarande det enda alternativet, se ovan om STAC-karta).
2. Kryssa i en eller flera samlingar i listan **Samlingar**, t.ex.
   Byggnader och Belägenhetsadresser.
3. Ställ in **Utbredning** på ett av följande sätt:
   - lämna den på aktuell kartvy,
   - klicka i fältet och välj ett befintligt lager som referens,
   - rita en ruta direkt på kartan,
   - eller skriv in koordinater manuellt.
4. Valfritt: kryssa i **Tidsfilter** och ange ett datumintervall (Från/Till)
   för att bara få träffar inom det spannet.
5. Klicka **Sök**.

Sökningen körs i bakgrunden (en QGIS-bakgrundsuppgift), så gränssnittet
låser sig inte. Antal träffar visas under sökknappen, t.ex. "4 träffar."
Om sökningen ger fler än 1000 träffar trunkeras resultatet - snäva då in
området eller tidsfiltret.

## 5. Välj och ladda ned

1. I gruppen **Träffar** ser ni en tabell med samling, namn, typ, datum och
   storlek för varje träff. Kryssa i de rader ni vill ha, eller använd
   **Markera alla** / **Avmarkera alla**.
2. Under **Hämta**, välj en målmapp med mappväljaren.
3. Kryssa i **Lägg till i projektet när klart** om ni vill att de
   nedladdade lagren ska läggas till i QGIS-projektet automatiskt när
   nedladdningen är klar. Vektordata levereras som `.zip`-filer som
   pluginet packar upp automatiskt och letar efter GeoPackage-/Shapefile-/
   GML-lager i.
4. Klicka **Hämta valda**. Är den sammanlagda storleken över 2 GB frågar
   pluginet om bekräftelse innan nedladdningen startar.
5. En förloppsindikator visar aktuell fil och hur mycket som laddats ned.
   Klicka **Avbryt** för att stoppa en pågående nedladdning.
6. När allt är klart visas ett meddelande med antal nedladdade filer, och
   eventuella lager dyker upp i lagerpanelen om steg 3 var ikryssat.

## Felsökning

**"Välj eller skapa en autentisering först."**
Ingen giltig inloggning är vald i **Autentisering**. Skapa en enligt steg 3
ovan, eller välj en befintlig i rullistan.

**"åtkomst nekad. Sökningen fungerade, men den valda autentiseringen får
inte hämta filer…"**
Sökningen lyckades (kontot är giltigt), men just den samlingen ni försöker
ladda ned är inte beställd för kontot. Kontrollera på Geotorget att
systemkontot har rätt STAC-vektor-produkt beställd, och att applikationen i
API-hanteraren prenumererar på STAC-vektor-API:et. Testa gärna en annan
samling (t.ex. Belägenhetsadresser) för att avgöra om problemet gäller en
specifik samling eller hela kontot.

**Inga samlingar visas i listan**
Kontrollera nätverksanslutningen - listan hämtas från Lantmäteriets öppna
katalogtjänst och kräver ingen inloggning. Ett meddelande om att samlingar
inte kunde hämtas visas i meddelandefältet högst upp i QGIS om anropet
misslyckas.

**"Ange en giltig utbredning."**
Utbredningen är tom eller ogiltig. Kontrollera att kartvyn eller det ritade
området faktiskt täcker ett rimligt område i Sverige.

**QGIS huvudlösenord efterfrågas när jag skapar en inloggning**
Det är normalt - QGIS autentiseringsdatabas är krypterad med ett
huvudlösenord som ni sätter första gången. Utan det kan inte nycklarna
sparas säkert.

## Kända begränsningar

- En `.zip`-tillgång antas innehålla en enda GeoPackage/ett enda lager per
  fil, vilket stämmer med hur Lantmäteriets vektorprodukter paketeras
  idag. Ett flerlagers-GPKG i zip-arkivet öppnas bara med sitt första
  lager.
- Sökning är begränsad till 1000 träffar.
- STAC-karta erbjuds inte, se förklaringen i README.
