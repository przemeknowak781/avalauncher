# Plan budowy demo: noc 3/4.10.2026

**Cel:** do 02:30 działa jeden ekran, który pokazuje dwa zdania tezy na prawdziwym terenie Tatr. Po 02:30 tylko poprawki i nagranie.

> Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z ponad 1500 policzonymi z góry scenariuszami lawin i wskazuje służbie lawinowej stoki, które mogą zagrozić szlakom. Gdy wiedza się starzeje, bo dron nie mógł polecieć, mówi to wprost i planuje, gdzie polecieć, żeby się dowiedzieć.

## 1. Zasady (obowiązują każdego agenta)

1. **Filtr dwóch zdań.** Budujesz tylko to, co widać w jednym z dwóch zdań. Wszystko inne: nie teraz.
2. **Efekt przed kompletnością.** Proof of concept na pokaz, nie wdrożenie. Prosty, czytelny model, który da się wytłumaczyć jednym zdaniem, wygrywa z dokładnym.
3. **Weryfikacja tylko niezbędna.** Jeden test dymny na pakiet i skrypt dowodu, który się uruchamia. Bez pokrycia testami, bez refaktoryzacji, bez abstrakcji na zapas.
4. **Uczciwość jest częścią designu.** Pogoda jest prawdziwa (IMGW-PIB), a grubość płyty i przeloty są syntetyczne i tak je podpisujemy na ekranie. Nigdzie nie piszemy „bezpiecznie”, „skalibrowane”, „miliony symulacji”. Liczba scenariuszy na ekranie to liczba faktycznie policzona.
5. **Tylko eskalacja.** Brak flagi nie oznacza braku zagrożenia: ten napis jest stale widoczny.
6. **Offline.** Demo działa bez sieci: zero CDN, biblioteki skopiowane do `web/vendor/`, dane w `web/data/`.
7. **Po polsku, krótko.** Cały tekst w interfejsie po polsku, zdania do 12 słów.
8. **Atrybucja.** Na ekranie i w README: „Teren: GUGiK NMT”, „Szlaki: © współtwórcy OpenStreetMap (ODbL)”.

## 2. Teren i dane (sprawdzone dziś o 22:50)

**Obszar:** Hala Gąsienicowa, Kasprowy Wierch, Kościelec, Świnica, Zawrat. Prostokąt w PL-1992 (EPSG:2180): easting 570 500–574 500, northing 149 500–153 500, czyli 4×4 km.

| Źródło | Jak pobrać | Uwagi |
| --- | --- | --- |
| **GUGiK NMT** (teren) | `https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModelFormatTIFF?service=WCS&version=2.0.1&request=GetCoverage&coverageId=DTM_PL-KRON86-NH_TIFF&format=image%2Ftiff&subset=y(149500,153500)&subset=x(570500,574500)&SCALESIZE=x(800),y(800)` | Działa: 800×800 co 5 m, nieskompresowany float32 GeoTIFF w paskach, maksimum 2300,8 m (Świnica). **Pułapka osi:** `y` to northing, `x` to easting (tak było w SkyWatch). Komórki `0.0` leżą poza Polską (Słowacja), więc traktuj je jako brak danych. Wysokości normalne Kronsztadt'86. Bez opłat, atrybucja wymagana. Jedno zapytanie ≤ 800×800. |
| **GUGiK ortofoto** (opcjonalne tło) | WMTS `https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMTS/StandardResolution`, warstwa `ORTOFOTOMAPA`, `image/jpeg`, macierze EPSG:2180/3857 | Tylko jeśli zostanie czas. Cieniowanie terenu z NMT wystarczy. |
| **Szlaki OSM** | Overpass `relation["route"="hiking"](49.215,19.965,49.255,20.025);out geom tags;` przez `https://overpass.kumi.systems/api/interpreter` z nagłówkiem `User-Agent` | Działa: 37 relacji z kolorem (`osmc:symbol`) i nazwą, np. „Hala Gąsienicowa – Liliowe”, „Czarny Staw Gąsienicowy – Kościelec”. `overpass-api.de` dał 406 i 504. Licencja ODbL. |
| **IMGW, Kasprowy Wierch** (opcjonalnie) | `https://danepubliczne.imgw.pl/api/data/synop/station/kasprowywierch` | Działa, ale tylko bieżący odczyt. Opcjonalny znaczek „stacja na żywo”, który offline pokazuje „brak łączności, ostatni odczyt X h temu”. |

