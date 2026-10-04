# Deck i pitch: Avalauncher

Scenariusz 10 slajdów w układzie z [kompendium](00_kompendium_hackyeah.md), sekcja 5. Wszystkie liczby pochodzą z [docs/12_wyniki.md](12_wyniki.md), jedynego źródła prawdy (stan 4.10, ok. 02:00). Pola „[do uzupełnienia]” i „[do potwierdzenia]” czekają na decyzję.

**Zasady decku:** prosto, jak krowie na rowie. Krótkie zdania, jeden pomysł na slajd, duży obraz, mało tekstu. Każdą liczbę zestawiamy z czymś, co zna dwunastolatek. Przy każdej liczbie piszemy, co jest prawdziwe, a co symulowane. Czcionka Archivo, kolory z `DESIGN.md`: pomarańcz to zagrożenie, fiolet to „nie wiem”, magenta to trasa drona. Na żadnym slajdzie nie piszemy „bezpiecznie”. Program uczący się metodą prób i błędów nazywamy „RL”, nigdy „AI”, bo słowo „AI” zostaje dla Claude Code na slajdzie 10. Eksport do PDF dopiero po zatwierdzeniu projektu graficznego (docs/16_design_decku.md).

**Słowniczek (jedno zdanie na pojęcie, do użycia na slajdach):**

- **Cyfrowy bliźniak:** komputerowa kopia góry, czyli teren, szlaki, śnieg i policzone z góry lawiny.
- **Płyta śnieżna:** zbita warstwa śniegu, która może się oderwać i zjechać jako lawina.
- **AvaFrame:** otwarty program, który liczy, jak lawina płynie po prawdziwym terenie.
- **Flaga „nie wiem”:** stok, o którym wiedza jest za stara, żeby powiedzieć „tak” albo „nie”.
- **Test logiki:** sprawdza, czy program dobrze liczy na wymyślonym śniegu, a nie, czy trafnie przewiduje lawiny w Tatrach.
- **IoU:** wspólna część dwóch obrysów podzielona przez ich łączną powierzchnię. 1 to pełna zgodność.
- **DGX Spark:** jeden mały komputer, który stoi na biurku.
- **Szybka kopia fizyki (surogat):** sieć neuronowa, która nauczyła się od AvaFrame rysować lawinę.
- **RL:** program, który uczy się metodą prób i błędów, jak gracz w grze.

---

## 1. Narracja w 5 zdaniach

1. Trzynastego stycznia 2025 rano, po trzech dniach zamieci na Kasprowym, dyżurny służby lawinowej musi powiedzieć, które stoki mogą zrzucić lawinę na szlak, a dron w taką pogodę nie wystartuje.
2. Avalauncher to komputerowa kopia góry: policzyliśmy z góry 1566 lawin na prawdziwym terenie Tatr, więc każdy pomiar z drona od razu porównujemy z gotowymi odpowiedziami, jak z tabliczką mnożenia.
3. Gdy dron nie może polecieć, Avalauncher nie udaje, że wie: stoki bez świeżego pomiaru dostają flagę „nie wiem”, a program planuje, gdzie polecieć, gdy pogoda pozwoli.
4. W teście logiki na prawdziwej pogodzie i wymyślonym śniegu, łącznie w 30 porankach, ten plan przy 20 minutach lotu oflagował groźny stok 29 razy, a lot wzdłuż szlaku 16 razy.
5. Mówimy wprost, co jest prawdziwe, a co symulowane, sprawdzamy, zanim obiecamy, i zaczynamy od pilota z jedną służbą na jednym szlaku.

## 2. Najmocniejsze liczby

