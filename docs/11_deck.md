# Deck i pitch: Avalauncher

Scenariusz 10 slajdów według układu z [kompendium](00_kompendium_hackyeah.md), sekcja 5. Każdy slajd: nagłówek w jednym zdaniu, 2–4 fakty, wizualizacja, notatka dla mówcy. Wszystkie liczby pochodzą z [docs/12_wyniki.md](12_wyniki.md), jedynego źródła prawdy (stan 4.10, ok. 02:00). Pola „[do uzupełnienia]” czekają na wynik.

**Zasady deku:** jeden nagłówek na slajd, mało tekstu, duże obrazy. Czcionka Archivo, kolory z `DESIGN.md` (papier, atrament, pomarańcz zagrożenia, fiolet niewiedzy, magenta trasy). Nigdy „bezpiecznie” jako obietnica, nigdy liczba bez źródła. Na każdym slajdzie z mapą stopka: „Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap · Śnieg: scenariusz syntetyczny”.

**Wizualizacje w `filmy/`** (lżejsze kopie JPG kadrów hero, surogatu i kalibracji: `web/media/`; sektory z pierwszej serii: S10 Mały Kościelec NE, S14 Mały Kościelec W, S17 Sucha Dolina W, S21 Beskid W, S22 Sucha Dolina NE, S27 Kasprowy Wierch W, S29 Świnica E, S31 Liliowe E):

- `porownania/przeglad_last.png`: 8 stref startowych, każda z jedną symulacją AvaFrame na mapie. Najmocniejszy obraz statyczny.
- `porownania/macierz_SXX.mp4` i `_last.png`: jedna strefa, 3 grubości płyty × 3 kalibracje tarcia.
- `3d/3d_SXX_*.mp4`: obrót kamery nad terenem 3D z ortofotomapą GUGiK i syntetycznym śniegiem, ciasno wykadrowany.
- `pojedyncze_2d/`: 72 pojedyncze symulacje.
- `hero/hero_S10_samosAT_2.0_mid.png`, `hero_S14_samosAT_2.0_std.png`, `hero_S22_samosAT_2.0_mid.png`, `hero_S31_samosAT_2.0_low.png`: kadry 4K, lawina AvaFrame na terenie 3D w chwili największego zasięgu.
- `hero/mapa_zasiegow.png` i `mapa_zasiegow_orbit.mp4`: cała biblioteka 1566 symulacji na terenie 3D, szlaki w zasięgu lawin wyróżnione.
- `hero/koncepcja_3d.png` i `koncepcja_orbit.mp4`: „Co wiemy, czego nie wiemy i dokąd polecieć”, z podpisem „ilustracja koncepcji”. Flagi na nim są poglądowe, nie z silnika.
- `kalibracja/porownanie.png`: AvaFrame wobec obrysu prawdziwej lawiny Popeletzbach (7.04.2009), siatka 21 przebiegów.
- `collage/2d_mozaika.mp4`: wszystkie 72 symulacje pierwszej serii naraz (8 stref × 3 grubości × 3 tarcia). `collage/3d_przeglad.mp4`: 12 lawin w 3D (6 stref × 2 warianty).
- `surrogate/porownanie.png`: AvaFrame, surogat U-Net i różnica zasięgu na 3 stokach spoza treningu. `surrogate/suwak.mp4`: surogat przy zmianie grubości płyty.
- Zrzuty ekranu demo: `docs/img/` [do zrobienia, `node tools/shot.mjs`].

---

## Slajd 1. Problem

**Nagłówek:** Rano po nocnym opadzie prognosta musi wiedzieć, które stoki zagrażają szlakom, a dron nie zawsze może polecieć.

- Nasz wycinek Tatr: 4×4 km wokół Hali Gąsienicowej, 72 strome strefy startowe nad 32 szlakami.
- Lawina rusza na stoku nad szlakiem, więc trzeba wiedzieć, co leży wyżej.
- Gdy pada śnieg, zagrożenie rośnie, a przelot bywa odwołany. Wiedza starzeje się wtedy, gdy jest najbardziej potrzebna.
- Demo stoi na prawdziwym epizodzie z IMGW Kasprowy Wierch, 11–13.01.2025: +34 cm nowego śniegu w 3 dni, 72 h zamieci, pokrywa 51 → 85 cm.

