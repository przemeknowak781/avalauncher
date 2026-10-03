# Ruch lawiny, scenariusze i kalibracja

## Solver referencyjny

[AvaFrame `com1DFA`](https://docs.avaframe.org/en/stable/moduleCom1DFA.html) przyjmuje DEM, obszar uwolnienia, grubość startową i parametry przepływu, a zwraca m.in. pola przestrzenne ruchu i zasięgu. Jest otwartym, udokumentowanym punktem startowym do eksperymentów. [Artykuł metodyczny](https://doi.org/10.5194/gmd-16-7013-2023) opisuje równania, testy i ograniczenia. [AvaFrameData 1.0](https://doi.org/10.5281/zenodo.20701552) zawiera sześć przykładów rzeczywistych zdarzeń; po inspekcji archiwum co najmniej Arzl zawiera DEM, a nie każdy scenariusz ma kompletny DEM i dane pogodowe. Dane trzeba uzupełniać per zdarzenie. Opis daty Arzl w materiałach archiwum jest niespójny z metadanymi rekordu; przed użyciem etykiety zdarzenia zweryfikować z autorem.

[SNOWPACK](https://www.wsl.ch/en/services-produkte/snowpack/) zasila stan śniegu przed zdarzeniem; AvaFrame symuluje ruch po zadanym uwolnieniu. Oprzeć walidację na obserwowanych obrysach, osadach, zasięgu i — gdzie są — śladach radarowych czasu/położenia. [GEODAR](https://doi.org/10.5281/zenodo.1042108) udostępnia trajektorie i profile z 77 pełnowymiarowych lawin, a [EnviDat 77](https://doi.org/10.16904/envidat.77) i [235](https://doi.org/10.16904/envidat.235) obrysy lawin z obrazowania SPOT6. Nie zakładać, że te zbiory opisują ten sam stok i to samo zdarzenie — wymagają dopasowania przestrzeni i czasu.

## Kalibracja

Parametry tarcia, uwalniania i porywania śniegu stroić do odseparowanych zdarzeń, a następnie sprawdzać na held-out zdarzeniach. Symulator nie zastąpi brakującej informacji o miejscu/masie uwolnienia. W literaturze wykonano już kalibrację bayesowską r.avaflow na prawdziwym zdarzeniu ([Fischer i in. 2020](https://doi.org/10.3390/geosciences10050191)); ocena nowości wymaga porównania jakości i kosztu obliczeń z takimi metodami.

Proponowany rekord biblioteki: `{terrain_id, snow_state_id, release_polygon, slab_depth_distribution, rheology, runout_raster, deposition_raster, source_version, uncertainty}`. Indeks podobieństwa powinien porównywać **stan wejściowy** scenariusza z aktualnym stanem stoku, bez podglądu wyniku, który chcemy przewidzieć. Jeśli aktualny pomiar wykracza poza bibliotekę, uruchomić solver i oznaczyć brak pokrycia zamiast wymuszać niedopasowany scenariusz.

## MuJoCo

MuJoCo ma elementy deformowalne ([dokumentacja `flex`](https://mujoco.readthedocs.io/en/3.13.0/XMLreference.html)), więc stwierdzenie, że potrafi wyłącznie ciała sztywne, byłoby błędne. Tu nie ma jednak zweryfikowanego modelu lawiny śnieżnej z uwolnieniem płyty, erozją, porywaniem śniegu i skalą całej doliny w MuJoCo. Do modelu referencyjnego użyć AvaFrame; MuJoCo można badać później do osobnego prototypu interakcji lub uproszczonego świata RL.

