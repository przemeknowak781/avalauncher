# Deck i pitch: Avalauncher

Scenariusz 10 slajdów w układzie z [kompendium](00_kompendium_hackyeah.md), sekcja 5. Wszystkie liczby pochodzą z [docs/12_wyniki.md](12_wyniki.md), jedynego źródła prawdy. Ta wersja korzysta z sekcji „Kalibracja na prawdziwych lawinach” (test bez podglądania na 5 zdarzeniach) i „Porównanie z komunikatami TOPR” (stan 4.10, po 03:15). Pola „[do uzupełnienia]” i „[do potwierdzenia]” czekają na decyzję.

**Oś opowieści:** najpierw rzeczywistość, potem teza i demo, na końcu dowody ułożone od najmocniejszego. Otwieramy prawdziwą lawiną, a nie dronem, który nie może lecieć. Teza zaczyna się od zdania „Drony regularnie mierzą śnieg”. Flaga „nie wiem” to cecha odporności i trafia na slajdy 4–5. Najmocniejszym dowodem jest porównanie z prawdziwymi lawinami. Test na wymyślonym śniegu (29 wobec 16) stoi na dole drabiny i jest podpisany jako test logiki. Kompendium każe zacząć od osoby w kryzysie. Zaczynamy od prawdziwej lawiny, żeby wartość wyników wybrzmiała od pierwszych sekund, a dyżurnego wprowadzamy zdaniem-mostem na końcu slajdu 1.

**Zasady decku:** prosto, jak krowie na rowie. Krótkie zdania, jeden pomysł na slajd, duży obraz, mało tekstu. Każdą liczbę zestawiamy z czymś, co zna dwunastolatek. Przy każdej liczbie piszemy, z czym ją porównaliśmy i co jest prawdziwe, a co symulowane. Czcionka Archivo, kolory z `DESIGN.md`: pomarańcz to zagrożenie, fiolet to „nie wiem”, magenta to trasa drona. Nigdy nie piszemy „bezpiecznie” ani „skalibrowany dla Tatr”. Wolno: „przetestowane na 5 prawdziwych lawinach z Austrii i Szwajcarii”, „przykładowa kalibracja”. Nie piszemy „fizyka sprawdzona” bez dopowiedzenia, że chodzi o lawiny z Austrii i Szwajcarii, nie z Tatr. Program uczący się metodą prób i błędów nazywamy „RL”, nigdy „AI”, bo słowo „AI” zostaje dla Claude Code na slajdzie 10. Dyżurny jest postacią fikcyjną. TOPR występuje tylko jako publiczne źródło komunikatów, bez logo i bez sugestii współpracy. Deck w stylu XP subtelnym (pasek tytułu Luna, przyciski okna, pasek zadań; treść czysta, czytelna z daleka, dużo powietrza). Eksport do PDF dozwolony.

**Słowniczek (jedno zdanie na pojęcie, do użycia na slajdach):**

- **Cyfrowy bliźniak:** komputerowa kopia góry, czyli teren, szlaki, śnieg i policzone z góry lawiny.
- **Płyta śnieżna:** zbita warstwa śniegu, która może się oderwać i zjechać jako lawina.
- **AvaFrame:** otwarty program, który liczy, jak lawina płynie po prawdziwym terenie.
- **Zasięg lawiny:** jak daleko od miejsca oderwania zjechała lawina.
- **Dopasowanie:** ustawienia dobrane na tej samej lawinie, na której je sprawdzamy. Łatwe, bo wynik jest podejrzany.
- **Test bez podglądania:** ustawienia dobieramy na czterech prawdziwych lawinach i sprawdzamy na piątej, której przy dobieraniu nie było. Potem po kolei każda lawina jest tą piątą. Jak klasówka z zadaniem, którego nie było w zeszycie.
- **Flaga „nie wiem”:** stok, o którym wiedza jest za stara, żeby powiedzieć „tak” albo „nie”.
- **Stopień zagrożenia:** jedna ocena w skali 1–5 dla całych polskich Tatr, podawana w komunikatach TOPR.
- **Test zdrowego rozsądku:** porównanie, które pokazuje, czy wynik ma sens, ale nie dowodzi trafności.
- **Test logiki:** sprawdza, czy program dobrze liczy na wymyślonym śniegu, a nie, czy trafnie przewiduje lawiny w Tatrach.
- **IoU:** wspólna część dwóch obrysów podzielona przez ich łączną powierzchnię. 1 to pełna zgodność.
- **DGX Spark:** jeden mały komputer, który stoi na biurku.
- **Szybka kopia fizyki (surogat):** sieć neuronowa, która nauczyła się od AvaFrame rysować lawinę.
- **RL:** program, który uczy się metodą prób i błędów, jak gracz w grze.

---

## 1. Narracja w 5 zdaniach

1. Siódmego kwietnia 2009 w Austrii zeszła prawdziwa lawina, a fizyka z ustawieniami dobranymi na innych lawinach policzyła jej zasięg z pomyłką 25 m na 1775 m, czyli o jeden szkolny basen.
2. Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z 1566 lawinami, które ten sam program policzył z góry na prawdziwym terenie Tatr, i wskazuje dyżurnemu służby lawinowej stoki, które mogą zagrozić szlakom.
3. Gdy wiedza się starzeje, bo zamieć trzyma drona na ziemi, a satelita nie widzi przez chmury, Avalauncher mówi to wprost flagą „nie wiem”, planuje, gdzie polecieć, żeby się dowiedzieć, i działa dalej bez internetu.
4. Nie porównujemy się sami ze sobą: fizykę sprawdziliśmy na 5 prawdziwych lawinach z Austrii i Szwajcarii, za każdym razem bez podglądania (typowa pomyłka zasięgu 92 m, najgorsza 350 m), a szybką kopię fizyki na stokach Tatr, których nigdy nie widziała (zgodność obrysów 0,81).
5. Mówimy wprost, co jest symulowane, czyli śnieg na stokach, loty drona i test logiki 29 wobec 16, dlatego zaczynamy od pilota z jedną służbą lawinową na jednym szlaku i od sprawdzianu na jej własnych lawinach.

## 2. Najmocniejsze liczby

Od najmocniejszego dowodu: najpierw porównania z rzeczywistością, potem prawdziwe dane wejściowe, na końcu test logiki na wymyślonym śniegu.