**Wizualizacja:** `filmy/hero/hero_S22_samosAT_2.0_mid.png` (Sucha Dolina NE: lawina dochodzi do szlaku) na pełny slajd. Na żywo: `filmy/hero/mapa_zasiegow_orbit.mp4`.

**Notatka:** Zaczynamy od jednej osoby i jednego poranka, bez nazwy projektu. Mówimy o dyżurnym, nie o technologii.

## Slajd 2. Teza i wyróżnik

**Nagłówek:** Avalauncher wie, co wie, wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.

- **Wie:** porównuje pomiar z drona z biblioteką lawin policzonych z góry i wskazuje sektory, które mogą zagrozić szlakom.
- **Wie, czego nie wie:** gdy dron nie poleciał, sektor dostaje flagę „nie wiem”, a nie znika z listy.
- **Alternatywa 1:** reguła „suma nowego śniegu z 3 dni” nie mówi, który stok i który szlak.
- **Alternatywa 2:** wielkie biblioteki scenariuszy (Bühler i in. 2022, ok. 2 mln stref) nie śledzą, gdzie wiedza się zestarzała, i nie planują przelotu.

**Wizualizacja:** `filmy/hero/koncepcja_3d.png` (pomarańcz: może zagrozić szlakowi, fiolet: nie wiem, magenta: plan przelotu). Podpis „ilustracja koncepcji” zostaje na obrazie.

**Notatka:** Nie twierdzimy, że to pierwszy cyfrowy bliźniak lawin. Nowe są dwie rzeczy: flaga „nie wiem” i plan przelotu.

## Slajd 3. Użytkownik i trzy kroki

**Nagłówek:** Dyżurny służby lawinowej robi trzy kroki przed porannym komunikatem.

1. Otwiera mapę. Widzi sektory z flagą: pomarańcz to „może zagrozić szlakowi”, fiolet to „nie wiem”.
2. Klika sektor. Widzi uzasadnienie: ile analogów z biblioteki dochodzi do szlaku i do którego odcinka.
3. Ustawia czas lotu. Dostaje plan przelotu: które sektory zmierzyć, w jakiej kolejności.

- Bez integracji i bez kont. Laptop, przeglądarka, dane w katalogu.

**Wizualizacja:** trzy małe zrzuty ekranu z numerami 1, 2, 3 (`docs/img/`).

**Notatka:** Decyzję zawsze podejmuje prognosta. Avalauncher wskazuje mu, gdzie patrzeć.

## Slajd 4. Demo: ekrany

**Nagłówek:** Jeden ekran pokazuje dwa poranki na prawdziwym terenie Tatr.

- **Dzień 1, 12.01.2025, dron poleciał:** dwa sektory z flagą zagrożenia. Po kliknięciu obrys zasięgu analogów i podświetlony odcinek szlaku.
- **Dzień 2, 13.01.2025, zamieć, bez przelotu:** mgła niewiedzy gęstnieje, sektory bez świeżego pomiaru dostają flagę „nie wiem”.
- **Plan przelotu:** suwak czasu lotu przelicza trasę na żywo, magenta na mapie.
- Okna: „Mapa — Hala Gąsienicowa”, „Sektory do uwagi”, „Plan przelotu”, „Sytuacja”.

**Wizualizacja:** zrzuty `http://localhost:8777` (dzień 1, sektor kliknięty) i `http://localhost:8777/?day=2` (mgła i plan) [do zrobienia, `node tools/shot.mjs`]. Demo online: <https://przemeknowak781.github.io/avalauncher/> (gdy repo będzie publiczne).

**Notatka:** Na żywo pokazujemy ten sam scenariusz. Wideo 90 s jako zapas, gdy sieć lub rzutnik zawiedzie.

## Slajd 5. Działanie przy degradacji

**Nagłówek:** Gdy brakuje danych, sieci albo usługi, Avalauncher mówi to wprost i dalej działa.