Przeliczenie WGS84 na PL-1992 bez bibliotek: [`tools/pl1992.py`](../tools/pl1992.py) (Transverse Mercator, południk 19°, k0 0,9992, przesunięcie −5 300 000). Kasprowy Wierch wypada przy (571 441, 151 517).

**Narzędzia na tej maszynie:** Python 3.11 bez numpy (do skryptów w `tools/` wolno doinstalować `pip install numpy pillow`; demo i silnik ich nie potrzebują), Node 24, git. GeoTIFF z NMT da się odczytać bez bibliotek: paski float32, little-endian, bez kompresji (tag 259 = 1).

Surowe pliki trafiają do `data/raw/` (w `.gitignore`). Do repo idą tylko zbudowane, małe pliki w `web/data/` (razem ≤ 15 MB).

## 3. Model: prosty i do wytłumaczenia jednym zdaniem

| Element | Jak liczymy | Zdanie dla jury |
| --- | --- | --- |
| Sektory (strefy startowe) | Komórki o nachyleniu 28–55° powyżej 1500 m, połączone w spójne obszary ≥ 0,5 ha, łącznie 8–20 sektorów. Każdy dostaje ekspozycję (8 kierunków), pasmo wysokości i nazwę od najbliższego szczytu lub stawu. | „Strome stoki, z których może ruszyć lawina.” |
| Biblioteka scenariuszy | Dla każdego sektora kombinacje: grubość płyty (0,3–1,5 m), nowy śnieg, nawianie, kąt zasięgu α (rozkład wokół wartości skalibrowanej w pakiecie E, bez kalibracji 22–32°). Tor spływu wzdłuż najszybszego spadku, zatrzymanie, gdy linia energii od szczytu strefy spada poniżej α, a szerokość zależy od objętości. Zapis: czy i który odcinek szlaku trafia. Kilka tysięcy scenariuszy. | „Tysiące lawin policzonych z góry prostym modelem zasięgu.” |
| Stan dnia (syntetyczny) | Na sektor: wysokość śniegu, przyrost od poprzedniego przelotu, nawianie (zawietrzne ekspozycje więcej), niepewność σ. Przelot radarem zmniejsza σ na sektorach, nad którymi przeleciał. | „Dron mierzy, ile śniegu przybyło i gdzie.” |
| **Wie** | Porównanie dzisiejszego stanu sektora z jego scenariuszami. Flaga „może zagrozić szlakowi”, gdy wystarczająco wiele podobnych analogów dochodzi do szlaku. | „Dzisiejszy śnieg przypomina lawiny, które dochodzą do szlaku.” |
| **Wie, czego nie wie** | σ rośnie z godzinami od pomiaru i z opadem od pomiaru. Flaga „nie wiem”, gdy σ przekracza próg na sektorze, który może dotknąć szlaku. Brak danych nigdy nie wycisza flagi. | „Od przelotu spadło 40 cm, więc już nie wiemy.” |
| Kalibracja (pakiet E) | AvaFrame `com1DFA` liczy 10–20 uwolnień w 2–3 sektorach na tym samym terenie GUGiK. Dobieramy α i współczynnik szerokości prostego modelu tak, żeby zasięgi zgadzały się z AvaFrame (minimalny błąd długości zasięgu i IoU obrysu). | „Prosty model skalibrowany do fizycznego solvera AvaFrame, błąd zasięgu ±X m.” Nigdy: „skalibrowany na prawdziwych lawinach”. |
| **Plan przelotu** | Zachłannie: wartość = spadek σ² × waga szlaku, koszt = minuty lotu od bazy. Wybór w budżecie czasu i kolejność trasy metodą najbliższego sąsiada. | „Leć tam, gdzie najwięcej się dowiesz dla szlaków.” |