| Liczba | Co to znaczy po ludzku | Źródło (docs/12) |
| --- | --- | --- |
| **+34 cm** nowego śniegu w 3 dni, **72 h** zamieci, pokrywa **51 → 85 cm** | Prawdziwa burza z poranków demo. W trzy dni dosypało więcej śniegu, niż ma szkolna linijka. Pokrywa urosła od kolana prawie do biodra dorosłego. Dane IMGW-PIB, Kasprowy Wierch, 11–13.01.2025. | Prawdziwa pogoda |
| **48 z 58** stoków może zrzucić lawinę na szlak, **47** już przy płycie **0,4 m** | Większość stromych stoków w naszym wycinku może sięgnąć szlaku, prawie wszystkie już przy płycie mniej więcej do kolana. Dlatego trzeba wiedzieć, który stok, a nie tylko ile napadało. To wynik symulacji AvaFrame. | Biblioteka scenariuszy (fizyka) |
| **1566** lawin w **30,4 min**, **0** nieudanych | Całą bibliotekę jeden mały komputer na biurku (DGX Spark, na 12 rdzeniach) policzył w pół godziny, czyli krócej niż trwa lekcja. Żaden przebieg się nie wysypał. Liczysz raz, potem tylko sprawdzasz, jak z tabliczką mnożenia. | Biblioteka scenariuszy (fizyka) |
| **29 wobec 16** groźnych stoków oflagowanych po locie (łącznie w **30** porankach, lot **20 min**) | Ten sam dron i ten sam czas lotu, zmienia się tylko trasa. Przez 30 poranków plan Avalaunchera oflagował groźny stok 29 razy, a lot wzdłuż szlaku 16 razy. Test logiki: pogoda prawdziwa, śnieg i loty wymyślone. | Dowód logiki silnika |
| **86 wobec 71** zdjętych „nie wiem”, niepewność **−23% wobec −7%** | Po locie z planem więcej znaków zapytania zamienia się w pomiar. Niepewność decyzji spada o 23%, a po locie wzdłuż szlaku tylko o 7%. Te same 30 poranków. | Dowód logiki silnika |
| RL **19,9%** wobec prostego planu **20,2%** (lot wzdłuż szlaku **5,4%**), **10,4 mln** próbnych poranków w **6 min** | Program uczący się metodą prób i błędów przećwiczył 10,4 mln porannych lotów i wyszedł na remis z prostym planem. Remis to nie wygrana, więc zostawiliśmy prosty plan, bo łatwiej go wyjaśnić i sprawdzić. To inny test (1000 poranków), więc nie zestawiamy go z 29 wobec 16. | RL dla planu przelotu |
| Zasięg **1795 m wobec 1775 m**, różnica **20 m**, IoU **0,73** | Dopasowaliśmy fizykę do jednej prawdziwej lawiny z Austrii (Popeletzbach, 7.04.2009). Najlepszy z 21 przebiegów różni się od prawdziwej drogi lawiny o 20 m na 1775 m. Wspólna część obu obrysów to prawie trzy czwarte ich łącznej powierzchni. Przykładowa kalibracja, nie dla Tatr. | Kalibracja na prawdziwej lawinie |
| **2,3 ms** zamiast **10,43 s**, ok. **4500×**, IoU **0,81** na **3** stokach spoza nauki | Szybka kopia fizyki rysuje lawinę szybciej niż mrugnięcie oka, także na stokach, których nigdy nie widziała. Porównujemy jeden rdzeń procesora z kartą graficzną. Kopia przybliża fizykę, ale jej nie zastępuje. | Sieć zastępcza (surogat) AvaFrame |

## 3. Slajdy

Czas slajdów sumuje się do 3:00 i pasuje do pitchu: historia 0:30, demo z pomysłem 1:30, dowód i uczciwość 0:40, pilot i zamknięcie 0:20.

Katalogu `docs/img/` jeszcze nie ma. Zrzuty z demo robi `node tools/shot.mjs <url> <plik.png> [szer wys czekanie_ms] [js]`, gdy demo działa na `http://localhost:8777`. Zrzuty są obowiązkowe przed zamknięciem decku. Zapasowe obrazy podajemy przy slajdach.

