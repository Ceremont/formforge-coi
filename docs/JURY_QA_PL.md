# Pytania jury — odpowiedzi zgodne z kodem 1.0

## 1. Dlaczego taka architektura?

Rozdzielamy czytniki dokumentów, analizę układu, model wewnętrzny, adapter COI i walidację. To rozwinięcie istniejącego FastAPI/Jinja/JS; zachowane API oraz testy zmniejszają ryzyko regresji.

## 2. Jak działa OCR?

Lokalny Tesseract pol+eng analizuje ograniczone warianty obrazu. Pillow wykonuje kontrast, deskew i progowanie; współrzędne są przeliczane do źródła. Timeout i limity procesów ograniczają zasoby.

## 3. Gdzie jest AI?

OCR wykorzystuje modele Tesseract. Opcjonalny własny Naive Bayes klasyfikuje role bloków. Domyślny pipeline rozpoznawania jest oparty na jawnych regułach; nie ma LLM ani zewnętrznego inference.

## 4. Dlaczego rozwiązanie hybrydowe?

Warstwa tekstowa i natywne kontrolki zachowują lepszą informację niż sam raster; OCR obsługuje skany. Reguły semantyczne i geometria łączą dowody, a człowiek zatwierdza niepewności.

## 5. Jak wykrywacie pola?

FieldDetector korzysta z miejsc odpowiedzi, kontrolek, etykiet, blank cells i geometrii. Przypisuje typ, źródło, heuristic score i powód. Score nie jest skalibrowanym prawdopodobieństwem.

## 6. Jak analizowane są tabele?

DOCX obejmuje rekurencyjne tabele i jawne puste komórki odpowiedzi. XLSX/ODS obsługują scalenia i rzadkie arkusze. Wiersz źródła nie staje się automatycznie dynamicznym repeating section bez dowodu.

## 7. Jak mapowany jest COI JSON?

Model wewnętrzny trafia do adaptera: title, tabs MAIN/FINISH, questions, sekcje, grid, field, states i flow.links. Deterministyczne UUID są identyfikatorami, a porównanie referencji jest semantyczne.

## 8. Co z literówką repetingSectionGrid?

Wejście akceptuje obie pisownie. Eksport używa repeatingSectionGrid zgodnie z przykładami. Oryginalny schemat i przykłady pozostają nienaruszone; profil rekurencyjny uzupełnia ograniczenia schemy.

## 9. Jak powstaje JSONata?

Kompilujemy ograniczone dowiedzione wyrażenia equals/not_equals/and/or z odwołaniami do technicznych pól. Nie przepisujemy dowolnego tekstu na arbitralny kod. Nierozpoznane warunki pozostają ostrzeżeniem.

## 10. Czy dynamiczne REQUIRED jest gotowe?

Model i preview obsługują warunkową obowiązkowość. Nie potwierdzono oficjalnego kontraktu serializacji dynamicznego REQUIRED; eksport nie udaje pełnej obsługi tej funkcji.

## 11. Jak weryfikujecie słowniki?

Katalog opisów służy do dopasowania dictionaryName. Pełne wartości musi rozwiązać COI; options dla słownika są puste. Własne propozycje z opcji można poprawić w edytorze. Binding wymaga potwierdzenia.

## 12. Czy działają rejestry PESEL/REGON?

Eksportujemy jawne wskazówki EXTERNAL_SYSTEM i readOnly. Żaden rejestr nie jest podłączony w lokalnej demonstracji. Nie uzupełniamy danych obywatela fikcyjną odpowiedzią.

## 13. Jak zapewniacie bezpieczeństwo?

Weryfikacja MIME/magic/container, ograniczenia nazwy i rozmiaru, ZIP/XML/makra, izolowane procesy z deadline i pamięcią, semafor, temp cleanup, JWT oraz read-only non-root Docker. To nie pełny pentest.

## 14. Czy działa offline?

Po instalacji tak: test kontenera --network none wykonał HTTP konwersję PDF, DOC i PNG/OCR z modelem lokalnym, a zewnętrzne połączenia były blokowane. Pierwszy build pobiera pakiety i dane OCR.

## 15. Jakie są licencje?

Python runtime ma 38 przypiętych dystrybucji z wybranymi permissive licenses; odfpy Apache, olefile BSD. OCR Apache/BSD. Native/OS audit i prawa zespołu pozostają częściowo otwarte, nie deklarujemy całego OCI bez copyleft.

## 16. Jak zachowuje się nowy dokument?

