# Pokrywa śnieżna i prognoza uruchomienia

## Co modelować

Stan wejściowy: ukształtowanie terenu bez śniegu, historia temperatury/opadów/wiatru/promieniowania, oszacowanie rozkładu wysokości śniegu i jego niepewności, warstwy oraz ich właściwości, ekspozycja stoku i warunki wyzwolenia. **Wysokość pokrywy nie jest równa niestabilności**: jednakowa głębokość może ukrywać różne warstwy słabe i różną wytrzymałość. Oddzielić lawiny suche, mokre i ślizgowe; zestaw Seewer Berg jest szczególnie związany z ostatnią klasą.

SNOWPACK odtwarza pionowy profil śniegu z danych meteorologicznych; Alpine3D dodaje przestrzenną fizykę śniegu. Dla prototypu model 1D na reprezentatywnych ekspozycjach jest osiągalny; przestrzenna interpolacja i transport wiatrem w strefach startowych są osobnym źródłem błędu. ERA5-Land jest przydatne jako tło meteorologiczne, ale siatka około 9 km nie rozstrzyga warunków pojedynczego żlebu. Bez lokalnych stacji, prognozy mezoskalowej i danych terenowych rozdzielczość mapy wyniku nie zwiększy rozdzielczości wiedzy.

## Interfejs do kolejnego modułu

Każdy scenariusz startowy powinien zawierać geometrię obszaru uwolnienia, grubość potencjalnie odrywającej się płyty (nie całą wysokość pokrywy), wariant prawdopodobieństwa uruchomienia oraz czas i typ lawiny. Brak wiarygodnego modelu uruchomienia oznacza wyłącznie warunkowe zdanie „jeśli ta porcja śniegu się uwolni, możliwy jest taki zasięg”.

## Dane i kontrola

- [EnviDat 425](https://doi.org/10.16904/envidat.425): dane do modeli dnia lawinowego i rozmiaru z symulacji pokrywy; cztery pobrane CSV. To świetny punkt odniesienia dla klasyfikacji, lecz obserwacje są przypisane do otoczenia stacji, nie stanowią mapy każdego żlebu.
- [EnviDat 222](https://doi.org/10.16904/envidat.222): obserwacje niestabilności i testy terenowe; pomagają ocenić model warstwy słabej.
- [EnviDat 583](https://doi.org/10.16904/envidat.583): pomiary glebowe i śniegowe, aktywność lawin ślizgowych, symulacje śniegu, geometria zdarzeń. Nie mieszać tych etykiet z suchymi lawinami płytowymi w jednej regresji bez oznaczenia typu.

## Test minimalny

Podział trening/walidacja po **zimie i lokalizacji**, z kontrolą niezależności stacji i zdarzenia; porównać z prostą sumą nowego śniegu z 3 dni, z modelem SNOWPACK i klasyfikatorem bez LiDAR. Raportować Brier score, kalibrację, precision–recall przy rzadkich zdarzeniach i odsetek niepewnych/nieoznaczonych dni. W artykule Mayer i in. prosty wskaźnik oparty o 3-dniowy przyrost śniegu był silnym punktem odniesienia, więc złożony model musi wykazać realną przewagę na próbie zewnętrznej.

Źródła: [SNOWPACK (WSL)](https://www.wsl.ch/en/services-produkte/snowpack/), [Alpine3D](https://alpine3d.slf.ch/), [Mayer i in., NHESS 2023](https://doi.org/10.5194/nhess-23-3445-2023), [ERA5-Land (Copernicus)](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land).

