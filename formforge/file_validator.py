import io
import re
import zipfile
from pathlib import Path

from defusedxml import ElementTree

from .config import Settings
from .errors import DocumentError


MIMES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}
FORBIDDEN = re.compile(r"[;:></\\|'*%$\x00-\x1f\x7f]")


class FileValidator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def validate(self, filename: str, mime: str, data: bytes) -> str:
        if not filename or len(filename) > 250 or FORBIDDEN.search(filename) or filename.strip() != filename:
            raise DocumentError("Nieprawidłowa nazwa pliku (maks. 250 znaków, bez znaków specjalnych).", 400, "invalid_filename")
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension == "doc":
            raise DocumentError(
                "Format DOC nie jest obsługiwany: brak zweryfikowanego konwertera na licencji permisywnej. Zapisz plik jako DOCX lub PDF.", 415, "doc_not_supported"
            )
        if extension not in MIMES:
            raise DocumentError("Niedozwolony format pliku.", 415, "unsupported_format")
        if not data:
            raise DocumentError("Przesłany plik jest pusty.", 400, "empty_file")
        if len(data) > self.settings.max_upload_mb * 1024 * 1024:
            raise DocumentError("Plik przekracza dopuszczalny rozmiar.", 413, "file_too_large")
        supplied_mime = mime.partition(";")[0].strip().lower()
        if supplied_mime not in (MIMES[extension], "application/octet-stream", ""):
            raise DocumentError("Typ MIME nie odpowiada rozszerzeniu pliku.", 415, "mime_mismatch")
        signatures = {"pdf": b"%PDF-", "png": b"\x89PNG\r\n\x1a\n", "jpg": b"\xff\xd8\xff", "jpeg": b"\xff\xd8\xff"}
        if extension in signatures and not data.startswith(signatures[extension]):
            raise DocumentError("Zawartość pliku nie odpowiada jego rozszerzeniu.", 415, "content_mismatch")
        if extension in ("docx", "xlsx", "ods"):
            self._validate_archive(data, extension)
        return extension

    def _validate_archive(self, data: bytes, extension: str):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                names = set(archive.namelist())
                if len(infos) > 3000 or len(names) != len(infos) or sum(i.file_size for i in infos) > self.settings.max_uncompressed_mb * 1024 * 1024:
                    raise DocumentError("Archiwum dokumentu przekracza limity bezpieczeństwa.", 413, "archive_limit")
                for item in infos:
                    if item.flag_bits & 1 or item.filename.startswith("/") or ".." in Path(item.filename).parts or "\\" in item.filename:
                        raise DocumentError("Niedozwolona struktura archiwum.", 400)
                    if "vbaproject" in item.filename.lower() or "macros/" in item.filename.lower():
                        raise DocumentError("Dokumenty zawierające makra nie są obsługiwane.", 415, "macros_rejected")
                if extension == "ods":
                    if "mimetype" not in names or archive.read("mimetype").decode().strip() != MIMES[extension] or "content.xml" not in names:
                        raise DocumentError("Zawartość nie jest arkuszem ODS.", 415)
                else:
                    expected = "word/document.xml" if extension == "docx" else "xl/workbook.xml"
                    if expected not in names or "[Content_Types].xml" not in names:
                        raise DocumentError("Zawartość archiwum nie odpowiada formatowi dokumentu.", 415, "content_mismatch")
                    types = archive.read("[Content_Types].xml").lower()
                    if b"macroenabled" in types:
                        raise DocumentError("Dokument z makrami jest niedozwolony.", 415, "macros_rejected")
                # Reject DTD/entity expansion before any third-party XML parser sees data.
                for info in infos:
                    if info.filename.endswith((".xml", ".rels")):
                        ElementTree.fromstring(archive.read(info), forbid_dtd=True)
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("Uszkodzone lub niebezpieczne archiwum dokumentu.") from exc