Stopka na każdym slajdzie z mapą: „Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap · Śnieg na stokach: scenariusz syntetyczny”.

### Slajd 1. Poranek

**Nagłówek:** Rano, po trzech dniach zamieci, dyżurny musi powiedzieć, które szlaki są groźne, a dron nie może wystartować.

**Co mówię:** Trzynasty stycznia 2025, Kasprowy Wierch. Od trzech dni sypie i wieje: 34 cm nowego śniegu, więcej niż szkolna linijka. Dron w zamieci nie poleci, a za chwilę trzeba napisać komunikat.

**Co pokazuję:** `filmy/hero/hero_S22_samosAT_2.0_mid.png` na cały slajd (lżejsza kopia: `web/media/hero_S22_samosAT_2.0_mid.jpg`). Bez nazwy projektu i bez interfejsu. Jedna linijka na obrazie: „Kasprowy Wierch, 11–13.01.2025: +34 cm śniegu w 3 dni, 72 h zamieci (IMGW-PIB, dane prawdziwe)”. Stopka: „Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap · Lawina: symulacja AvaFrame, śnieg syntetyczny”. Kadr to Sucha Dolina NE, czyli ten sam stok, który demo zapala w dniu 1. Na slajdzie 4 mówimy to na głos.

**Czas:** 30 s (0:00–0:30).

### Slajd 2. Pomysł

**Nagłówek:** Avalauncher to cyfrowy bliźniak góry, czyli jej komputerowa kopia, która wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.

**Co mówię:** Liczyć lawiny już umiemy. Nowe są dwie rzeczy: flaga „nie wiem” i plan, gdzie polecieć. Reguła „ile napadało w 3 dni” mówi kiedy, ale nie mówi, który stok.

**Co pokazuję:** `filmy/hero/koncepcja_3d.png` (lżejsza kopia: `web/media/landing/hero_koncepcja_2400.jpg`). Podpis „ilustracja koncepcji” zostaje widoczny, bo flagi na tym obrazie są poglądowe, nie z silnika. Legenda: pomarańcz = może zagrozić szlakowi · fiolet = nie wiem · magenta = trasa drona. Pasek pod obrazem, dużym drukiem, z dwiema alternatywami: „Reguła »co najmniej 30 cm w 3 dni« mówi kiedy, ale nie który stok. Wielkie biblioteki lawin (Bühler i in. 2022) nie mówią, gdzie wiedza się zestarzała.”

**Czas:** 15 s (0:30–0:45).

### Slajd 3. Trzy kroki dyżurnego

**Nagłówek:** Dyżurny robi trzy kroki: otwiera mapę, klika stok i ustawia czas lotu.

**Co mówię:** Nad Halą Gąsienicową 48 z 58 stromych stoków może zrzucić lawinę na szlak, więc dyżurny musi wiedzieć, na które patrzeć. Pomarańczowy stok może zagrozić szlakowi, a fioletowy znaczy „nie wiem”. Po kliknięciu widać, do którego odcinka szlaku dochodzą podobne lawiny.

**Co pokazuję:** trzy zrzuty z dużymi cyframi 1, 2, 3:

1. `docs/img/krok1_mapa.png`: mapa dnia 1 z flagami. `node tools/shot.mjs http://localhost:8777 docs/img/krok1_mapa.png`
2. `docs/img/krok2_stok.png`: karta klikniętej Suchej Doliny NE z odcinkiem szlaku. `node tools/shot.mjs http://localhost:8777 docs/img/krok2_stok.png 1440 860 3500 "[js klikający sektor S22]"`
3. `docs/img/krok3_trasa.png`: suwak czasu lotu na 20 min i magentowa trasa. `node tools/shot.mjs "http://localhost:8777/?day=2" docs/img/krok3_trasa.png`

Podpis: „Laptop i przeglądarka, bez kont i integracji”. Zapas, dopóki nie ma zrzutów: `filmy/hero/mapa_zasiegow.png` z podpisem „48 z 58 stoków sięga szlaku w symulacjach AvaFrame”.

