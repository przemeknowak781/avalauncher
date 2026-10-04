# Prawdziwe dane w demo

`python tools/real/build_kasprowy.py` czyta archiwum IMGW-PIB i zapisuje `web/data/kasprowy_2024_25.json`
(seria dobowa 1.10.2024–31.05.2025, epizody burzowe, poranki demo).

| Warstwa | Źródło | Status w demo | Licencja / atrybucja |
|---|---|---|---|
| Teren | GUGiK NMT (`data/raw/nmt_gasienicowa_5m.tif`, siatka 10 m w aplikacji) | prawdziwe | dane GUGiK udostępniane bezpłatnie (podstawę prawną do sprawdzenia przed publikacją); „Teren: GUGiK NMT” |
| Ortofoto | GUGiK ortofotomapa (`data/raw/ortho_*.jpg`) | prawdziwe, tylko w renderach 3D | jw.; „Ortofoto: GUGiK” |
| Szlaki | OpenStreetMap (`data/raw/osm_hiking.json`) | prawdziwe | ODbL; „© współtwórcy OpenStreetMap” |
| Pogoda, archiwum | IMGW-PIB, dane publiczne, dobowe synop `s_d`, stacja Kasprowy Wierch 349190650, 1987 m (`data/raw/kasprowy_2024.zip`, `kasprowy_2025.zip`) | prawdziwe | „Źródło: IMGW-PIB”; dane z danepubliczne.imgw.pl, wolno je przetwarzać z podaniem źródła; przetworzenie jest nasze, nie IMGW |
| Pogoda, na żywo | IMGW-PIB API `danepubliczne.imgw.pl/api/data/synop/station/kasprowywierch` | prawdziwe, poza scenariuszem demo | jw. |
| Biblioteka lawin | AvaFrame com1DFA 2.1 (EUPL-1.2) policzone na DGX Spark: `web/data/scenarios.json`, `scenario_cells.bin`, `library_heat.bin` | wynik symulacji na prawdziwym terenie | AvaFrame: EUPL-1.2 |
| Grubość płyty na stokach, przeloty drona | `web/data/days.json` | syntetyczne | podpisane na ekranie |

## Jak czytamy IMGW `s_d` (opis kolumn: `s_d_format.txt`)

- Pliki CSV bez nagłówka, kodowanie cp1250. Status `8` = brak pomiaru (zapisujemy `null`), status `9` = brak zjawiska (zapisujemy `0`).
- `hs_cm` = PKSN, poranny pomiar pokrywy (06 UTC). `new_cm` = dodatni przyrost PKSN względem poprzedniego ranka: przybliżenie świeżego śniegu, zaniżone przez osiadanie i wywiewanie.
- `swe_mm` = PKSN × RWSN (RWSN to mm wody na cm śniegu). `precip_mm` = SMDB z rodzajem ROOP (S śnieg, W deszcz); przyrost PKSN rano dnia D to głównie opad doby D−1.
- Zamieć: ZMNI (niska) i ZMWS (wysoka), godziny; `blowing_h` = większa z nich. Wiatr: FF10 i FF15, godziny z wiatrem ≥10 i >15 m/s.

## Luki, powiedziane wprost

- W serii październik–maj nie ma brakujących pomiarów PKSN, SNEG, ZMWS ani opadu.
- Brak średniej prędkości i kierunku wiatru dla zimy 2024/25: plik `s_d_t` w archiwum 2024 kończy się 30.06.2024, archiwum 2025 go nie ma (sprawdzone na serwerze IMGW 4.10.2026). Kierunek wiatru pokazujemy tylko z odczytu na żywo.
- Kasprowy Wierch to wywiewana kopuła szczytowa: pokrywa na stacji jest niższa niż w nawiewanych żlebach. Stacja mówi, kiedy padało i wiało, a nie ile śniegu leży na danym stoku. Tę lukę w demo wypełnia scenariusz syntetyczny płyty.

## Epizody burzowe (3 dni przyrostu PKSN z zamiecią, bez nakładania)

| Okno | Przyrost | Zamieć | Opad | Pokrywa |
|---|---|---|---|---|
| 28–30.11.2024 | +29 cm | 40 h | 32,5 mm | 1 → 30 cm |
| 11–13.01.2025 | +34 cm | 72 h | 43,5 mm | 51 → 85 cm |
| 6–8.04.2025 | +30 cm | 72 h | 39,1 mm | 65 → 95 cm |

Poranki demo (`demo_days`): 12.01.2025 (dzień 1, przelot wykonany) i 13.01.2025 (dzień 2: +20 cm w dobę, zamieć wysoka 24 h, przelot odwołany).