| Liczba | Z czym porównaliśmy | Co to znaczy po ludzku | Źródło (docs/12) |
| --- | --- | --- | --- |
| Typowa pomyłka zasięgu (mediana) **92 m**, średnio **154 m**, najgorzej **+350 m**. **5** prawdziwych lawin (3 z Austrii, 2 ze Szwajcarii), **234** symulacje, w **4 z 5** prób wygrywa ta sama kalibracja samosAT | Z obrysami prawdziwych lawin zmierzonymi w terenie. Ustawienia dobrane na czterech lawinach, sprawdzone na piątej (test bez podglądania) | Typowa pomyłka jest krótsza niż boisko piłkarskie. Najgorsza (Kleiner Ötscherbach) to prawie okrążenie bieżni. W 4 z 5 prób wygrywa to samo ustawienie. Podejrzewamy brak lasu (Filisur: każdy z 43 przebiegów jedzie za daleko) i porywania śniegu (Eiskar: −227 m); wariant z lasem i porywaniem z danych zdarzeń (parametry domyślne, niestrojone) nie zmniejszył błędu: średnio 153,7 m, mediana 124 m. Model bez lasu i bez porywania. Przykładowa kalibracja, nie dla Tatr. | Kalibracja na prawdziwych lawinach |
| Popeletzbach: **+25 m** na **1775 m**, IoU **0,70** | Z prawdziwą lawiną z Austrii (7.04.2009), przy ustawieniu dobranym bez niej | Pomyłka to jeden szkolny basen na drodze dłuższej niż cztery okrążenia bieżni. Na 10 kratek zamalowanych przez prawdziwą lawinę albo przez nas 7 zamalowały obie. To najlepszy z pięciu testów, dlatego zawsze mówimy też o pozostałych. Dopasowanie do tej samej lawiny (21 przebiegów: +20 m, IoU 0,73) podajemy tylko na dopytanie. | Kalibracja na prawdziwych lawinach; Popeletzbach: opublikowany wynik |
| Zgodność obrysów **0,81** na **3** stokach spoza nauki (dodatkowo **10** sąsiednich wyjętych), **2,3 ms** zamiast **10,43 s**, ok. **4500×** | Z fizyką AvaFrame na stokach Tatr, których sieć nie widziała | Na 10 kratek 8 wspólnych. Lawina gotowa szybciej niż mrugnięcie oka. Sędzią jest tu fizyka, a fizykę sprawdziliśmy na prawdziwych lawinach. Najsłabszy stok testowy to Sucha Dolina NE (0,72) i pokazujemy właśnie go. | Sieć zastępcza (surogat) AvaFrame |
| 12–13.01.2025 stopień **1 → 2 → 3**, kalendarz **9**, potem **12** sektorów. Przy „trójce” **1** trafienie (13.01), **1** pominięcie (15–16.03), **1** doba spóźnienia (6.04) | Z oficjalnym stopniem zagrożenia z komunikatów TOPR cytowanych w prasie, zima 2024/25 | W styczniu nasza uproszczona reguła zapala stoki w te same dni, w które rośnie oficjalny stopień, choć już 10–11.01 kalendarz zapalał 8 sektorów, gdy TOPR był na 1 (nie rozstrzygamy: wyprzedzenie czy fałszywy alarm). W marcu jedną „trójkę” przeoczyła, w kwietniu spóźniła się o dobę. Stopień to jedna ocena dla całych Tatr, a my liczymy pojedyncze stoki, więc to test zdrowego rozsądku, nie walidacja. | Porównanie z komunikatami TOPR |
| Sentinel-2: 11.01 chmury nad **100%** terenu, 12.01 brak przelotu, 13.01 chmury nad **86%**. Pierwszy czysty obraz 16.01, trzy dni po zamieci | Z prawdziwymi zdjęciami satelitarnymi z dni zamieci | Satelita widział tyle, co ty przez zaparowaną szybę. Nawet w czysty dzień pokazuje, gdzie leży śnieg, a nie ile go jest. Dlatego dron. | Satelita w dniach zamieci |
| **+34 cm** nowego śniegu w 3 dni, **72 h** zamieci, pokrywa **51 → 85 cm** | Nie porównanie, tylko prawdziwe dane wejściowe: IMGW-PIB, Kasprowy Wierch, 11–13.01.2025 | Więcej nowego śniegu niż szkolna linijka. Pokrywa urosła od kolana prawie do biodra dorosłego. To prawdziwa burza z poranków demo. | Prawdziwa pogoda |
| **1566** lawin w **30,4 min**, **0** nieudanych. **48 z 58** stoków sięga szlaku | Nie porównanie, tylko dane wejściowe: AvaFrame na terenie GUGiK NMT, a grubość płyty to scenariusze | Cała biblioteka liczy się na jednym komputerze na biurku (DGX Spark, 12 rdzeni) krócej, niż trwa lekcja. Większość stromych stoków może zrzucić lawinę na szlak, więc trzeba wiedzieć który. Liczysz raz, potem tylko sprawdzasz, jak z tabliczką mnożenia. | Biblioteka scenariuszy (fizyka) |
| **29 wobec 16** groźnych stoków oflagowanych po locie, **86 wobec 71** zdjętych „nie wiem”, niepewność **−23% wobec −7%** (**30** poranków, lot **20 min**) | Z samym sobą: nasz plan lotu wobec lotu wzdłuż szlaku, na prawdziwej pogodzie IMGW i wymyślonym śniegu | Ten sam dron i ten sam czas, zmienia się tylko trasa. Test logiki: sprawdza, czy program dobrze liczy, a nie, czy trafnie przewiduje lawiny w Tatrach. | Dowód logiki silnika |
| RL **19,9%** wobec prostego planu **20,2%** (lot wzdłuż szlaku **5,4%**), **10,4 mln** próbnych poranków w **6 min**, test na **1000** poranków | Bardziej wymyślna metoda wobec naszego prostego planu | Remis to nie wygrana, więc RL nie wdrożyliśmy. Najpierw sprawdzamy, potem obiecujemy. To inny test niż 29 wobec 16, więc ich nie zestawiamy. | RL dla planu przelotu |

## 3. Slajdy

Czas slajdów sumuje się do 3:00: prawdziwa lawina i teza 0:45, demo z odpornością 1:05, dowody 0:55, pilot i zamknięcie 0:15.

Katalogu `docs/img/` jeszcze nie ma. Zrzuty z demo robi `node tools/shot.mjs <url> <plik.png> [szer wys czekanie_ms] [js]`, gdy demo działa na `http://localhost:8777`. Zrzuty są obowiązkowe przed zamknięciem decku. Zapasowe obrazy podajemy przy slajdach.

Stopka na każdym slajdzie z mapą Tatr: „Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap · Śnieg na stokach: scenariusz syntetyczny”.

Na slajdach 6–8 w rogu stoi mały znacznik drabiny dowodów w czterech stopniach: prawdziwe lawiny → stoki spoza nauki → komunikaty TOPR → test logiki. Czwarty stopień jest szary i przerywany. Bieżący stopień jest podświetlony. Grafikę rysuje projekt decku (docs/16_design_decku.md).

