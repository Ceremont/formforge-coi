"""Bounded read-only Word 97–2003 text subset, based on Microsoft MS-DOC.

OLE parsing is delegated to BSD olefile. No Office process, executable, embedded
object, field code or macro is run. This is not a Word pagination/render engine.
"""

import io
import re
import struct

import olefile

from .errors import DocumentError

MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def malformed():
    return DocumentError("Nieprawidłowa struktura binarnego dokumentu Word.", 422, "invalid_doc")


def number(data, offset, fmt="I"):
    size = struct.calcsize("<" + fmt)
    if offset < 0 or offset + size > len(data):
        raise malformed()
    return struct.unpack_from("<" + fmt, data, offset)[0]


def parse_piece_table(word, table, max_chars=2_000_000):
    if number(word, 0, "H") != 0xA5EC or number(word, 2, "H") < 0xC1:
        raise DocumentError("Obsługiwany jest tekst DOC Word 97–2003; starszą wersję zapisz jako DOCX/PDF.", 415, "doc_version")
    flags = number(word, 10, "H")
    if flags & 0x100:
        raise DocumentError("Zaszyfrowany DOC nie jest obsługiwany.", 415, "encrypted_doc")
    csw = number(word, 32, "H")
    if not 14 <= csw <= 64:
        raise malformed()
    long_start = 34 + csw * 2
    cslw = number(word, long_start, "H")
    if not 22 <= cslw <= 64:
        raise malformed()
    long_start += 2
    counts = [number(word, long_start + i * 4, "i") for i in range(3, 11)]
    if any(n < 0 for n in counts) or sum(counts) > max_chars:
        raise DocumentError("DOC przekracza limit znaków.", 413, "doc_text_limit")
    pairs = long_start + cslw * 4
    if not 34 <= number(word, pairs, "H") <= 256:
        raise malformed()
    start = number(word, pairs + 2 + 33 * 8)
    length = number(word, pairs + 2 + 33 * 8 + 4)
    if length < 5 or start + length > len(table):
        raise malformed()
    clx = table[start : start + length]
    pos = 0
    while pos < len(clx) and clx[pos] == 1:
        pos += 3 + number(clx, pos + 1, "H")
    if pos >= len(clx) or clx[pos] != 2:
        raise malformed()
    size = number(clx, pos + 1)
    if size < 4 or (size - 4) % 12 or pos + 5 + size > len(clx):
        raise malformed()
    plc = clx[pos + 5 : pos + 5 + size]
    n = (size - 4) // 12
    if not 1 <= n <= 100_000:
        raise malformed()
    cps = [number(plc, i * 4) for i in range(n + 1)]
    if cps[0] != 0 or cps[-1] > max_chars + 1 or any(a >= b for a, b in zip(cps, cps[1:])) or cps[-1] < sum(counts):
        raise malformed()
    parts = []
    for i in range(n):
        fc = number(plc, 4 * (n + 1) + i * 8 + 2)
        compressed = bool(fc & 0x40000000)
        offset = (fc & 0x3FFFFFFF) // (2 if compressed else 1)
        size = (cps[i + 1] - cps[i]) * (1 if compressed else 2)
        if offset < 32 or offset + size > len(word):
            raise malformed()
        raw = word[offset : offset + size]
        # MS-DOC's compressed Unicode mapping is CP1252 except its undefined
        # bytes, which retain their Unicode code points. Do not guess CP1250.
        if compressed:
            text = "".join(bytes([b]).decode("cp1252") if b not in {0x81, 0x8D, 0x8F, 0x90, 0x9D} else chr(b) for b in raw)
        else:
            text = raw.decode("utf-16le", errors="strict")
        parts.append(text)
    text = "".join(parts)
    # CP offsets count UTF-16 units, so slice bytes rather than Python codepoints.
    units = text.encode("utf-16le")
    main = units[: counts[0] * 2].decode("utf-16le", errors="strict")
    box_start = sum(counts[:6])
    boxes = units[box_start * 2 : (box_start + counts[6]) * 2].decode("utf-16le", errors="strict")
    return main, boxes, counts


