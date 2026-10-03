# Oryginalność: stan techniki i hipotezy

**Werdykt (3.10.2026):** obecny pomysł jest sensowną hipotezą badawczą. Na podstawie przeglądu wskazanych prac nie można odpowiedzialnie twierdzić, że „pierwszy na świecie system RL do prognozowania lawin” lub „pierwszy cyfrowy bliźniak lawin”. Pełne badanie nowości wymaga jeszcze systematycznego przeglądu literatury i baz patentowych; ten handoff nie jest opinią patentową.

Dokładne lokalizacje krótkich cytatów z treści dziewięciu prac i operacyjny przykład znajdują się w [handoffie cyfrowego bliźniaka](08_cyfrowy_blizniak_use_case.md). Poniższe punkty są syntezą tych źródeł, nie cytatami z samych abstraktów.

| Twierdzenie | Znany precedens | Konsekwencja |
| --- | --- | --- |
| Prognoza naturalnych suchych lawin z modelu śniegu i ML | Mayer i in., NHESS 2023: dane SNOWPACK, model niestabilności, prognoza dnia lawinowego i rozmiaru | Sama prognoza na pogodzie i śniegu nie jest nowa. |
| RL łączący symulator fizyczny i zastępczy model neuronowy | HyPER, ICLR 2025: decyzje, kiedy uruchamiać dokładny solver | Sam schemat RL + fizyka nie jest nowy; nie jest to demonstracja domenowa dla lawin. |
| Kalibracja symulacji realną lawiną | Fischer i in., *Geosciences* 2020: kalibracja z użyciem wnioskowania bayesowskiego | Sama kalibracja parametrów nie wystarczy do tezy o nowości. |
| LiDAR + symulacja zasięgu | Dillon i Hammonds, preprint 2021; Ainer-Sharp i in., ISSW 2024: mapy głębokości LiDAR + RAMMS do oceny maksymalnego zasięgu | „Jedno skanowanie i porównanie scenariuszy” ma bliskie odpowiedniki. |
| Pomiar głębokości z platformy powietrznej | Kolpuke i in., IEEE TGRS 2024: radar mapujący powierzchnię i spód śniegu | Radarowe oszacowanie głębokości również ma precedens. |

**Najmocniejsza hipoteza do przetestowania:** cyklicznie aktualizowany, probabilistyczny stan stoku powstaje z pojedynczego oblotu LiDAR + radar wybranych transektów + lokalnych ograniczeń z rozpoznawalnych skał i drzew + poprzedniej prognozy śniegu. System odnajduje i ewentualnie dosymulowuje scenariusze o podobnym stanie wejściowym, raportując rozkład prawdopodobnych zasięgów i jawne obszary bez danych. Algorytm wybiera, gdzie następny pomiar lub droga symulacja najbardziej zmniejszy niepewność. **Oryginalność może tkwić w całym protokole asymilacji, doboru obliczeń, otwartym benchmarku i potwierdzonej poprawie na niewidzianych stokach.** To wniosek projektowy z przeglądu, nie zaobserwowany wynik.

Nie należy mylić podobieństwa mapy śniegu do scenariusza z prawdopodobieństwem, że lawina zejdzie. Do tej drugiej wielkości potrzebne są warunki obciążenia, warstwa słaba, historia pogody i etykiety zdarzeń; brak obserwacji lawiny nie zawsze znaczy, że jej nie było.

## Test nowości, który może tę hipotezę obalić

1. Poszukać osobno: „avalanche digital twin data assimilation”, „single flight snow depth radar lidar avalanche scenario retrieval”, „active sensing avalanche RL”, „uncertainty calibrated runout ensemble”. Przeszukać artykuły, materiały ISSW i patenty, z tabelą roszczeń zamiast ogólnego zapytania.
2. Zbudować trzy równie uczciwe punkty odniesienia: LiDAR + ręczne przedziały RAMMS/AvaFrame; fuzja pomiarów + losowy wybór symulacji; predyktor zagrożenia bez oblotu.
3. Wykazać oddzielnie poprawę pomiaru grubości, przewidywania uruchomienia, zasięgu i kalibracji prawdopodobieństw. Mierzyć transfer na inny stok i inną zimę.

## Źródła pierwotne

- Mayer i in. (2023), [Prediction of natural dry-snow avalanche activity](https://doi.org/10.5194/nhess-23-3445-2023), zwłaszcza opis danych i walidacji.
- Srikishan i in. (ICLR 2025), [HyPER](https://proceedings.iclr.cc/paper_files/paper/2025/hash/58575be50c9b47902359920a4d5d1ab4-Abstract-Conference.html), [kod](https://github.com/scailab/HyPER).
- Fischer i in. (2020), [Bayesian calibration of an avalanche model](https://doi.org/10.3390/geosciences10050191).
- Dillon i Hammonds (2021), [LiDAR initialized RAMMS, preprint](https://doi.org/10.5194/tc-2020-368).
- Ainer-Sharp i in. (ISSW 2024), [RPAS LiDAR + RAMMS](https://arc.lib.montana.edu/snow-science/item/3143).
- Kolpuke i in. (2024), [airborne snow radar](https://doi.org/10.1109/TGRS.2024.3359125).