## 4. Kontrakt danych (pozwala pracować równolegle)

Wszystkie współrzędne w komórkach siatki analizy: `[col, row]`, gdzie `row = 0` to północ.

```text
web/data/terrain.json   { crs:"EPSG:2180", e0, n0, cell_m:10, width, height,
                          elevation:"terrain_f32.bin", hillshade:"hillshade.png",
                          attribution:"Teren: GUGiK NMT" }
web/data/terrain_f32.bin  Float32, row-major od północy, width×height
web/data/hillshade.png    cieniowanie (oraz opcjonalnie ortho.jpg)
web/data/sectors.json   [{ id:"S01", name:"Kościelec NE", aspect:"NE", band:"1900–2100 m",
                           polygon:[[c,r],…], centroid:[c,r], area_ha, flight_cost_min }]
web/data/trails.json    [{ id:"T03", name:"Murowaniec – Zawrat", color:"blue",
                           path:[[c,r],…], segments:[{ id:"T03-2", from:i, to:j }] }]
web/data/scenarios.json { count, model:"linia energii (kąt α)",
                          items:[{ id, sector, slab_m, new_cm, wind, alpha_deg,
                                   runout_m, hits:["T03-2",…], footprint:[[c,r],…] }] }
web/data/days.json      [{ id:"d1", label:"Dzień 1, 7:00", flight:{ flown:true, path:[[c,r],…] },
                           weather:{ new_cm, wind_dir, wind_ms, hours_since_flight },
                           sectors:{ S01:{ hs_m, dhs_m, wind, sigma_m, hours_since_measured } } }, …]
web/data/proof.json     { mornings:30, misses:{ avalauncher, baseline_3d },
                          uncertainty_drop:{ plan, fixed_route }, note:"dane syntetyczne" }
```

Silnik `web/engine.js` (czyste funkcje, ES module, działa w przeglądarce i w Node):

```text
assess(day, sectors, scenarios, trails) → [{ sector, kind:"zagrozenie"|"nie_wiem",
                                            reason, analogs, analogs_hitting, trails:[names] }]
planFlight(day, sectors, flags, budget_min) → { route:[sector ids], path:[[c,r],…], minutes, sigma_drop }
```

## 5. Pakiety pracy i właściciele

Każdy agent pracuje tylko w swoich katalogach i robi małe commity na `main` (`git pull --rebase` przed pushem).

| Pakiet | Właściciel katalogów | Wynik | Gotowe, gdy | Czas |
| --- | --- | --- | --- | --- |
| **A. Teren i szlaki** | `tools/build_terrain.py`, `data/` | `terrain.json`, `terrain_f32.bin`, `hillshade.png`, `sectors.json`, `trails.json` | Plik PNG z cieniowaniem i nałożonymi sektorami i szlakami wygląda jak Tatry | 60 min |
| **B. Scenariusze, dni, silnik, dowód** | `tools/build_scenarios.py`, `web/engine.js`, `tools/proof.mjs` | `scenarios.json`, `days.json`, `proof.json`, silnik | Dzień 1 daje 2 flagi „zagrożenie”, dzień 2 daje ≥ 1 flagę „nie wiem” i plan przelotu; dowód się uruchamia | 120 min |
| **C. Ekran** | `web/index.html`, `web/app.js`, `web/style.css`, `web/vendor/` | Jeden ekran, opis w sekcji 6 | Dwa poranki przechodzą bez ręcznych poprawek, offline | 180 min |
| **E. AvaFrame i kalibracja** (DGX) | `tools/avaframe/`, `data/avaframe/` | `web/data/calibration.json`: `{ solver:"AvaFrame com1DFA <wersja>", runs:N, alpha_deg, width_factor, runout_error_m, iou, examples:[{ sector, footprint_avaframe, footprint_simple }] }` | Co najmniej 10 przebiegów i dopasowane α; ekran pokazuje obok siebie jeden obrys z AvaFrame i z prostego modelu | do 01:00, potem stop |
| **D. Repo i zgłoszenie** | `README.md`, `LICENSE`, `docs/10_ai_i_licencje.md` | Instrukcja uruchomienia, licencja, ujawnienie użycia AI, atrybucje | Link do repo otwiera się w oknie incognito | 30 min |