### Slajd 1. Prawdziwa lawina

**Nagłówek:** Ta lawina zeszła naprawdę. Fizyka z ustawieniami dobranymi na innych lawinach pomyliła się o 25 m na 1775 m.

**Co mówię:** Siódmy kwietnia 2009, Tyrol w Austrii. Z tego żlebu zeszła prawdziwa lawina. Przerywana linia to jej ślad, zmierzony w terenie. Ciemna linia to nasza fizyka. Ustawienia dobraliśmy na innych prawdziwych lawinach, tej nie podglądaliśmy. Lawina przejechała 1775 metrów, a my pomyliliśmy się o 25, tyle co szkolny basen. To nasz najlepszy z pięciu takich testów. Resztę, także najgorszy, pokażę za chwilę. Z takimi lawinami co rano mierzy się dyżurny służby lawinowej w Tatrach.

**Co pokazuję:** panel Popeletzbach z `filmy/kalibracja/5_lawin.png`, wysoki, po lewej. Przycinamy go nad wierszem „NAJLEPSZY PRZEBIEG”, bo ten wiersz podaje inną liczbę (+15 m) niż nagłówek. Zostaje wiersz „TEST BEZ TEGO ZDARZENIA: +25 m zasięgu · IoU 0,70”. Na slajdzie podpisujemy tylko dwie linie: przerywana = prawdziwa lawina, ciemna ciągła = nasza fizyka bez podglądania. Pomarańczowa plama pod spodem to najlepsze dopasowanie, więc w legendzie piszemy „pomarańcz: dopasowanie”. Jeśli projekt decku pozwoli, lepiej wyrenderować wariant panelu bez plamy (`tools/calibration/board_multi.py`). Po prawej dwie wielkie liczby, jedna pod drugą: „1775 m: tyle przejechała prawdziwa lawina” i „25 m: tyle się pomyliliśmy, jeden szkolny basen”. Pod nimi mniejszym drukiem: „Wspólna część obrysów 0,70: na 10 kratek 7 wspólnych”. Podpis: „Popeletzbach, Tyrol Wschodni (Austria), mokra lawina, 7.04.2009. Test bez podglądania: ustawienia dobrane na 4 innych lawinach. Najlepszy z 5 testów, wszystkie na slajdzie 6. Przykładowa kalibracja, nie dla Tatr. Obrys: OpenNHM/AvaFrameData (F. Perzl, BFW), CC BY 4.0 · Teren: Land Tirol, CC BY 4.0 AT · Model: AvaFrame com1DFA”. Bez nazwy projektu, bez logo, bez interfejsu.

**Czas:** 25 s (0:00–0:25).

### Slajd 2. Teza

**Nagłówek:** Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z 1566 lawinami policzonymi z góry.

**Co mówię:** Tym samym programem, AvaFrame, policzyliśmy z góry 1566 lawin na prawdziwym terenie Tatr. Nad Halą Gąsienicową 48 z 58 stromych stoków może zrzucić lawinę na szlak. Dyżurny nie obejrzy wszystkich. Dlatego dron mierzy śnieg, a Avalauncher od razu szuka odpowiedzi wśród gotowych lawin, jak w tabliczce mnożenia. Reguła „30 centymetrów w 3 dni” mówi kiedy, ale nie mówi, który stok.

**Co pokazuję:** `filmy/hero/hero_S22_samosAT_2.0_mid.png` (lżejsza kopia: `web/media/hero_S22_samosAT_2.0_mid.jpg`): jedna lawina z biblioteki, Sucha Dolina NE, która zalewa żółty szlak. Górny pasek z tytułem i licznikiem „t = 34 s” przycinamy, bo licznik myli się z 34 cm. Podpis: „Jedna z 1566: Sucha Dolina NE, płyta 2,0 m. Ten stok zapali się w demo”. Pod obrazem pasek dużym drukiem z dwiema alternatywami: „Reguła »co najmniej 30 cm w 3 dni« mówi kiedy, ale nie który stok · Wielkie biblioteki lawin (Bühler i in. 2022) nie mówią, gdzie wiedza się zestarzała · Avalauncher mówi jedno i drugie”. Stopka: „Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap · Lawina: symulacja AvaFrame, śnieg syntetyczny”. Dyżurny jest postacią fikcyjną, bez nazwy i logo TOPR.

**Czas:** 20 s (0:25–0:45).

### Slajd 3. Trzy kroki dyżurnego

**Nagłówek:** Dyżurny robi trzy kroki: otwiera mapę, klika stok i ustawia czas lotu.

**Co mówię:** Teren, szlaki i pogoda są prawdziwe, a śnieg na stokach i loty drona wymyślone. Dwunasty stycznia 2025, prawdziwa pogoda IMGW z Kasprowego: od wczoraj sypie i wieje. O świcie dron zmierzył śnieg (w demo: przelot syntetyczny). Krok pierwszy: mapa. Na pomarańczowo świecą Sucha Dolina NE i Beskid NE, czyli stoki, które mogą zagrozić szlakowi. Krok drugi: klikam Suchą Dolinę, stok z poprzedniego slajdu, i widzę, do którego odcinka szlaku dochodzą podobne lawiny. Krok trzeci to suwak czasu lotu.

**Co pokazuję:** trzy zrzuty z dużymi cyframi 1, 2, 3:

1. `docs/img/krok1_mapa.png`: mapa dnia 1 z dwoma zapalonymi stokami. `node tools/shot.mjs http://localhost:8777 docs/img/krok1_mapa.png`
2. `docs/img/krok2_stok.png`: karta klikniętej Suchej Doliny NE z odcinkiem szlaku. `node tools/shot.mjs http://localhost:8777 docs/img/krok2_stok.png 1440 860 3500 "[js klikający sektor S22]"`
3. `docs/img/krok3_trasa.png`: suwak czasu lotu na 20 min i magentowa trasa. `node tools/shot.mjs "http://localhost:8777/?day=2" docs/img/krok3_trasa.png`

Podpis: „Laptop i przeglądarka, bez kont i integracji”. Legenda: pomarańcz = może zagrozić szlakowi · fiolet = nie wiem · magenta = trasa drona. Stopka: „Pogoda: IMGW-PIB (prawdziwa) · Grubość płyty i loty drona: syntetyczne · Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap”. Zapas, dopóki nie ma zrzutów: `filmy/hero/mapa_zasiegow.png` z przyciętym podtytułem i podpisem „48 z 58 stoków sięga szlaku w symulacjach AvaFrame”.

**Czas:** 25 s (0:45–1:10). Na scenie demo na żywo.

