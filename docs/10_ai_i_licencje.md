# Użycie AI, zasoby zewnętrzne i licencje

Regulamin zadania Defence wymaga ujawnienia istotnego użycia AI i cytowania zasobów zewnętrznych z licencjami. Ten plik to pełna lista. Stan na 4.10.2026.

## 1. Użycie AI

**Narzędzie:** Claude Code (Anthropic), model Claude Opus 5.5 (`claude-opus-5-5`).

Użycie było istotne. Większość kodu, tekstów i wizualizacji napisał Claude na polecenie zespołu. W nocy 3/4.10 pracowało równolegle kilka agentów Claude Code, każdy we własnych katalogach.

| Obszar | Co robił Claude | Gdzie w repo |
| --- | --- | --- |
| Research | Przegląd literatury, precedensów i źródeł danych, szkice raportów | `docs/01`–`docs/08`, `catalog/datasets.json` |
| Strategia zgłoszenia | Analiza regulaminu i kryteriów oceny | notatki zespołu (poza repo) |
| Kod | Pobieranie i przetwarzanie terenu, pogody IMGW i szlaków, sektory, silnik flag i planu przelotu, dowód, ekran demo, skrypty AvaFrame, kalibracja na lawinie Popeletzbach, benchmarki, sieć-surogat, eksperyment RL | `tools/`, `web/`, `src/`, `.github/` |
| Wizualizacje | Skrypty renderujące mapy, filmy 2D i 3D z wyników AvaFrame, plansze surogatu i kalibracji | `tools/avaframe/`, `tools/visuals/`, `tools/surrogate/`, `tools/calibration/`, `web/media/`, `filmy/` (poza Git) |
| Dokumentacja | README, plan budowy, deck, skrypt pitchu, ten plik | `README.md`, `docs/09`–`docs/11` |

**Co zdecydowali ludzie:**

- wybór problemu, zakres i teza w dwóch zdaniach;
- persona, scenariusz demo (dwa poranki) i to, co wycinamy;
- wybór świata wizualnego ekranu (`DESIGN.md`);
- przegląd wyników i decyzja, co trafia do zgłoszenia.

**Odpowiedzialność.** Za treść zgłoszenia odpowiada zespół. Liczby w README i w deku pochodzą z plików wynikowych w repo (`web/data/*.json`) albo z pomiarów opisanych w README. Nie dopisywaliśmy liczb z pamięci modelu.

**Dane osobowe.** Nie przekazywaliśmy modelowi danych osobowych osób trzecich. Repo nie zawiera danych osobowych.

## 2. Dane

