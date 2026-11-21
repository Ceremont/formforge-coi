# Demo FormForge — 2:45

Przed wystąpieniem: uruchom już zbudowany obraz, sprawdź health i pol+eng,
przygotuj nowy pusty dokument od jury oraz własny PDF na wypadek awarii.
Nie używaj danych obywateli. Zrób próbę z zegarem. Film publiczny ma limit 3 min;
ten skrypt nie jest dowodem nagrania ani opublikowania filmu.

| Czas | Działanie / wypowiedź |
|---|---|
| 0:00–0:15 | „Od dokumentu do e-formularza. FormForge pomaga przenieść pusty blankiet do konfiguracji COI, pozostawiając kontrolę człowiekowi.” |
| 0:15–0:40 | Prześlij nowy PDF/DOCX jury. Pokaż rzeczywisty czas, nie procent postępu. „Analiza działa lokalnie, bez zewnętrznych API.” |
| 0:40–1:05 | W przeglądzie wskaż liczbę pól i ostrzeżenia. Otwórz dokument, wybierz pole, pokaż źródło/bbox lub odtworzony tekst. |
| 1:05–1:30 | W edytorze popraw etykietę/typ jednego rzeczywistego błędu. Jeśli brak pominięcia, zmień czytelną etykietę i nazwij to korektą redakcyjną. Poczekaj na walidację; pokaż blokadę eksportu podczas zmiany. |
| 1:30–1:55 | Otwórz eForm, wypełnij testowe pole; jeśli dokument ma wykrytą zależność, przełącz jawny wybór. Nie przedstawiaj reguły ręcznej jako automatycznie wykrytej. |
| 1:55–2:20 | Zgodność z COI: schema, business rules, ostrzeżenia. „To lokalne kontrole. Rzeczywisty importer pozostaje niezweryfikowany.” |
| 2:20–2:45 | Pobierz JSON, pokaż title/tabs/flow. „68/69 źródeł konwertuje; na 3 nowych dokumentach F1 surowych pól 58,95%. Potrzebny jest przegląd, integracja i dalsze pomiary.” |

## Rozszerzona demonstracja techniczna — 7–9 minut

1. Pokaż POST convert i odpowiedź: detected_form kontra form z uzupełnieniami standardu.
2. Źródło strony 2, zoom, pochodzenie pola, tabela DOCX lub adres komórki XLSX.
3. Filtr „Wymagają weryfikacji”, zmiana typu, walidator, opcje, potwierdzenie właściwości.
4. Dodanie pominiętego pola, usunięcie nadmiarowego, cofnięcie i ponowienie.
5. Na własnej grupie pokaż powtarzanie; nazwij ręczną zmianę. Sprawdź zachowanie odpowiedzi po dodaniu wiersza.
6. Na własnym wielostronicowym demo pokaż radio Osoba/Firma i NIP, FINISH bez input.
7. JSON: wyszukiwanie, format, niezależne ponowne sprawdzenie, eksport.
8. Pokaż R3 manifest/freeze/metodę i listę brakujących pól; 01/05 nie są holdoutem.
9. Pokaż Compose internal processor, UID10001, read-only i offline-verification.json.
10. Zakończ ograniczeniami importera, licencji i formalnego przekazania.

## Scenariusze awaryjne

- Wolny OCR: pokaż czas, poczekaj do zadeklarowanego limitu. Anuluj oczekiwanie,
  przejdź na własny PDF z warstwą tekstową i powiedz, że to demonstracja zastępcza.
  Nie udawaj zakończenia OCR i nie podmieniaj gotowego JSON po nazwie.
- Docker: sprawdź `docker compose ps` i `docker compose logs --tail=40`. Jeśli daemon
  niedostępny, użyj wcześniej zainstalowanego lokalnego Pythona/Tesseract wg README.
- Nieobsługiwany/bezpiecznie odrzucony DOC: pokaż kontrolowany błąd, poproś o PDF/DOCX;
  użyj własnego demonstratora, jasno odróżniając go od dokumentu jury.
- Błąd rozpoznania: pokaż go w źródle i popraw w edytorze. Jeśli złożona zależność
  przekracza zakres mappera, zostaw ostrzeżenie; nie deklaruj zgodności importera.
- Brak łączności: po build przetwarzanie nie wymaga Internetu. Publiczny link filmu
  i repo muszą zostać przygotowane wcześniej przez zespół.
