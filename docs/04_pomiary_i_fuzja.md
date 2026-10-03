# LiDAR, radar i punkty terenowe w jednym oblocie

## Co pojedynczy oblot rzeczywiście obserwuje

Zimowy LiDAR mierzy powierzchnię śniegu. Głębokość na współrzędnych bez roślinności to różnica wysokości tej powierzchni i **wcześniej pozyskanego modelu gruntu bez śniegu**, po wyrównaniu układów odniesienia. Przy drzewach, skałach i w cieniach ubytki oraz błędy rejestracji powinny dostać maskę jakości i przedział błędu. [SnowEx20/Grand Mesa](https://nsidc.org/data/snex20_bsal_sd/versions/1) jest konkretnym przykładem połączenia oblotu bez śniegu z 2016 r. i zimowego z 2020 r.; nie jest to jeden przelot w jednym dniu.

Radar penetrujący śnieg (GPR; także wielokanałowy FMCW/UWB) może dać odbicia od górnej i dolnej granicy śniegu oraz od warstw wewnętrznych. Z czasu przejścia i prędkości fali zależnej od przenikalności/densytetu szacuje się grubość. [Kolpuke i in. 2024](https://doi.org/10.1109/TGRS.2024.3359125) wykazali taki pomiar z platformy lotniczej dla pokrywy 1,2–2,6 m, z pomiarami terenowymi do kalibracji. [Dupuy i in. 2026](https://doi.org/10.1016/j.coldregions.2025.104641) opisują GPR niesiony dronem: kompromis częstotliwości, rozdzielczości i penetracji, szczególnie w mokrym śniegu. Dane z drona lecącego kilka metrów nad śniegiem **nie potwierdzają automatycznie** wykonalności tego samego podwieszenia pod helikopterem na innej wysokości; trzeba dobrać geometrię anten, prędkość, zasięg i procedury lotnicze.

## Punktowe ograniczenia z krajobrazu

Zdjęcia odsłoniętych skał, znaków i sztywnych pni wykonane bez śniegu oraz zimą mogą dostarczyć lokalnych oszacowań poziomu zasypania. Punkty mają współrzędne, geometrię widocznej części i niepewność; ruchome gałęzie, nawisy, oszronienie i perspektywa obrazu są źródłami błędu. Filhol i in. (2019) używali naturalnych punktów kontrolnych w fotogrametrii pokrywy śnieżnej — sama technika nie jest nowa. Pojedynczy głaz ogranicza głębokość w sąsiedztwie, nie identyfikuje całej doliny ani niewidocznej warstwy słabej.

## Proponowany algorytm asymilacji

1. Przygotować historyczny DTM bez śniegu, położenie trwałych punktów, metadane dokładności i siatkę obszaru.
2. Zarejestrować LiDAR i zdjęcia do DTM; zachować rozkład błędu georeferencji. Wyznaczyć mapę `h_snow = z_winter - z_bare` tam, gdzie piksele są wiarygodne.
3. Wzdłuż wybranych linii pomierzyć GPR, zidentyfikować echo podstawy i wyznaczyć grubość wraz z niepewnością przenikalności; kalibrować sondażami tam, gdzie można bezpiecznie.
4. Dodać lokalne obserwacje skał/pni jako ograniczenia z przedziałem, nie jako pewną prawdę. Połączyć z prognozą SNOWPACK/Alpine3D i zachować maski braku danych.
5. Zapisać posterior `p(grubość, gęstość, warstwy, możliwy obszar uwolnienia | oblot, pogoda, pomiary terenowe)` w próbkach/ensemble. Dopiero z tego stanu wyszukać i uruchomić scenariusze ruchu.

Wysokość pokrywy, ekwiwalent wodny SWE, gęstość i grubość odrywanej płyty mają różne jednostki i role. LiDAR mierzy pierwszą wielkość przez różnicę wysokości; radar pomaga z pierwszą i warstwami; SWE wymaga jeszcze gęstości. [SnowEx20 zestawienie LiDAR + GPR](https://nsidc.org/data/snex20_gm_swe_sd/versions/1) jest użytecznym zbiorem do sprawdzenia tych zależności. Radaru nie traktować jako pewnego wskaźnika niebezpieczeństwa lawinowego.

## Test terenowy

Przed obietnicą jednego przelotu wykonać mały pilot: DTM bez śniegu, zimowy oblot, powtarzalne zdjęcia 10–20 punktów, kilka transektów GPR i niezależne sondowania. Porównać błąd głębokości i zakres pokrycia dla: LiDAR sam, LiDAR + punkty, LiDAR + radar, trzy sygnały razem. Weryfikować osobno las, otwarte stoki, śnieg mokry i suchy.

Źródła: [Kolpuke i in. (2024)](https://doi.org/10.1109/TGRS.2024.3359125), [Dupuy i in. (2026)](https://doi.org/10.1016/j.coldregions.2025.104641), [Filhol i in. (2019)](https://doi.org/10.1029/2018WR024530), [SnowEx20 BSAL](https://nsidc.org/data/snex20_bsal_sd/versions/1), [SnowEx20 GPR/SWE](https://nsidc.org/data/snex20_gm_swe_sd/versions/1).