- **Brak przelotu:** niepewność rośnie z czasem i z opadem. Sektor dostaje flagę „nie wiem”. Brak danych nigdy nie wycisza flagi.
- **Brak sieci:** scenariusze są policzone z góry. Ekran działa offline na laptopie, bez CDN i bez serwera w chmurze.
- **Brak stacji IMGW:** znaczek pokazuje ostatni odczyt i godzinę albo brak łączności. Scenariusz się nie zatrzymuje.
- **Ograniczony czas lotu:** plan wybiera sektory, które dają najwięcej wiedzy nad szlakami w dostępnych minutach.

**Wizualizacja:** zrzut dnia 2 z mgłą niewiedzy i trasą przelotu. Obok ikona braku sieci w zasobniku.

**Notatka:** To wprost wymóg zadania: niepełne dane, ograniczone zasoby, niedostępne usługi. Brak flagi nie oznacza, że jest bezpiecznie.

## Slajd 6. Dowód

<!-- proof:start -->
**Nagłówek:** W teście logiki Avalauncher nie przeocza groźnych stoków, a reguła 3 dni przeocza 121 ze 144.

**Podpis pod nagłówkiem:** „Dane syntetyczne, test logiki. Pogoda: IMGW-PIB (prawdziwe). Grubość płyty i przeloty: syntetyczne. Poranki: 23.12.2024–21.01.2025.”

- **Wie:** przeoczenia 0 wobec 121 (reguła „suma nowego śniegu z 3 dni”), fałszywe alarmy 0 wobec 25. Cena: 549 flag „nie wiem”, głównie w porankach bez przelotu.
- **Wie, czego nie wie:** plan na 20 min wobec patrolu wzdłuż niebieskiego szlaku: zdjęte „nie wiem” 86 wobec 71, groźne stoki z flagą po przelocie 29 wobec 16, spadek niepewności 23% wobec 7%.
<!-- proof:end -->
<!-- surr:start -->
- **Surogat:** U-Net uczona na 1215 symulacjach AvaFrame z 45 stoków. Na 3 stokach spoza treningu IoU zasięgu 0,81. Jedna mapa 2,3 ms na GPU wobec 10,43 s AvaFrame na rdzeń CPU, ok. 4500× szybciej. Dowód koncepcji, nie zamiennik.
<!-- surr:end -->
- **Przykładowa kalibracja na prawdziwym zdarzeniu z Austrii (Popeletzbach, 7.04.2009):** najlepszy samosAT, odryw 0,6 m, IoU zasięgu 0,73, błąd zasięgu +20 m.

**Wizualizacja:** po lewej tabela dwóch miar. Po prawej `filmy/kalibracja/porownanie.png` (AvaFrame wobec prawdziwej lawiny) i `filmy/surrogate/porownanie.png` (AvaFrame, surogat, różnica). Gdy jest miejsce: `filmy/hero/mapa_zasiegow.png`.

**Notatka:** Zero przeoczeń bierze się stąd, że gdy Avalauncher nie wie, mówi „nie wiem”. Mówimy o cenie (549 flag „nie wiem”) i o tym, że 0/0 to słaby dowód: błąd modelu zmienia prawdę tylko w 44 przypadkach. Mocniejsza liczba to plan wobec patrolu: 86 wobec 71.

## Slajd 7. Mapowanie do Defence

**Nagłówek:** Avalauncher wykrywa zagrożenie wcześniej i zmniejsza skutki przy ograniczonych zasobach.

- **Wykrywa wcześniej:** wskazuje stoki nad szlakami, zanim ktoś na nie wejdzie.
- **Zmniejsza skutki:** planuje przelot tam, gdzie wiedza jest najstarsza, a szlak najbardziej narażony.
- **Odporność:** działa przy niepełnych danych, bez sieci i z małą liczbą ludzi. Człowiek zostaje w pętli decyzji.
- **Interesariusze:** służba lawinowa i prognosta, a przez komunikat turyści i ratownicy.

**Wizualizacja:** prosty schemat: pomiar → porównanie z biblioteką → flaga lub „nie wiem” → plan przelotu → prognosta.

**Notatka:** Defence w tym konkursie znaczy odporność, nie wojsko. Mówimy o ochronie ludzi na szlaku.

## Slajd 8. Prawdziwe a symulowane

