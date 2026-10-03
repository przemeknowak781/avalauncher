# Architektura, RL i DGX Spark

**Stan projektu: 3.10.2026.** Plan wdrożenia, bez obietnicy czasu treningu na sprzęcie, którego tu nie testowano.

## Trzy oddzielne wielkości

1. `HS(x,y,t)`: aktualna wysokość śniegu, maska braków, błędy pomiaru; dodatkowo rozkład warstw i gęstości z modelu.
2. `P(uwolnienie | dane, miejsce, horyzont, typ)`: ryzyko zejścia konkretnej klasy lawiny, wymagające etykiet zdarzeń i walidacji kalibracji.
3. `P(zasięg, wysokość przepływu, prędkość, ciśnienie | uwolnienie, dane)`: wynik warunkowych symulacji dynamiki.

Częstość zasięgu w sztucznie wylosowanych wariantach tarcia **nie** jest prawdopodobieństwem, że lawina w ogóle ruszy.

| Moduł | Wejścia → wyjścia | Narzędzie / kontrola |
| --- | --- | --- |
| Georejestracja | Letni DTM + zimowy LiDAR + punkty stałe → wspólna siatka, `HS`, maska i błąd | GDAL/PDAL albo równoważne; niezależne punkty kontrolne, jednostki i pionowy układ odniesienia. |
| Pomiary uzupełniające | Obraz skały/pnia/tyczki oraz profil GPR → lokalna głębokość ± błąd | Najpierw tyczki i pomierzone skały; osłonięty lub odkształcony pień odrzucić. |
| Stan pokrywy | Pogoda + historia + pomiary → profil i ensemble | [SNOWPACK](https://snowpack.slf.ch/)/[Alpine3D](https://alpine3d.slf.ch/); reanaliza i realna prognoza oceniane oddzielnie. |
| Asymilacja | Ensemble + obserwacje → zaktualizowane rozkłady `HS`, SWE i warstw | Najpierw filtr cząsteczkowy lub aktualizacja ensemble; nie testować na obserwacji, którą włączono do stanu. |
| Start i przepływ | Hipotezy strefy/miąższości → scenariusze zasięgu | [AvaScenarioModelChain](https://github.com/OpenNHM/AvaScenarioModelChain) jako baseline, [AvaFrame `com1DFA`](https://docs.avaframe.org/en/latest/moduleCom1DFA.html) jako solver, [r.avaflow](https://www.avaflow.org/) jako alternatywa. |
| Porównanie | Zarejestrowany pomiar i stany scenariuszy → ranking podobieństwa | Aktualne `src/avalauncher/`; wyłącznie syntetyczny przykład bez predykcji uwolnienia. |

W kodzie `SnowDepthSensor`, `SnowpackModel` i `FlowModel` są **interfejsami**, bez działających adapterów. Każde uruchomienie przyszłego solvera musi zapisać teren, strefę uwolnienia, parametry, wersję, czas i sumy plików. Podobieństwo aktualnej mapy do scenariusza oceniać na **stanach wejściowych**, bez korzystania z przyszłego wyniku jako cechy.

## MuJoCo i miejsce RL

[MuJoCo](https://mujoco.readthedocs.io/en/latest/XMLreference.html) ma obiekty odkształcalne (`flex`) i kontakty, lecz nie jest zwalidowanym modelem przepływu śniegu z erozją, porywaniem materiału i warstwową niestabilnością w skali doliny. Do referencyjnego przepływu wybrać AvaFrame. MuJoCo może kiedyś opisywać drona, robota pomiarowego albo uproszczone środowisko polityki sensorów, po osobnej walidacji.

RL ma sens jako **decyzja sekwencyjna**: gdzie skierować następny pomiar, kiedy uruchomić kosztowny solver, kiedy powstrzymać się od oceny. Stan: rozkład niepewności i maska widoczności; akcje: dostępne transekty/kadry/obliczenia; koszt: czas lotu, pogoda, energia, opóźnienie. Nagroda ma odzwierciedlać poprawę na niewidzianych zdarzeniach przy tym samym budżecie, z osobną karą za fałszywe uspokojenie. Dla jednorazowej kalibracji parametrów prostsze metody bayesowskie i ensemble są obowiązkowym punktem odniesienia, nie dodatkiem ([Fischer i in. 2020](https://doi.org/10.3390/geosciences10050191); [Zhao i Kowalski 2022](https://doi.org/10.1007/s10346-022-01857-z)).

## DGX Spark — realistyczny podział pracy

[NVIDIA podaje](https://www.nvidia.com/en-us/products/workstations/dgx-spark/): GB10 Grace Blackwell, 20-rdzeniowy Arm, 128 GB wspólnej pamięci LPDDR5x, 273 GB/s i 4 TB NVMe. „Do 1 PFLOP” oznacza wydajność tensorową **FP4**, a nie solver lawiny w FP32. [Przewodnik portowania](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/overview.html) podaje środowisko Arm64; [tabela zależności](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/porting/dependencies.html) wskazuje CUDA Toolkit 13.0 i w wydaniu z kwietnia 2026 oznacza cuCIM jako niewspierany — przed instalacją sprawdzić bieżące wersje.

| Praca | Rozmieszczenie na Spark | Najpierw sprawdzić |
| --- | --- | --- |
| DEM, GDAL/PDAL, resampling | CPU i zapis kafelkami | Dostępność binariów Arm64, czas I/O. |
| SNOWPACK, Alpine3D, AvaFrame/Cython | Osobne procesy natywne CPU | Kompilacja `aarch64`, wyniki testów wzorcowych, czas jednego scenariusza. GPU nie przyspieszy ich automatycznie. |
| Enkoder obrazów, surrogate, ewentualna polityka RL | GPU w zgodnym kontenerze PyTorch | Pamięć, widoczność CUDA, powtarzalność, jakość na danych odłożonych. |
| Wielkie serie symulacji | Lokalnie po benchmarku lub zewnętrzne HPC | Czas solvera, RAM i koszt; nie wywodzić go z liczby FLOP FP4. |

Dla skali: jedna siatka 1024×1024 z sześcioma warstwami `float32` zajmuje **24 MiB surowych tablic**, bez masek, gradientów i aktywacji. Zacząć od kafli 512×512 z zakładką, preobliczonej biblioteki scenariuszy, małego enkodera oraz batch 1/4/16; potem profilować rzeczywiste maksimum wspólnej pamięci i przepustowość. Zapis każdego przebiegu: commit, hash danych, wersje sterownika/CUDA/kontenera, podział zbioru, seed, czas i pamięć. [Instrukcja kompilacji NVIDIA](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/porting/compilation.html) pokazuje ustawienie architektury `121-real`; kompatybilność wersji i wszystkich zależności trzeba zweryfikować na urządzeniu.
