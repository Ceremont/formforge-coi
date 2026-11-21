# FormForge — prezentacja PL (10 slajdów)

Wersja PDF: FormForge_COI_1.0_Presentation_PL.pdf. Dane mają jawny zakres; importer pozostaje niezweryfikowany.

## 1. FormForge

Od dokumentu do e-formularza.

- Lokalna cyfryzacja pustych blankietów urzędowych.
- Wydanie 1.0 · HackNation 2026 · niezależny projekt COI.
- Człowiek weryfikuje wynik przed eksportem.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 2. Problem

Blankiet jest czytelny dla człowieka. System potrzebuje struktury.

- PDF, Word, arkusze i skany opisują te same dane w różnych układach.
- Sama ekstrakcja tekstu nie wystarcza do pól, typów i zależności.
- Poprawny JSON nie dowodzi kompletnego rozpoznania dokumentu.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 3. Nasze rozwiązanie

Jeden proces, z widocznymi decyzjami.

- Prześlij dokument → rozpoznaj pola → porównaj ze źródłem.
- Popraw etykiety, typy, sekcje, opcje i reguły.
- Sprawdź lokalne kontrole i pobierz COI FormDefinition.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 4. Jak działa system

Model pośredni łączy dokument i konfigurację.

- Czytniki formatów / OCR → analiza układu i ról bloków.
- Pola ze źródłami → sekcje i jawne polityki standardu.
- Adapter COI → schema + profil rekurencyjny + reguły techniczne.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 5. Document Intelligence

Dowód źródłowy zamiast niejawnej odpowiedzi.

- Geometria PDF/obrazu, komórki arkusza i odtworzony tekst DOCX.
- Reguły semantyczne, lokalny Tesseract oraz opcjonalny własny Naive Bayes.
- Wynik heurystyki nie jest skalibrowanym prawdopodobieństwem.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 6. Zgodność z COI

Oficjalna struktura. Oddzielne poziomy weryfikacji.

- MAIN / FINISH, sekcje, repeating grid, UUID, walidatory i flow.links.
- Słowniki, EXTERNAL_SYSTEM i ograniczone SHOW / READ_ONLY / JSONata.
- Rzeczywisty importer niezweryfikowany; dynamiczne REQUIRED i pełne rejestry pozostają otwarte.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 7. Bezpieczeństwo i lokalność

Dokument pozostaje na wskazanym serwerze.

- Limity pliku, MIME i container checks, procesy z timeout, tymczasowe dane.
- Compose: UID10001, read-only, internal processor, CPU/RAM/PID limits.
- Realny test --network none: PDF + DOC + OCR + model lokalny. Build wymaga sieci.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 8. Wyniki testów

Mierzymy osobno konwersję i rozpoznanie.

- 196 pytest PASS. Browser E2E i Docker/offline sprawdzone.
- Źródła organizatora: 62/69 → 68/69 lokalnie poprawnych eksportów.
- Nowe 3 dokumenty R3: F1 pól 52,63% → 58,95%; 28/41 match, 54 predykcje. Mała próba, jeden anotator.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 9. Potencjał wdrożenia

Następny krok: potwierdzona integracja.

- Test rzeczywistego importera i szerszy niezależny korpus z wieloma anotatorami.
- Pełne wartości słowników/rejestry, lepsze pola i złożone zależności.
- Audyt natywnych licencji, praw zespołu i bezpieczeństwa; bez obietnic oszczędności.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.

## 10. Przegląd, korekta, eksport

Od dokumentu do e-formularza — z kontrolą człowieka.

- Działający lokalny produkt: upload, źródło, edytor, eForm, walidacja i JSON.
- Referencje 01/05: F1 workflow 98,04% / 97,20%, z jawnymi dodatkami standardu; to nie holdout.
- Przed oddaniem: importer, formalności/licencje, dostęp jury i publiczny film ≤3 min.

Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.
