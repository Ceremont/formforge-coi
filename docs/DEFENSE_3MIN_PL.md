> Historical report from the preview phase. The current official COI implementation and verification are described in [COI_COMPATIBILITY_REPORT.md](COI_COMPATIBILITY_REPORT.md) and [REFERENCE_COMPARISON.md](REFERENCE_COMPARISON.md). Earlier missing-material and compatibility statements below are superseded.

# Scenariusz obrony — 3 minuty

Scenariusz demonstracji na żywo. Tekst w cudzysłowie jest do wypowiedzenia;
czynności wykonujemy równolegle. Przed pokazem uruchom lokalny serwer, przygotuj
formularz spoza demo i sprawdź OCR. Nie przedstawiaj syntetycznego holdoutu jako
zewnętrznego benchmarku ani eksportu preview jako oficjalnego JSON COI.

## 0:00–0:25 — problem i rozwiązanie

„Urzędnik, który cyfryzuje papierowy wniosek, musi rozpoznać jego pola, sekcje i
reguły. FormForge skraca ten etap: przyjmuje dokument, buduje uporządkowaną
strukturę i pokazuje działający e-formularz. Wszystko odbywa się lokalnie.
Dokument nie trafia do zewnętrznej usługi AI, a oryginał znika z serwera po
zakończeniu żądania.”

## 0:25–0:55 — dokument wejściowy

**Czynność:** prześlij nowy PDF lub obraz, pokaż wynik analizy.

„Wgrywam formularz, dla którego nie przygotowaliśmy gotowego JSON-a. Silnik
odczytuje tekst i geometrię. Dla skanu porównuje kilka wariantów lokalnego OCR:
oryginał, poprawiony kontrast, skalowanie, korektę pochylenia i progowanie.
Zwykły tekstowy PDF przechodzi szybką ścieżkę. Każde pole zachowuje odwołanie do
strony i obszaru źródła.”

## 0:55–1:30 — kontrola i poprawki

**Czynność:** wybierz pole, pokaż źródło, popraw etykietę lub typ, dodaj pole.

„Po lewej widzimy dokument, po prawej rozpoznane pola lub wygenerowany
e-formularz. Wybór pola wskazuje źródło: dla obrazu zaznaczamy obszar, dla PDF
przechodzimy do strony. Wynik heurystyki nie jest prawdopodobieństwem poprawności.
Elementy niepewne wymagają przeglądu. Urzędnik może zmienić typ, walidację,
obowiązkowość, sekcję i słownik, połączyć pola w grupę albo usunąć błędną propozycję.”

## 1:30–2:00 — eForm i eksport

**Czynność:** zastosuj zmiany, otwórz eForm, pokaż błąd PESEL i pobierz JSON.

„Po zatwierdzeniu zmian przebudowujemy model, JSON i podgląd. Formularz sprawdza
między innymi PESEL, NIP, REGON, datę i wymagane wartości. Jawne zależności mogą
sterować widocznością pól i sekcji oraz obowiązkowością. Nie zgadujemy reguł
prawnych. Pobierany plik odzwierciedla aktualne poprawki, a wartości testowe nie
są zapisywane jako wniosek.”

## 2:00–2:35 — dowody i architektura

**Czynność:** pokaż tabelę w ACCURACY_REPORT i lokalny Swagger.

„REST API działa niezależnie od interfejsu. Testy obejmują rzeczywiste pliki,
błędy, uwierzytelnianie i sprzątanie danych. Na osobnym, zamrożonym zestawie
syntetycznym uzyskaliśmy recall około 95,5 procent i F1 około 97,7 procent.
To mały test lokalny, nie benchmark COI. Publikujemy także pominięcia i błędne
typy, zamiast ukrywać je za pojedynczym wynikiem.”

## 2:35–3:00 — uczciwy status i następny krok

„Dzisiaj eksport ma status preview. Bez oficjalnych par formularz–JSON nie
deklarujemy zgodności z importerem COI. Przygotowaliśmy konfigurowalny adapter
i ścisłą walidację schematu. DOC pozostaje jawnie nieobsługiwany, a kontener
wymaga sprawdzenia na działającym Dockerze. Następny krok to oficjalne materiały,
niezależne dokumenty urzędowe i pomiar jakości przed wdrożeniem.”