**Czas:** 25 s (0:45–1:10). W pitchu ten slajd zastępuje demo na żywo.

### Slajd 4. Dwa poranki

**Nagłówek:** Ten sam ekran i dwa poranki: gdy dron leci, groźne stoki się zapalają, a gdy stoi, stoki bez pomiaru dostają flagę „nie wiem”.

**Co mówię:** Dwunastego stycznia, w scenariuszu demo, dron mierzy śnieg i zapalają się Sucha Dolina NE i Beskid NE. Sucha Dolina NE to stok z pierwszego slajdu. Trzynastego dron stoi, gęstnieje mgła niewiedzy, a kolejne stoki dostają fioletową flagę, zamiast zniknąć z listy.

**Co pokazuję:** dwa zrzuty obok siebie:

- `docs/img/dzien1.png` z podpisem „12.01.2025: dron poleciał”. `node tools/shot.mjs http://localhost:8777 docs/img/dzien1.png`
- `docs/img/dzien2_mgla.png` z podpisem „13.01.2025: zamieć, bez lotu”. `node tools/shot.mjs "http://localhost:8777/?day=2" docs/img/dzien2_mgla.png`

Stopka: „Pogoda: IMGW-PIB (prawdziwa) · Grubość płyty i loty drona: syntetyczne · Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap”. Na scenie pokazujemy demo na żywo, a jako zapas mamy surowe ujęcia ekranu do scenariusza filmu.

**Czas:** 30 s (1:10–1:40).

### Slajd 5. Gdy coś nie działa

**Nagłówek:** Bez drona, bez sieci i bez stacji pogodowej Avalauncher dalej działa, bo 1566 lawin policzyliśmy z góry.

**Co mówię:** Całą bibliotekę jeden mały komputer na biurku policzył w 30,4 minuty i żaden przebieg się nie wysypał. To jak tabliczka mnożenia: liczysz raz, potem tylko sprawdzasz, nawet bez internetu. Gdy nie ma lotu, stok dostaje flagę „nie wiem”, a gdy nie ma stacji, widać ostatni odczyt z godziną.

**Co pokazuję:** `filmy/hero/mapa_zasiegow.png` (na żywo: `filmy/hero/mapa_zasiegow_orbit.mp4`, lżejsza kopia: `web/media/landing/mapa_zasiegow_orbit.jpg`). To cała biblioteka na terenie 3D, z wyróżnionymi szlakami w zasięgu lawin. Duży napis: „1566 lawin · 30,4 min · 0 nieudanych”. Podpis: „Fizyka AvaFrame na 12 rdzeniach jednego komputera DGX Spark”. Trzy ikonki: brak drona → flaga „nie wiem” · brak sieci → działa offline na laptopie · brak stacji IMGW → ostatni odczyt z godziną.

**Czas:** 20 s (1:40–2:00).

### Slajd 6. Dowód

**Nagłówek:** Przy tych samych 20 minutach lotu plan Avalaunchera znajduje więcej groźnych stoków niż lot wzdłuż szlaku: łącznie w 30 porankach 29 wobec 16.

**Co mówię:** Ten sam dron i ten sam czas, zmienia się tylko trasa. Plan leci tam, gdzie pomiar najwięcej powie o szlaku, i zamienia w pomiar więcej znaków zapytania: 86 wobec 71. W innym teście RL, czyli program uczący się metodą prób i błędów, po 10,4 mln próbnych poranków tylko zremisował z prostym planem, więc zostawiliśmy prosty.