**Nagłówek:** Teren, szlaki, pogoda i fizyka lawin są prawdziwe, a stan śniegu na stokach i przeloty syntetyczne.

| Element | Stan |
| --- | --- |
| Teren | Prawdziwy: GUGiK NMT, 4×4 km |
| Szlaki | Prawdziwe: OpenStreetMap, 32 szlaki |
| Biblioteka scenariuszy | Prawdziwa fizyka: 1566 symulacji AvaFrame com1DFA, standardowe kalibracje tarcia |
| Pogoda | IMGW-PIB (prawdziwe): Kasprowy Wierch, zima 2024/25; kierunek wiatru założony |
| Kalibracja | Przykładowa, na prawdziwym zdarzeniu z Austrii (Popeletzbach). Dla Tatr brak, to pierwszy krok wdrożenia |
| Grubość płyty, przeloty, odczyty drona, błąd modelu | Syntetyczne |
| Śnieg w filmach 3D | Syntetyczny, na prawdziwej ortofotomapie GUGiK |

**Wizualizacja:** sama tabela, bez obrazu.

**Notatka:** Ta tabela chroni nas przed zarzutem przesady. Avalauncher nie jest zwalidowaną prognozą i nie służy do samodzielnego ostrzegania.

## Slajd 9. Wdrożenie i mapa drogowa

**Nagłówek:** Pierwszy krok to pilot z jedną służbą na jednym korytarzu szlaku.

- **Pilot:** kalibracja AvaFrame na lokalnych zdarzeniach z Tatr (TOPR), tak jak tej nocy przykładowo na Popeletzbach. Prawdziwe przeloty nad jednym korytarzem.
- **Platforma:** nowy masyw to konfiguracja: teren, strefy, szlaki, lokalne zdarzenia. Nowe źródło danych przez jeden interfejs.
- **Liczenie:** biblioteka liczy się na jednej maszynie klasy DGX Spark (1566 symulacji w 30,4 min), a działa na laptopie.
- **Dalej:** surogat U-Net dla nowych stref (IoU 0,81 na stokach spoza treningu), SNOWPACK, osuwiska na tym samym silniku. Dobór przelotów z RL: [do uzupełnienia, gdy trafi do `docs/12_wyniki.md`]. Do sprawdzenia: zgody na loty nad parkiem narodowym i poza zasięgiem wzroku.

**Wizualizacja:** oś czasu w trzech krokach: pilot → kalibracja → kolejny masyw. W tle kadr z `filmy/3d/3d_S27_samosAT_2.0.mp4` (Kasprowy Wierch W).

**Notatka:** Nie obiecujemy przenośności modelu między górami. Każdy teren kalibruje się lokalnie z miejscową służbą.

## Slajd 10. Zespół, AI i licencje

**Nagłówek:** Zbudowaliśmy to w jedną noc z pomocą AI i z otwartych danych, z pełną atrybucją.

- **Zespół:** [do uzupełnienia: imiona i role].
- **AI:** Claude Code, model Claude Opus 5.5: research, kod, dokumentacja, wizualizacje. Zakres i tezę ustalili ludzie.
- **Dane:** teren i ortofotomapa GUGiK, szlaki © współtwórcy OpenStreetMap (ODbL), pogoda IMGW-PIB (dane przetworzone), lawina Popeletzbach z OpenNHM/AvaFrameData (CC BY 4.0, DOI 10.5281/zenodo.20701552), teren Land Tirol (CC BY 4.0 AT).
- **Oprogramowanie:** AvaFrame (EUPL-1.2), Archivo (OFL), numpy, scipy, pandas, rasterio, matplotlib, Pillow, pyshp, PyTorch, ffmpeg. Nasz kod: MIT. Lista: `docs/10_ai_i_licencje.md`.

**Wizualizacja:** link do repo (github.com/przemeknowak781/avalauncher) i do demo (przemeknowak781.github.io/avalauncher), kod QR do demo.

**Notatka:** To ujawnienie, którego wymaga regulamin. Mówimy o nim spokojnie, bez przepraszania.

---

## Pitch na 3 minuty

Podział z kompendium. Jeśli limit będzie inny, skaluj proporcjonalnie. Zdania krótkie, do mówienia na głos.

