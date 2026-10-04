# Deck v2: storyboard dla osoby, która widzi Avalauncher pierwszy raz

Uwaga użytkownika (4.10, ok. 09:15): tytuły to frazesy dla wtajemniczonych, slajdy przeładowane danymi, brak zrzutów z aplikacji. Ten storyboard zastępuje układ slajdów z docs/11_deck.md.

**Zasady:**
- Każdy tytuł to zwykłe zdanie, które zrozumie osoba nietechniczna, która nic o projekcie nie wie.
- Bez żargonu: nie piszemy „cyfrowy bliźniak”, VOI, IoU, surogat, RL, leave-one-out, sektor, płyta, AvaFrame w tytule.
- Najwyżej jedna liczba na slajd. Wyjątek to slajd 7, gdzie mogą być dwie.
- Slajdy 1 i 4–6 to duże zrzuty ekranu aplikacji (co najmniej 60% slajdu) z 1–3 strzałkami i krótkimi dopiskami.
- Tekst pod tytułem: najwyżej 2 krótkie linijki.
- Stopka z atrybucją jest małym drukiem.

| # | Tytuł (dosłownie) | Pod tytułem (najwyżej 2 linijki) | Obraz |
| --- | --- | --- | --- |
| 1 | Avalauncher pokazuje na mapie, które stoki w Tatrach mogą zrzucić lawinę na szlak | Dla służby lawinowej, która co rano decyduje, gdzie jest groźnie. | `docs/img/krok1_mapa.png` na całą szerokość; strzałka do pomarańczowych stoków: „tu może zejść lawina na szlak” |
| 2 | Co rano ktoś musi zdecydować, czy szlaki w górach są dziś groźne | Śnieg na każdym stoku jest inny, a stoków są dziesiątki. Pomyłka kosztuje życie albo zamknięty szlak. | `web/media/hero_S22_samosAT_2.0_mid.jpg` (lawina nad szlakiem, 3D); mały podpis: „Kasprowy Wierch, styczeń 2025: 34 cm nowego śniegu w 3 dni (IMGW)” |
| 3 | Jak to działa: dron mierzy śnieg, komputer porównuje z policzonymi lawinami, mapa pokazuje groźne stoki | — | Trzy kafelki ze strzałkami: 1) dron nad stokiem (prosta ikona SVG) „Dron co rano mierzy śnieg nad szlakami”, 2) siatka małych obrysów lawin (fragment `filmy/hero/mapa_zasiegow.png` lub `web/media/landing/*`) „Komputer porównuje pomiar z tysiącami lawin policzonych wcześniej”, 3) mini `krok1_mapa.png` „Mapa pokazuje stoki, które mogą zagrozić szlakowi” |
| 4 | Kliknij stok, a zobaczysz, dokąd zjechałaby lawina | Pomarańczowy obszar to zasięg lawiny. Tu dochodzi do szlaku spod Kasprowego. | `docs/img/krok2_stok.png` duży; strzałka do pomarańczowego zasięgu i do szlaku |
| 5 | Gdy dron nie może polecieć, aplikacja mówi wprost: nie wiem | Stoki bez świeżego pomiaru dostają fioletową flagę zamiast zgadywania. | `docs/img/dzien2_mgla.png` duży; strzałka do fioletowej mgły: „tu wiedza jest za stara” |
| 6 | I podpowiada, gdzie polecieć, żeby dowiedzieć się najwięcej | Trasa drona idzie tam, gdzie niewiedza jest największa, a nie wzdłuż szlaku. | `docs/img/krok3_trasa.png` (lub `po_przelocie.png`) duży; strzałka do magentowej trasy |
| 7 | Sprawdziliśmy to na prawdziwych lawinach | Na 5 lawinach z Austrii i Szwajcarii komputer pomylił się typowo o 92 m (lawiny miały od ok. 270 m do 2,3 km). Na lawinie Popeletzbach: 25 m na 1775 m. | `web/media/landing/kalibracja_5_lawin.jpg` lub `filmy/kalibracja/5_lawin.png` przycięte do samych 5 paneli map, bez tabel i opisów; podpis: „przerywana linia: prawdziwa lawina · pomarańcz: obliczenie” |
| 8 | Działa bez internetu i mówi uczciwie, co jest prawdziwe, a co symulowane | — | Dwie kolumny z ikonami. **Prawdziwe:** teren Tatr (GUGiK), szlaki (OpenStreetMap), pogoda zimy 2024/25 (IMGW). **Na razie symulowane:** grubość śniegu na stokach, loty drona. Mały zrzut dymka „Brak łączności — pracuję na danych z pamięci” jeśli jest w docs/img, inaczej bez |
| 9 | Następny krok: jedna zima z jedną służbą lawinową na jednym szlaku | Prawdziwe pomiary z drona i ich własne obserwacje lawin, żeby dopasować obliczenia do Tatr. | Prosta oś: „dziś: demo na danych z zimy 2024/25” → „pilotaż: 1 szlak, 1 zima” → „cała służba”. Bez liczb |
| 10 | Zbudowane w jedną noc z otwartych danych | W jedną noc policzyliśmy 1566 lawin na jednym komputerze; docelowo tysiące. Kod otwarty, użycie AI ujawnione. | `docs/img/logowanie.png` mały, linki: demo https://przemeknowak781.github.io/avalauncher/ i repo https://github.com/przemeknowak781/avalauncher; stopka z licencjami |

**Kolory na zrzutach i strzałkach:** pomarańcz = może zagrozić szlakowi, fiolet = nie wiem, magenta = trasa drona.

**Czego nie dajemy:** wykresów, tabel, „29 wobec 16”, RL i wyników sieci neuronowej w liczbach. Wszystko to zostaje w README i w docs/12.