**Co pokazuję:** dwie wielkie pary liczb: „29 wobec 16” (groźny stok oflagowany po locie) i „86 wobec 71” (zdjęte „nie wiem”). Mniejsza linia: „Niepewność decyzji spada o 23%, po locie wzdłuż szlaku o 7%”. Duży podpis: „Test logiki: prawdziwa pogoda IMGW, wymyślony śnieg i loty. Sprawdza, czy program dobrze liczy, a nie, czy trafnie przewiduje lawiny w Tatrach.” Wąski pasek na dole: „Inny test, 1000 poranków, spadek niepewności: RL 19,9% · prosty plan 20,2% · lot wzdłuż szlaku 5,4%. Remis, więc zostaje prosty plan.”

Obraz: `docs/img/po_przelocie.png` (`?day=2`, suwak 20 min, po kliknięciu „Wykonaj przelot”): `node tools/shot.mjs "http://localhost:8777/?day=2" docs/img/po_przelocie.png 1440 860 3500 "[js: przelot 20 min]"`. Zapas: `filmy/rl/trasy.png` (lżejsza kopia: `web/media/rl_trasy.jpg`), ale tylko po trzech poprawkach. Po pierwsze, legendę zakrywamy, bo 24% / 83% / 83% dotyczy jednego poranka i tych liczb nie ma w docs/12. Po drugie, kolory podpisujemy wprost, bo na obrazie pomarańcz to lot wzdłuż szlaku, fiolet to prosty plan, a magenta to RL, czyli inaczej niż w legendzie decku. Po trzecie, napisy „Plan VOI silnika” i „Stały patrol” zamieniamy na „plan Avalaunchera” i „lot wzdłuż szlaku”.

**Czas:** 15 s (2:00–2:15).

### Slajd 7. Odporność, nie wojsko

**Nagłówek:** Avalauncher wykrywa zagrożenie wcześniej, zmniejsza skutki i działa przy braku danych, a decyzję zostawia człowiekowi.

**Co mówię:** Wskazuje groźne stoki, zanim ktoś na nie wejdzie. Wysyła drona tam, gdzie wiedza nad szlakiem jest najsłabsza. Decyzję zawsze podejmuje dyżurny.

**Co pokazuję:** `filmy/kiedy/kalendarz.png`, czyli cała zima 2024/25. Górny pas to prawdziwa pogoda IMGW z trzema burzami (+29, +34, +30 cm). Kolory pokazują, że stoki zapalają się w połowie stycznia i na początku kwietnia. Podpis: „Uproszczona reguła (heurystyka), nie prognoza. Kierunek wiatru założony.” Trzy hasła dużym drukiem: wykrywa wcześniej · zmniejsza skutki · działa przy braku danych.

**Czas:** 10 s (2:15–2:25).

### Slajd 8. Co prawdziwe, co przybliżone, co symulowane

**Nagłówek:** Teren, szlaki, pogoda i fizyka lawin są prawdziwe, a śnieg na stokach i loty drona są symulowane.

**Co mówię:** Mówimy wprost, co jest czym. Fizykę dopasowaliśmy do jednej prawdziwej lawiny z Austrii i najlepszy z 21 przebiegów różni się od niej o 20 m na 1775 m. Dla Tatr takiej kalibracji jeszcze nie ma, to pierwszy krok pilota.

**Co pokazuję:** tabela w trzech kolumnach, dużym drukiem.

| Prawdziwe | Przybliżone | Symulowane lub założone |
| --- | --- | --- |
| Teren: GUGiK NMT | Kalibracja: przykładowa, z Austrii, nie dla Tatr | Grubość płyty na stokach |
| Szlaki: OpenStreetMap | Szybka kopia fizyki: przybliża AvaFrame, nie zastępuje go | Loty i odczyty drona |
| Pogoda: IMGW-PIB Kasprowy Wierch, zima 2024/25 | Kalendarz zagrożenia: uproszczona reguła | „Prawda” i błąd modelu w teście logiki |
| Fizyka lawin: 1566 symulacji AvaFrame | | Kierunek wiatru |
| Lawina Popeletzbach, Austria, 7.04.2009 (OpenNHM/AvaFrameData) | | Śnieg w filmach 3D |

