# Wyniki nocy 3/4.10.2026: liczby do decku i README

Jedno źródło prawdy dla liczb. Każda liczba ma plik, z którego pochodzi. Stan na 4.10.2026, ok. 02:00.

## Kalibracja na prawdziwej lawinie

**Model AvaFrame skalibrowany na obserwowanym zdarzeniu trafia zasięg z IoU 0,73 i błędem długości zasięgu 20 m.** Źródło: [web/data/calibration.json](../web/data/calibration.json), plansza `filmy/kalibracja/porownanie.png`, skrypty `tools/calibration/`.

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

Zastrzeżenia: grubość odrywu nie była w danych, więc to założenie z siatki 0,6–1,6 m, a najlepszy wynik leży na jej dolnej krawędzi. samosAT to kalibracja dla suchego śniegu, tu użyta do lawiny mokrej. To przykładowa kalibracja na zdarzeniu z Austrii; dla Tatr potrzebne są lokalne obserwacje (TOPR).

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

Model: obciążenie nowym śniegiem z 3 dni i nawiewanie (godziny zamieci) → prawdopodobieństwo uwolnienia × udział analogów z biblioteki, które dochodzą do szlaku. Zastrzeżenia: IMGW nie podaje kierunku wiatru dla tej zimy, przyjęto W–SW i to decyduje, które stoki się zapalają; składnik mokrych lawin nie przekracza progu tej zimy; archiwum stopni zagrożenia TOPR nie jest dostępne, więc brak porównania. Heurystyka PoC, docelowo SNOWPACK.
