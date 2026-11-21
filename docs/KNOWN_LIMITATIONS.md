# Znane ograniczenia 1.0

Wydanie działa i ma dowody lokalnych kontroli. Nie potwierdzono wszystkich wymagań konkursowych.

1. **Importer COI** nie był dostępny. JSON Schema, profil rekurencyjny i business rules
   są lokalne. Schemat organizatora jest niepełny, ma `repetingSectionGrid`, przykłady
   mają `repeatingSectionGrid`; obsługujemy obie pisownie wejścia i emitujemy drugą.
   Nie poprawiamy oryginałów. Przykłady FINISH naruszają część reguł technicznych.
2. **Kompletność** nie jest zagwarantowana. R3: 28/41 dopasowanych pól przy 54
   predykcjach, P=51,85%, R=68,29%, F1=58,95%. To 3 dokumenty, 2 wydawców,
   jeden anotator, nie populacyjny wskaźnik. Pełna trafność sekcji/workflow nieznana.
3. **Brakujące pola R3:** certificate_kind, registration_stay, deregistration_stay,
   relationship; copy_kind, act_kind, person1, event1, person2;
   requesting_org, krs, country, proceeding. Nadmiarowe: odpowiednio 9, 14 i 3.
   Lista etykiet/matchy w field-metrics.json. Edytor pozwala dodać/usunąć pola.
4. **Warunki:** rozpoznawane jawne proste wybory, ograniczone and/or i SHOW/READ_ONLY.
   Podkreślenia/skreślenia, odwołania do punktów, złożone statusy/obliczenia i część
   załączników wymagają ręcznej reguły. Dynamiczne REQUIRED pozostaje w modelu/preview
   i ostrzeżeniach: brak potwierdzonego oficjalnego kontraktu serializacji.
   Nie emitujemy wymyślonego JSONata dla nierozstrzygalnego warunku.
5. **Słowniki/rejestry:** są opisy/bindingi. Nie ma pełnych wartości COI ani integracji
   PESEL/REGON. Read-only pola EXTERNAL_SYSTEM są jawnie niedostępne lokalnie.
6. **DOC:** wyłącznie ograniczony tekst Word97–2003. Bez pełnej geometrii/składu,
   obrazów, pól Word i właściwości tabel. Starsze, encrypted, makra i embedded objects
   odrzucane. DOC08 ma osadzone obiekty; nie twierdzimy, że wykryto w nim malware.
7. **OCR:** CPU, jakość zależy od obrazu. Ręczne pismo i niski kontrast niezweryfikowane.
   Duży raster dzielony na fragmenty; granice i semantyka powtórzeń mogą być błędne.
8. **Preview:** nasz renderer modelu mapowanego do COI, nie renderer platformy.
   Maksymalnie 20 instancji grupy; odpowiedzi/file inputs tylko w pamięci DOM.
   Zmiana definicji odświeża preview i usuwa testowe odpowiedzi. FINISH nie wysyła wniosku.
   Rekonstrukcja tekstu Word/arkuszy nie zachowuje wiernej typografii.
9. **Bezpieczeństwo:** limity/izolacja/testy nie zastępują pentestu ani audytu parserów.
   Anulowanie w UI przerywa oczekiwanie; serwer sprząta po zakończeniu lub timeout.
   Dla użytkowania sieciowego trzeba włączyć JWT, TLS i zarządzanie dostępem.
10. **Licencje/formalności:** pełny native SBOM i interpretacja zakazu copyleft wobec
    standardowego OS są otwarte. Prawa zespołu/umowa i publiczna redystrybucja schemy
    niepotwierdzone. Film <=3 min nie nagrany/nie opublikowany, dostęp jury nie sprawdzony.
11. **Powtarzalność:** core Python lock i bazowy digest są przypięte. Pakiety apt są
    rejestrowane inventory, ale repo apt nie jest zamrożonym snapshotem. Zweryfikowano
    ARM64/Apple Silicon; pełny test x86_64 nie był wykonany.
12. **Zakres produktu:** brak podpisu, wysyłki do urzędu, archiwizacji, baz obywateli,
    fine-tuning LLM, automatycznego ustalania prawa/treści zgód i opłat.

Największe ryzyka na obronie: jakość na nowym blankiecie, nieznane zachowanie
importera oraz nierozstrzygnięte licencje/prawa. Patrz macierz wymagań, raport dokładności i scenariusz awaryjny demo.