Przy wierszu kalibracji miniatura `filmy/kalibracja/porownanie.png` (lżejsza kopia: `web/media/kalibracja_porownanie.jpg`) z podpisem „Dopasowanie do prawdziwej lawiny z Austrii: 1795 m wobec 1775 m”. Na dole: „Avalauncher nie jest zwalidowaną prognozą.”

**Czas:** 15 s (2:25–2:40).

### Slajd 9. Pilot

**Nagłówek:** Pierwszy krok to pilot z jedną służbą lawinową na jednym szlaku i kalibracja na jej własnych lawinach.

**Co mówię:** W Tatrach zrobimy to samo, co na lawinie z Austrii: dopasujemy fizykę do miejscowych zdarzeń. Potem prawdziwe loty nad jednym szlakiem. Nowe stoki policzy szybka kopia fizyki, która rysuje lawinę w 2,3 ms zamiast 10,43 s.

**Co pokazuję:** `filmy/surrogate/porownanie.png` (lżejsza kopia: `web/media/surrogate_porownanie.jpg`): AvaFrame, szybka kopia i różnica między nimi na 3 stokach, których sieć nie widziała. Podpis: „Szybka kopia fizyki: 2,3 ms na karcie graficznej zamiast 10,43 s na jednym rdzeniu procesora, ok. 4500×. IoU 0,81: wspólna część obrysów to 0,81 ich łącznej powierzchni, a 1 to pełna zgodność. Dowód koncepcji, nie zamiennik AvaFrame.” Oś w trzech krokach: pilot z lokalną kalibracją → prawdziwe loty nad jednym szlakiem → kolejny masyw. Drobnym drukiem: „Do sprawdzenia: zgody na loty nad parkiem narodowym”.

**Czas:** 15 s (2:40–2:55).

### Slajd 10. Zespół, AI, licencje

**Nagłówek:** Zbudowaliśmy to w jedną noc z otwartych danych i z pomocą AI, a każde źródło jest podpisane.

**Co mówię:** Rano dyżurny dalej decyduje sam, ale teraz wie, czego nie wie, i wie, gdzie wysłać drona. Avalauncher: cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć. (Slajd zostaje na ekranie podczas pytań.)

