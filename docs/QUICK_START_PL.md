# FormForge 1.1 — cztery kroki do konfiguracji COI

**Projektujesz wzór formularza. Użyj pustego blankietu, bez danych obywatela.**

## Uruchomienie

Rozpakuj projekt do katalogu o prostej nazwie, np. `FormForge-COI`.
Uruchom Docker Desktop i wykonaj w tym katalogu:

```sh
docker compose build
docker compose up -d --wait
curl http://127.0.0.1:8000/api/health
```

Otwórz http://127.0.0.1:8000. Inny port:
`FORMFORGE_HTTP_PORT=8772 docker compose up -d --wait`.
Zatrzymanie: `docker compose down`.
Jeśli Buildx zgłasza problem Unicode w ścieżce, użyj katalogu ASCII.
Pierwszy build potrzebuje Internetu; po instalacji analiza działa lokalnie.

## 1. Dodaj dokument

Kliknij **Wybierz dokument**, upuść pusty formularz albo wybierz
**Wypróbuj przykładowy formularz**. Przykład jest analizowany od początku.
Po zakończeniu otworzy się krok 2; nie szukaj wyniku na dole strony.

## 2. Sprawdź i popraw

Po lewej dokument, po prawej lista pól i wybrane właściwości. Kliknij pole,
aby zobaczyć jego źródło. Podpis **Pole dodane na podstawie standardu COI** oznacza
uzupełnienie wymagające przeglądu, a nie bezpośredni odczyt z dokumentu.

Popraw nazwę, typ, obowiązkowość i opcje. Potwierdź sprawdzone pole checkboxem.
Możesz dodać brakujące lub usunąć nadmiarowe pole. Zmiany są automatycznie
sprawdzane. Uchwyt między panelami zmienia ich szerokość; działa też klawiaturą.

**Zobacz uwagi** rozdziela błędy do poprawy, elementy do potwierdzenia i informacje.
Przycisk **Zatwierdź i przejdź dalej** nie potwierdza wszystkich pól zbiorczo.

## 3. Przetestuj formularz

Zobacz formularz oczami obywatela. Wpisuj tylko fikcyjne odpowiedzi. Sprawdź wybory,
widoczność, wymagane pola, strony i powtarzanie. Rejestry publiczne nie są podłączone;
wyjaśnienie przy zablokowanym polu nie oznacza pobrania danych.

**Wróć do edycji** pozwala poprawić strukturę. **Przejdź do eksportu** otwiera podsumowanie.
Odpowiedzi testowe nie są wpisywane do JSON COI.

## 4. Eksportuj do COI

Sprawdź osobno schemat JSON, lokalne reguły, przegląd treści i status importera.
Kliknij **Pobierz JSON COI**. Przy blokujących błędach dostępny jest jawny szkic;
popraw błędy przed użyciem pliku. Poprawność lokalna nie jest potwierdzeniem importu.

## Tryb ekspercki

Przycisk w headerze udostępnia pełny edytor, wszystkie wcześniejsze zakładki,
JSON, diagnostykę i API. Zmiana trybu zachowuje dokument, bieżące prawki i wartości
preview. Nie trzeba zaczynać od nowa. W **Przegląd → Co oznaczają liczby?** są
odrębne liczniki źródła/modelu/eksportu i stanów COI.

DOC ma ograniczony odczyt Word97–2003; Word/arkusze nie zachowują pełnego składu
w widoku źródła. Rzeczywisty importer COI i kompletność dowolnego nowego formularza
nie są potwierdzone. Więcej: UX_1.1_REPORT.md, KNOWN_LIMITATIONS.md i README.
