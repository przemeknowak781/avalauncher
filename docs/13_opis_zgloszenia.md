# Zgłoszenie HackTribe: teksty do wklejenia

Liczby pochodzą z [docs/12_wyniki.md](12_wyniki.md). Pola w nawiasach kwadratowych uzupełnia zespół.

## Pola formularza

| Pole | Wartość |
| --- | --- |
| Tytuł projektu | Avalauncher |
| Podtytuł | Cyfrowy bliźniak góry, który wie, czego nie wie, i mówi, gdzie polecieć, żeby się dowiedzieć |
| Zadanie | Defence (odporność) |
| Zespół | [nazwa zespołu] |
| Członkowie | [imiona i nazwiska, 1–6 osób] |
| Repozytorium | https://github.com/przemeknowak781/avalauncher |
| Demo | https://przemeknowak781.github.io/avalauncher/ (dzień 2: `?day=2`) |
| Strona projektu | https://przemeknowak781.github.io/avalauncher/projekt.html |
| PDF | deck/avalauncher_deck.pdf (10 slajdów) |
| Film | filmy/wideo/avalauncher_film_roboczy.mp4 (wersja robocza) |

## Opis (PL)

Avalauncher to cyfrowy bliźniak góry dla służby lawinowej. Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z 1566 lawinami policzonymi z góry w AvaFrame na prawdziwym terenie Tatr (GUGiK NMT, szlaki OpenStreetMap) i wskazuje stoki, które mogą zagrozić szlakom. Gdy wiedza się starzeje, bo dron nie mógł polecieć, mówi to wprost flagą „nie wiem” i planuje, gdzie polecieć, żeby się dowiedzieć. Działa bez internetu, a decyzję zawsze podejmuje człowiek.

Sprawdziliśmy to na rzeczywistości. Fizykę na 5 prawdziwych lawinach z Austrii i Szwajcarii (AvaFrameData), za każdym razem bez podglądania wyniku: typowa pomyłka zasięgu 92 m, na Popeletzbach 25 m na 1775 m. Szybką kopię fizyki (sieć neuronowa, ok. 4500× szybsza) na stokach, których nie widziała: zgodność obrysów 0,81. Pogoda to prawdziwa zima 2024/25 z IMGW-PIB, a stopień zagrożenia z komunikatów TOPR rośnie 12–13.01.2025 w te same dni, w które zapala się nasz kalendarz. Grubość płyty i loty drona są syntetyczne i tak podpisane. Zbudowane w jedną noc z otwartych danych, z pomocą AI (ujawnione w repo).

## Opis (EN, jeśli formularz go wymaga)

Avalauncher is a digital twin of the mountain for the avalanche service. Drones regularly measure snow above hiking trails, and Avalauncher compares every measurement with 1,566 avalanches pre-computed in AvaFrame on real Tatra terrain (GUGiK DEM, OpenStreetMap trails) and points to the slopes that can threaten trails. When knowledge goes stale because the drone could not fly, it says so with an "I don't know" flag and plans where to fly to find out. It works offline, and a human always decides.

We checked it against reality. The physics on 5 real avalanches from Austria and Switzerland (AvaFrameData), each time without looking at the held-out result: typical runout error 92 m, 25 m over 1,775 m on Popeletzbach. The fast neural copy of the physics (about 4,500× faster) on slopes it never saw: footprint agreement (IoU) 0.81. Weather is the real 2024/25 winter from IMGW-PIB, and the official avalanche danger level rises on 12–13.01.2025, the same days our calendar lights up. Slab thickness and drone flights are synthetic and labelled as such. Built in one night from open data, with AI assistance (disclosed in the repo).

## Ujawnienie AI i licencje

Pełny opis: [docs/10_ai_i_licencje.md](10_ai_i_licencje.md). Kod na licencji MIT ([LICENSE](../LICENSE)).

## Przed wysłaniem

- [ ] Repo publiczne, Pages włączone (Source: GitHub Actions), demo otwiera się w oknie incognito
- [ ] Nazwa zespołu i członkowie wpisani
- [ ] PDF załączony, linki sprawdzone w incognito
- [ ] Termin i długość pitchu potwierdzone na Discordzie