Przechodzi ten sam pipeline pod dowolną poprawną nazwą, bez lookup referencyjnego JSON. Wynik może być częściowy; UI pokazuje źródła, ostrzeżenia i pozwala poprawić brakujące/nadmiarowe pola.

## 17. Jak mierzycie dokładność?

Oddzielamy znane referencje, development i prospektywny R3. Stałe anotacje, match jeden-do-jednego i typy, bez UUID byte comparison. Raportujemy precision/recall/F1, zakres typów/sekcji i N/A tam, gdzie nie ma ground truth.

## 18. Czy 68/69 oznacza 98,6% dokładności?

Nie. To liczba źródeł konwertowanych do lokalnie poprawnej konfiguracji, a nie trafność pól. R3 micro F1 surowych pól wynosi 58,95%, przy 28/41 matchach i 54 predykcjach.

## 19. Co przy błędzie OCR?

Brak Tesseract, języka lub deadline daje kontrolowany komunikat/ostrzeżenie. Nie deklarujemy sukcesu, jeśli brak pól. Można ponowić z lepszym obrazem lub PDF z tekstem; źródło i limity pozostają kontrolowane.

## 20. Co przy nieznanym formacie?

Serwer sprawdza faktyczną zawartość. Nieobsługiwany format jest odrzucany, zwykle 415. Zmiana rozszerzenia nie omija kontroli; makra, szyfrowanie i embedded objects w DOC są celowo odrzucane.

## 21. Co z Word DOC?

Jest ograniczony własny read-only parser Word97–2003 z olefile. Obsługuje tekst i część tabel/textboxów, nie skład Word. DOC08 z osadzonymi obiektami pozostaje odrzucony; to istotna luka wymagań.

## 22. Jakie ograniczenia są najważniejsze?

Nieznany importer, niepełne pola/warunki i sekcje nowych blankietów, brak pełnych słowników/rejestrów, podzbiór DOC i otwarty native-license audit. Wszystko jest w macierzy i KNOWN_LIMITATIONS.

## 23. Czy rozwiązanie jest skalowalne?

Obecny procesor ma domyślnie dwa worker slots i izolowane procesy. Nadmiar dostaje 429. Nie zmierzyliśmy produkcyjnej przepustowości ani klastra; potrzebne są load tests, orkiestracja i kontrola obciążenia.

## 24. Co trzeba przed produkcją?

Test prawdziwego importera, szerszy zespół anotujący i korpus, potwierdzenie polityk COI, pełny audyt praw/licencji i bezpieczeństwa, JWT/TLS/zarządzanie użytkownikami oraz obserwowalność bez danych dokumentów.

## 25. Czym różni się od zwykłego OCR?

OCR daje tekst. FormForge buduje pola, typy, sekcje, źródła, ograniczone zależności i formalny eksport COI, a następnie weryfikuje i umożliwia korektę. Nie oznacza to pełnego zrozumienia prawa.

## 26. Czym różni się od JSON generowanego przez LLM?

Nie wysyłamy treści do zewnętrznego modelu. Wynik przechodzi jawny model/adapter i walidatory; decyzje mają źródło. Reguły mogą również się mylić, co pokazują nasze metryki.

## 27. Czy da się bez AI?

Tekstowe PDF/DOCX/arkusze działają w trybie reguł bez opcjonalnego klasyfikatora. Skany potrzebują OCR Tesseract, który sam używa modelu. Nie nazywamy OCR przetwarzaniem bez modelu.

## 28. Czy sprawdzono prawdziwy importer COI?

Nie. Nie było dostępu do działającej platformy. Lokalny schemat, profil i reguły są sprawdzone; oznaczenie target_import_verified zawsze pozostaje false.

## 29. Jakie dane są przetwarzane i gdzie?

Przeznaczeniem są puste blankiety. Upload trafia wyłącznie na wskazany lokalny serwer, temp jest usuwany. Model/źródło i testowe odpowiedzi żyją w pamięci karty; nie ma bazy wniosków ani telemetryki.

## 30. Co dalej poprawić?

Kolejny niezależny korpus z wieloma anotatorami, lepsze rozdzielanie pól urzędowych/obywatelskich, OCR tabel i skreśleń, importer integration, oficjalne słowniki/rejestry. Nowe strojenie wymaga nowego holdoutu.

## 31. Czy film i repo są już przekazane?

Nie wykonano publikacji, zmiany visibility ani nadania dostępu. Dostarczamy lokalne commity/tag, czysty ZIP, PDF i skrypt. Właściciel musi nagrać publiczny film <=3 min i zapewnić dostęp jury oraz formalności prawne.
