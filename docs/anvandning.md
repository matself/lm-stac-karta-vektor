# Användarhandledning: Geodata: Vektor (Lantmäteriet)

Pluginet söker och laddar ned öppna vektordata från Lantmäteriets
**STAC-vektor**-tjänst: Byggnader, Marktäcke, Fastighetsindelning,
Belägenhetsadresser, Ortnamn samt Kommun, län och rike. Data är indelad per
kommun. Kräver QGIS 3.44 eller senare. För en teknisk sammanfattning på
engelska, se [README.md](../README.md).

STAC-karta (rasterkartor) erbjuds inte, se "STAC-karta is disabled" i
README. Pluginet är fristående och inte utvecklat av Lantmäteriet.

## 1. Skaffa inloggningsuppgifter (endast för nedladdning)

Sökning fungerar utan inloggning. Nedladdning kräver:

1. På [Geotorget](https://geotorget.lantmateriet.se/): kontrollera att
   systemkontot har beställt STAC-vektor (nedladdning).
2. I Lantmäteriets API-hanterare (apimanager.lantmateriet.se): skapa en
   applikation som prenumererar på STAC-vektor-API:et.
3. Generera ett **Consumer Key** och **Consumer Secret** för applikationen.

Behörigheten gäller per samling: ett konto kan ha åtkomst till
`belagenhetsadresser` men inte till `byggnader`. Det är den vanligaste
orsaken till "åtkomst nekad".

## 2. Logga in i pluginet

1. Öppna panelen från Plugins-menyn eller verktygsfältet.
2. Under **Anslutning**, klicka **Ny Lantmäteriet-inloggning…**.
3. Fyll i ett namn samt Consumer Key och Consumer Secret. Samma inloggning
   kan återanvändas i systerpluginet Geodata: Ortofoto & höjd.
4. Klicka OK. Uppgifterna sparas krypterat i QGIS autentiseringsdatabas;
   pluginet lagrar dem aldrig själv. Inloggningen väljs automatiskt i
   rullistan **Autentisering**.

## 3. Sök

1. Under **Sökning**, välj en eller flera **Samlingar**.
2. Ställ in **Utbredning**: aktuell kartvy, ett befintligt lager, en ruta
   ritad på kartan eller koordinater.
3. Valfritt: kryssa i **Tidsfilter** och ange Från/Till.
4. Klicka **Sök**. Sökningen körs i bakgrunden och resultatet trunkeras vid
   1000 träffar; snäva då in området eller tidsfiltret.

## 4. Välj och ladda ned

1. Kryssa i de träffar du vill ha i tabellen (eller **Markera alla** /
   **Avmarkera alla**). Namnkolumnen visar kommunnamn och kommunkod när
   Lantmäteriets beskrivning har formen "… för `<kommun>` kommun".
2. Under **Hämta**, välj målmapp.
3. **Lägg till i projektet när klart** packar upp zip-filerna och lägger
   till lagren i projektet. Lager med en stil (Fastighetsindelning,
   Marktäcke, Kommun/län/rike) läggs till redan stilsatta, se
   [stilfiler.md](stilfiler.md).
4. **Ortnamn** levereras som en enda rikstäckande fil (~989 000 objekt).
   Kryssa i **Dela upp ortnamn per län** för 21 mindre GeoPackage-filer.
5. Klicka **Hämta valda**. Över 2 GB frågar pluginet om bekräftelse.
   **Avbryt** stoppar en pågående nedladdning.

## Felsökning

**"Välj eller skapa en autentisering först."**
Ingen inloggning är vald. Skapa en enligt steg 2 eller välj en befintlig.

**"åtkomst nekad. Sökningen fungerade, men den valda autentiseringen får
inte hämta filer…"**
Kontot är giltigt men samlingen är inte beställd för det. Kontrollera
beställningen på Geotorget och prenumerationen i API-hanteraren. Testa en
annan samling för att se om det gäller hela kontot.

**Inga samlingar visas**
Kontrollera nätverksanslutningen. Listan kräver ingen inloggning.

**"Ange en giltig utbredning."**
Utbredningen är tom eller ogiltig. Kontrollera att den ligger i Sverige.

**QGIS frågar efter huvudlösenord**
Normalt. Autentiseringsdatabasen är krypterad med ett huvudlösenord som du
sätter första gången.

## Kända begränsningar

- Sökningen är begränsad till 1000 träffar.
- STAC-karta erbjuds inte, se README.
