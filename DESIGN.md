# DESIGN: Mapa tatrzańska

Świat wizualny ekranu demo. Wybrany 3.10.2026. Zmiany tylko za zgodą zespołu.

**Scena:** jury ogląda ekran w jasnej hali, z 3–4 m, na rzutniku lub ekranie LED. Stąd jasny papier i bardzo duża, czytelna typografia.

**Świat:** papierowa mapa turystyczna Tatr. Kremowy papier, hipsometria i miękkie cieniowanie, poziomice co 50 m (warstwice główne co 250 m), stawy na niebiesko, szlaki w ich prawdziwych kolorach z białą obwódką.

## Kolor (role, nie paleta)

| Rola | Wartość | Użycie |
| --- | --- | --- |
| papier | `#f4efe4`, głębszy `#ebe4d4` | tło, powierzchnie |
| atrament | `#1d1b17`, drugi `#5a5244` | tekst, ramki, aktywny dzień |
| zagrożenie | `#e8590c` (tekst `#a63b00`) | „Może zagrozić szlakowi”: kreskowanie i obrys, bo na mapach kreskowanie oznacza strefę zagrożenia |
| niewiedza | `#5b3fd1` + biała mgła | „Nie wiem”: mgła niewiedzy i fioletowy obrys |
| trasa | `#d6007e` | plan przelotu, dron, akcja „Leć”; magenta jak na mapach lotniczych |

Czerwień jest zarezerwowana dla czerwonego szlaku. Alarmy nigdy nie używają czerwieni.

## Typografia

Jedna rodzina: **Archivo** (zmienna, osie szerokości i grubości, OFL, `web/vendor/fonts/`). Szeroka (`font-stretch: 112–125%`, grubość 750–800) do nagłówków i liczb. Normalna do tekstu (17 px bazowo). Zwężona (75–87,5%) do podpisów na mapie, jak w kartografii.

## Ruch

Jeden autorski moment: **mgła niewiedzy**. Zagęszcza się, gdy wiedza się starzeje, a przelot drona czyści ją na żywo. Wejścia list to delikatny ruch w górę. Wszystko z wygaszeniem wykładniczym. `prefers-reduced-motion` wyłącza animacje.

## Zakazy (z Impeccable)

Bez kolorowych pasków z lewej na kartach, bez etykiet nad nagłówkami, bez emoji i znaków Unicode zamiast ikon (ikony to rysowane SVG), bez gradientowego tekstu, bez kart w kartach, bez zmyślonych liczb. Numery 1, 2, 3 są dozwolone, bo łączą listę z mapą.