**Pakiet E ma limit czasu.** AvaFrame liczy na CPU (GPU się nie przyda), DGX daje 20 rdzeni Arm na równoległe przebiegi. Najpierw sprawdzić `pip install avaframe` na aarch64; gdy kompilacja nie wyjdzie w 30 min, spróbować na tym laptopie (Windows, Python 3.11). Gdy do 01:00 nie ma ≥ 10 przebiegów, E odpada, a B zostaje przy α z literatury. Teren dla AvaFrame: ten sam wycinek NMT jako ASCII grid, obszary uwolnienia z `sectors.json` jako shapefile. AvaFrame to EUPL-1.2: cytujemy w README i w ujawnieniu zasobów.

**Zależności:** C startuje od razu na danych udawanych zgodnych z kontraktem (`web/data/mock/`). B potrzebuje sektorów i szlaków z A: do tego czasu pisze silnik na danych udawanych. Integracja o 01:30.

## 6. Ekran: jeden widok

- **Mapa (70% szerokości):** cieniowanie Tatr z NMT, szlaki w ich kolorach, sektory jako półprzezroczyste plamy. Kolory: czerwony to „może zagrozić szlakowi”, fiolet to „nie wiem”, szary to brak flagi. Po kliknięciu sektora pojawia się obwiednia zasięgu analogów i podświetlony odcinek szlaku. Ścieżka planowanego przelotu jako animowana przerywana linia. Widok 3D (three.js z `web/vendor/`) to cel P1, dopiero gdy 2D działa.
- **Panel (30%):** przełącznik **Dzień 1 / Dzień 2**, lista flag jako karty (jedna linijka powodu plus liczba analogów), suwak **czas lotu** (10–40 min), który na żywo przelicza plan, i licznik „N scenariuszy policzonych z góry”.
- **Stała stopka:** „Brak flagi ≠ bezpiecznie. Decyzję podejmuje prognosta.” · „Śnieg, przeloty i pogoda: dane syntetyczne.” · atrybucje.
- **Styl:** ciemny, spokojny, jedna czcionka, bez surowych logów i bez JSON-a na ekranie.

Przykładowe teksty kart:
- „**Kościelec NE, 1900–2100 m.** 45 cm nawiane od przelotu. 38 z 120 analogów dochodzi do szlaku Murowaniec – Zawrat.”
- „**Nie wiem: Świnica N.** Ostatni pomiar 26 h temu, od tego czasu 40 cm śniegu.”
- „**Plan przelotu, 20 min:** 3 sektory, niepewność nad szlakami −62%.”

## 7. Harmonogram

| Godzina | Co | Kto |
| --- | --- | --- |
| 23:00–00:00 | A: teren, sektory, szlaki. B i C na danych udawanych. D: licencja i ujawnienie AI. | A, B, C, D |
| 00:00–01:30 | B: scenariusze i dni na prawdziwych sektorach. C: mapa, karty, suwak. | B, C |
| 01:30–02:30 | Integracja, dowód, przejście dwóch poranków od początku do końca. **02:30: zamrożenie funkcji.** | wszyscy |
| 06:00–08:00 | Polerowanie, zrzuty ekranu, nagranie 90 s. | C, D |

## 8. Czego nie robimy

Kalibracji na prawdziwych zdarzeniach, SNOWPACK, RL, osuwisk, drugiego masywu, szkicu komunikatu, logowania, backendu, testów poza dymnymi. Kod w `src/avalauncher/` zostaje jako zaplecze badawcze: demo go nie używa.

## 9. Stan na 23:30 i polecenia startowe dla agentów

