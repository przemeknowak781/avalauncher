# Avalauncher: wytyczne dla agentów

HackYeah 2026, zadanie Defence. Termin zgłoszenia: 4.10.2026, 11:00. Zamrożenie funkcji: 02:30.

**Teza, której służy każda linijka kodu:**
Drony regularnie mierzą śnieg nad szlakami, a Avalauncher porównuje każdy pomiar z tysiącami scenariuszy lawin policzonych z góry, których uczy się sieć neuronowa, i wskazuje służbie lawinowej stoki, które mogą zagrozić szlakom. Gdy wiedza się starzeje, bo dron nie mógł polecieć, mówi to wprost i planuje, gdzie polecieć, żeby się dowiedzieć.

Pełny plan, kontrakt danych i podział pracy: [docs/09_plan_budowy.md](docs/09_plan_budowy.md). Przeczytaj go przed pierwszą zmianą.

## Zasady

- Buduj tylko to, co widać w jednym z dwóch zdań. Szybko, efektownie, prosto.
- Weryfikuj tylko w niezbędnym zakresie: jeden test dymny na pakiet.
- Pracuj tylko w swoich katalogach (plan, sekcja 5). Trzymaj się kontraktu danych (sekcja 4).
- Demo działa offline: bez CDN, biblioteki w `web/vendor/`.
- Teksty w interfejsie po polsku. Nigdy „bezpiecznie”, „skalibrowany dla Tatr” ani zmyślone liczby. Wolno: „przykładowa kalibracja na prawdziwym zdarzeniu z Austrii (Popeletzbach)”.
- Pogoda jest prawdziwa (IMGW-PIB Kasprowy Wierch, zima 2024/25). Grubość płyty na stokach i przeloty drona są syntetyczne i tak są podpisane. Teren to GUGiK NMT, szlaki pochodzą z OpenStreetMap (atrybucja na ekranie). Liczby tylko z docs/12_wyniki.md.
- Nie zmieniaj `docs/00`–`docs/08` ani `src/avalauncher/`.
- Surowe dane trafiają do `data/raw/` (poza Git). Nie commituj sekretów ani plików powyżej 15 MB.
- Małe commity na `main`, przed pushem `git pull --rebase`.

## Prezentacja i film (decyzje użytkownika, 4.10.2026)

Ok. 08:15–08:20 użytkownik wybrał w czacie: deck „Styl XP jak aplikacja”, film „Surowe ujęcia + szybki montaż”, a potem napisał: „wznawiamy. Styl xp subtelny, nie nachalny ale widoczny i rozpoznawalny”. To zastępuje blokady z 02:40.

- **Deck:** 10 slajdów w deck/ według docs/11_deck.md, w stylu XP subtelnym: rozpoznawalne akcenty (pasek tytułu okna Luna, przyciski okna, pasek zadań), ale treść czysta, czytelna z daleka, dużo powietrza. Eksport do PDF dozwolony.
- **Film:** scenariusz docs/15_wideo.md. Wolno nagrać surowe ujęcia i zmontować wersję roboczą bez głosu, z napisami.
- Postać ratownika jest fikcyjna; nie używamy nazwy ani logo TOPR, Skype ani Microsoft jako sugestii partnerstwa.