### Slajd 4. „Nie wiem”

**Nagłówek:** Gdy wiedza się starzeje, Avalauncher mówi to wprost: „nie wiem”. I pokazuje, gdzie polecieć, żeby się dowiedzieć.

**Co mówię:** Trzynasty stycznia, trzeci dzień zamieci. Spadło 34 centymetry nowego śniegu, więcej niż szkolna linijka. Dron stoi w hangarze. Wczorajszy pomiar starzeje się jak wczorajsza gazeta, więc kolejne stoki dostają fioletową flagę „nie wiem”. Nie znikają z listy. Ustawiam 20 minut lotu i pojawia się trasa na pierwsze okno pogody. Klikam „Wykonaj przelot”: mgła znika tam, gdzie dron zmierzył.

**Co pokazuję:** dwa zrzuty obok siebie:

- `docs/img/dzien2_mgla.png` z podpisem „13.01.2025: zamieć, bez lotu”. `node tools/shot.mjs "http://localhost:8777/?day=2" docs/img/dzien2_mgla.png`
- `docs/img/po_przelocie.png` z podpisem „Po przelocie 20 min”. `node tools/shot.mjs "http://localhost:8777/?day=2" docs/img/po_przelocie.png 1440 860 3500 "[js: przelot 20 min]"`

Nad zrzutami jedna linijka: „Kasprowy Wierch, 11–13.01.2025: +34 cm w 3 dni, 72 h zamieci, pokrywa 51 → 85 cm (IMGW-PIB, dane prawdziwe)”. Liczby fioletowych stoków nie podajemy, bo nie ma jej w docs/12. Legenda jak na slajdzie 3. Stopka: „Pogoda: IMGW-PIB (prawdziwa) · Grubość płyty i loty drona: syntetyczne · Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap”. Na scenie demo na żywo, a w zapasie surowe ujęcia ekranu do scenariusza filmu (docs/15_wideo.md).

**Czas:** 20 s (1:10–1:30).

### Slajd 5. Odporność

**Nagłówek:** Bez lotu, bez satelity i bez sieci Avalauncher działa dalej, a decyzję zostawia człowiekowi.

**Co mówię:** Czy pomógłby satelita? Sprawdziliśmy prawdziwe zdjęcia Sentinel-2. Jedenastego stycznia nad naszym terenem były same chmury. Dwunastego satelita nie przeleciał. Trzynastego chmury zakrywały 86 procent. A gdy padnie internet? 1566 lawin leży na laptopie, a przy pogodzie widać ostatni zapisany odczyt IMGW i to, ile godzin temu go zrobiono. To jest odporność: wskazujemy stoki do sprawdzenia, zanim ktoś wejdzie na szlak, wysyłamy drona tam, gdzie wiedza jest najsłabsza, i działamy, gdy brakuje danych. Decyduje człowiek.

**Co pokazuję:** w tle lewy panel „Barwy naturalne” z `filmy/satelita/porownanie.png`, bez nagłówka i podtytułu planszy, bo podtytuł podaje „siatka 4 × 4 km”, a tej liczby nie ma w docs/12. Plik `web/data/sentinel_truecolor.jpg` ma tylko 400×400 px, więc nadaje się najwyżej na miniaturę. Na tle trzy kafelki z datami: „11.01: chmury nad 100% terenu” · „12.01: brak przelotu” · „13.01: chmury nad 86%”. Pod nimi: „Pierwszy czysty obraz: 16.01, trzy dni po zamieci. Satelita pokazuje, gdzie leży śnieg, ale nie ile go jest. Grubość płyty musi zmierzyć dron.” Po prawej trzy ikonki: brak lotu → flaga „nie wiem” i plan lotu · brak sieci → 1566 lawin na laptopie (30,4 min, 0 nieudanych, jeden DGX Spark) · brak świeżego odczytu IMGW → ostatni zapisany odczyt i jego wiek. Na dole trzy hasła dla kategorii Defence, dużym drukiem: może pomóc zapobiegać: wskazuje stoki do sprawdzenia, zanim ktoś wejdzie na szlak · może zmniejszać skutki: kieruje drona tam, gdzie wiedza jest najsłabsza · działa przy braku danych. Narzędzie jest niezwalidowane, więc hasła mówią „może”, nie „robi”. Stopka: „Zawiera zmodyfikowane dane Copernicus Sentinel (2025) · Sentinel-2 L2A przez Element84 Earth Search (AWS Open Data)”.

Odczyt IMGW na żywo jest poza scenariuszem demo. Przy błędzie sieci albo serwera IMGW aplikacja pokazuje ostatni zapisany odczyt z jego wiekiem (`web/app.js`, funkcje `live` i `liveText`). Awarię da się pokazać na żywo bez wyłączania Wi-Fi: menu Plik → „Symuluj awarię łączności” (`web/index.html`).

**Czas:** 20 s (1:30–1:50).

### Slajd 6. Sprawdzian na 5 prawdziwych lawinach

**Nagłówek:** Sprawdziliśmy fizykę na 5 prawdziwych lawinach z Austrii i Szwajcarii, za każdym razem bez podglądania: typowa pomyłka 92 m, najgorsza 350 m.

**Co mówię:** Nie porównujemy się sami ze sobą. Do jednej lawiny łatwo dopasować fizykę, bo żleb prowadzi lawinę jak tor saneczkowy. Dlatego wzięliśmy pięć prawdziwych lawin z Austrii i Szwajcarii, z obrysami zmierzonymi w terenie. Ustawienia dobieramy na czterech, a sprawdzamy na piątej, której nie widziały. Potem bierzemy następną, aż każda będzie tą sprawdzaną. Jak klasówka z zadaniem, którego nie było w zeszycie. Typowa pomyłka to 92 metry, krócej niż boisko piłkarskie. Średnio 154. Najgorzej 350 metrów za daleko. Podejrzewamy dwie przyczyny: nasz model nie ma lasu, a lawiny w Szwajcarii stanęły w lesie, i nie liczy śniegu, który lawina zbiera po drodze. Sprawdziliśmy to: wariant z lasem i porywaniem śniegu z danych zdarzeń, na parametrach domyślnych, nie zmniejszył błędu (średnio 153,7 m, mediana 124 m). Przyczyn jeszcze nie znamy i mówimy to wprost. W czterech z pięciu prób wygrało to samo ustawienie.