**Co pokazuję:** kod QR do demo (<https://przemeknowak781.github.io/avalauncher/>, gdy repo będzie publiczne) i link do repo (github.com/przemeknowak781/avalauncher). Zespół: [do uzupełnienia: imiona i role]. AI: Claude Code (Claude Opus 5.5) pisał kod, teksty i wizualizacje, a zakres i tezę ustalili ludzie. Dane: GUGiK (teren, ortofotomapa), © współtwórcy OpenStreetMap (ODbL), IMGW-PIB (dane przetworzone), OpenNHM/AvaFrameData (CC BY 4.0, DOI 10.5281/zenodo.20701552), Land Tirol (CC BY 4.0 AT). Programy: AvaFrame (EUPL-1.2), pełna lista w `docs/10_ai_i_licencje.md`. Nasz kod: MIT. W tle przyciemniony kadr z `filmy/3d/3d_S27_samosAT_2.0.mp4` (Kasprowy Wierch W, śnieg syntetyczny). Na dole hasło.

**Czas:** 5 s (2:55–3:00).

---

## 4. Pitch na 3 minuty

Układ z kompendium. Zdania krótkie, do mówienia na głos. Jeśli limit będzie inny, skaluj proporcjonalnie.

**Zdanie otwierające:** Trzynasty stycznia 2025, siódma rano, Kasprowy Wierch. Od trzech dni sypie i wieje.

**Zdanie zamykające:** Rano dyżurny dalej decyduje sam, ale teraz wie, czego nie wie, i wie, gdzie wysłać drona.

**0:00–0:30. Historia, bez nazwy projektu (slajd 1)**

> Trzynasty stycznia 2025, siódma rano, Kasprowy Wierch. Od trzech dni sypie i wieje: 34 centymetry nowego śniegu, więcej niż szkolna linijka. Dyżurny służby lawinowej za chwilę pisze komunikat. Wczoraj dron zmierzył śnieg nad szlakami. Dziś, w zamieci, nie poleci. Co dyżurny jeszcze wie, a czego już nie wie?

**0:30–0:45. Pomysł (slajd 2)**

> Pomaga mu Avalauncher, komputerowa kopia góry. Liczyć lawiny już umiemy. Nowe są dwie rzeczy: flaga „nie wiem” i plan, gdzie polecieć, żeby się dowiedzieć.

**0:45–2:00. Demo na żywo, ten sam scenariusz (slajdy 3–5)**

> Prawdziwy teren Hali Gąsienicowej z GUGiK, szlaki z OpenStreetMap, pogoda IMGW z tamtych dni. Śnieg na stokach i loty drona są w demo wymyślone.
>
> Nad tą doliną 48 z 58 stromych stoków może zrzucić lawinę na szlak. Dyżurny nie obejrzy wszystkich.
>
> Dwunasty stycznia, dron poleciał. Avalauncher porównał pomiar z 1566 lawinami policzonymi z góry. Krok pierwszy: otwieram mapę. Na pomarańczowo świecą Sucha Dolina NE i Beskid NE. Krok drugi: klikam Suchą Dolinę. To stok z pierwszego slajdu. Widzę, do którego odcinka szlaku dochodzą podobne lawiny.
>
> Trzynasty stycznia, zamieć, dron stoi. Wiedza się starzeje, na mapie gęstnieje mgła. Kolejne stoki dostają fioletową flagę „nie wiem”. Nie znikają z listy.
>
> Krok trzeci: ustawiam 20 minut lotu. Avalauncher rysuje trasę na pierwsze okno pogody. Klikam „Wykonaj przelot”. Mgła znika tam, gdzie dron zmierzył.
>
> A gdy padnie internet? Wszystko leży na laptopie. Liczysz raz, potem tylko sprawdzasz, jak z tabliczką mnożenia.

**2:00–2:40. Dowód, odporność, uczciwość (slajdy 6–8)**

> Czy to działa? Sprawdziliśmy to w teście logiki, na prawdziwej pogodzie i wymyślonym śniegu. Łącznie w 30 porankach, przy 20 minutach lotu, nasz plan oflagował groźny stok 29 razy, a lot wzdłuż szlaku 16 razy.
>
> Sprawdziliśmy też RL, program uczący się metodą prób i błędów. Zremisował z prostym planem, więc zostawiliśmy prosty. Najpierw sprawdzamy, potem obiecujemy.
>
> To jest odporność: wykrywamy wcześniej, zmniejszamy skutki i działamy, gdy brakuje danych. Decyduje człowiek.
>
> Uczciwie: teren, szlaki, pogoda i fizyka są prawdziwe, a śnieg na stokach i loty są symulowane. Fizykę dopasowaliśmy do prawdziwej lawiny z Austrii, nie z Tatr.

**2:40–3:00. Kto użyje pierwszy i zamknięcie (slajdy 9–10)**

> Pierwszy krok to pilot z jedną służbą lawinową na jednym szlaku i kalibracja na jej własnych lawinach.
>
> Rano dyżurny dalej decyduje sam, ale teraz wie, czego nie wie, i wie, gdzie wysłać drona. Avalauncher: cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.

## 5. Pytania jury

Po jednym zdaniu na pytanie. Zapisać na kartce przy stanowisku.

1. **Kto za to zapłaci?** Pierwszy zapłaci ten, kto dziś odpowiada za szlaki zimą, czyli służba lawinowa albo park narodowy, a w pilocie nasza część kosztu to laptop i jedno liczenie biblioteki na jeden teren, bo kod jest otwarty (MIT). [do potwierdzenia przed pitchem: kto realnie kupuje i utrzymuje]
2. **Co z fałszywymi alarmami?** W teście logiki Avalauncher dał 0 fałszywych alarmów wobec 25 dla reguły „30 cm w 3 dni”, kosztem 549 flag „nie wiem”, które proszą o pomiar, a nie ogłaszają zagrożenia.
3. **Czy to działa bez sieci?** Tak: 1566 lawin jest policzonych z góry i leży na laptopie, ekran działa w przeglądarce bez internetu, a gdy stacja IMGW milczy, widać ostatni odczyt z godziną.
4. **Czym to się różni od komunikatu TOPR?** Komunikat podaje stopień zagrożenia dla całego regionu, a Avalauncher nie zastępuje go, tylko pomaga temu, kto go pisze, bo wskazuje konkretne stoki nad konkretnymi szlakami i mówi, gdzie wiedza jest za stara.
5. **Czy to jest sprawdzone w Tatrach?** Jeszcze nie: fizykę dopasowaliśmy do jednej prawdziwej lawiny z Austrii (20 m różnicy na 1775 m), a 29 wobec 16 to test logiki na wymyślonym śniegu, dlatego pierwszym krokiem jest pilot z kalibracją na lawinach z Tatr.
6. **Czemu plan lotu nie korzysta z RL?** Sprawdziliśmy go: RL po 10,4 mln próbnych poranków zremisował z prostym planem (19,9% wobec 20,2% spadku niepewności), więc zostaje prosty plan, bo łatwiej go wyjaśnić i sprawdzić.

**Na dopytanie (tylko gdy jury zapyta):**

- Fałszywe alarmy: reguła „30 cm w 3 dni” przeoczyła 121 groźnych sytuacji, a Avalauncher 0. Mówimy to tylko razem z ceną (549 flag „nie wiem”, z tego 505 w poranki z odwołanym lotem) i dodajemy, że to słaby dowód, bo w syntetycznym teście błąd modelu zmienia prawdę tylko w 44 przypadkach.
- TOPR: nie porównaliśmy się z archiwum stopni zagrożenia TOPR, bo nie jest dostępne.
- RL wyłapał trochę więcej zagrożeń (1936 wobec 1810 z 7924), ale zdjął mniej „nie wiem” (3915 wobec 3987). Trochę lepszy wynik w jednej mierze to jeszcze nie wygrana.
- Przyspieszenie 4500× to porównanie jednego rdzenia procesora z kartą graficzną. Z nauki sieci wyłączyliśmy dodatkowo 10 sąsiednich stoków, których lawiny wchodzą na stoki testowe, żeby sieć nie mogła ściągać.
- Jedna symulacja AvaFrame trwa 107 s na laptopie (i5-1245U) i 6,7 s na DGX Spark.
- W kalibracji grubość odrywu jest założona i najlepszy wynik leży na dolnej krawędzi siatki (0,6–1,6 m). samosAT to ustawienie dla suchego śniegu, a tu użyliśmy go do lawiny mokrej.
- W kalendarzu zagrożenia kierunek wiatru jest założony (W–SW), bo IMGW nie podaje go dla tej zimy, a to on decyduje, które stoki się zapalają.
- Prywatność: nie przetwarzamy danych osobowych. Dron mierzy śnieg, nie ludzi.

## Przed zamknięciem decku

- Zrobić zrzuty do `docs/img/` (slajdy 3, 4, 6) przez `node tools/shot.mjs`, gdy demo działa na porcie 8777.
- Jeśli na slajdzie 6 zostaje `filmy/rl/trasy.png`: zakryć legendę i przepisać nazwy oraz kolory tras.
- Nie używać liczb spoza docs/12. Wycięte z poprzedniej wersji: „4×4 km”, „72 strefy”, „32 szlaki”, „121 ze 144”, „ok. 2 mln stref”.
- Eksport do PDF dopiero po zatwierdzeniu docs/16_design_decku.md.
