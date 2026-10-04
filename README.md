# Avalauncher

**Prototyp cyfrowego bliźniaka góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.**

Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z ponad 1500 policzonymi z góry scenariuszami lawin i wskazuje służbie lawinowej stoki, które mogą zagrozić szlakom. Gdy wiedza się starzeje, bo dron nie mógł polecieć, mówi to wprost i planuje, gdzie polecieć, żeby się dowiedzieć.

HackYeah 2026, zadanie Defence (odporność). Zespół: Przemysław Nowak, Łukasz Janiec, Cezary Pastor.

## Dwie rzeczy, które robi

| | Wie | Wie, czego nie wie |
| --- | --- | --- |
| **Wejście** | Nowy przelot drona nad szlakiem i strefami startowymi nad nim | Czas i opad od ostatniego przelotu |
| **Co liczy** | Do których scenariuszy z biblioteki podobna jest dziś każda strefa startowa | Jak bardzo zestarzała się wiedza o każdym sektorze |
| **Co pokazuje** | Sektory, które mogą zagrozić szlakom, z uzasadnieniem | Flagę „nie wiem” i plan następnego przelotu w dostępnym czasie lotu |

Wszystko inne służy tym dwóm kolumnom.

## Demo: dwa poranki

1. **Dzień 1 (12.01.2025), dron poleciał.** Porównanie z biblioteką scenariuszy wskazuje sektory, które mogą zagrozić szlakom. Kliknięcie sektora pokazuje, dlaczego.
2. **Dzień 2 (13.01.2025), zamieć, dron nie poleciał.** Wiedza o sektorach się starzeje i sektory bez świeżego pomiaru dostają flagę „nie wiem”. Avalauncher proponuje plan przelotu na pierwsze okno pogodowe.

Pogoda: IMGW-PIB (prawdziwe). Grubość płyty i przeloty: syntetyczne. Poranki demo leżą w prawdziwym epizodzie 11–13.01.2025: +34 cm nowego śniegu w 3 dni, 72 h zamieci w dobach 11–13.01, pokrywa 51 → 85 cm. Sumy dobowe IMGW (zamieć, opad) obejmują całą dobę, więc widok o 7:00 pokazuje je z doby poprzedniej.

Działa lokalnie i offline: scenariusze są policzone z góry, więc wynik w terenie jest natychmiastowy i nie potrzebuje sieci.

## Jak uruchomić demo

Wystarczy Python 3.7 lub nowszy. Bez instalacji pakietów, bez sieci.

```bash
python -m http.server 8777 --directory web
```

- Dzień 1: <http://localhost:8777>
- Dzień 2 od razu: <http://localhost:8777/?day=2>

Wersja online (GitHub Pages, gdy repo będzie publiczne): <https://przemeknowak781.github.io/avalauncher/>. Biblioteka scenariuszy ma osobną stronę: `biblioteka.html`.

Otwórz przez serwer, nie przez `file://`: przeglądarka blokuje wtedy moduły i odczyt danych. Znaczek „stacja IMGW na żywo” potrzebuje sieci. Bez niej pokazuje ostatni odczyt albo brak łączności, a scenariusz działa dalej.

## Wyniki tej nocy

Pomiary z 3/4.10.2026. Wszystkie liczby pochodzą z [docs/12_wyniki.md](docs/12_wyniki.md). Teren: GUGiK NMT (prawdziwy). Pogoda: IMGW-PIB (prawdziwe). Grubość płyty i przeloty: syntetyczne.

**Teren i strefy**

- Wycinek: Hala Gąsienicowa, Kasprowy Wierch, Kościelec, Świnica, Zawrat.
- GUGiK NMT 5 m, przeliczony na siatkę 10 m.
- Strefy startowe wyznaczone z terenu regułą nachylenia i wysokości, z podziałem po ekspozycji.
- Szlaki z OpenStreetMap, w ich prawdziwych kolorach.

**Biblioteka scenariuszy (AvaFrame com1DFA 2.1)**

