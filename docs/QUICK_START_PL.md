# FormForge — start dla jury

Od dokumentu do e-formularza. Wydanie 1.0, przetwarzanie lokalne, jawny przegląd wyniku.

1. Rozpakuj ZIP do katalogu o prostej nazwie, np. `FormForge-COI`.
2. Otwórz terminal w tym katalogu i uruchom Docker Desktop.
3. Wykonaj:

```sh
docker compose build
docker compose up -d --wait
docker compose ps
curl http://127.0.0.1:8000/api/health
```

4. Otwórz http://127.0.0.1:8000. Dokumentacja API: http://127.0.0.1:8000/docs.
5. Kliknij „Wydanie zaświadczenia” albo prześlij nowy pusty dokument.
6. Porównaj źródło z polami. Popraw etykietę/typ/opcje w edytorze, poczekaj na walidację.
7. Otwórz podgląd i zgodność. Pobierz JSON COI. Wartości testowe z podglądu nie są eksportowane.

Zatrzymanie: `docker compose down`. Port zajęty: ustaw
`FORMFORGE_HTTP_PORT=8766 docker compose up -d --wait`, otwórz port 8766.
Błąd Buildx dotyczący Unicode: przenieś rozpakowany projekt do katalogu ASCII.
Alternatywa lokalna Python 3.14 + Tesseract: dokładne komendy w README.
Pierwszy build potrzebuje Internetu; gotowy obraz analizuje bez dostępu zewnętrznego.

Sprawdzone 68/69 źródeł daje lokalnie poprawny JSON. To nie wynik kompletności.
Importer COI: niezweryfikowany. DOC: podzbiór Word97–2003, bez obiektów/makr.
Trzy nowe dokumenty mają F1 surowych pól 58,95%, więc weryfikacja człowieka jest konieczna.
Film <=3 min, dostęp do repo i kwestie prawne wymagają finalizacji przez zespół.