**Co pokazuję:** `filmy/kalibracja/5_lawin.png` (plansza istnieje, 1920×1080). Pięć paneli z obserwowanym obrysem (przerywana linia) i śladem z testu bez podglądania (ciemna linia). Wiersze „NAJLEPSZY PRZEBIEG” przyciemniamy albo wycinamy, bo slajd mówi o teście bez podglądania. Dolne zdanie planszy z „94 m” wycinamy, bo to ustawienie dobrane na tych samych pięciu lawinach, czyli nie walidacja. W rogu wielka liczba „92 m”, pod nią „typowa pomyłka, krócej niż boisko piłkarskie · średnio 154 m · najgorzej +350 m · w 4 z 5 prób to samo ustawienie”. Pasek: „Dopasowanie do jednej lawiny to jeszcze nie sprawdzian. Sprawdzianem jest lawina, której nie użyliśmy do dobierania ustawień.” Podpis: „Sprawdzone na prawdziwych lawinach z Austrii i Szwajcarii. Przykładowa kalibracja, nie dla Tatr. Model bez lasu i bez porywania śniegu, grubość odrywu zmierzona tylko na Eiskar. Dane zdarzeń: OpenNHM/AvaFrameData 1.0, CC BY 4.0 (dane: F. Perzl, BFW; WLV; SLF Davos, wg metadanych zdarzeń w `web/data/calibration.json`) · Teren: Land Tirol 5 m, CC BY 4.0 AT; BEV ALS DTM 1 m, CC BY 4.0; © swisstopo swissALTI3D 2 m (2019) [licencja do potwierdzenia przed pokazem] · Model: AvaFrame com1DFA 2.1”. Znacznik drabiny: stopień 1.

**Czas:** 25 s (1:50–2:15).

### Slajd 7. Szybka kopia na stokach, których nie widziała

**Nagłówek:** Szybką kopię fizyki sprawdziliśmy na stokach Tatr, których nigdy nie widziała: zgodność obrysów 0,81, ok. 4500 razy szybciej.

**Co mówię:** Szybka kopia fizyki to sieć neuronowa, która uczyła się od AvaFrame. W przyszłości może przyspieszyć liczenie nowych stoków; dziś to dowód koncepcji na 3 stokach tego samego wycinka. Sprawdziliśmy ją na trzech stokach Tatr, których nigdy nie widziała. Dziesięć sąsiednich schowaliśmy, żeby nie mogła ściągać. Na 10 kratek 8 pokrywa się z fizyką. Lawinę rysuje szybciej niż mrugnięcie oka. Kopię porównujemy z fizyką, a fizykę z prawdziwymi lawinami.

**Co pokazuję:** `filmy/surrogate/porownanie.png` (lżejsza kopia: `web/media/surrogate_porownanie.jpg`), przycięty do paska nagłówka (10,4 s · 2,3 ms · 0,81 · ≈ 4500×) i do wiersza Sucha Dolina NE (AvaFrame | szybka kopia | różnica), czyli stoku z demo. Prawy podpis wiersza („IoU 0,70, średnio 0,72, 27 przebiegów”) zasłaniamy, bo pojedynczego wyniku 0,70 i liczby 27 nie ma w docs/12. Zamiast niego: „Sucha Dolina NE: 0,72, najsłabszy z 3 stoków testowych, pokazujemy go uczciwie”. Duży napis: „3 stoki, których sieć nie widziała. Z nauki wyjęliśmy też 10 sąsiednich stoków, żeby nie mogła ściągać.” Pasek z łańcuchem dowodów: prawdziwe lawiny ↔ fizyka (slajdy 1 i 6) · fizyka ↔ szybka kopia (ten slajd). Podpis: „2,3 ms na karcie graficznej zamiast 10,43 s na jednym rdzeniu procesora. Dowód koncepcji: kopia przybliża AvaFrame, nie zastępuje go. Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap · Grubość płyty: scenariusze, nie pomiar”. Na żywo zamiast planszy: `web/media/landing/surogat_suwak.mp4`. Znacznik drabiny: stopień 2.

**Czas:** 15 s (2:15–2:30).

### Slajd 8. Drabina dowodów

**Nagłówek:** Najmocniejsze dowody to porównania z prawdziwymi lawinami. Test na wymyślonym śniegu podpisujemy uczciwie: to test logiki.

**Co mówię:** Naszą prostą regułę „kiedy” porównaliśmy też z komunikatami TOPR z tej zimy. W styczniu stopień rośnie w te same dni co u nas, choć już 10–11.01 kalendarz zapalał 8 sektorów, gdy TOPR był na 1, i nie rozstrzygamy, czy to wyprzedzenie, czy fałszywy alarm. W marcu jedną „trójkę” przeoczyliśmy, a w kwietniu spóźniliśmy się o dobę. Na dole drabiny jest test logiki na wymyślonym śniegu: 29 wobec 16. RL zremisował, więc go nie wdrożyliśmy.

**Co pokazuję:** drabina dowodów, tabela w trzech kolumnach, od najmocniejszego wiersza, jedna liczba w wierszu:

| Z czym porównaliśmy | Wynik | Co to sprawdza |
| --- | --- | --- |
| 5 prawdziwych lawin z Austrii i Szwajcarii, test bez podglądania | typowa pomyłka 92 m | czy fizyka trafia w rzeczywistość |
| 3 stoki Tatr, których sieć nie widziała | 0,81 | czy szybka kopia nie ściąga (sędzią jest fizyka) |
| komunikaty TOPR z zimy 2024/25, cytowane w prasie | przy „trójce”: 1 trafienie, 1 pominięcie, 1 doba spóźnienia | zdrowy rozsądek uproszczonej reguły, nie walidacja |
| wymyślony śnieg na prawdziwej pogodzie (wiersz szary, przerywany) | 29 wobec 16 | test logiki: czy program dobrze liczy |

Wąski pasek pod tabelą: „Sprawdziliśmy też RL: 19,9% wobec 20,2% spadku niepewności (1000 poranków). Remis, więc zostaje prosty plan.” Pod nim pasek w trzech kolumnach, małym drukiem. PRAWDZIWE: teren GUGiK NMT · szlaki OpenStreetMap · pogoda IMGW-PIB Kasprowy Wierch, zima 2024/25 · zdjęcia Sentinel-2 · 5 lawin do porównania (OpenNHM/AvaFrameData) · stopnie TOPR z prasy. PRZYBLIŻONE: fizyka AvaFrame (bez lasu i porywania śniegu) · szybka kopia fizyki · kalendarz zagrożenia (uproszczona reguła). SYMULOWANE LUB ZAŁOŻONE: grubość płyty na stokach · loty i odczyty drona · „prawda” w teście logiki · kierunek wiatru (W–SW) · śnieg w filmach 3D. Linia werdyktu dużym drukiem: „Fizyka: sprawdzana na lawinach z Austrii i Szwajcarii, nie w Tatrach · Plan lotu: sprawdzony testem logiki · Prognoza dla Tatr: jeszcze niesprawdzona”. Na dole: „Avalauncher nie jest zwalidowaną prognozą dla Tatr.” Przypis: „Stopnie z komunikatów TOPR cytowanych w prasie (PAP przez opoka.org.pl, rmf24.pl, dziennik.pl i in., źródła w docs/12), bez logo i bez współpracy z TOPR.” Znacznik drabiny: cała drabina. Obok tego wiersza nie stawiamy hasła „wykrywa wcześniej”, bo docs/12 nie rozstrzyga, czy 10–11.01 to wyprzedzenie, czy fałszywy alarm.

