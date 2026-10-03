# Protokół badań i kryteria przejścia

## Etap 0 — audyt danych

Wybrać jeden stok i jedną klasę lawin. Sprawdzić, czy istnieją: DTM bez śniegu, zimowa obserwacja, historia pogody **oraz obserwowany** obrys/front/osad tych samych zdarzeń. Grand Mesa SnowEx umożliwia porównanie czujników, ale nie daje samoistnie zbioru lawin. Przypadki AvaFrame służą sprawdzeniu solvera; Dorfberg to głównie lawiny ślizgowe. Dla każdego zdarzenia ustalić UTC, strefę startową, układ poziomy/pionowy, wersję terenu, jakość meteorologii, licencję i cenzurowanie etykiet. Nie dzielić losowo pikseli jednej lawiny na trening i test.

## Etap 1 — pomiar i rekonstrukcja śniegu

Porównać (A) SNOWPACK/Alpine3D z pogodą, (B) LiDAR minus DTM, (C) B + kalibrowane tyczki/skały, (D) C + GPR. Walidować na odłożonych sondach, profilach i innej zimie. Miary: MAE/RMSE grubości w metrach, błąd w lesie i na stokach otwartych, pokrycie przedziału 90%, odsetek powierzchni z poprawnym wynikiem i koszt pomiaru. [Tyczki SnowEx20](https://nsidc.org/data/snex20_sd_tli/versions/1) są przydatne jako pomiar punktowy. Produkt SWE wyprowadzony z LiDAR i GPR nie może służyć jako całkowicie niezależny test tych samych danych wejściowych.

## Etap 2 — uruchomienie i zasięg

Baselines: stałe strefy potencjalnego uwolnienia + AvaFrame; model pokrywy z pogodą; aktualizowany stan z pomiarów; parametry kalibrowane metodami bayesowskimi. Oceniać **osobno**: prawdopodobieństwo uwolnienia w zdefiniowanym oknie oraz zasięg *pod warunkiem uwolnienia*. Dla pierwszego: Brier/log-score, reliability, recall przy ustalonym dopuszczalnym false-alarm rate. Dla drugiego: IoU faktycznej depozycji, błąd długości zasięgu, czas przejścia frontu tam, gdzie są dane GEODAR, pokrycie przedziałów ensemble. Wynik symulowanego RAMMS nie jest terenowym ground truth. Raporty prowadzić oddzielnie dla suchych, mokrych i ślizgowych lawin.

Reanaliza ERA5 korzysta z informacji z późniejszego czasu. Historyczny replay prognozy musi używać tylko danych dostępnych *w chwili wydania* prognozy; ograniczenie podkreślają [Viallon-Galinier i in. 2023, dyskusja](https://doi.org/10.5194/tc-17-2245-2023). Podział walidacji po zimie i dolinie, a nie po pikselu, jest konieczny dla testu przenośności.

## Etap 3 — agent sekwencyjny

Stworzyć środowisko, w którym działanie to wykonalny następny transekt GPR, kadr, punkt kontrolny albo uruchomienie drogiej symulacji. Ten sam budżet dla polityki RL, losowego wyboru, regularnej siatki, zachłannej redukcji wariancji i oczekiwanej wartości informacji. Wynik na odłożonych sezonach/lokalizacjach, z kosztem lotu, opóźnieniem i niepewnością; ocenić także fałszywie uspokajające przypadki. Agent nie może zobaczyć późniejszego obrazu lub wyniku zdarzenia w stanie treningowym.

## Kryteria decyzji

- **Stop na etapie 0:** brak wiarygodnego połączenia obserwacji i etykiet konkretnego zdarzenia.
- **Stop na etapie 1:** dodatkowy czujnik nie poprawia niezależnego pomiaru po uwzględnieniu kosztu albo psuje kalibrację niepewności.
- **Stop na etapie 2:** przewaga znika w innej dolinie/zimie, model bywa niebezpiecznie zbyt pewny albo wymaga danych z przyszłości.
- **Stop dla RL:** prosta aktywna selekcja osiąga taki sam wynik przy tym samym budżecie.

Progi ilościowe ustalić z partnerem terenowym **przed** wglądem w wynik testu. Wynik badań nie jest dopuszczeniem systemu do samodzielnego ostrzegania w górach.