- Pierwsza seria: 72 symulacje dla 8 stref, czyli 8 stref × 3 grubości płyty (0,6 / 1,3 / 2,0 m) × 3 kalibracje tarcia (samosAT Small / Medium / standard). W każdej z nich lawina dochodzi do co najmniej jednego odcinka szlaku.
<!-- lib:start -->
- Pełna biblioteka: 1566 symulacji dla 58 stref: 9 grubości płyty (0,4–2,0 m) × 3 kalibracje tarcia, 0 nieudanych. 48 z 58 stref dochodzi do szlaku (przepływ > 0,1 m).
<!-- lib:end -->
- Każdy scenariusz zapisuje zasięg, obrys i odcinki szlaków, do których dochodzi lawina.

**Czas liczenia**

| Zadanie | Laptop (Intel i5-1245U) | DGX Spark (GB10, 20 rdzeni Arm) |
| --- | --- | --- |
| Jedna symulacja com1DFA (benchmark, ta sama strefa) | 107 s | 6,7 s |
| 72 symulacje równolegle | nie mierzone | 129 s na 10 procesach |
| Klatka renderu 3D | 15,6 s | 4,9 s |
| Pełna biblioteka, 1566 symulacji | nie mierzone | 30,4 min na 12 rdzeniach |

| GPU, ten sam test | DGX Spark (GB10) | RTX A4500 |
| --- | --- | --- |
| Uczenie sieci konwolucyjnej na mapach 128×128 | 739 próbek/s | 1114 próbek/s |
| Mnożenie macierzy fp16 | 94,5 TFLOPS | 71,9 TFLOPS |

**Decyzja:** fizyka i renderingi na CPU Sparka, uczenie surogatu na GPU Sparka. RTX A4500 uczy szybciej, ale wyniki AvaFrame powstają na Sparku i nie trzeba ich przesyłać, a GPU ma dostęp do 128 GB pamięci wspólnej z CPU. Spark jest współdzielony, więc używaliśmy najwyżej 10–12 procesów naraz.

**Kalibracja na prawdziwych lawinach (przykładowa, nie dla Tatr).** Na 5 prawdziwych lawinach z Austrii i Szwajcarii, test bez podglądania: mediana błędu zasięgu 92 m, średnio 154 m, najgorzej +350 m; Popeletzbach +25 m, IoU 0,70. Dane zdarzeń OpenNHM/AvaFrameData 1.0, 234 symulacje AvaFrame; ustawienie tarcia wybierane na czterech lawinach i sprawdzane na piątej, po kolei na każdej. Model bez lasu i bez porywania śniegu. Podejrzewamy, że stąd część błędu, ale wariant z lasem i porywaniem z danych zdarzeń (parametry domyślne, niestrojone) go nie zmniejszył: średnio 153,7 m, mediana 124 m. Grubość odrywu zmierzono tylko na Eiskar (2,7 m), dla reszty przyjęto 1,2 m. Dopasowanie na tym samym zdarzeniu (Popeletzbach, 21 przebiegów, w próbie, nie walidacja): samosAT, odryw 0,6 m, IoU 0,727, błąd +20 m. Dla Tatr potrzebne są lokalne obserwacje.

**Uczenie przez wzmacnianie (RL) dla planu przelotu.** Polityka RL (REINFORCE, 10,4 mln epizodów w 6 min na GPU DGX Spark) na 1000 porankach spoza treningu daje 19,9% spadku niepewności wobec 20,2% planu VOI (patrol 5,4%): dorównuje, ale nie pokonuje, więc zostajemy przy prostszym planerze. Prawda losowana z przekonania silnika, liczby nieporównywalne z 86 wobec 71.

<!-- surr:start -->
**Surogat.** Sieć U-Net uczona na 1215 symulacjach AvaFrame przybliża mapę grubości przepływu bez uruchamiania fizyki. Na 3 stokach wyłączonych z treningu (81 symulacji) średnie IoU zasięgu wynosi 0,81 (IoU to wspólna część obu obrysów podzielona przez ich sumę; 1 oznacza pełną zgodność). Jedna mapa: 2,3 ms na GPU Sparka. AvaFrame w pełnej bibliotece: 10,4 s na symulację na jednym rdzeniu CPU (mediana). To dowód koncepcji. Surogat nie zastępuje AvaFrame.
<!-- surr:end -->

**Test logiki na 30 porankach: prawdziwa pogoda, syntetyczny stan stoków** (`web/data/proof.json`, skrypt `tools/proof.mjs`):