**Czas:** 15 s (2:30–2:45).

### Slajd 9. Pilot

**Nagłówek:** Pierwszy krok to pilot z jedną służbą lawinową na jednym szlaku i sprawdzian na jej własnych lawinach.

**Co mówię:** W Tatrach zrobimy to samo co w Austrii i Szwajcarii: sprawdzimy fizykę na miejscowych lawinach, bez podglądania. Potem przyjdą prawdziwe loty nad jednym szlakiem. Kolejny masyw: najpierw AvaFrame i lokalny sprawdzian; szybka kopia do sprawdzenia.

**Co pokazuję:** przyciemniony `filmy/hero/mapa_zasiegow.png` (lżejsza kopia: `web/media/landing/mapa_zasiegow_orbit.jpg`) z przyciętym podtytułem, bo liczby „1291 z 1566” nie ma w docs/12. Na nim oś w trzech krokach: sprawdzian na lawinach z Tatr → prawdziwe loty nad jednym szlakiem → kolejny masyw (najpierw AvaFrame i lokalny sprawdzian; szybka kopia do sprawdzenia). Drobnym drukiem: „Do sprawdzenia: zgody na loty nad parkiem narodowym”. Stopka: „Teren: GUGiK NMT · Szlaki: © współtwórcy OpenStreetMap · Śnieg na stokach: scenariusz syntetyczny”.

**Czas:** 10 s (2:45–2:55).

### Slajd 10. Zespół, AI, licencje

**Nagłówek:** Zbudowaliśmy to w jedną noc z otwartych danych i z pomocą AI, a każde źródło jest podpisane.

**Co mówię:** Rano dyżurny dalej decyduje sam, ale ma fizykę przetestowaną na 5 prawdziwych lawinach z Austrii i Szwajcarii (typowa pomyłka 92 m), świeży pomiar z drona i uczciwe „nie wiem”. (Slajd zostaje na ekranie podczas pytań.)

