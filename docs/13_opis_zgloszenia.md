# Zgłoszenie HackTribe: teksty do wklejenia

Liczby pochodzą z [docs/12_wyniki.md](12_wyniki.md). Pola w nawiasach kwadratowych uzupełnia zespół. Oba opisy mają mniej niż 1200 znaków ze spacjami .

## Pola formularza

| Pole | Wartość |
| --- | --- |
| Tytuł projektu | Avalauncher |
| Podtytuł | Cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć |
| Zadanie | Defence (odporność) |
| Zespół | [nazwa zespołu] |
| Członkowie | Przemysław Nowak, Łukasz Janiec, Cezary Pastor |
| Repozytorium | https://github.com/przemeknowak781/avalauncher |
| Demo | https://przemeknowak781.github.io/avalauncher/ (dzień 2: `?day=2`) |
| Strona projektu | https://przemeknowak781.github.io/avalauncher/projekt.html |
| PDF | deck/avalauncher_deck.pdf (10 slajdów, ze zrzutami ekranu i linkami do repo i demo na slajdzie 10) |
| Film (zapas, nieobowiązkowy) | [link do filmu]. Wersja z głosem: `filmy/wideo/avalauncher_film_glos.mp4` (2:28, 22 MB), poza Git; wgrać na platformę albo pod osobny link |

## Opis (PL)

Avalauncher to prototyp cyfrowego bliźniaka góry dla służby lawinowej. Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z tysiącami scenariuszy lawin policzonych z góry w AvaFrame na prawdziwym terenie Tatr (w jedną noc: 1566, uczy się ich sieć neuronowa) i wskazuje stoki, które mogą zagrozić szlakom. Gdy wiedza się starzeje, bo dron nie mógł polecieć, mówi to wprost flagą „nie wiem” i planuje, gdzie polecieć, żeby się dowiedzieć. Działa bez sieci; w dniach zamieci 11–13.01.2025 nie widział terenu nawet satelita Sentinel-2. Decyduje człowiek.

Fizykę sprawdziliśmy na 5 prawdziwych lawinach z Austrii i Szwajcarii, bez podglądania wyniku: typowa pomyłka zasięgu 92 m, średnio 154 m, najgorsza 350 m. Szybka kopia fizyki (sieć neuronowa, ok. 4500× szybsza) na stokach, których nie widziała: zgodność obrysów 0,81. Pogoda jest prawdziwa (IMGW-PIB, zima 2024/25). Grubość płyty i loty drona są syntetyczne, więc plan lotu sprawdziliśmy tylko testem logiki: wyjaśnia 86 „nie wiem”, patrol wzdłuż szlaku 71. To nie jest zwalidowana prognoza dla Tatr. Zbudowane w jedną noc z otwartych danych, z pomocą AI (ujawnione w repo).

## Opis (EN, jeśli formularz go wymaga)

Avalauncher is a prototype digital twin of the mountain for the avalanche service. Drones regularly measure snow above hiking trails, and Avalauncher compares every measurement with thousands of avalanche scenarios pre-computed in AvaFrame on real Tatra terrain (1,566 in one night, learned by a neural network) and points to the slopes that can threaten trails. When knowledge goes stale because the drone could not fly, it says so with an "I don't know" flag and plans where to fly to find out. It works offline; during the 11–13.01.2025 storm even the Sentinel-2 satellite could not see the terrain. A human decides.

We tested the physics on 5 real avalanches from Austria and Switzerland without peeking at the held-out event: typical runout error 92 m, mean 154 m, worst 350 m. A fast neural copy of the physics (about 4,500× faster) on slopes it never saw: footprint agreement (IoU) 0.81. Weather is real (IMGW-PIB, winter 2024/25). Slab thickness and drone flights are synthetic, so the flight plan is only logic-tested: 86 "I don't know" sectors resolved vs 71 for a patrol along the trail. This is not a validated forecast for the Tatras. Built in one night from open data; AI use disclosed in the repo.

Skąd liczby (docs/12): 1566 symulacji (Biblioteka scenariuszy); 92 / 154 / 350 m (leave-one-out, 5 lawin); 0,81 i ok. 4500× (Sieć zastępcza); 86 wobec 71 (Dowód logiki, 30 poranków, przelot 20 min); satelita 11.01 chmury 100%, 12.01 brak przelotu, 13.01 chmury 86% (Sentinel-2).