<!-- proof:start -->
Dane syntetyczne, test logiki. Pogoda: IMGW-PIB (prawdziwe). Grubość płyty i przeloty: syntetyczne. Poranki dowodu: IMGW-PIB Kasprowy Wierch, 23.12.2024–21.01.2025 (kierunek wiatru założony).

- 30 poranków × 48 stref nad szlakami daje 1440 par „strefa, poranek”. W 144 z nich strefa naprawdę zagraża szlakowi. Przelot był odwołany w 15 porankach.
- „Prawda” zawiera błąd modelu, o którym silnik nie wie: jedna kalibracja tarcia na poranek i błąd grubości płyty ±15–25% plus szum. Zmienia on wynik w 44 parach.

**Wie** (wobec reguły „suma nowego śniegu z 3 dni ≥ 30 cm”, która flaguje naraz wszystkie stoki nad szlakami):

| Miara | Avalauncher | Reguła 3 dni |
| --- | --- | --- |
| Przeoczone groźne pary (z 144) | 0 | 121 |
| Fałszywe alarmy „zagrożenie” | 0 | 25 |
| Flagi „nie wiem” | 549 | nie dotyczy |

Cena zera przeoczeń to 549 flag „nie wiem”. 505 z nich padło w porankach bez przelotu. 431 padło na stokach, które w danej chwili nie zagrażały (te grupy się nakładają). Nie liczymy ich jako fałszywych alarmów, bo „nie wiem” nie mówi „zagrożenie”, tylko „trzeba zmierzyć”.

**Wie, czego nie wie** (plan przelotu wobec patrolu wzdłuż niebieskiego szlaku Murowaniec – Czarny Staw – Zawrat, ten sam czas lotu 20 min):

| Miara | Plan Avalaunchera | Stała trasa |
| --- | --- | --- |
| Zdjęte flagi „nie wiem” | 86 | 71 |
| Groźne stoki z flagą po przelocie | 29 | 16 |
| Spadek niepewności decyzji | 23% | 7% |

Błąd modelu zmienia prawdę tylko w 44 przypadkach, więc wynik 0 przeoczeń i 0 fałszywych alarmów to słaby dowód. To test spójności logiki na danych syntetycznych, a nie walidacja na prawdziwych lawinach w Tatrach.
<!-- proof:end -->

## Czym nie jest

- **Nie mówi, że zagrożenia nie ma.** Tylko podnosi uwagę. Brak flagi nie oznacza braku zagrożenia.
- **Nie wydaje komunikatu.** Stopień zagrożenia i zamknięcia szlaków ustala prognosta. Avalauncher wskazuje mu, gdzie patrzeć.
- **Nie jest pierwszym cyfrowym bliźniakiem lawin.** Wielkie biblioteki scenariuszy już istnieją (np. Bühler i in. 2022, dla całego kantonu). Nowe są dwie rzeczy: śledzenie, gdzie wiedza się zestarzała, i plan przelotu, który ją odświeża ([przegląd](docs/01_oryginalnosc.md)).

## Jak sprawdzamy, że działa

Na 30 porankach z prawdziwą pogodą IMGW i syntetycznym stanem stoków, po jednej mierze na każde zdanie tezy:

1. **Wie:** ile sektorów zagrażających szlakom przeoczy Avalauncher, a ile prosta reguła „suma nowego śniegu z 3 dni”, czyli silny punkt odniesienia z [docs/02](docs/02_pokrywa_i_uruchomienie.md).
2. **Wie, czego nie wie:** o ile szybciej spada niepewność nad groźnymi sektorami przy planie Avalaunchera niż przy locie zawsze tą samą trasą, przy tym samym czasie lotu.

Wyniki: tabela w sekcji „Wyniki tej nocy”.

## Prawdziwe a symulowane

