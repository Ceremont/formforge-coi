# FormForge 0.4 → 0.5 → 1.0: plan i stan początkowy

Punkt wyjścia: commit `aaa8148`, wersja 0.3.0, czyste drzewo robocze.
Nowa gałąź: `feature/competition-final`; bez scalenia do main.
Baseline: 178 testów, 62/69 źródeł COI przetworzonych i lokalnie poprawnych.
Siedem binarnych DOC odrzuconych. Zamrożone wyniki coi-v1 oraz engine-v03
pozostają historycznym materiałem, nie nowym niezależnym testem.

## Już działa

REST API, izolowane procesy, walidacja uploadu/JWT, lokalny OCR pol+eng,
DOCX textbox/tabele, PDF/arkusze/duże obrazy, oficjalny adapter COI,
schema/profile/business validation, edytor, source mapping, lokalny eForm,
eksport, kontener non-root/read-only z wewnętrzną siecią procesora.

## Częściowe

Semantyka sekcji i etykiet PDF; złożone warunki i powtarzalność; słowniki
obejmują opisy i bindingi, nie kompletne wartości; eForm nie ma dynamicznych
instancji grup i nawigacji FINISH. Interfejs wymaga polskich komunikatów,
czytelnej syntezy jakości, filtrów i bezpiecznej obsługi niezapisanych zmian.

## Blokery i nieweryfikowalne wymagania

Brak zweryfikowanego konwertera binarnego DOC, dostępu do docelowego importera
i rejestrów. Pełny audyt natywnych składników obrazu oraz umowa przeniesienia
praw/zgody na rozpowszechnianie materiałów organizatora nie są zastępowane
przez metadane pakietów. Nie publikujemy tych materiałów w czystym ZIP.
Film i dostęp jury do repozytorium wymagają działania zespołu; bez publikacji
lub zmiany visibility w tej iteracji.

## Kolejność

1. 0.4: wymagania z rzeczywistymi źródłami, poprawki sprawdzonych błędów
   etykiet/sekcji, kontrola jakości z rekomendacjami; sprawdzenie DOC bez
   naruszenia licencji/bezpieczeństwa. Regresje i benchmark w coi-final.
   Nowe dokumenty wybieramy po zamrożeniu silnika. Commit 0.4 po działającym E2E.
2. 0.5: rozwój istniejącego JS/CSS: ekran startowy i przegląd, filtry edytora,
   JSON workspace, dostępność i polskie komunikaty, nawigacja i grupy eForm.
   Faktyczne testy browser/viewport, screenshots; commit 0.5.
3. 1.0: stabilizacja, kontener/offline/security/license evidence, kompletna
   dokumentacja jury, PDF prezentacji, scenariusz demo, czysta paczka,
   VERSION/CHANGELOG/release notes, commit release i lokalny tag v1.0.0.

Każdy PASS w macierzy wymaga dowodu kodu i wykonanej kontroli. Wynik poprawny
technicznie nie jest dowodem kompletnego rozpoznania ani importu do COI.
Nieweryfikowalne elementy pozostają UNVERIFIED, a brakujące FAIL/PARTIAL.

## Zakończenie 0.4

191 pytest i browser smoke przeszły; 68/69 konwersji, wszystkie 68 lokalnie
poprawne. R1/R2 zachowane jako development/audyt; R3 ma zablokowane adnotacje
i brak strojenia na jego wynikach. Umiarkowana poprawa niezależnego F1, istotne
braki pozostają jawne w FINAL_ACCURACY_REPORT. Jeden mapping-only crash guard
ma osobny zapis SHA i dowód niezmienności predykcji/eksportów holdoutu.

## Zamknięcie implementacji

0.4 zapisany w b9d723a (191 testów), 0.5 w bd2d754 (194 testy). Wydanie 1.0 ma 196 testów, rzeczywisty Docker/offline i materiały jury. Szczegółowe wyniki oraz pozostające częściowe/niezweryfikowane wymagania są w FINAL_COMPETITION_REPORT i COI_REQUIREMENTS_MATRIX. Tag lokalny v1.0.0, bez merge/push.
