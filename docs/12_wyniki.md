# Wyniki nocy 3/4.10.2026: liczby do decku i README

Jedno źródło prawdy dla liczb. Każda liczba ma plik, z którego pochodzi. Stan na 4.10.2026, ok. 02:00.

## Kalibracja na prawdziwych lawinach

**Na 5 prawdziwych lawinach z Austrii i Szwajcarii (234 symulacje AvaFrame) jedno wspólne ustawienie, niezmieniona kalibracja samosAT z odrywem 1,2 m, myli długość zasięgu średnio o 94 m. W teście leave-one-out (ustawienie wybrane bez danego zdarzenia) średni błąd to 154 m, mediana 92 m. Najlepsze dopasowanie pojedynczego zdarzenia: Kleiner Ötscherbach, IoU 0,83, zasięg 50 m za krótki.** Źródło: [web/data/calibration.json](../web/data/calibration.json) (klucze `events`, `loo`, `summary`), `data/avaframe/calib_results.csv` (234 wiersze), plansza `filmy/kalibracja/5_lawin.png`, skrypty `tools/calibration/run_multi.py`, `score_multi.py`, `loo_calib.py`, `board_multi.py`.

Wszystkie dane zdarzeń: OpenNHM/AvaFrameData 1.0, DOI [10.5281/zenodo.20701552](https://doi.org/10.5281/zenodo.20701552), CC-BY-4.0. Model: AvaFrame com1DFA 2.1, siatka 5 m, bez lasu i porywania śniegu, 43 przebiegi na zdarzenie (samosATSmall / samosATMedium / samosAT × odryw 0,4–2,0 m co 0,2 m oraz Voellmy μ 0,15–0,45 × ξ 1000–8000 przy 1,2 m), na Eiskar dodatkowo 19 przebiegów przy zmierzonych 2,7 m. 0 nieudanych, 0 zatrzymanych na limicie czasu.

| Zdarzenie | Gdzie, kiedy | Lawina / obserwacja | Teren | Odryw | Najlepszy przebieg | Zasięg | IoU / osad | Test bez zdarzenia: ustawienie | Zasięg | IoU / osad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Popeletzbach | Tyrol Wschodni, Austria, 7.04.2009 | mokra; obszar lawiny i osad | Land Tirol 5 m, CC BY 4.0 AT | nieznany | Voellmy μ 0,35, ξ 8000, 1,2 m | +15 m | IoU 0,730 | samosAT, 1,2 m | +25 m | IoU 0,70 |
| Kleiner Ötscherbach | Dolna Austria, 25.02.2009 | sucha płynąca; obszar lawiny | BEV ALS DTM 1 m (2025), CC BY 4.0 | nieznany | Voellmy μ 0,25, ξ 4000, 1,2 m | −50 m | IoU 0,831 | Voellmy μ 0,15, ξ 1000, 1,2 m | +350 m | IoU 0,70 |
| Eiskar | Ramsau am Dachstein, Styria, Austria, 15.01.2019 | sucha z chmurą pyłową, silne porywanie; tylko osad części płynącej | BEV ALS DTM 1 m (2024), CC BY 4.0 | **zmierzony 2,7 m** (skan z drona) | Voellmy μ 0,15, ξ 2000, 2,7 m | −13 m | osad 64% | samosAT, 2,7 m | −227 m | osad 45% |
| Filisur 1 | Gryzonia, Szwajcaria, 23.02.2012 | mokra, zatrzymana przez las; tylko osad | swisstopo swissALTI3D 2 m (2019) | nieznany | samosATSmall (μ 0,22), 0,4 m | +40 m | osad 94% | samosAT, 1,2 m | +77 m | osad 94% |
| Filisur 2 | Gryzonia, Szwajcaria, 23.02.2012 | mokra, zatrzymana na skraju lasu; tylko osad | swisstopo swissALTI3D 2 m (2019) | nieznany | Voellmy μ 0,45, ξ 1000, 1,2 m | +67 m | osad 79% | samosAT, 1,2 m | +92 m | osad 50% |

Jak wybrano „najlepszy przebieg”: dla zdarzeń z obszarem lawiny (Popeletzbach, Kleiner Ötscherbach) największe IoU; dla zdarzeń z samym osadem (Eiskar, Filisur) najmniejszy błąd zasięgu wśród przebiegów, które pokrywają co najmniej 50% osadu. IoU liczone z samym osadem jest niskie z założenia, więc tam miarą jest pokrycie osadu i zasięg. Zasięg = największa odległość pozioma od najwyższego punktu odrywu; plus znaczy za daleko. Na Popeletzbach Voellmy μ 0,35, ξ 8000 wyprzedza opublikowany samosAT 0,6 m tylko o 0,003 IoU, a ξ 8000 to krawędź siatki, więc cytujemy dalej opublikowany wynik (IoU 0,727, +20 m, niżej).

**Jedno ustawienie dla wszystkich 5 (w próbie):** samosAT (μ 0,155), odryw 1,2 m tam, gdzie grubość jest nieznana, 2,7 m na Eiskar. Błędy zasięgu: +25 m, −51 m, −227 m, +77 m, +92 m; średnio 94 m. Wybrane spośród 18 ustawień na tych samych zdarzeniach, więc to nie jest walidacja.

**Leave-one-out (walidacja):** dla każdego zdarzenia wybieramy jedno ustawienie tarcia, które ma najmniejszy średni błąd zasięgu na pozostałych czterech, i stosujemy je bez zmian do pominiętego. Grubość odrywu z reguły, nie dopasowana: 1,2 m (środek siatki) tam, gdzie jest nieznana, zmierzone 2,7 m na Eiskar. Kandydatów 18 (Voellmy μ 0,15, ξ 8000 odpada, bo na Kleiner Ötscherbach dotknął brzegu obszaru). Wynik: **średni błąd zasięgu 154 m, mediana 92 m**; w 4 z 5 prób wybór to ta sama kalibracja samosAT. Największy błąd, +350 m na Kleiner Ötscherbach: bez niego wygrywa Voellmy μ 0,15, ξ 1000, bo Eiskar przy zmierzonej grubości wymaga małego tarcia (porywanie śniegu nie jest modelowane), a na Kleiner Ötscherbach to tarcie przestrzeliwuje. Warianty: grubość wybierana razem z tarciem na czterech zdarzeniach daje 160 m (mediana 102 m); grubość dopasowana do każdego zdarzenia, także pominiętego (optymistycznie, test podgląda wynik), daje 144 m.

Zastrzeżenia: grubość odrywu zmierzono tylko na Eiskar; dla pozostałych 4 zdarzeń jest nieznana i w „najlepszym przebiegu” dobrana z siatki. 4 z 5 najlepszych przebiegów leży na krawędzi siatki (Popeletzbach ξ 8000, Eiskar μ 0,15, Filisur 1 odryw 0,4 m, Filisur 2 μ 0,45 i ξ 1000); tylko Kleiner Ötscherbach ma optimum wewnątrz. Na Filisur 1 i 2 każdy z 43 przebiegów przestrzeliwuje (o +40 do +205 m i +67 do +191 m), bo lawiny zatrzymał las, a przebiegi są bez lasu: dla tych zdarzeń nie ma kalibracji tarcia. Na Eiskar rodzina samosAT staje 227–572 m za krótko, a względem obrysu Max (część płynąca + pył) najlepszy przebieg jest 386 m za krótki. Teren jest nowszy niż każde zdarzenie. samosAT to kalibracja dla suchego śniegu, tu użyta też do lawin mokrych. Licencję swisstopo dla terenu Filisur trzeba potwierdzić przed pokazem. To przykładowa kalibracja na zdarzeniach z Austrii i Szwajcarii; dla Tatr potrzebne są lokalne obserwacje (TOPR).

### Popeletzbach: opublikowany wynik (bez zmian)

**Model AvaFrame skalibrowany na obserwowanym zdarzeniu trafia zasięg z IoU 0,73 i błędem długości zasięgu 20 m.** Źródło: [web/data/calibration.json](../web/data/calibration.json) (klucze `best`, `table`), plansza `filmy/kalibracja/porownanie.png`, skrypty `tools/calibration/`. W siatce 234 przebiegów ten sam przebieg (samosAT, 0,6 m) wychodzi identycznie: IoU 0,727, +20 m.

| Co | Wartość |
| --- | --- |
| Zdarzenie | Popeletzbach (Tyrol Wschodni, Austria), lawina mokrego śniegu, 7.04.2009 |
| Dane zdarzenia | OpenNHM/AvaFrameData 1.0, DOI [10.5281/zenodo.20701552](https://doi.org/10.5281/zenodo.20701552), CC-BY-4.0; strefa uwolnienia, obserwowany obszar lawiny i obrys osadu (zebrał Frank Perzl, BFW) |
| Teren | Land Tirol, model terenu 5 m (WCS gis.tirol.gv.at), CC BY 4.0 AT; teren współczesny, zdarzenie z 2009 r. |
| Model | AvaFrame com1DFA 2.1, siatka 5 m, bez lasu i porywania śniegu |
| Liczba przebiegów | 21 (kalibracje tarcia samosAT / samosATMedium / samosATSmall / Voellmy × grubość odrywu 0,6–1,6 m) |
| Najlepszy | samosAT (μ 0,155), odryw 0,6 m |
| IoU zasięgu (przepływ > 0,1 m) | **0,727** (przy progu ciśnienia 1 kPa: 0,739) |
| Precyzja / czułość | 0,873 / 0,813 |
| Pokrycie obserwowanego osadu | 63% |
| Długość zasięgu: symulacja / obserwacja | 1795 m / 1775 m, **błąd +20 m** |
| Drugie i trzecie miejsce | samosATMedium 0,6 m (IoU 0,724), Voellmy μ 0,35, ξ 4000, 1,1 m (IoU 0,718, błąd −20 m) |

Zastrzeżenia: grubość odrywu nie była w danych, więc to założenie z siatki 0,6–1,6 m, a najlepszy wynik leży na jej dolnej krawędzi. W szerszej siatce 0,4–2,0 m odryw 0,4 m daje IoU 0,720, więc dla samosAT 0,6 m nie jest już krawędzią. samosAT to kalibracja dla suchego śniegu, tu użyta do lawiny mokrej. To przykładowa kalibracja na zdarzeniu z Austrii; dla Tatr potrzebne są lokalne obserwacje (TOPR).

## Sieć zastępcza (surogat) AvaFrame

**Sieć przewiduje zasięg lawiny na stokach, których nie widziała, z IoU 0,81, ok. 4500× szybciej niż AvaFrame.** Źródło: [web/data/surrogate.json](../web/data/surrogate.json), `filmy/surrogate/metrics.json`, plansza `filmy/surrogate/porownanie.png`, film `filmy/surrogate/suwak.mp4`, skrypty `tools/surrogate/`.

| Co | Wartość |
| --- | --- |
| Model | U-Net, 6 poziomów (32–320 kanałów), 7,26 mln parametrów, wejście 256×256 komórek po 10 m, PyTorch bf16 |
| Dane treningowe | 1215 przebiegów AvaFrame z biblioteki, 45 stoków |
| Stoki testowe (poza treningiem) | S14 Mały Kościelec W, S22 Sucha Dolina NE, S31 Liliowe E; 81 przebiegów |
| Dodatkowo wyłączone | 10 stoków, których lawiny wchodzą na teren stoków testowych (S09, S49, S50, S53, S55, S56, S59, S64, S69, S71) |
| IoU zasięgu na stokach testowych | **0,805** średnio, mediana 0,834; S14 0,832, S22 0,719, S31 0,863 |
| IoU na danych treningowych | 0,915 |
| Czas: AvaFrame / surogat | 10,43 s na symulację (1 rdzeń CPU, mediana z 174 logów) / **2,3 ms** na mapę (GPU GB10) |
| Przyspieszenie | ok. 4500× |
| Trening | 11 min (666 s), 3000 kroków, batch 32, GPU DGX Spark |

Zastrzeżenie: dowód koncepcji. Surogat przybliża mapę maksymalnej grubości przepływu, nie zastępuje AvaFrame.

## Biblioteka scenariuszy (fizyka)

**1566 symulacji AvaFrame w 30,4 min na 12 rdzeniach DGX Spark.** Źródło: [web/data/scenarios.json](../web/data/scenarios.json), skrypty `tools/avaframe/library/`.

- 58 stref startowych × 9 grubości płyty (0,4–2,0 m co 0,2 m) × 3 kalibracje tarcia (samosATSmall, samosATMedium, samosAT); 0 nieudanych przebiegów.
- 48 z 58 stref dochodzi do szlaku (przepływ > 0,1 m); 47 już przy 0,4 m. Najdłuższy zasięg: Świnica NW, 2,0 m, 1868 m. Najgrubszy przepływ na szlaku: Kasprowy Wierch S, 2,0 m, 12,9 m.
- Kalibracja tarcia prawie nie zmienia trafień w szlak (82–83% przebiegów), wydłuża średni zasięg z 817 m (samosATSmall) do 912 m (samosAT).

## Dowód logiki silnika

**Na 30 prawdziwych porankach IMGW plan przelotu wyjaśnia więcej niewiadomych niż patrol wzdłuż szlaku: 86 wobec 71.** Źródło: [web/data/proof.json](../web/data/proof.json), skrypty `tools/proof.mjs`, `tools/synth.mjs`.

| Miara, przelot 20 min, 30 poranków | Plan Avalaunchera | Patrol wzdłuż szlaku |
| --- | --- | --- |
| Wyjaśnione sektory „nie wiem” | **86** | 71 |
| Zagrażające stoki oflagowane po przelocie | **29** | 16 |
| Spadek niepewności decyzji | **−23%** | −7% |

Wobec reguły „suma nowego śniegu z 3 dni ≥ 30 cm”: przeoczenia 0 wobec 121, fałszywe alarmy 0 wobec 25. Ceną jest 549 flag „nie wiem” (505 w poranki z odwołanym przelotem, 431 na stokach niezagrażających), a błąd modelu zmienia prawdę tylko w 44 przypadkach, więc 0/0 to słaby dowód. Pogoda: IMGW-PIB Kasprowy Wierch, 23.12.2024–21.01.2025 (kierunek wiatru założony). Grubość płyty, prawda i przeloty: dane syntetyczne, test logiki.

## Prawdziwa pogoda

Źródło: [web/data/kasprowy_2024_25.json](../web/data/kasprowy_2024_25.json) z dobowego archiwum IMGW-PIB, stacja Kasprowy Wierch (1987 m).

| Epizod | Nowy śnieg (3 dni) | Zamieć | Pokrywa przed → po |
| --- | --- | --- | --- |
| 28–30.11.2024 | +29 cm | 40 h | 1 → 30 cm |
| **11–13.01.2025** (poranki demo 12 i 13.01) | +34 cm | 72 h | 51 → 85 cm |
| 6–8.04.2025 | +30 cm | 72 h | 65 → 95 cm |

## Satelita w dniach zamieci (Sentinel-2)

**W dniach zamieci satelita nie widział naszego terenu: 11.01.2025 chmury nad 100% obszaru, 12.01 brak przelotu, 13.01 chmury nad 86%. Pierwszy czysty obraz jest z 16.01, trzy dni po epizodzie.** Źródło: [web/data/sentinel_snow.json](../web/data/sentinel_snow.json), plansza `filmy/satelita/porownanie.png`, skrypty `tools/satellite/`.

| Co | Wartość |
| --- | --- |
| Scena | S2A_34UDV_20250116, 16.01.2025, 09:56 UTC; Copernicus Sentinel-2 L2A (Element84 Earth Search, AWS Open Data) |
| Chmury nad obszarem 16.01 | 0,0% |
| Śnieg (NDSI > 0,4) | 98,7% komórek; 1300–1500 m 91,2%, 1500–1700 m 99,5%, powyżej 1700 m 100% |
| Sprawdzenie założonego wiatru W–SW | nie rozstrzyga: na grzbietach powyżej 1800 m odsłonięte najwyżej 0,8% komórek w 7 czystych scenach 16.01–25.02.2025 |

Zastrzeżenie: satelita pokazuje, gdzie leży śnieg, a nie jego grubość ani warstwy.

## Sprzęt: pomiary na naszych zadaniach

| Zadanie | Laptop i5-1245U | DGX Spark GB10 | Shadow RTX A4500 |
| --- | --- | --- | --- |
| 1 symulacja AvaFrame | 107 s | **6,7 s** | zawiesił się |
| 72 symulacje (10 procesów) | — | 129 s | — |
| Klatka renderu 3D | 15,6 s | **4,9 s** | — |
| Mnożenie macierzy fp16 | — | **94,5 TFLOPS** | 71,9 TFLOPS |
| Trening sieci 128² | — | 739 próbek/s | **1114 próbek/s** |

Decyzja: fizyka i rendery na CPU Sparka, trening surogatu na GPU Sparka (dane na miejscu, 128 GB pamięci wspólnej).

## RL dla planu przelotu

**Polityka RL dorównuje prostemu planowi według wartości informacji, ale go nie pokonuje, więc zgodnie z docs/07 zostajemy przy prostszym planerze.** Źródło: [web/data/rl.json](../web/data/rl.json), `filmy/rl/krzywa_uczenia.png`, `filmy/rl/trasy.png`, skrypty `tools/rl/`.

| 1000 poranków spoza treningu, przelot 20 min | RL | Plan VOI | Patrol wzdłuż szlaku |
| --- | --- | --- | --- |
| Spadek niepewności decyzji | 19,9% | **20,2%** | 5,4% |
| Wyjaśnione sektory „nie wiem” (z 33 059) | 3915 | **3987** | 2895 |
| Wychwycone zagrożenia (z 7924) | **1936** | 1810 | 1189 |

Trening: REINFORCE, 10,4 mln epizodów w 6 min na GPU DGX Spark. Środowisko woła prawdziwy silnik (różnica kontrolna 1e-13). Zastrzeżenie: prawda losowana z przekonania silnika (uczciwy test trasowania, ale nie świat z błędem modelu z dowodu powyżej), więc liczby nie są wprost porównywalne z 86 wobec 71.

## Kiedy schodzą: kalendarz uwolnień (heurystyka)

**Na prawdziwej zimie 2024/25 ryzyko zapala się w połowie stycznia i na początku kwietnia; 12.01 ryzyko ≥ 0,5 ma 9 sektorów, 13.01 już 12, wszystkie na stokach NE/E/N.** Źródło: [web/data/release_calendar.json](../web/data/release_calendar.json) (58 sektorów × 181 dni), `filmy/kiedy/kalendarz.png`, skrypty `tools/when/`.

Model: obciążenie nowym śniegiem z 3 dni i nawiewanie (godziny zamieci) → prawdopodobieństwo uwolnienia × udział analogów z biblioteki, które dochodzą do szlaku. Zastrzeżenia: IMGW nie podaje kierunku wiatru dla tej zimy, przyjęto W–SW i to decyduje, które stoki się zapalają; składnik mokrych lawin nie przekracza progu tej zimy; archiwum lawiny.topr.pl nie jest dostępne, porównanie z komunikatami cytowanymi w prasie poniżej. Heurystyka PoC, docelowo SNOWPACK.

## Porównanie z komunikatami TOPR (zima 2024/25)

**Oficjalny stopień rośnie 12–13.01.2025 (1 → 2 → 3, „najwyższy dotąd w sezonie”) w te same dni, w które kalendarz zapala 9, potem 12 sektorów; 15–16.03 i 6.04 TOPR ma „trójkę”, a kalendarz jest ciemny.** Źródło: [web/data/topr_compare.json](../web/data/topr_compare.json); stopnie z komunikatów TOPR cytowanych w prasie, kalendarz z `release_calendar.json` (próg 0,5).

| Data | Stopień TOPR | Kalendarz: sektory ≥ 0,5 (z 58) | Śnieg Kasprowy: komunikat / IMGW w kalendarzu | Źródło |
|---|---|---|---|---|
| 16.12.2024 | 2 | 0 | 25 / 23 cm | [radiomaryja.pl](https://www.radiomaryja.pl/informacje/tatry-drugi-stopien-zagrozenia-lawinowego/) |
| 04.01.2025 | 2 | 0 | 45 / 45 cm | [radiomaryja.pl](https://www.radiomaryja.pl/informacje/tatry-wzroslo-zagrozenie-lawinowe-do-drugiego-stopnia-duze-opady-sniegu/) |
| 12.01.2025 | 1 → 2 | 9 | 65 / 65 cm | [przedruk komunikatu TOPR/TPN (blog)](https://krolowasuperstarblog.wordpress.com/2025/01/12/wzroslo-zagrozenie-lawinowe-w-tatrach-karkonoszach-i-babiej-gorze/) |
| 13.01.2025 | 2 → 3 | 12 | 85 / 85 cm | [PAP przez opoka.org.pl](https://opoka.org.pl/News/Polska/2024/na-kasprowym-65-cm-sniegu-w-tatrach-wzrasta-zagrozenie-lawinowe), [misyjne.pl](https://misyjne.pl/tatry-trzeci-stopien-zagrozenia-lawinowego/) |
| 15.03.2025 | 3 | 0 | brak / 61 cm | [rmf24.pl](https://www.rmf24.pl/regiony/zakopane/news-niebezpiecznie-w-tatrach-topr-oglosil-trzeci-stopien-zagroze,nId,7931716) |
| 16.03.2025 | 3 | 0 | 65 / 65 cm | [PAP przez opoka.org.pl](https://opoka.org.pl/News/Polska/2025/tatry-trzeci-stopien-zagrozenia-lawinowego-trudne-warunki) |
| 27.03.2025 | 1 | 0 | 65 / 65 cm | [PAP przez opoka.org.pl](https://opoka.org.pl/News/Polska/2025/tatry-maleje-zagrozenie-lawinowe-ryzyko-lawin-na-stromych) |
| 06.04.2025 | 3 | 0 | 80 / 76 cm | [dziennik.pl](https://wiadomosci.dziennik.pl/wydarzenia/artykuly/9772183,zima-uderzyla-z-impetem-zagrozenie-lawinowe-w-tatrach.html) |
| 09.04.2025 | 3 → 2 | 8 | 92 / 92 cm | [rmf24.pl](https://www.rmf24.pl/regiony/zakopane/news-po-sniezycach-wyszlo-slonce-warunki-dla-narciarzy-w-tatrach-,nId,7946118) |

Co pasuje: wzrost 12–13.01 pokrywa się z kalendarzem dzień w dzień; 27.03 TOPR obniża do 1, kalendarz ciemny. Co nie pasuje: 10–11.01 kalendarz ma już po 8 sektorów, gdy TOPR był jeszcze na 1 (wyprzedzenie albo fałszywy alarm, nie rozstrzygamy); 15–16.03 TOPR 3, kalendarz 0 (pominięcie; nawiewanie tylko ok. 12 h w 3 doby, a heurystyka mocno waży transport wiatrem przy założonym W–SW); 6.04 TOPR 3, kalendarz zapala się dopiero 7–9.04 (opóźnienie o dobę); 9.04 TOPR schodzi na 2, kalendarz nadal 8; 16.12 i 4.01 TOPR 2, kalendarz 0. Brak stopnia w zebranych źródłach dla 26.11–3.12.2024 i 1–3.04.2025 (kalendarz zapala tam 8–9 sektorów). Archiwum lawiny.topr.pl i Wayback Machine były niedostępne. W prasie nie znaleźliśmy lawin z tej zimy w naszym wycinku mapy.

Zastrzeżenie: stopień TOPR to jedna ocena w skali 1–5 dla całych polskich Tatr, a kalendarz liczy lokalne sektory z ryzykiem ≥ 0,5, więc przy „trójce” jedno trafienie (13.01), jedno pominięcie (15–16.03) i jedno opóźnienie o dobę (6.04) to test zdrowego rozsądku, nie dowód trafności prognozy; grubość śniegu na Kasprowym w komunikatach pochodzi z tej samej stacji IMGW, którą czyta kalendarz, więc jej zgodność potwierdza tylko, że demo liczy na liczbach prawdziwej zimy.