| Zasób | Do czego | Licencja i warunki | Atrybucja |
| --- | --- | --- | --- |
| **GUGiK, Numeryczny Model Terenu** (NMT, siatka 5 m, WCS) | Teren 4×4 km, przeskalowany do 10 m; nachylenie, ekspozycja, strefy startowe; wejście dla AvaFrame | Dane z państwowego zasobu geodezyjnego udostępniane bez opłat; wymagane podanie źródła | „Teren: GUGiK NMT” (na ekranie i w README) |
| **GUGiK, ortofotomapa** (1 m, WMTS) | Tekstura terenu w filmach 3D; śnieg na niej jest syntetyczny | Bez opłat; wymagane podanie źródła | „Ortofotomapa: GUGiK” (w filmach i w deku) |
| **OpenStreetMap** (Overpass API) | 32 szlaki turystyczne z nazwami i kolorami | ODbL 1.0. Plik `web/data/trails.json` to baza pochodna z OSM i udostępniamy go na ODbL 1.0 | „Szlaki: © współtwórcy OpenStreetMap” (na ekranie), openstreetmap.org/copyright |
| **IMGW-PIB, dane publiczne: archiwum dobowych danych synoptycznych** (stacja Kasprowy Wierch, 1.10.2024–31.05.2025) | Prawdziwa pogoda dwóch poranków demo (12–13.01.2025) i 30 poranków dowodu (23.12.2024–21.01.2025); `web/data/kasprowy_2024_25.json` | Dane publiczne IMGW-PIB; wymagane podanie źródła i informacja o przetworzeniu | „Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy. Dane zostały przetworzone.” |
| **IMGW-PIB, dane publiczne: API synop** (odczyt na żywo, Kasprowy Wierch) | Znaczek „stacja na żywo” na ekranie. Nie wpływa na scenariusz demo | Jak wyżej | Jak wyżej |
| **OpenNHM / AvaFrameData 1.0**, zdarzenie avaPopeletzbach (obszar odrywu, obrys i depozyt lawiny z 7.04.2009; dane zebrał Frank Perzl, BFW) | Przykładowa kalibracja AvaFrame na prawdziwym zdarzeniu z Austrii (`web/data/calibration.json`) | CC BY 4.0, DOI 10.5281/zenodo.20701552 | Autorzy zbioru i DOI w `calibration.json`, w README i w deku |
| **Land Tirol, Geländemodell 5 m** (WCS gis.tirol.gv.at) | Teren dla symulacji Popeletzbach | CC BY 4.0 AT | „Teren: Land Tirol – data.tirol.gv.at” |
| **Wikimedia Commons, zdjęcie „Winter in Tatry Mountains - Poland”** (Radek Kucharski, Kasprowy Wierch, 15.01.2026; https://commons.wikimedia.org/wiki/File:Winter_in_Tatry_Mountains_-_Poland.jpg) | Tapeta pulpitu w aplikacji i w filmie (`web/media/tapeta/tatry_1920.jpg`, `tatry_1280.jpg`: przycięte i zmniejszone) | CC BY 4.0 | „Tapeta: Radek Kucharski, Wikimedia Commons, CC BY 4.0” (okno „O projekcie” w aplikacji) |

**Pogoda: IMGW-PIB (prawdziwe). Grubość płyty i przeloty: syntetyczne.** Szczegóły: stan śniegu na stokach (grubość płyty), przeloty i odczyty drona oraz błąd modelu w dowodzie są wygenerowane przez nasze skrypty. Kierunek wiatru jest założony, bo archiwum IMGW go nie zawiera dla zimy 2024/25. Tak to podpisujemy na ekranie, w README i w deku.

**Literatura.** Prace cytowane w `docs/01`–`docs/08` (m.in. Bühler i in. 2022, Mayer i in. 2023) podajemy z DOI. Ich danych nie dołączamy do repo.

**Wygląd interfejsu.** Interfejs aplikacji, ekran logowania, strona „O projekcie”, deck i komunikator w filmie są inspirowane stylem Windows XP (hołd dla estetyki z lat 2001–2006). Wszystko narysowaliśmy od zera w CSS i SVG: nie używamy grafik, ikon, czcionek, dźwięków ani logotypów Microsoftu. Windows i Windows XP są znakami towarowymi Microsoft Corporation. Projekt nie jest powiązany z firmą Microsoft ani przez nią wspierany.

## 3. Oprogramowanie

| Zasób | Do czego | Licencja |
| --- | --- | --- |
| **AvaFrame 2.1**, moduł `com1DFA` (avaframe.org) | Symulacje gęstego przepływu lawiny na terenie GUGiK; biblioteka scenariuszy; dane do uczenia surogatu | EUPL-1.2. Używamy go bez zmian jako biblioteki. Nasz kod w `tools/avaframe/` tylko go wywołuje |
| numpy, scipy | Obliczenia na siatkach, morfologia sektorów | BSD-3-Clause |
| matplotlib | Renderingi map i filmów | Licencja Matplotlib (oparta na PSF, zgodna z BSD) |
| Pillow | Obrazy, cieniowanie, tekstury | MIT-CMU (HPND) |
| pyshp | Zapis stref uwolnienia jako shapefile dla AvaFrame | MIT |
| shapely | Geometria obszarów uwolnienia | BSD-3-Clause |
| pyogrio | Odczyt i zapis danych wektorowych w AvaFrame | MIT |
| pandas | Przetwarzanie archiwum IMGW | BSD-3-Clause |
| rasterio (z GDAL) | Odczyt terenu Land Tirol i rasteryzacja obrysów lawiny Popeletzbach | BSD-3-Clause (GDAL: MIT) |
| PyTorch | Benchmark GPU, sieć-surogat U-Net i jej eksport do ONNX | BSD-3-Clause |
| imageio-ffmpeg | Wywołanie ffmpeg z Pythona | BSD-2-Clause |
| ffmpeg | Kodowanie filmów MP4 | LGPL-2.1+ (niektóre kompilacje GPL). Narzędzie, nie jest dołączone do repo |
| Python 3.11, Node.js | Środowisko uruchomieniowe skryptów | PSF License, MIT |
| Microsoft Edge (tryb headless) | Zrzuty ekranu demo (`tools/shot.mjs`) | Narzędzie, nie jest dołączone do repo |
| GitHub Pages, GitHub Actions (`actions/checkout`, `configure-pages`, `upload-pages-artifact`, `deploy-pages`) | Hosting demo z katalogu `web/` (`.github/workflows/pages.yml`) | Usługa GitHub; akcje na licencji MIT |

**Czcionka.** Archivo (Omnibus-Type, The Archivo Project Authors), SIL Open Font License 1.1. Plik i licencja w `web/vendor/fonts/`.

**Interfejs.** Motyw okien w stylu klasycznego pulpitu (`web/xp/`) napisaliśmy od zera. Nie zawiera zasobów Microsoft. Ikony to własne rysunki SVG.

**Demo offline.** Ekran nie ładuje nic z CDN. Wszystkie biblioteki i dane leżą w `web/`.

## 4. Sprzęt

- Laptop zespołu (Intel Core i5-1245U, Windows 11): ekran demo, budowa terenu, pierwsze przebiegi AvaFrame.
- Biblioteka 1566 symulacji AvaFrame policzona na Sparku w 30,4 min na 12 rdzeniach.
- NVIDIA DGX Spark (GB10, 20 rdzeni Arm, 128 GB pamięci wspólnej), maszyna współdzielona: przebiegi AvaFrame na CPU, renderingi, uczenie surogatu na GPU.
- Stacja z RTX A4500: tylko porównawczy benchmark GPU.

## 5. Nasz kod

Kod napisany przez zespół (z pomocą AI, jak wyżej) jest na licencji MIT, plik [`LICENSE`](../LICENSE). Licencja MIT nie obejmuje danych i programów z sekcji 2 i 3: każdy zachowuje własną licencję.

Pierwszy commit w repo ma datę 3.10.2026, 15:22, czyli po starcie kodowania o 11:00.
