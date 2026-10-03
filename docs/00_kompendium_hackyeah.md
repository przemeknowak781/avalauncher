# HackYeah 2026, track Defence: kompendium zwycięzcy

Oct 3, 2026 · @Pomeblo

> **Master doc zespołu na HackYeah 2026.** Wersja żywa: [Claude Docs](https://claude.ai/code/artifact/f71804e0-6fb3-43d3-b885-f540ec5d17c2). Ten plik to eksport z 3.10.2026, ok. 22:45; przy rozbieżnościach obowiązuje wersja żywa.

## TL;DR

**Jest 3 października, ok. 21:00, a finalny termin zgłoszeń to 4 października, 11:00, czyli zostało około 14 godzin.** Checkpoint z 20:00 (pierwsza wersja robocza) już minął. Źródło terminów: [harmonogram na platformie HackTribe](https://hackyeah2026.hacktribe.co/schedule).

1. **Defence w tym konkursie znaczy odporność (resilience), nie wojsko.** Oficjalny opis zadania mówi o cyberbezpieczeństwie, odporności infrastruktury, dezinformacji i reagowaniu kryzysowym ([opis zadania](https://hackyeah2026.hacktribe.co/challenges/default/)).
2. **Wagi kryteriów:** Idea i innowacja 30%, związek z kategorią 20%, użyteczność praktyczna 20%, design 20%, kompletność i wartość wdrożeniowa tylko 10% ([regulamin zadania Defence](https://mudnibfuppwadjkynscc.supabase.co/storage/v1/object/public/task-files/6f0f5e2e-246f-4078-a3f7-1aad9152e9f0/files/312cc8e5-48a3-4c4b-a9a1-9b28861995e9.pdf)). Wniosek (moja ocena): wąski, dopracowany i dobrze opowiedziany prototyp wygrywa z szerokim, ale niedokończonym.
3. **Zbuduj jedną działającą ścieżkę użytkownika (vertical slice), nie platformę.** Reszta ma być w slajdach jako mapa drogowa.
4. **Zaprojektuj pod niepełne dane, ograniczone zasoby i niedostępność usług.** To jest wprost wymóg z dokumentu szczegółów zadania, więc tryb offline lub degradacji to tani sposób na punkty w kryterium "związek z kategorią".
5. **Zgłoszenie to PDF do 10 slajdów plus opis, repo, demo i zrzuty ekranu**, po polsku lub angielsku. Użycie AI wolno, ale istotne użycie trzeba ujawnić, a zewnętrzne zasoby cytować z licencjami.
6. **Złóż wersję roboczą jak najwcześniej, finał do 9:30 rano.** Regulamin podaje 23:00 jako koniec zgłoszeń, a harmonogram 11:00. Rozbieżność opisuję niżej, a bezpieczna wersja to 11:00 (lub wcześniej).
7. **Wykorzystaj mentorów dziś wieczorem**, szczególnie tych od cyberbezpieczeństwa i pitchu (lista w sekcji 2).
8. **Finaliści są ogłaszani o 15:00, pitch o 16:00, zwycięzcy o 17:45.** Przygotuj pitch zanim go potrzebujesz. Długość pitchu nie jest podana w źródłach, którymi dysponuję, więc zapytaj organizatorów.
9. **Pula nagród w Defence to 8000 PLN brutto** (z podatkiem), a podział na miejsca nie jest opublikowany.
10. **Uczciwie:** nie ma recepty gwarantującej wygraną. To kompendium zwiększa szanse, bo celuje w opublikowane kryteria, ale ocena jury zawsze zawiera element niewymierny.

## Nasz projekt: Avalauncher

**Cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.**

**W dwóch zdaniach:** Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z tysiącami policzonych z góry scenariuszy lawin i wskazuje służbie lawinowej stoki, które mogą zagrozić szlakom. Gdy wiedza się starzeje, bo dron nie mógł polecieć, mówi to wprost i planuje, gdzie polecieć, żeby się dowiedzieć.

**Dla dziesięciolatka:** Nad górami lata dron, który sprawdza, ile śniegu napadało i gdzie, a nasz komputer porównuje to z tysiącami lawin przećwiczonych na niby i podpowiada ratownikom, które miejsca nad szlakami mogą być groźne. Kiedy czegoś nie wie, na przykład dlatego, że dron nie mógł polecieć, mówi o tym głośno i pokazuje, gdzie trzeba polecieć, żeby się dowiedzieć.

**Zasada pracy:** każda funkcja, slajd i zdanie pitchu służy jednemu z tych dwóch zdań. Co nie służy, idzie na slajd z mapą drogową albo wypada.

### Overview

Po nocnym opadzie służba lawinowa ma kilku ludzi, duży teren i komunikat do wydania. Avalauncher robi dla niej dwie rzeczy. Po każdym przelocie porównuje stan stref startowych z biblioteką scenariuszy i wskazuje sektory, które mogą zagrozić szlakom. Między przelotami śledzi, jak starzeje się wiedza o każdym sektorze, i planuje następny przelot tam, gdzie najbardziej jej brakuje. Nigdy nie mówi „bezpiecznie”: decyzję o stopniu zagrożenia i zamknięciach podejmuje prognosta.

**Persona:** prognosta lub dyżurny służby lawinowej rano po opadzie. Do sprawdzenia przed slajdem: kto wydaje komunikat w danym regionie i czy TOPR stosuje 5-stopniową skalę EAWS.

### Dane: skąd bliźniak wie, co wie

Zakładamy regularne przeloty helikoptera lub UAV nad korytarzami kluczowych szlaków: szlakiem i strefami startowymi nad nim, bo lawina rusza na stoku powyżej trasy. Najwięcej informacji niesie zmiana pokrywy między dwoma przelotami.

| Źródło | Co daje | Ograniczenie |
| --- | --- | --- |
| Radar (GPR) | Grubość pokrywy i warstwy wzdłuż linii przelotu | Profile, nie mapa; wymaga gęstości śniegu, mokry śnieg utrudnia pomiar |
| LiDAR lub fotogrametria | Geometria powierzchni śniegu | Wymaga modelu terenu bez śniegu |
| Landmarki (skały, tyczki, drzewa) | Lokalne punkty zasypania i rejestracja przelotów | Wspomagająco; drzewa najsłabsze (uginanie, korona) |
| Stacje i dane klimatyczne | Opad, wiatr, temperatura między przelotami | Rozdzielczość nie rozstrzyga pojedynczego żlebu |
| Dane historyczne i parametry naukowe | Analogi zdarzeń, parametry modelu zasięgu | Kalibracja lokalna dla każdego terenu |

Między przelotami wiedza się starzeje: niepewność sektora rośnie z czasem i z opadem od ostatniego pomiaru. Odwołany przelot w czasie śnieżycy, czyli wtedy, gdy zagrożenie rośnie, to tryb degradacji, który pokazujemy w demo.

### Platforma, nie wytrenowany model

Sprzedajemy platformę, którą konfiguruje się i kalibruje dla konkretnego terenu, a nie gotowy, wytrenowany produkt. Nowy teren to konfiguracja: model terenu, strefy startowe, szlaki i lokalne zdarzenia historyczne. Nowe źródło danych podłącza się przez jeden interfejs (`ports.py`), jeśli podaje wartość, niepewność i czas pomiaru. Kalibrację robi się lokalnie z miejscową służbą, bo przenośność modelu między górami to otwarta hipoteza (H4 w docs/08) i jej nie obiecujemy. Tego nie ma w dwóch zdaniach, więc w demo tego nie budujemy: to slajd 9.

### Tezy i kryteria jury

| Teza | Co znaczy w praktyce | Kryterium |
| --- | --- | --- |
| 1. Wie | Porównuje pomiar z biblioteką scenariuszy i wskazuje sektory, które mogą zagrozić szlakom, z uzasadnieniem | Użyteczność 20% |
| 2. Wie, czego nie wie | Luki i wiedza zestarzała od ostatniego przelotu trafiają na listę jako flaga „nie wiem”, zamiast z niej znikać | Kategoria 20% (niepełne dane) |
| 3. Mówi, gdzie polecieć | Plan następnego przelotu: które sektory zmieścić w dostępnym czasie lotu, żeby najbardziej zmniejszyć niepewność nad szlakami | Innowacja 30% (ograniczone zasoby) |
| 4. Tylko podnosi uwagę | Nigdy nie mówi „bezpiecznie” i nie wydaje komunikatu; stopień ustala prognosta (karta sektora ma podpis: ekspozycja i pasmo wysokości) | Kategoria 20% |
| 5. Działa offline | Scenariusze policzone z góry, więc wynik w terenie jest natychmiastowy i bez sieci | Kategoria 20% (degradacja usług) |

**Wyróżnik wobec prior artu:** Mayer i in. 2023 prognozują dzień lawinowy dla otoczenia stacji, a Bühler i in. 2022 wyznaczyli ok. 2 mln stref startowych ze scenariuszami dla całego kantonu. Sama biblioteka scenariuszów, nawet ogromna, nie jest więc nowa: cyfrowy bliźniak to nośnik, nie wyróżnik. Wyróżniają nas dwie rzeczy: śledzenie, gdzie wiedza się zestarzała od ostatniego przelotu, i plan następnego przelotu. Nie twierdzimy, że to pierwszy cyfrowy bliźniak lawin ani że model jest skalibrowany na danych rzeczywistych.

### Demo: jedna ścieżka

1. **Dzień 1, dron poleciał (zdanie pierwsze).** Porównanie z biblioteką scenariuszy wskazuje dwa sektory, które mogą zagrozić szlakom. Kliknięcie sektora pokazuje, dlaczego.
2. **Dzień 2, śnieżyca, dron nie poleciał (zdanie drugie).** Wiedza o sektorach się starzeje i jeden z nich dostaje flagę „nie wiem”. Avalauncher proponuje plan przelotu na pierwsze okno pogodowe.

Wycięte z demo, bo nie służą dwóm zdaniom: szkic wpisu do komunikatu i przełącznik drugiego masywu. Szlaki to jedyna warstwa zagrożona w demo, droga jest tylko tłem mapy.

**Dowód (slajd 6), po jednej mierze na każde zdanie, na 30 syntetycznych porankach:**

1. Wie: ile sektorów zagrażających szlakom przeoczy Avalauncher, a ile prosta reguła „suma nowego śniegu z 3 dni” (silny punkt odniesienia z docs/02).
2. Wie, czego nie wie: o ile szybciej spada niepewność nad groźnymi sektorami przy planie Avalaunchera niż przy locie zawsze tą samą trasą, przy tym samym czasie lotu.

**Prawdziwe a symulowane:** teren, przeloty i pogoda w demo są syntetyczne. Scenariusze liczymy naprawdę, ale uproszczonym modelem zasięgu (linia energii, rodzina alfa-beta), i w pitchu podajemy faktycznie policzoną liczbę. Docelowo biblioteka z AvaFrame, kalibrowana na lokalnych zdarzeniach historycznych.

### Mapa drogowa (slajd 9)

- Platforma dla każdego masywu: nowy teren przez konfigurację i lokalną kalibrację, nowe dane przez jeden interfejs.
- Pilot z jedną służbą na jednym korytarzu szlaku: kalibracja na lokalnych zdarzeniach.
- Biblioteka scenariuszy z AvaFrame zamiast uproszczonego modelu, integracja z SNOWPACK.
- Osuwiska na tym samym silniku; ocena dostępności tras w sytuacjach kryzysowych.
- Aktywny dobór przelotów z RL dopiero wtedy, gdy pokona proste reguły.
- Do sprawdzenia przed slajdem: zgody na przeloty dronów nad parkiem narodowym i loty poza zasięgiem wzroku pilota.

### Do zrobienia w repo przed zgłoszeniem

- [ ] Upublicznić repo albo dać dostęp jury (dziś zwraca 404 bez logowania)
- [ ] Dodać plik LICENSE
- [ ] Dopisać ujawnienie użycia AI i licencje zasobów zewnętrznych
- [ ] Silnik: sektory zamiast całej siatki, porównanie przelotów bez wymogu identycznego czasu, luki i zestarzała wiedza podnoszą flagę
- [ ] Biblioteka scenariuszy z uproszczonego modelu zasięgu i plan następnego przelotu
- [ ] Dowód: dwie miary na 30 syntetycznych porankach (przeoczone sektory; spadek niepewności przy planie kontra stała trasa)
- [ ] Ekran demo offline: dwa poranki z suwakiem dnia

## 1. Fakty o HackYeah 2026 i zasady

HackYeah 2026 to 12. edycja, 24-godzinny hackathon stacjonarny w Tauron Arena Kraków, 3 i 4 października 2026 ([hackyeah.pl](https://hackyeah.pl/), [infosec-conferences](https://infosec-conferences.com/event/20261003-hackyeah-2026/)). Zadania dzielą się na otwarte (Open Tasks) i partnerskie (Partner Tasks), a każda grupa ma pulę 25 000 PLN, razem 50 000 PLN. Defence jest jednym z pięciu zadań otwartych, obok AI, ImpactHer, Smart City oraz Sport & Healthcare ([lista wyzwań](https://hackyeah2026.hacktribe.co/challenges/)).

### Harmonogram (Europe/Warsaw)

| Kiedy | Co | Uwaga |
| --- | --- | --- |
| 3.10, 11:00 | Start kodowania, zadania odblokowane | minione |
| 3.10, 16:00 | Przerwa pizzowa | minione |
| 3.10, 20:00 | Project checkpoint: pierwsza wersja robocza | minione, sprawdź na platformie, czy można złożyć spóźnioną |
| 4.10, 11:00 | Finalny termin zgłoszeń i start oceny jury | twardy termin wg harmonogramu |
| 4.10, 15:00 | Ogłoszenie finalistów |  |
| 4.10, 16:00 | Pitching finalistów | długość nieznana |
| 4.10, 17:45 | Ogłoszenie zwycięzców |  |

Źródło: [harmonogram HackTribe](https://hackyeah2026.hacktribe.co/schedule).

### Sprzeczność w terminach

Harmonogram platformy kończy zgłoszenia 4.10 o 11:00, natomiast [ogólny regulamin](https://hackyeah.pl/rules?lang=en) (pkt 4.3) i PDF zadania mówią o oknie od 23:00 3.10 do 23:00 4.10. Przy wydarzeniu 24-godzinnym (start 11:00) wersja z 11:00 jest wewnętrznie spójna, a "PM" wygląda na błąd. To moja interpretacja, nie potwierdzenie organizatora. Zapytaj na [Discordzie](https://discord.com/invite/JJzBhMs5uF) lub przy stanowisku organizatora i do tego czasu planuj na 11:00.

### Najważniejsze zasady z regulaminu

- **Zespół:** od 1 do 6 osób (PDF zadania Defence).
- **Ocena:** jury min. 3 osoby, głosowanie większościowe, decyzje ostateczne bez odwołań. Jury może nie przyznać nagrody, gdy projekt zdobywa mniej niż 50% punktów (regulamin, pkt 5.2 do 5.7).
- **Zmiany po terminie** są ignorowane (pkt 5.8).
- **Prawa autorskie** do nagrodzonego rozwiązania nie przechodzą na sponsora zadania Defence (PDF zadania). Uczestnik deklaruje pełne prawa do swojego wkładu i brak naruszeń praw osób trzecich (pkt 6.1, 6.2). Organizator może bezpłatnie wykorzystywać wizerunek uczestników (pkt 6.4).
- **AI i zasoby zewnętrzne:** dozwolone, z pełną odpowiedzialnością zespołu. Istotne użycie AI trzeba ujawnić, zasoby zewnętrzne cytować z zachowaniem licencji, a plagiat lub fałszowanie autorstwa to podstawa do dyskwalifikacji ([szczegóły zadania](https://mudnibfuppwadjkynscc.supabase.co/storage/v1/object/public/task-files/6f0f5e2e-246f-4078-a3f7-1aad9152e9f0/files/020c69e4-f03f-4e5b-b3f3-2038d424f127.pdf)).
- **Na miejscu:** własny sprzęt i brak wsparcia technicznego organizatora, opaska przez całe wydarzenie, zakaz broni, materiałów wybuchowych, alkoholu i narkotyków (pkt 3.6, 3.7, 8.3, 8.6).
- **Nagrody** wydawane w ciągu 90 dni od ogłoszenia wyników, bez zamiany na gotówkę w przypadku nagród rzeczowych (pkt 4.10, 4.11).

Podsumowanie regulaminu przygotowałem na podstawie automatycznej ekstrakcji treści stron, więc numery punktów warto zweryfikować w oryginale, zanim oprzesz na nich decyzję.

## 2. Zadanie Defence i mentorzy

Zadanie Defence prosi o narzędzie, aplikację, system lub prototyp, który pomaga zapobiegać zagrożeniom, wykrywać je wcześniej albo zmniejszać ich skutki. Problemy, o których mowa, to przerwy w usługach, manipulacja wiadomościami, przejęte konta i skutki dla całych organizacji lub społeczności ([opis](https://hackyeah2026.hacktribe.co/challenges/default/), [szczegóły](https://mudnibfuppwadjkynscc.supabase.co/storage/v1/object/public/task-files/6f0f5e2e-246f-4078-a3f7-1aad9152e9f0/files/020c69e4-f03f-4e5b-b3f3-2038d424f127.pdf)).

### Przykładowe kierunki z oficjalnego dokumentu

- Wskazywanie słabości w małych organizacjach i priorytetyzacja zabezpieczeń.
- Weryfikacja podejrzanych wiadomości, treści i źródeł informacji.
- Koordynacja reagowania kryzysowego i wymiana informacji.
- Mapowanie zależności między usługami i punktów awarii.
- Upraszczanie zrozumienia i przestrzegania procedur bezpieczeństwa.

### Co rozwiązanie musi pokazać

Realistyczny scenariusz, wymierną poprawę sytuacji, działanie przy niepełnych informacjach, ograniczonych zasobach lub niedostępnych usługach oraz to, komu i jak pomaga (interesariusze). Ostatnie zdanie opisu zadania brzmi jak test akceptacji: zbuduj coś, co działa, gdy naprawdę jest potrzebne.

### Mentorzy związani z cyberbezpieczeństwem lub pitchem

Rezerwacja: zakładka [1:1 Sessions](https://hackyeah2026.hacktribe.co/timetable/), przycisk "Find my mentor". Profile pochodzą z [listy mentorów](https://hackyeah2026.hacktribe.co/timetable/mentors/); liczba slotów to stan z chwili sprawdzenia i szybko się zmienia. Etykieta "Expert in specific Task" na platformie nie mówi, którego zadania, więc zapytaj wprost.

Lista mentorów z cyberbezpieczeństwa i pitchu jest na platformie HackTribe (zakładka 1:1 Sessions); w repo jej nie powielamy.

Wskazówka (moja ocena): jedną sesję przeznacz na walidację pomysłu z praktykiem cyberbezpieczeństwa, drugą, rano, na próbny pitch z osobą od storytellingu.

## 3. Kryteria oceny i jak pod nie projektować

Pięć kryteriów z wagami pochodzi z [regulaminu zadania Defence](https://mudnibfuppwadjkynscc.supabase.co/storage/v1/object/public/task-files/6f0f5e2e-246f-4078-a3f7-1aad9152e9f0/files/312cc8e5-48a3-4c4b-a9a1-9b28861995e9.pdf) oraz [ogólnego regulaminu](https://hackyeah.pl/rules?lang=en) (pkt 5.5). Kolumna "Co robić" to moja interpretacja, bo organizatorzy nie publikują rubryki opisowej.

| Kryterium | Waga | Co robić |
| --- | --- | --- |
| Idea i innowacja | 30% | Jedno zdanie wyróżnika: co robi inaczej niż istniejące rozwiązania. Nazwij 2 konkretne alternatywy (np. arkusz, istniejące narzędzie) i powiedz, czego nie potrafią. |
| Związek z kategorią | 20% | Wskaż, czy projekt zapobiega, wykrywa, czy zmniejsza skutki, i pokaż działanie w trybie awaryjnym (brak sieci, brak danych, niedostępna usługa). Unikaj "ogólnego AI" bez wiązania z zagrożeniem. |
| Użyteczność praktyczna | 20% | Jedna osoba (persona), jedna sytuacja, trzy kroki do użycia, brak wymaganej integracji. Zadaj sobie pytanie, kto zainstaluje to w poniedziałek. |
| Design | 20% | Spokojny, czytelny interfejs, jeden pełny ekran demo bez surowych logów, spójny deck. To jedna piąta oceny, więc zasługuje na realny czas. |
| Kompletność i wartość wdrożeniowa | 10% | Działa ścieżka od początku do końca, w repo jest README i instrukcja uruchomienia. Tylko 10%, więc nie poświęcaj dla niej innowacji ani designu. |

### Co z tego wynika

Suma wag Idea, Kategoria i Design to 70%, a Kompletność tylko 10%. Działa to na korzyść projektów, które mają wyraźną, nieoczywistą tezę i dobrze wyglądają, nawet gdy część zaplecza jest zasymulowana. Granica jest uczciwość: jeśli coś jest makietą lub danymi syntetycznymi, napisz to w deku i w README, bo plagiat i fałszowanie autorstwa to w regulaminie podstawa do dyskwalifikacji.

Próg 50% punktów oznacza, że jury może w ogóle nie przyznać nagrody w kategorii. Projekt, który jest dobry tylko pod jednym względem (np. świetny UI bez związku z odpornością), ryzykuje właśnie tę barierę.

Kryteria są wspólne dla wszystkich zadań otwartych, więc jury porównuje różne projekty tymi samymi kategoriami. Kryterium "Relation to Category" jest tym, co odróżnia projekt Defence od np. Smart City lub AI. Nie zakładaj, że dobry projekt AI zostanie oceniony wysoko w Defence.

## 4. Strategia: wybór problemu i plan do 11:00

Ta sekcja to moje rekomendacje, wyprowadzone z kryteriów i opisu zadania, a nie fakty organizatora. Nie wiem, jaki masz już pomysł ani ile osób liczy zespół, więc plan działa dla 1 do 6 osób (w pojedynkę role po prostu się łączą).

### Filtr wyboru problemu (4 pytania)

1. **Czy da się go pokazać w 90 sekund na jednym scenariuszu?** Jeśli nie, jest za szeroki.
2. **Kto konkretnie jest użytkownikiem?** "Obywatele" to nie odpowiedź, "księgowa w 15-osobowej firmie podczas ataku phishingowego" tak.
3. **Co działa, gdy nie ma internetu, API lub danych?** Wymóg z opisu zadania, więc musi być odpowiedź.
4. **Co jest nieoczywiste?** Szczególnie zatłoczone kierunki to prawdopodobnie detektor dezinformacji i detektor phishingu (to hipoteza, bo nie widzę zgłoszeń innych zespołów). Tam jury zobaczy wiele podobnych demo, a Tobie trudniej się wyróżnić w kryterium innowacji o wadze 30%.

### Kierunki z oficjalnego dokumentu i pomysł na wyróżnik

| Kierunek z dokumentu | Pomysł na wyróżnik (hipoteza) | Ryzyko |
| --- | --- | --- |
| Słabości małych organizacji | Triage w 10 minut: kilka pytań plus automatyczny skan publiczny, wynik jako 3 priorytetowe działania, nie raport na 40 stron | Skan zewnętrznych systemów tylko za zgodą właściciela, nigdy cudzych |
| Weryfikacja wiadomości i źródeł | Narzędzie dla osoby, która musi zdecydować pod presją czasu, pokazujące dowody i niepewność, nie wyrok prawda/fałsz | Zatłoczone, ryzyko fałszywych alarmów |
| Koordynacja kryzysowa | Wymiana informacji w sieci o słabej łączności (offline-first, synchronizacja po odzyskaniu sieci) | Trudna demonstracja, wymaga dobrego scenariusza |
| Zależności i punkty awarii | Graf zależności usług (kto zależy od jakiego dostawcy) i symulacja "co jeśli X padnie" dla gminy lub firmy | Łatwo zrobić efektowny graf bez realnej wartości |
| Zrozumienie procedur | Procedura bezpieczeństwa jako interaktywna lista kontrolna w trakcie incydentu, dostosowana do roli | "Chatbot do procedur" jest wyeksploatowany |

### Plan godzinowy (od 21:00 do 11:00)

| Czas | Cel | Gotowe, gdy |
| --- | --- | --- |
| 21:00 do 21:45 | Zamroż zakres: problem, persona, jedno zdanie tezy, definicja "działa" | Teza i scenariusz demo zapisane na jednej stronie |
| 21:45 do 22:30 | Szkielet repo i UI, 10 minut z mentorem na walidację | Ekran startowy widzi się pod adresem, który można otworzyć |
| 22:30 do 02:30 | Zbuduj ścieżkę od początku do końca (jedna persona, jeden scenariusz) | Scenariusz demo przechodzi bez ręcznych poprawek |
| 02:30 | Zamrożenie nowych funkcji. Złóż wersję roboczą, jeśli platforma na to pozwala po terminie checkpointu | Zgłoszenie istnieje w systemie, nawet niepełne |
| 02:30 do 06:00 | Sen na zmianę (osoba, która będzie pitchować, śpi co najmniej 3 godziny) | Jedna osoba zawsze nad kodem lub deckiem |
| 06:00 do 08:00 | Polerowanie UI, stany błędów, nagranie 90-sekundowego wideo demo jako zapas | Wideo i zrzuty ekranu zapisane lokalnie |
| 08:00 do 09:00 | Deck (max 10 slajdów), README, lista użycia AI i zasobów zewnętrznych | PDF wygenerowany, linki sprawdzone |
| 09:00 do 09:30 | Złożenie zgłoszenia na platformie | Potwierdzenie widoczne, linki otwierają się w oknie incognito |
| 09:30 do 11:00 | Bufor na awarie, pierwszy pitch na głos | Nic nie zmieniasz w kodzie, tylko w razie krytycznego błędu |
| 11:00 do 15:00 | Próby pitchu (min. 3 razy z czasem), plan B demo offline | Demo działa bez Wi-Fi |

Dwa ryzyka na sali, o których warto pamiętać: na wydarzeniu są tysiące osób ([Wikipedia podaje blisko 3000 uczestników w 2023](https://en.wikipedia.org/wiki/HackYeah)), a sieć może być przeciążona, więc demo ma działać lokalnie lub z własnego hotspotu. Organizator nie zapewnia wsparcia technicznego (regulamin, pkt 3.7).

## 5. Zgłoszenie, deck i pitch

Zgłoszenie składa się na platformie HackTribe i wymaga tytułu projektu, nazwy zespołu, listy członków (1 do 6), opisu oraz PDF-a z maksymalnie 10 slajdami, zawierającego zrzuty ekranu, link do repozytorium, link do dema, grafiki i powiązane materiały. Można pisać po polsku lub angielsku ([regulamin zadania Defence](https://mudnibfuppwadjkynscc.supabase.co/storage/v1/object/public/task-files/6f0f5e2e-246f-4078-a3f7-1aad9152e9f0/files/312cc8e5-48a3-4c4b-a9a1-9b28861995e9.pdf)). Poniższy układ slajdów i pytania do jury to moja propozycja pod opublikowane kryteria.

### Układ 10 slajdów

1. **Problem w jednym scenariuszu.** Konkretna osoba, konkretny moment kryzysu, konkretny koszt.
2. **Teza i wyróżnik.** Jedno zdanie plus dwie alternatywy, których nie przypominasz (kryterium 30%).
3. **Użytkownik i jego trzy kroki.** Kto, kiedy, co robi (użyteczność 20%).
4. **Demo: ekrany.** Trzy zrzuty z podpisami, nie surowe logi (design 20%).
5. **Działanie przy degradacji.** Co się dzieje bez sieci, bez danych, przy niedostępnej usłudze (wprost wymóg zadania).
6. **Dowód.** Wynik na scenariuszu testowym: czas, liczba błędów, porównanie z „bez narzędzia”. Jeśli dane są syntetyczne, napisz to.
7. **Mapowanie do Defence.** Zapobiega, wykrywa czy zmniejsza skutki, i dlaczego to odporność (kategoria 20%).
8. **Prawdziwe vs symulowane.** Uczciwa tabela. Buduje wiarygodność i chroni przed zarzutem fałszowania.
9. **Wdrożenie.** Kto pierwszy użyje, jak do niego dotrze, co w następnym kroku (kompletność i wartość wdrożeniowa 10%).
10. **Zespół, użyte AI i zasoby zewnętrzne z licencjami.** To jest ujawnienie, którego wymaga opis zadania.

### Pitch (szkic na 3 minuty, dopasuj do podanego limitu)

Czas pitchu finalistów nie jest podany w źródłach, do których mam dostęp, więc ustal go z organizatorami, a poniższy podział skaluj proporcjonalnie.

- 0:00 do 0:30: historia osoby w kryzysie, bez tytułu projektu i bez technologii.
- 0:30 do 2:00: na żywo ten sam scenariusz, od początku do końca, bez wyjaśniania architektury.
- 2:00 do 2:40: dlaczego inaczej niż alternatywy i co dzieje się przy degradacji.
- 2:40 do 3:00: kto użyje pierwszy i jedno zdanie zamykające.

### Typowe błędy

- Demo zależne od zewnętrznego API bez zapasu: nagraj wideo i miej lokalny fallback.
- Deck pisany o 10:45, a zgłoszenie o 10:58. Zgłoszenia po terminie są ignorowane (regulamin, pkt 5.8).
- Opowiadanie o technologii zamiast o problemie. Jury ocenia pomysł, użyteczność i design znacznie wyżej niż implementację.
- Obietnica, że system „wykrywa wszystko”. W kontekście bezpieczeństwa przesada obniża wiarygodność.

### Pytania, które jury prawdopodobnie zada (hipoteza)

Skąd bierzecie dane i co z fałszywymi alarmami? Co z prywatnością i RODO (minimalizacja danych)? Kto za to zapłaci i kto to utrzyma? Co zrobi system, gdy nie ma sieci? Czym różni się to od narzędzia X? Przygotuj po jednym zdaniu odpowiedzi na każde i zapisz je na kartce przy stanowisku.

## 6. Kontekst: język i realia, które jury zna

Przy kategorii o odporności jury prawdopodobnie ceni odwołanie do realnych ram prawnych i polityk. Poniższe dwa punkty pochodzą ze źródeł wtórnych (prasa branżowa i agencyjna), więc zweryfikuj je u źródła, zanim wpiszesz liczbę lub datę na slajd.

- **Polska, NIS2.** Nowelizacja ustawy o krajowym systemie cyberbezpieczeństwa (KSC), wdrażająca dyrektywę NIS2, weszła w życie 3 kwietnia 2026. Według [itwiz.pl](https://itwiz.pl/nowelizacja-ustawy-o-ksc-zaczyna-obowiazywac-rusza-harmonogram-wdrozenia-nis2-w-polsce/) podmioty mają wniosek o wpis do rejestru złożyć do 3 października 2026, systemy i procedury wdrożyć do 3 kwietnia 2027, a pierwszy audyt podmiotów kluczowych ma być do 3 kwietnia 2028. Dla projektu skierowanego do małych i średnich organizacji to realny powód, dla którego popyt na proste narzędzia rosnie.
- **UE, strategia gotowości.** W marcu 2025 Komisja Europejska przedstawiła strategię Preparedness Union, w której zachęca obywateli do posiadania zapasów na co najmniej 72 godziny kryzysu ([Reuters przez Fidelity](https://fidelity.com/news/article/default/202503260726RTRSNEWSCOMBINED_KCN3G311A-OUSWD_1), [Cyprus Mail](https://cyprus-mail.com/2025/03/26/eu-tells-the-public-to-hold-72-hours-of-emergency-supplies)). Hasło "72 godziny" jest użyteczną miarą dla scenariusza demo: co działa w pierwszej dobie po awarii.

### Słownik, który buduje wiarygodność w tej kategorii

Odporność (resilience), ciągłość działania, wczesne ostrzeganie, świadomość sytuacyjna, zależności i pojedyncze punkty awarii, degradacja "z gracją" (graceful degradation), człowiek w pętli. Unikaj języka wojskowego i ofensywnego: zadanie dotyczy ochrony ludzi, danych i usług.

## 7. Ryzyka i granice

- **Dual-use i etyka.** Nie buduj narzędzi ofensywnych (skanery cudzych systemów, generatory realnej dezinformacji do użycia poza demo). Test tylko na własnych lub syntetycznych danych i na systemach, które kontrolujesz. To moja zasada ostrożności, nie zapis regulaminu, ale jury ocenia też odpowiedzialność, a naruszenie cudzych systemów to ryzyko prawne.
- **Dezinformacja.** Jeśli generujesz przykładowe fałszywe treści do demonstracji, oznacz je wyraźnie jako syntetyczne i nie używaj prawdziwych osób ani prawdziwych instytucji jako „autorów” fałszywek.
- **Dane osobowe.** Minimalizuj dane. Nie wrzucaj prawdziwych danych osób do publicznego repo ani do zewnętrznych modeli.
- **Sekrety.** Jeśli repo jest publiczne, sprawdź historię commitów pod kątem kluczy API i haseł przed złożeniem zgłoszenia.
- **Licencje i autorstwo.** Zewnętrzne biblioteki, dane i grafiki cytuj z licencją. Jeśli korzystasz z kodu napisanego wcześniej, oddziel go w opisie od pracy z hackathonu (to prosta praktyka ostrożności wobec zapisu o plagiacie i fałszowaniu autorstwa, nie wymóg, który znalazłem w regulaminie).
- **AI.** Dozwolone, ale ujawnij istotne użycie i odpowiadasz za rezultat. Zapisuj na bieżąco, czego użyłeś, żeby slajd 10 nie powstawał z pamięci o 9:00.
- **Terminy.** Zmiany po terminie są ignorowane, a regulamin i harmonogram różnią się w godzinie zamknięcia (sekcja 1). Zgłoszenie między 9:00 a 9:30 eliminuje to ryzyko.
- **Prawa autorskie i wizerunek.** Prawa do nagrodzonego rozwiązania zostają przy autorze, a organizator może bezpłatnie używać wizerunku uczestników.

## 8. Checklista końcowa i źródła

### Checklista

- [ ] Potwierdzić u organizatorów godzinę zamknięcia zgłoszeń (11:00 czy 23:00) i długość pitchu
- [ ] Sprawdzić na platformie, czy można złożyć wersję roboczą po checkpointcie z 20:00
- [ ] Zamrozić zakres: teza, persona, scenariusz demo
- [ ] Zarezerwować co najmniej 1 sesję 1:1 z mentorem od cyber i 1 od pitchu
- [ ] Zbudować ścieżkę od początku do końca (jeden scenariusz) i trzy zrzuty ekranu
- [ ] Zaprojektować i pokazać tryb degradacji (bez sieci lub bez usługi)
- [ ] Nagrać 90-sekundowe wideo demo jako zapas
- [ ] Przygotować PDF (max 10 slajdów), opis, repo z README, link do dema
- [ ] Ujawnić użycie AI, zasoby zewnętrzne i licencje
- [ ] Przejrzeć repo pod kątem sekretów i danych osobowych
- [ ] Złożyć zgłoszenie do 9:30 i otworzyć wszystkie linki w oknie incognito
- [ ] Przeprowadzić 3 próby pitchu z zegarem przed 15:00 (ogłoszenie finalistów)

### Źródła (otwarte w tej sesji)

- [Zadanie Defence, opis](https://hackyeah2026.hacktribe.co/challenges/default/)
- [Zadanie Defence, regulamin (PDF)](https://mudnibfuppwadjkynscc.supabase.co/storage/v1/object/public/task-files/6f0f5e2e-246f-4078-a3f7-1aad9152e9f0/files/312cc8e5-48a3-4c4b-a9a1-9b28861995e9.pdf)
- [Zadanie Defence, szczegóły (PDF)](https://mudnibfuppwadjkynscc.supabase.co/storage/v1/object/public/task-files/6f0f5e2e-246f-4078-a3f7-1aad9152e9f0/files/020c69e4-f03f-4e5b-b3f3-2038d424f127.pdf)
- [Lista wyzwań HackYeah 2026](https://hackyeah2026.hacktribe.co/challenges/)
- [Harmonogram HackTribe](https://hackyeah2026.hacktribe.co/schedule)
- [Lista mentorów](https://hackyeah2026.hacktribe.co/timetable/mentors/)
- [Regulamin ogólny HackYeah 2026](https://hackyeah.pl/rules?lang=en)
- [Strona główna HackYeah](https://hackyeah.pl/)
- [Wydarzenie w katalogu infosec-conferences](https://infosec-conferences.com/event/20261003-hackyeah-2026/)
- [HackYeah na Wikipedii](https://en.wikipedia.org/wiki/HackYeah)
- [itwiz.pl o nowelizacji KSC](https://itwiz.pl/nowelizacja-ustawy-o-ksc-zaczyna-obowiazywac-rusza-harmonogram-wdrozenia-nis2-w-polsce/)
- [Reuters przez Fidelity o strategii UE](https://fidelity.com/news/article/default/202503260726RTRSNEWSCOMBINED_KCN3G311A-OUSWD_1)

Ograniczenia: dokumenty PDF i regulamin przeczytałem przez automatyczną ekstrakcję treści, a opisu pitchingu, podziału nagrody Defence na miejsca, składu jury ani listy partnerskich mentorów Defence nie znalazłem. Sekcje 4, 5 i 7 to rekomendacje, nie fakty organizatorów.
