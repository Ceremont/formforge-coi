"""Train an optional tiny MIT-licensed development classifier, entirely offline."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from formforge.local_ai import train

    examples = [
        ("DANE WNIOSKODAWCY", "heading"),
        ("INFORMACJE O SPRAWIE", "heading"),
        ("ZAŁĄCZNIKI I OŚWIADCZENIA", "heading"),
        ("DANE KONTAKTOWE", "heading"),
        ("Prosimy wypełnić czytelnie pola wniosku i podpisać w wyznaczonym miejscu.", "instruction"),
        ("Należy wybrać jeden wariant i wpisać wszystkie wymagane dane.", "instruction"),
        ("Wypełnij dane oraz zaznacz odpowiednie pole zgodnie ze stanem faktycznym.", "instruction"),
        ("Administratorem danych osobowych jest urząd miasta. Dane przetwarzane są na podstawie przepisów prawa.", "legal"),
        ("Zgodnie z ustawą o ochronie danych osobowych dane służą do realizacji postępowania administracyjnego.", "legal"),
        ("Podstawa prawna przetwarzania danych osobowych oraz prawa osoby której dane dotyczą.", "legal"),
        ("Imię i nazwisko", "text"),
        ("PESEL i data urodzenia", "text"),
        ("Telefon kontaktowy oraz adres e-mail", "text"),
        ("Kod pocztowy i miejscowość", "text"),
        ("Informacja o terminie rozpatrzenia sprawy i sposobie odbioru dokumentu.", "information"),
        ("Wniosek można złożyć osobiście w siedzibie urzędu gminy.", "information"),
    ]
    model = train(examples)
    destination = ROOT / "formforge/data/block_roles.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(model.model_dump_json(indent=2))
    print(destination)


if __name__ == "__main__":
    main()
