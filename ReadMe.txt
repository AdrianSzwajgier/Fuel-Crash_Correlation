1. Informacje formalne:
    a. Nazwa projektu: Wypadki drogowe a ceny paliw w Polsce.

    b. Skład grupy projektowej:
        - Adrian Szwajgier (dane o wypadkach i cenach paliwa, backend, frontend),
        - Kamil Tokarski (dane inflacji, obsługa użytkowników, backend, frontend).

    c. Technologie:
        Aplikacja: Django (Python),
        Frontend (wygląd): Bootstrap,
        Baza danych: SQLite,
        REST API: GUS DBW API.

2. Opis projektu:
    a. Problem integracyjny: Analiza danych wypadków drogowych w kontekście cen paliw.
    b. Opis problemu: Analiza danych wypadków drogowych oraz cen paliw jest trudna, ze względu na rozproszenie danych. Same dane często nie są w postaci sprzyjającej porównywanie oraz analizę. Ceny paliw są zazwyczaj tylko wyświetlane na stronie, a statystyki wypadków to obszerne pliki pdf na każdy rok. Jedynie inflację, użytą tutaj do korekty cen paliw, można uzyskać z API.
    Aczkolwiek nawet tutaj nie jest to proste, ponieważ to API jest bardzo rozbudowane, a dokumentacja mało przyjazna i zrozumiałą.
    c. Lista przykładowych pytań:
        - Czy wzrost cen paliw wpływa na spadek liczby wypadków?
        - Jak wyglądają ceny paliw w latach 2010-2025 po uwzględnieniu inflacji a jak bez jej uwzględniania?
        - Jak bardzo inflacja wpływa na cenę paliwa?
        - Czy istnieje korelacja między liczbą wypadków a cenami paliw?
        - W których miesiącach roku korelacja między wypadkami a ceną paliwa jest największa?

3. Konfiguracja środowiska:
    Aplikację testowano i uruchamiano, używając IDE PyCharm 2025.3.5, wszystkie niezbędne biblioteki są umieszczone w pliku requiremnets.txt, a komendy do uruchomienia w pliku README.md

4. Wykorzystane dane:
 - Statystyki wypadków Policji: https://statystyka.policja.pl/st/ruch-drogowy/76562,Wypadki-drogowe-raporty-roczne.html
 - Ceny paliw (Internetowa Giełda Rolna): https://www.ewgt.com.pl/towary/dane/index.php?id=6
 - Inflacja GUS (API DBW): https://api.stat.gov.pl/Home/DBWApi