def inspect_doc(data, max_bytes=80 * 1024 * 1024):
    if not data.startswith(MAGIC):
        raise DocumentError("Zawartość pliku nie jest dokumentem DOC.", 415, "content_mismatch")
    try:
        with olefile.OleFileIO(io.BytesIO(data), raise_defects=olefile.DEFECT_INCORRECT) as ole:
            entries = ole.listdir(streams=True, storages=True)
            if len(entries) > 3000 or sum(ole.get_size(p) for p in ole.listdir()) > max_bytes:
                raise DocumentError("Kontener OLE przekracza limity bezpieczeństwa.", 413, "ole_limit")
            names = {part.casefold() for entry in entries for part in entry}
            if names & {"vba", "macros", "_vba_project", "_vba_project_cur", "objectpool"}:
                raise DocumentError("DOC z makrami lub osadzonymi obiektami nie jest obsługiwany.", 415, "macros_rejected")
            if not ole.exists("WordDocument"):
                raise malformed()
            word = ole.openstream("WordDocument").read()
            table_name = "1Table" if number(word, 10, "H") & 0x200 else "0Table"
            if not ole.exists(table_name):
                raise malformed()
            return parse_piece_table(word, ole.openstream(table_name).read())
    except DocumentError:
        raise
    except Exception as exc:
        raise malformed() from exc


def display_text(text):
    # Keep displayed field results; never execute or expose field instructions.
    stack, output = [], []
    for char in text:
        if char == "\x13":
            stack.append(False)
        elif char == "\x14" and stack:
            stack[-1] = True
        elif char == "\x15" and stack:
            stack.pop()
        elif all(stack):
            output.append(char)
    text = "".join(output).replace("\x07", "\t").replace("\x0b", "\n").replace("\r", "\n")
    return re.sub(r"[\x00-\x06\x08\x0e-\x1f]", "", text)


def read_doc(extractor, path):
    main, boxes, counts = inspect_doc(path.read_bytes(), extractor.settings.max_uncompressed_mb * 1024 * 1024)
    extractor.analysis["legacy_doc"] = {"format": "Word97-2003", "main_characters": counts[0], "textbox_characters": counts[6], "geometry_available": False}
    extractor.warnings.append("Częściowy model DOC: tekst i granice komórek; bez składu Word, geometrii, obrazów i pełnych właściwości tabel. Sprawdź oryginał.")
    for story, text in [("main", main), ("textbox", boxes)]:
        if not text.strip():
            continue
        for page_text in display_text(text).split("\x0c"):
            if not page_text.strip():
                continue
            page = extractor.page(f"Strona {len(extractor.pages) + 1}", source="doc_logical")
            for row, line in enumerate(page_text.splitlines(), 1):
                cells = line.split("\t")
                for column, content in enumerate(cells, 1):
                    from .layout_analyzer import fold

                    bare_label = story == "textbox" and bool(
                        re.fullmatch(
                            r"(?:nazwa\s*/?\s*imie i nazwisko|imie i nazwisko|nip|pesel|regon|miejscowosc|ulica|nr domu|nr lokalu|kod pocztowy|numer telefonu|adres poczty elektronicznej|data uiszczenia oplaty|wysokosc oplaty|nr rachunku|dane wlasciciela)",
                            fold(content.strip()),
                        )
                    )
                    extractor.add(
                        content,
                        page,
                        method="doc_piece_table",
                        kind="cell" if len(cells) > 1 else "text",
                        metadata={
                            "story": story,
                            "table_id": f"doc_{page}",
                            "row": row,
                            "column": column,
                            "paired_blank": bare_label or column < len(cells) and not cells[column].strip(),
                            "requires_review": True,
                            "choice_evidence": "Etykieta pola w poddokumencie textbox DOC; geometria niedostępna, wymagane potwierdzenie"
                            if bare_label
                            else "Tekst źródła DOC; granice komórek bez geometrii",
                        },
                    )