**Co pokazuję:** kod QR do demo (<https://przemeknowak781.github.io/avalauncher/>, gdy repo będzie publiczne) i link do repo (github.com/przemeknowak781/avalauncher). Zespół: [do uzupełnienia: imiona i role]. AI: Claude Code (Claude Opus 5.5) pisał kod, teksty i wizualizacje, a zakres i tezę ustalili ludzie. Dane: GUGiK (teren, ortofotomapa), © współtwórcy OpenStreetMap (ODbL), IMGW-PIB (dane przetworzone), zmodyfikowane dane Copernicus Sentinel (2025) przez Element84 Earth Search (AWS Open Data), OpenNHM/AvaFrameData 1.0 (CC BY 4.0, DOI 10.5281/zenodo.20701552), Land Tirol (CC BY 4.0 AT), BEV ALS DTM 1 m (CC BY 4.0), © swisstopo swissALTI3D 2 m [licencja do potwierdzenia przed pokazem], stopnie TOPR z komunikatów cytowanych w prasie. Programy: AvaFrame (EUPL-1.2), pełna lista w `docs/10_ai_i_licencje.md`. Nasz kod: MIT. W tle przyciemniony kadr z `filmy/3d/3d_S27_samosAT_2.0.mp4` (Kasprowy Wierch W, śnieg syntetyczny). Hasło na dole: „Drony mierzą śnieg. Avalauncher wskazuje stoki, które mogą zagrozić szlakom.” Bez nazwy i logo TOPR.

**Czas:** 5 s (2:55–3:00).

---

## 4. Pitch na 3 minuty

Zdania krótkie, do mówienia na głos. Jeśli limit będzie inny, skaluj proporcjonalnie. Gdy przy próbie wyjdzie za długo, tnij najpierw zdanie o satelicie (slajd 5), potem zdanie o RL (slajd 8). Najgorszy wynik (350 m) i przyznanie się do pomyłek przy „trójkach” zostają zawsze.

**Zdanie otwierające:** Siódmy kwietnia 2009, Tyrol w Austrii. Z tego żlebu zeszła prawdziwa lawina.

**Zdanie zamykające:** Rano dyżurny dalej decyduje sam, ale ma fizykę przetestowaną na 5 prawdziwych lawinach z Austrii i Szwajcarii (typowa pomyłka 92 m), świeży pomiar z drona i uczciwe „nie wiem”.

**0:00–0:25. Prawdziwa lawina, bez nazwy projektu (slajd 1)**

> Siódmy kwietnia 2009, Tyrol w Austrii. Z tego żlebu zeszła prawdziwa lawina. Przerywana linia to jej zmierzony ślad. Ciemna to nasza fizyka, ustawiona bez podglądania tej lawiny. Lawina przejechała 1775 metrów. Pomyliliśmy się o 25, tyle co szkolny basen. To najlepszy z pięciu testów, resztę pokażę. Z takimi lawinami co rano mierzy się dyżurny w Tatrach.

**0:25–0:45. Teza (slajd 2)**

> Tym samym programem policzyliśmy z góry 1566 lawin na prawdziwym terenie Tatr. Nad Halą Gąsienicową 48 z 58 stromych stoków może zrzucić lawinę na szlak. Dyżurny nie obejrzy wszystkich. Dlatego drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z gotowymi lawinami, jak z tabliczką mnożenia.

**0:45–1:10. Demo na żywo, 12 stycznia (slajd 3)**

> Teren, szlaki i pogoda są prawdziwe, a śnieg na stokach i loty drona wymyślone. Dwunasty stycznia 2025, o świcie dron zmierzył śnieg. Krok pierwszy: mapa. Świecą Sucha Dolina NE i Beskid NE. Krok drugi: klikam Suchą Dolinę i widzę, do którego odcinka szlaku dochodzą podobne lawiny.

**1:10–1:30. 13 stycznia (slajd 4)**

> Trzynasty stycznia: 34 centymetry nowego śniegu w trzy dni, więcej niż szkolna linijka. Dron stoi. Pomiar się starzeje, więc kolejne stoki dostają fioletową flagę „nie wiem”. Krok trzeci: ustawiam 20 minut lotu i pojawia się trasa. Klikam „Wykonaj przelot”. Mgła znika tam, gdzie dron zmierzył.

**1:30–1:50. Odporność (slajd 5)**

> Satelita w te dni nie widział terenu. Bez internetu 1566 lawin dalej leży na laptopie. Avalauncher wskazuje stoki do sprawdzenia, zanim ktoś wejdzie na szlak, i działa, gdy brakuje danych. Decyduje człowiek.

**1:50–2:15. Sprawdzian na prawdziwych lawinach (slajd 6)**

> Nie porównujemy się sami ze sobą. Do jednej lawiny łatwo dopasować fizykę, więc wzięliśmy pięć prawdziwych lawin z Austrii i Szwajcarii. Dobieramy ustawienia na czterech, sprawdzamy na piątej, po kolei. Jak klasówka z zadaniem spoza zeszytu. Typowa pomyłka: 92 metry, krócej niż boisko. Najgorsza: 350 metrów. Podejrzewamy brak lasu i porywania śniegu, ale wariant z lasem i porywaniem nie zmniejszył błędu, więc przyczyn jeszcze nie znamy. W czterech z pięciu prób wygrało to samo ustawienie.

**2:15–2:30. Stoki, których sieć nie widziała (slajd 7)**

> Szybka kopia fizyki to dowód koncepcji. Na stokach Tatr, których nigdy nie widziała, na 10 kratek 8 pokrywa się z fizyką. Lawina jest gotowa szybciej niż mrugnięcie oka.

**2:30–2:45. Drabina dowodów (slajd 8)**

> Prostą regułę „kiedy” porównaliśmy z komunikatami TOPR: w styczniu stopień rośnie w te same dni, choć już 10–11.01 zapalaliśmy 8 sektorów przy TOPR na 1 (wyprzedzenie czy fałszywy alarm, nie rozstrzygamy), w marcu jedna „trójka” przeoczona, w kwietniu doba spóźnienia. Na dole drabiny jest test logiki na wymyślonym śniegu: 29 wobec 16. RL zremisował, więc go nie wdrożyliśmy.

**2:45–2:55. Pilot (slajd 9)**

> Pierwszy krok to pilot z jedną służbą lawinową na jednym szlaku i sprawdzian na jej własnych lawinach.

**2:55–3:00. Zamknięcie (slajd 10)**

> Rano dyżurny dalej decyduje sam, ale ma fizykę przetestowaną na 5 prawdziwych lawinach z Austrii i Szwajcarii (typowa pomyłka 92 m), świeży pomiar z drona i uczciwe „nie wiem”.

## 5. Pytania jury

Po jednym zdaniu na pytanie. Zapisać na kartce przy stanowisku.

1. **Czy to tylko porównanie z samym sobą?** Nie: fizykę sprawdziliśmy na 5 prawdziwych lawinach z Austrii i Szwajcarii, za każdym razem z ustawieniem dobranym bez tej lawiny (typowa pomyłka zasięgu 92 m, średnio 154 m, najgorzej 350 m), szybką kopię z fizyką na stokach, których nie widziała (0,81), a kalendarz z komunikatami TOPR z prasy (przy „trójce” 1 trafienie, 1 pominięcie, 1 doba spóźnienia); z samymi sobą porównujemy tylko plan lotu (29 wobec 16) i podpisujemy to jako test logiki.
2. **Czemu nie wystarczy jedna lawina?** Do jednej łatwo dopasować ustawienia, bo żleb prowadzi lawinę jak tor saneczkowy (na Popeletzbach kilka różnych ustawień daje prawie to samo IoU: 0,727, 0,724, 0,718), dlatego liczy się test bez podglądania na pięciu lawinach: typowo 92 m.
3. **Kto za to zapłaci?** Pierwszy zapłaci ten, kto dziś odpowiada za szlaki zimą, czyli służba lawinowa albo park narodowy, a w pilocie nasza część kosztu to laptop i jedno liczenie biblioteki na jeden teren, bo kod jest otwarty (MIT). [do potwierdzenia przed pitchem: kto realnie kupuje i utrzymuje]
4. **Co z fałszywymi alarmami?** W teście logiki Avalauncher dał 0 fałszywych alarmów wobec 25 dla reguły „30 cm w 3 dni”, kosztem 549 flag „nie wiem”, które proszą o pomiar, a nie ogłaszają zagrożenia; na prawdziwej zimie 10–11.01 kalendarz zapalał już po 8 sektorów, gdy TOPR był na 1, i nie rozstrzygamy, czy to wyprzedzenie, czy fałszywy alarm.
5. **Czy to działa bez sieci?** Tak: 1566 lawin leży na laptopie, ekran działa w przeglądarce bez internetu, a gdy sieć albo serwer IMGW milczy, widać ostatni zapisany odczyt i jego wiek (pokażemy to na żywo: menu Plik → „Symuluj awarię łączności”).
6. **Czym to się różni od komunikatu TOPR?** Komunikat podaje jeden stopień 1–5 dla całych polskich Tatr, a Avalauncher go nie zastępuje, tylko pomaga temu, kto go pisze, bo wskazuje konkretne stoki nad konkretnymi szlakami i mówi, gdzie wiedza jest za stara; nasz kalendarz porównaliśmy z komunikatami cytowanymi w prasie i przy „trójce” mamy jedno trafienie (13.01), jedno pominięcie (15–16.03) i jedno opóźnienie o dobę (6.04).
7. **Czy to jest sprawdzone w Tatrach?** Jeszcze nie: fizykę sprawdziliśmy na 5 prawdziwych lawinach z Austrii i Szwajcarii (typowo 92 m), a 29 wobec 16 to test logiki na wymyślonym śniegu, dlatego pilot zaczyna się od takiego samego sprawdzianu na lawinach z Tatr.
8. **Czemu nie satelita?** W dniach zamieci satelita nie widział terenu (11.01 chmury nad 100%, 12.01 brak przelotu, 13.01 chmury nad 86%), a nawet w czysty dzień pokazuje, gdzie leży śnieg, a nie ile go jest.
9. **Czemu plan lotu nie korzysta z RL?** Sprawdziliśmy go: RL po 10,4 mln próbnych poranków zremisował z prostym planem (19,9% wobec 20,2% spadku niepewności), więc zostaje prosty plan, bo łatwiej go wyjaśnić i sprawdzić.

**Na dopytanie (tylko gdy jury zapyta):**

- Popeletzbach ma trzy liczby i nie wolno ich mieszać. Opublikowane dopasowanie (21 przebiegów, samosAT, odryw 0,6 m): +20 m, IoU 0,727. Najlepszy przebieg w 43 przebiegach Popeletzbach (z 234): +15 m, IoU 0,730, ale na krawędzi siatki (ξ 8000). Test bez podglądania: +25 m, IoU 0,70. W decku jest tylko ta ostatnia.
- Jedno ustawienie dla wszystkich 5 lawin, dobrane na tych samych lawinach, myli się średnio o 94 m, ale to nie jest walidacja, bo podgląda wynik. Walidacją jest test bez podglądania: 154 m średnio, 92 m mediana. Warianty: grubość odrywu dobierana razem z tarciem daje 160 m (mediana 102 m), a grubość dopasowana także do pominiętej lawiny (optymistycznie) daje 144 m.
- Zastrzeżenia kalibracji: grubość odrywu zmierzono tylko na Eiskar (2,7 m), dla reszty przyjęto 1,2 m. 4 z 5 najlepszych przebiegów leży na krawędzi siatki. Na Filisur 1 i 2 każdy z 43 przebiegów przestrzeliwuje; podejrzewamy brak lasu, ale z lasem z danych zdarzeń (parametry domyślne) nadal każdy przebieg przestrzeliwuje (o +36 do +160 m i +56 do +145 m). Na Eiskar rodzina samosAT staje 227–572 m za krótko; porywanie z domyślną grubością 0,3 m daje 187–522 m. Wariant z lasem i porywaniem w teście bez podglądania: średnio 153,7 m (bez lasu 154,2 m), mediana 124 m (bez lasu 92 m), w granicach 100 m 1 z 5 zdarzeń (bez lasu 3 z 5). samosAT to kalibracja dla suchego śniegu, tu użyta też do lawin mokrych. Teren jest nowszy niż każde zdarzenie. Licencję swisstopo trzeba potwierdzić przed pokazem.
- TOPR: archiwum lawiny.topr.pl i Wayback Machine były niedostępne, więc stopnie bierzemy z komunikatów cytowanych w prasie; wiersz 12.01 opiera się na przedruku na blogu. Poza „trójkami”: 27.03 TOPR obniża do 1, kalendarz ciemny (zgodność); 9.04 TOPR schodzi na 2, kalendarz nadal 8; 16.12 i 4.01 TOPR 2, kalendarz 0. W prasie nie znaleźliśmy lawin z tej zimy w naszym wycinku mapy.
- Grubość śniegu na Kasprowym z komunikatów zgadza się z IMGW (np. 85 / 85 cm 13.01), ale to ta sama stacja IMGW, więc to tylko dowód, że liczymy na prawdziwej zimie, a nie dowód trafności.
- Fałszywe alarmy w teście logiki: reguła „30 cm w 3 dni” przeoczyła 121 groźnych sytuacji, a Avalauncher 0. Mówimy to tylko razem z ceną (549 flag „nie wiem”, z tego 505 w poranki z odwołanym lotem) i dodajemy, że to słaby dowód, bo w syntetycznym teście błąd modelu zmienia prawdę tylko w 44 przypadkach.
- RL wyłapał trochę więcej zagrożeń (1936 wobec 1810 z 7924), ale zdjął mniej „nie wiem” (3915 wobec 3987). Trochę lepszy wynik w jednej mierze to jeszcze nie wygrana.
- Przyspieszenie 4500× to porównanie jednego rdzenia procesora z kartą graficzną. Z nauki sieci wyłączyliśmy dodatkowo 10 sąsiednich stoków, których lawiny wchodzą na stoki testowe, żeby sieć nie mogła ściągać.
- Jedna symulacja AvaFrame trwa 107 s na laptopie (i5-1245U) i 6,7 s na DGX Spark (benchmark na jednej strefie). Podstawą przyspieszenia 4500× jest inna liczba: 10,43 s, mediana na przebieg z biblioteki na 1 rdzeniu CPU.
- Pogoda o 7:00: sumy dobowe IMGW (zamieć, opad, Tmin) obejmują całą dobę, także godziny po 7:00, więc ekran demo pokazuje je z doby poprzedniej (dla obu poranków demo zamieć to i tak 24 h); kalendarz uwolnień liczy obciążenie z dób poprzednich, bez podglądania dnia, który ocenia.
- W kalendarzu zagrożenia kierunek wiatru jest założony (W–SW), bo IMGW nie podaje go dla tej zimy, a to on decyduje, które stoki się zapalają. Pominięcie 15–16.03 wynika m.in. z tego, że nawiewanie trwało wtedy tylko ok. 12 h w 3 doby.
- Prywatność: nie przetwarzamy danych osobowych. Dron mierzy śnieg, nie ludzi.

## Przed zamknięciem decku

- Zrobić zrzuty do `docs/img/` (slajdy 3 i 4) przez `node tools/shot.mjs`, gdy demo działa na porcie 8777.
- Popeletzbach: na slajdach 1 i 6 tylko +25 m (test bez podglądania). Liczby +15 m i +20 m nie mogą stać obok niej na żadnym obrazie.
- Przyciąć liczby spoza docs/12 albo mylące: „NAJLEPSZY PRZEBIEG” i dolne zdanie z „94 m” na `filmy/kalibracja/5_lawin.png` (slajdy 1 i 6) · „t = 34 s” na hero S22 (slajd 2) · „1291 z 1566” na `filmy/hero/mapa_zasiegow.png` (slajdy 3 i 9) · „4 × 4 km” na `filmy/satelita/porownanie.png` (slajd 5) · „IoU 0,84 / 0,70 / 0,87” i „27 przebiegów” na `filmy/surrogate/porownanie.png` (slajd 7) · „47 z 58 sektorów” na `filmy/kiedy/kalendarz.png` · „9 z 21” i 0,63 / 0,58 / 0,38 na `filmy/kalibracja/porownanie.png` · legenda 24% / 83% / 83% na `filmy/rl/trasy.png`.
- Potwierdzić licencję swisstopo swissALTI3D (teren Filisur) i wpisać ją na slajdach 6 i 10.
- Nie używać liczb spoza docs/12. Wycięte z poprzednich wersji: „4×4 km”, „72 strefy”, „32 szlaki”, „121 ze 144”, „ok. 2 mln stref”, „jeden krok na sto” (≈ 1%), „2 z 58”, liczba fioletowych stoków w dniu 2.
- `filmy/hero/koncepcja_3d.png` i `koncepcja_orbit.mp4` są teraz wynikiem silnika dla dnia 2 (te same flagi i plan co na ekranie demo; legenda „Plan przelotu (7 stoków)” zgadza się z „7 sektorów w planie” w demo). Stara ilustracja leży obok jako `*_stara_ilustracja.*` i nie trafia na slajdy.
- Deck w stylu XP subtelnym (pasek tytułu Luna, przyciski okna, pasek zadań; treść czysta). Eksport do PDF dozwolony.