**0:00–0:30. Historia, bez nazwy projektu**

> Trzynasty stycznia 2025, siódma rano. Na Kasprowym od trzech dni pada i wieje: trzydzieści cztery centymetry nowego śniegu. Dyżurny służby lawinowej ma przed sobą dziesiątki stromych stoków nad szlakami. Za chwilę musi napisać komunikat. Wczoraj dron przeleciał nad Halą Gąsienicową. Dziś nie poleci, bo jest zamieć. Co dyżurny wie, a czego już nie wie?

**0:30–2:00. Demo na żywo, ten sam scenariusz**

> To prawdziwy teren i prawdziwa pogoda: Hala Gąsienicowa, model terenu z GUGiK, szlaki z OpenStreetMap, dane IMGW z tamtych dni.
>
> Dzień pierwszy. Dron poleciał. Avalauncher porównał pomiar z biblioteką ponad 1500 lawin policzonych z góry fizycznym solverem AvaFrame. Dwa sektory dostały flagę. Klikam jeden. Widzę, ile podobnych lawin dochodzi do szlaku i do którego odcinka.
>
> Dzień drugi. Zamieć, dron nie poleciał. Wiedza się starzeje. Na mapie gęstnieje mgła. Sektory bez świeżego pomiaru dostają flagę „nie wiem”. Nie znikają z listy. Zostają i mówią: nie wiemy.
>
> Avalauncher planuje przelot na pierwsze okno pogodowe. Ustawiam dwadzieścia minut lotu. Plan wybiera sektory, które dadzą najwięcej wiedzy nad szlakami. Klikam „Wykonaj przelot”. Dron przelatuje, mgła znika tam, gdzie zmierzył.

**2:00–2:40. Dlaczego inaczej i co przy degradacji**

> Biblioteki scenariuszy lawin już istnieją. W Szwajcarii jeden kanton ma około dwóch milionów stref startowych ze scenariuszami. My dodajemy dwie rzeczy: śledzimy, gdzie wiedza się zestarzała, i mówimy, gdzie polecieć, żeby ją odświeżyć.
>
> Wszystko jest policzone z góry, więc działa bez sieci, na laptopie. Gdy brakuje danych, Avalauncher mówi to wprost. Nigdy nie mówi, że jest bezpiecznie. Decyzję podejmuje prognosta.
>
<!-- pitchproof:start -->
> Uczciwie: teren, szlaki, pogoda i fizyka są prawdziwe. Stan śniegu na stokach i przeloty są syntetyczne. W teście logiki na trzydziestu takich porankach reguła trzech dni przeoczyła 121 groźnych sytuacji, a Avalauncher żadnej, bo gdy nie wie, mówi to.
<!-- pitchproof:end -->

**2:40–3:00. Kto użyje pierwszy i zamknięcie**

> Pierwszy krok to pilot z jedną służbą na jednym korytarzu szlaku i kalibracja na jej zdarzeniach. Avalauncher to cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.

## Krótkie odpowiedzi na pytania jury

- **Skąd dane?** Teren GUGiK, szlaki OSM, pogoda IMGW, fizyka AvaFrame z przykładową kalibracją na prawdziwym zdarzeniu z Austrii. Stan stoków i przeloty w demo są syntetyczne. W pilocie: prawdziwe przeloty i zdarzenia służby.
- **Co z fałszywymi alarmami?** W teście logiki Avalauncher dał 0 fałszywych flag „zagrożenie”, reguła 3 dni 25. Kosztem są flagi „nie wiem”: proszą o pomiar, a nie ogłaszają zagrożenia.
- **Co bez sieci?** Działa. Biblioteka jest policzona z góry i leży na laptopie.
- **Kto zapłaci i utrzyma?** Służba lawinowa lub park narodowy w pilocie. Konfiguracja nowego terenu, nie nowy produkt. [do potwierdzenia przed pitchem]
- **Czym różni się od istniejących bibliotek?** Flagą „nie wiem” i planem przelotu, który ją zdejmuje.
- **Prywatność?** Nie przetwarzamy danych osobowych. Dron mierzy śnieg, nie ludzi.