## Ujawnienie AI i licencje

Pełny opis: [docs/10_ai_i_licencje.md](10_ai_i_licencje.md). Kod na licencji MIT ([LICENSE](../LICENSE)).

## Przed wysłaniem (stan sprawdzony 4.10.2026, ok. 09:25)

Zrobione:

- [x] Repo publiczne (GitHub API: `visibility: public`), Pages włączone, demo i projekt.html odpowiadają 200
- [x] PDF ma 10 stron, zrzuty ekranu, linki do demo i repo, ujawnienie AI i licencje (slajd 10)
- [x] README z instrukcją uruchomienia, LICENSE (MIT), docs/10 z ujawnieniem AI
- [x] Brak sekretów i plików powyżej 15 MB, brak odwołań do CDN

Do zrobienia przez koordynatora (przed 10:30):

- [ ] Zatwierdzić i wypchnąć zmiany w `web/`, README i docs (Pages stoi na dea3ab3, bez poprawek z tej nocy), potem sprawdzić, że workflow Pages przeszedł
- [ ] Zrobić na nowo zrzut okna flagi do slajdu 3 (PDF pokazuje jeszcze „zwykle rusza i dochodzi do szlaku”, czego silnik już nie mówi) i wyeksportować PDF ponownie (`node deck/tools/export.mjs`)
- [ ] README: usunąć dopisek „gdy repo będzie publiczne”

Do zrobienia przez użytkownika:

- [x] Członkowie wpisani (formularz i slajd 10). Nazwa zespołu: [do wpisania w formularzu]
- [ ] swisstopo: sprawdzić warunki użycia darmowych geodanych swisstopo i zamienić „[licencja do potwierdzenia przed pokazem]” (slajdy 6 i 10, README) na właściwą atrybucję albo zwykły przypis
- [ ] Film: zdecydować, czy dołączamy wersję roboczą (1:54) i gdzie ją umieścić; sprawdzić, czy platforma ma limit długości lub rozmiaru
- [ ] Potwierdzić na Discordzie godzinę zamknięcia (11:00) i długość pitchu
- [ ] Złożyć zgłoszenie na HackTribe i otworzyć wszystkie linki w oknie incognito

## Formularz HackTribe (EN), wersja z 4.10, ok. 10:30

**Problem:** Every winter morning the avalanche service has to decide which slopes may release onto hiking trails. The official bulletin gives one danger level (1–5) for the whole Polish Tatras, while snow differs from slope to slope. In physics simulations of the area around Hala Gąsienicowa, 48 of 58 steep slopes can send an avalanche onto a trail, 47 of them already with a 0.4 m slab. During the real storm of 11–13 January 2025 (+34 cm of new snow in 3 days, IMGW-PIB), the official level rose from 1 to 3, and the Sentinel-2 satellite could not see the terrain on any of those days (100% cloud, no overpass, 86% cloud). Drones can measure under the clouds, but someone has to turn measurements into a slope-by-slope decision quickly, and say honestly when the data is too old.

**Solution:** Avalauncher is decision support for the avalanche service: a digital twin of the mountain that knows what it doesn't know. Drones regularly measure snow above trails; Avalauncher compares every measurement with thousands of avalanche scenarios pre-computed with the AvaFrame physics solver on real Tatra terrain, learned by a neural network that draws a runout about 4,500× faster, and flags the slopes that may threaten trails. When knowledge goes stale because the drone could not fly, it says "I don't know" and plans where to fly to find out. It works offline. A human always decides.

**What's done:** Working web demo on real data: GUGiK terrain, OpenStreetMap trails, real IMGW-PIB weather of winter 2024/25 (two demo mornings, 12–13.01.2025). 1,566 AvaFrame avalanche simulations computed in one night (30.4 min on a DGX Spark). Physics checked against 5 real avalanches from Austria and Switzerland without peeking: typical runout error 92 m (25 m over 1,775 m on Popeletzbach). Neural surrogate: footprint agreement 0.81 on slopes it never saw. Flight planner: an RL policy trained on 10.4 million simulated mornings tied the simple value-of-information plan, so we kept the simpler one. Offline mode, 3D avalanche player, landing page, deck, video. Synthetic: slab thickness on slopes and drone flights (labelled). Goal next: a one-winter pilot with one avalanche service on one trail, calibrated on their own observations.
