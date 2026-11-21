import io
import zipfile

import pytest

from formforge.config import Settings
from formforge.errors import DocumentError
from formforge.file_validator import FileValidator, MIMES
from conftest import SAMPLES


@pytest.mark.parametrize(
    "name", ["../x.pdf", "a/b.pdf", "x\\y.pdf", "a;b.pdf", "a:b.pdf", "x%.pdf", "a|b.pdf", "a'b.pdf", "a*.pdf", "a$.pdf", "a>b.pdf", "a<b.pdf", "a" * 251 + ".pdf", "a\x00.pdf"]
)
def test_filename_rejected(name):
    with pytest.raises(DocumentError) as exc:
        FileValidator(Settings()).validate(name, "application/pdf", b"%PDF-1.4")
    assert exc.value.code == "invalid_filename"


@pytest.mark.parametrize("ext", list(MIMES))
def test_real_content_type(ext):
    name = f"zaswiadczenie.{ext if ext != 'jpeg' else 'jpg'}"
    data = (SAMPLES / name).read_bytes()
    assert FileValidator(Settings()).validate("dokument." + ext, MIMES[ext], data) == ext


@pytest.mark.parametrize(
    "name,mime,data,status",
    [
        ("x.pdf", "image/png", b"%PDF-1", 415),
        ("x.pdf", "application/pdf", b"not a pdf", 415),
        ("x.doc", "application/msword", b"fake", 415),
        ("x.exe", "application/octet-stream", b"MZ", 415),
        ("x.png", "image/png", b"", 400),
        ("x.docx", MIMES["docx"], b"broken", 422),
    ],
)
def test_invalid_content(name, mime, data, status):
    with pytest.raises(DocumentError) as exc:
        FileValidator(Settings()).validate(name, mime, data)
    assert exc.value.status == status


def test_wrong_zip_format():
    with pytest.raises(DocumentError):
        FileValidator(Settings()).validate("x.docx", MIMES["docx"], (SAMPLES / "zgloszenie.xlsx").read_bytes())


def test_size_limit():
    with pytest.raises(DocumentError) as exc:
        FileValidator(Settings(max_upload_mb=1)).validate("x.pdf", MIMES["pdf"], b"%PDF-" + b" " * 1024 * 1024)
    assert exc.value.status == 413


@pytest.mark.parametrize("entry,body", [("word/vbaProject.bin", b"macro"), ("../escape", b"path"), ("evil.xml", b'<!DOCTYPE a [<!ENTITY x "bad">]><a>&x;</a>')])
def test_macro_traversal_and_entities(entry, body):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", b"<Types/>")
        archive.writestr("word/document.xml", b"<document/>")
        archive.writestr(entry, body)
    with pytest.raises(DocumentError):
        FileValidator(Settings()).validate("x.docx", MIMES["docx"], buffer.getvalue())