| Element | Stan |
| --- | --- |
| Teren | Prawdziwy: GUGiK NMT, wycinek Hali Gąsienicowej |
| Szlaki | Prawdziwe: OpenStreetMap |
| Strefy startowe | Wyznaczone z prawdziwego terenu prostą regułą nachylenia i wysokości, bez inwentarza służby |
| Biblioteka scenariuszy | Liczona naprawdę fizycznym solverem AvaFrame com1DFA na prawdziwym terenie |
| Parametry symulacji | Standardowe kalibracje tarcia z AvaFrame. Przykładowa kalibracja: 5 prawdziwych lawin z Austrii i Szwajcarii (OpenNHM/AvaFrameData), test bez podglądania; nie dla Tatr |
| Pogoda | Prawdziwa: IMGW-PIB Kasprowy Wierch, zima 2024/25 (dobowe archiwum). Kierunek wiatru założony, bo brak go w archiwum |
| Satelita | Prawdziwy: Copernicus Sentinel-2 L2A (Element84 Earth Search, AWS Open Data), pokrywa śnieżna 16.01.2025; w dniach zamieci chmury |
| Grubość płyty na stokach, przeloty i odczyty drona | Syntetyczne |
| 30 poranków dowodu | Prawdziwa pogoda, syntetyczny stan stoków i błąd modelu |
| Śnieg w filmach 3D | Syntetyczny, nałożony na prawdziwą ortofotomapę GUGiK |
| Stacja IMGW Kasprowy Wierch | Prawdziwy odczyt na żywo, poza scenariuszem demo |

Avalauncher nie jest zwalidowaną prognozą zagrożenia i nie służy do samodzielnego ostrzegania. Kalibracja na zdarzeniach historycznych to pierwszy krok wdrożenia z lokalną służbą.

## Materiały

Filmy i plansze leżą w `filmy/`. Katalog jest poza Git, bo ma ok. 230 MB. Udostępniamy go na żądanie; lżejsze kopie leżą w `web/media/`.

| Katalog | Co zawiera |
| --- | --- |
| `filmy/porownania/` | Macierz 3×3 dla każdego z 8 sektorów (grubość płyty × kalibracja tarcia) i przegląd wszystkich sektorów, z kadrem końcowym PNG |
| `filmy/pojedyncze_2d/` | 72 pojedyncze symulacje AvaFrame w 2D |
| `filmy/3d/` | 16 filmów 3D z obrotem kamery, ciasno wykadrowanych: 8 sektorów, po 2 warianty |
| `filmy/plansze/` | Plansze do deku |
| `filmy/hero/` | Kadry 4K: cztery lawiny AvaFrame na terenie 3D (S10, S14, S22, S31); `mapa_zasiegow.png` i `mapa_zasiegow_orbit.mp4`; `koncepcja_3d.png` i `koncepcja_orbit.mp4`: wynik silnika demo dla dnia 2 (te same flagi i plan przelotu co na ekranie), stan śniegu syntetyczny |
| `filmy/collage/` | `2d_mozaika.mp4`: wszystkie 72 symulacje pierwszej serii naraz; `3d_przeglad.mp4`: 16 lawin w 3D (8 stref × 2 warianty) |
| `filmy/kalibracja/` | `5_lawin.png`: AvaFrame na 5 prawdziwych lawinach, test bez podglądania; `5_lawin_las.png`: wariant z lasem i porywaniem śniegu; `porownanie.png`: dopasowanie w próbie na lawinie Popeletzbach |
| `filmy/surrogate/` | `porownanie.png`: AvaFrame, surogat i różnica na 3 stokach spoza treningu; `suwak.mp4`: surogat przy zmianie grubości płyty; `surrogate_unet.onnx`: wytrenowana sieć (30 MB) |

Skrypty, z których powstały: [`tools/avaframe/`](tools/avaframe/), [`tools/visuals/`](tools/visuals/), [`tools/surrogate/`](tools/surrogate/), [`tools/calibration/`](tools/calibration/). Lżejsze kopie kadrów do strony leżą w `web/media/`.

## Skąd bliźniak wie, co wie

Docelowo: regularne przeloty helikoptera lub UAV nad korytarzami szlaków: radar (GPR) mierzy grubość pokrywy wzdłuż linii przelotu, LiDAR lub fotogrametria mierzy powierzchnię śniegu, a skały, tyczki i drzewa służą wspomagająco jako punkty kontrolne. W demo przeloty i odczyty są syntetyczne. Między przelotami lukę wypełniają stacje pogodowe, dane klimatyczne i historia zdarzeń. Ograniczenia każdego źródła opisuje [docs/04](docs/04_pomiary_i_fuzja.md).

