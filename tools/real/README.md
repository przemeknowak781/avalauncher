# Real data in Avalauncher: sources and licences

What on screen is real, and what is still a scenario.

| Layer | Source | Status | Licence / attribution |
|---|---|---|---|
| Terrain (slopes, release zones, AvaFrame DEM) | GUGiK NMT, 5 m grid resampled to 10 m (`data/raw/nmt_gasienicowa_5m.tif`) | real | GUGiK open data, free reuse (Prawo geodezyjne i kartograficzne art. 40a); "Teren: GUGiK NMT" |
| Orthophoto (3D render texture) | GUGiK orthophoto (`data/raw/ortho_*.jpg`) | real, summer image; the snow on it is synthetic | GUGiK open data; "Ortofoto: GUGiK" |
| Hiking trails | OpenStreetMap (`data/raw/osm_hiking.json`) | real | ODbL; "© współtwórcy OpenStreetMap" |
| Weather, winter 2024/25 | IMGW-PIB daily synop archive, station Kasprowy Wierch 349190650, 1987 m (`data/raw/kasprowy_2024.zip`, `kasprowy_2025.zip`) | real | IMGW-PIB public data, reuse allowed with source credit: "Źródło: IMGW-PIB" |
| Weather, live | IMGW-PIB API `danepubliczne.imgw.pl/api/data/synop/station/kasprowywierch` | real, live | as above |
| Avalanche library | AvaFrame com1DFA runs on the DGX Spark (`web/data/scenarios.json`, `scenario_cells.bin`, `library_heat.bin`) | computed from the real terrain | AvaFrame is EUPL-1.2 |
| Slab thickness on slopes, drone passes and readings | `tools/build_days.mjs` | synthetic | none |

## `build_kasprowy.py`

`python tools/real/build_kasprowy.py` reads the two IMGW zips (cp1250 CSV, no header; columns per
[`s_d_format.txt`](https://danepubliczne.imgw.pl/data/dane_pomiarowo_obserwacyjne/dane_meteorologiczne/dobowe/synop/s_d_format.txt))
and writes `web/data/kasprowy_2024_25.json`: one record per day from 1 Oct 2024 to 31 May 2025.

- `hs_cm` PKSN snow depth (morning 06 UTC reading), `new_cm` = positive day-to-day rise of PKSN,
  `swe_mm` = PKSN × RWSN (RWSN is water equivalent in mm per cm of snow, not a total),
  `precip_mm`/`precip_type` SMDB/ROOP, `snowfall_h` SNEG, `blowing_low_h`/`blowing_high_h` ZMNI/ZMWS,
  `wind10_h`/`wind15_h` FF10/FF15 (hours with wind ≥10 / >15 m/s), `tmin_c`/`tmax_c`/`tmean_c`.
- IMGW status "9" (phenomenon did not occur) becomes 0, status "8" (no measurement) becomes null.
  The winter has no missing rows or status-8 values in these fields.
- Episodes are the three largest non-overlapping 3-day sums of `new_cm` with blowing snow in the window.
  `demo_days` are the two demo mornings: the day before and the morning of the biggest snow rise of
  the top episode.

Storm episodes found:

| Window | New snow (3 days) | Blowing snow | Precipitation | Snow depth |
|---|---|---|---|---|
| 28–30 Nov 2024 | +29 cm | 40 h | 32.5 mm | 1 → 30 cm |
| 11–13 Jan 2025 | +34 cm | 72 h | 43.5 mm | 51 → 85 cm (demo days 12 and 13 Jan) |
| 6–8 Apr 2025 | +30 cm | 72 h | 39.1 mm | 65 → 95 cm |

## Known gaps

- There is no daily mean wind speed or direction for the 2024/25 winter. The `s_d_t` file in the 2024
  archive ends on 2024-06-30, and the 2025 archive (local and on the IMGW server) has no `s_d_t` file.
  FF10/FF15 hours stand in for wind. Only the live reading has wind direction.
- `new_cm` underestimates snowfall: settling and wind scouring at the summit offset some of the rise.
  Kasprowy Wierch is a wind-exposed dome, so gullies get more snow than the station records.
- The rise read on the morning of day D is mostly snow from precipitation day D−1 (IMGW precipitation
  days run 06–06 UTC). For example, 25.1 mm on 12 Jan was followed by +20 cm on the morning of 13 Jan.