**Gotowe w sesji koordynującej:**
- Pakiet A: `tools/build_terrain.py` buduje z GUGiK NMT i OSM: `terrain.json`, `terrain_f32.bin` (400×400 co 10 m, 1314–2299 m), `hillshade.png` (5 m), `sectors.json` + `sectors_u8.bin` (72 strefy startowe, dzielone po ekspozycji), `trails.json` (32 szlaki, pole `paths` zamiast `path`, segmenty po ok. 300 m z polem `part`). Surowe pliki w `data/raw/`.
- Szkielet ekranu C: `web/index.html`, `style.css`, `app.js` (mapa canvas, flagi, suwak planu, pulsujące wyróżnienie flag, stacja IMGW Kasprowy Wierch na żywo z trybem offline). Podgląd: `.claude/launch.json` (`python -m http.server 8777 --directory web`).
- Silnik tymczasowy `web/engine.js` i dane udawane `tools/make_mock_days.py` → `web/data/mock/days.json` (`base` = Murowaniec, `exposure`, `days`). Ekran czyta `data/days.json`, a gdy go brak, dane udawane.
- Biblioteki: numpy, pillow, scipy, pyshp, **AvaFrame 2.1 (działa na tym laptopie, `com1DFA` się importuje)**. Uwaga: AvaFrame obniżył numpy do 1.26.4.

**Polecenia startowe** (każdy agent najpierw czyta `CLAUDE.md` i ten plik):

- **B, silnik i dowód:** „Zbuduj `tools/build_scenarios.py` (biblioteka scenariuszy linią energii po najszybszym spadku na `terrain_f32.bin` dla sektorów z `sectors.json`, trafienia w segmenty `trails.json`) oraz `days.json` z historią dwóch poranków z sekcji 6. Zastąp wnętrze `web/engine.js` porównaniem z analogami i starzeniem wiedzy, zachowując sygnatury `assess` i `planFlight` oraz pole `exposure` wyliczone ze scenariuszy. Plan przelotu ma priorytetowo brać sektory »nie wiem«. Napisz `tools/proof.mjs` (30 syntetycznych poranków, dwie miary) → `web/data/proof.json`. Gotowe, gdy dzień 1 daje 2 flagi zagrożenia, dzień 2 co najmniej jedną flagę »nie wiem«, a proof się uruchamia.”
- **C, ekran:** „Trzymaj się świata z `DESIGN.md` (Mapa tatrzańska). Dopracuj ekran w `web/` według sekcji 6: po kliknięciu sektora obwiednia zasięgu analogów i podświetlony segment szlaku, panel dowodu z `proof.json`, porównanie AvaFrame i prostego modelu z `calibration.json` (gdy plik istnieje), animacja przejścia między dniami. Potem P1: widok 3D z three.js w `web/vendor/`. Nie zmieniaj `engine.js`.”
- **D, repo:** „Dodaj `LICENSE` (MIT dla naszego kodu), `docs/10_ai_i_licencje.md` (użycie AI: Claude; zasoby: GUGiK NMT, OSM ODbL, IMGW, AvaFrame EUPL-1.2), sekcję uruchomienia demo w README i zrzuty ekranu w `docs/img/`.”
**Spark (DGX) gotowy dla pakietu E:** dostęp przez SSH w sieci Tailscale (szczegóły poza repo). Środowisko: osobny venv z AvaFrame 2.1, `com1DFA` działa (bez `fiona`; odczyt i zapis przez `pyogrio`). Maszyna współdzielona: najwyżej 12 procesów naraz, `nice -n 10`.

- **E, AvaFrame:** „W `tools/avaframe/` przygotuj projekt AvaFrame `com1DFA` na wycinku NMT (ASCII grid) z 2–3 sektorów (`sectors_u8.bin` → shapefile przez pyshp), puść 10–20 uwolnień (lokalnie albo na Sparku), dopasuj α i szerokość prostego modelu B do zasięgów AvaFrame i zapisz `web/data/calibration.json`. Limit: 01:00.”