## Dalej

- **Platforma, nie wytrenowany model:** nowy masyw to konfiguracja (teren, strefy startowe, szlaki, lokalne zdarzenia) i lokalna kalibracja. Nowe źródło danych podłącza się przez jeden interfejs ([`ports.py`](src/avalauncher/ports.py)), jeśli podaje wartość, niepewność i czas pomiaru. Przenośności między górami nie obiecujemy, bo to otwarta hipoteza ([H4](docs/08_cyfrowy_blizniak_use_case.md)).
- Pilot z jedną służbą na jednym korytarzu szlaku: kalibracja AvaFrame na lokalnych zdarzeniach z Tatr (TOPR), tak jak tej nocy przykładowo na 5 lawinach z Austrii i Szwajcarii, i integracja z SNOWPACK.
- Osuwiska na tym samym silniku; ocena dostępności tras w sytuacjach kryzysowych.
- Aktywny dobór przelotów z RL dopiero wtedy, gdy pokona proste reguły.

## Licencje i użycie AI

- Nasz kod: MIT, plik [`LICENSE`](LICENSE).
- Dane i programy zewnętrzne zachowują własne licencje. Teren i ortofotomapa: GUGiK. Szlaki: © współtwórcy OpenStreetMap (ODbL). Pogoda: IMGW-PIB (dane przetworzone). Lawiny do kalibracji: OpenNHM/AvaFrameData 1.0 (CC BY 4.0; dane F. Perzl, BFW; WLV; SLF Davos); teren: Land Tirol (CC BY 4.0 AT), BEV ALS DTM 1 m (CC BY 4.0), © swisstopo swissALTI3D (warunki licencji do potwierdzenia). Satelita: zawiera zmodyfikowane dane Copernicus Sentinel (2025), Sentinel-2 L2A przez Element84 Earth Search (AWS Open Data). Solver: AvaFrame (EUPL-1.2). Czcionka: Archivo (OFL).
- Kod, teksty i wizualizacje powstały z dużym udziałem Claude Code (model Claude Opus 5.5). Zakres i tezę ustalili ludzie.
- Pełna lista i atrybucje: [docs/10](docs/10_ai_i_licencje.md).

## Zaplecze badawcze

Kod w `src/avalauncher/` to pierwszy szkielet (3.10) do porównywania siatek śniegu. Demo go nie używa. Python 3.11+, bez zależności:

```bash
PYTHONPATH=src python -m avalauncher compare --observation examples/synthetic_observation.json --scenarios examples/synthetic_scenarios.json
PYTHONPATH=src python -m unittest discover -s tests -v
```

1. [Oryginalność i hipotezy](docs/01_oryginalnosc.md): znane precedensy i test nowości.
2. [Pokrywa i uruchomienie](docs/02_pokrywa_i_uruchomienie.md): stan śniegu, warstwy i prawdopodobieństwo uwolnienia.
3. [Dynamika i symulatory](docs/03_dynamika_i_symulatory.md): AvaFrame, kalibracja, MuJoCo.
4. [LiDAR, radar, landmarki](docs/04_pomiary_i_fuzja.md): pomiary i ich ograniczenia.
5. [Zbiory danych](docs/05_dane.md): 13 zweryfikowanych źródeł z DOI w [katalogu JSON](catalog/datasets.json); surowe pliki nie są dołączone.
6. [Architektura, RL, DGX Spark](docs/06_rl_i_dgx.md): kontrakty i etapy treningu.
7. [Plan walidacji](docs/07_walidacja.md): testy na niewidzianych sezonach i stokach.
8. [Cyfrowy bliźniak i cytaty](docs/08_cyfrowy_blizniak_use_case.md): precedensy, cytaty z publikacji i przypadek użycia.
9. [Plan budowy demo](docs/09_plan_budowy.md): noc 3/4.10, kontrakt danych i podział pracy.
10. [Użycie AI i licencje](docs/10_ai_i_licencje.md): ujawnienie i atrybucje.
11. [Deck i pitch](docs/11_deck.md): scenariusz 10 slajdów i pitch na 3 minuty.
