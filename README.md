# Avalauncher

**Cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć.**

Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z tysiącami policzonych z góry scenariuszy lawin i wskazuje służbie lawinowej stoki, które mogą zagrozić szlakom. Gdy wiedza się starzeje, bo dron nie mógł polecieć, mówi to wprost i planuje, gdzie polecieć, żeby się dowiedzieć.

HackYeah 2026, zadanie Defence (odporność). Master doc zespołu: [kompendium](docs/00_kompendium_hackyeah.md).

## Dwie rzeczy, które robi

| | Wie | Wie, czego nie wie |
| --- | --- | --- |
| **Wejście** | Nowy przelot drona nad szlakiem i strefami startowymi nad nim | Czas i opad od ostatniego przelotu |
| **Co liczy** | Do których scenariuszy z biblioteki podobna jest dziś każda strefa startowa | Jak bardzo zestarzała się wiedza o każdym sektorze |
| **Co pokazuje** | Sektory, które mogą zagrozić szlakom, z uzasadnieniem | Flagę „nie wiem” i plan następnego przelotu w dostępnym czasie lotu |

Wszystko inne służy tym dwóm kolumnom.

## Demo: dwa poranki

1. **Dzień 1, dron poleciał.** Porównanie z biblioteką scenariuszy wskazuje dwa sektory, które mogą zagrozić szlakom. Kliknięcie sektora pokazuje, dlaczego.
2. **Dzień 2, śnieżyca, dron nie poleciał.** Wiedza o sektorach się starzeje i jeden z nich dostaje flagę „nie wiem”. Avalauncher proponuje plan przelotu na pierwsze okno pogodowe.

Działa lokalnie i offline: scenariusze są policzone z góry, więc wynik w terenie jest natychmiastowy i nie potrzebuje sieci.

## Czym nie jest

- **Nie mówi, że jest bezpiecznie.** Tylko podnosi uwagę. Brak flagi nie oznacza braku zagrożenia.
- **Nie wydaje komunikatu.** Stopień zagrożenia i zamknięcia szlaków ustala prognosta. Avalauncher wskazuje mu, gdzie patrzeć.
- **Nie jest pierwszym cyfrowym bliźniakiem lawin.** Wielkie biblioteki scenariuszy już istnieją (Bühler i in. 2022: ok. 2 mln stref startowych dla całego kantonu). Nowe są dwie rzeczy: śledzenie, gdzie wiedza się zestarzała, i plan przelotu, który ją odświeża ([przegląd](docs/01_oryginalnosc.md)).

## Jak sprawdzimy, że działa

Na 30 syntetycznych porankach, po jednej mierze na każde zdanie tezy:

1. **Wie:** ile sektorów zagrażających szlakom przeoczy Avalauncher, a ile prosta reguła „suma nowego śniegu z 3 dni”, czyli silny punkt odniesienia z [docs/02](docs/02_pokrywa_i_uruchomienie.md).
2. **Wie, czego nie wie:** o ile szybciej spada niepewność nad groźnymi sektorami przy planie Avalaunchera niż przy locie zawsze tą samą trasą, przy tym samym czasie lotu.

## Prawdziwe a symulowane

| Element | Stan |
| --- | --- |
| Teren, przeloty, pogoda | Syntetyczne |
| Biblioteka scenariuszy | Liczona naprawdę, ale uproszczonym modelem zasięgu (linia energii, rodzina alfa-beta), nie AvaFrame |
| Kalibracja na zdarzeniach historycznych | Brak; to pierwszy krok wdrożenia z lokalną służbą |
| Obecny kod | Porównuje syntetyczne siatki wysokości śniegu; silnik sektorów i ekran są w budowie |

Avalauncher nie jest zwalidowaną prognozą zagrożenia i nie służy do samodzielnego ostrzegania.

## Uruchomienie

Python 3.11+, bez zewnętrznych zależności:

```bash
PYTHONPATH=src python -m avalauncher compare --observation examples/synthetic_observation.json --scenarios examples/synthetic_scenarios.json
```

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Skąd bliźniak wie, co wie

Regularne przeloty helikoptera lub UAV nad korytarzami szlaków: radar (GPR) mierzy grubość pokrywy wzdłuż linii przelotu, LiDAR lub fotogrametria mierzy powierzchnię śniegu, a skały, tyczki i drzewa służą wspomagająco jako punkty kontrolne. Między przelotami lukę wypełniają stacje pogodowe, dane klimatyczne i historia zdarzeń. Ograniczenia każdego źródła opisuje [docs/04](docs/04_pomiary_i_fuzja.md).

## Dalej

- **Platforma, nie wytrenowany model:** nowy masyw to konfiguracja (teren, strefy startowe, szlaki, lokalne zdarzenia) i lokalna kalibracja. Nowe źródło danych podłącza się przez jeden interfejs ([`ports.py`](src/avalauncher/ports.py)), jeśli podaje wartość, niepewność i czas pomiaru. Przenośności między górami nie obiecujemy, bo to otwarta hipoteza ([H4](docs/08_cyfrowy_blizniak_use_case.md)).
- Pilot z jedną służbą na jednym korytarzu szlaku; biblioteka z AvaFrame i integracja z SNOWPACK.
- Osuwiska na tym samym silniku; ocena dostępności tras w sytuacjach kryzysowych.
- Aktywny dobór przelotów z RL dopiero wtedy, gdy pokona proste reguły.

## Zaplecze badawcze

0. [Kompendium HackYeah 2026](docs/00_kompendium_hackyeah.md): master doc do zgłoszenia i pitchu.
1. [Oryginalność i hipotezy](docs/01_oryginalnosc.md): znane precedensy i test nowości.
2. [Pokrywa i uruchomienie](docs/02_pokrywa_i_uruchomienie.md): stan śniegu, warstwy i prawdopodobieństwo uwolnienia.
3. [Dynamika i symulatory](docs/03_dynamika_i_symulatory.md): AvaFrame, kalibracja, MuJoCo.
4. [LiDAR, radar, landmarki](docs/04_pomiary_i_fuzja.md): pomiary i ich ograniczenia.
5. [Zbiory danych](docs/05_dane.md): 13 zweryfikowanych źródeł z DOI w [katalogu JSON](catalog/datasets.json); surowe pliki nie są dołączone.
6. [Architektura, RL, DGX Spark](docs/06_rl_i_dgx.md): kontrakty i etapy treningu.
7. [Plan walidacji](docs/07_walidacja.md): testy na niewidzianych sezonach i stokach.
8. [Cyfrowy bliźniak i cytaty](docs/08_cyfrowy_blizniak_use_case.md): precedensy, cytaty z publikacji i przypadek użycia.
