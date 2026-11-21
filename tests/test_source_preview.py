import io
import tempfile
from pathlib import Path

from PIL import Image

from conftest import SAMPLES
from formforge import main


def test_source_preview_real_raster_and_cleanup(client, monkeypatch):
    original = tempfile.TemporaryDirectory
    paths = []

    def directory(*args, **kwargs):
        result = original(*args, **kwargs)
        paths.append(Path(result.name))
        return result

    monkeypatch.setattr(main.tempfile, 'TemporaryDirectory', directory)
    response = client.post('/api/v1/forms/source-page?page=2', files={'file': ('multi.pdf', (SAMPLES / 'wielostronicowy.pdf').read_bytes(), 'application/pdf')})
    assert response.status_code == 200, response.text if response.status_code != 200 else ''
    assert response.headers['content-type'] == 'image/png'
    with Image.open(io.BytesIO(response.content)) as image:
        assert image.width > 500 and image.height > 500
        assert image.width * image.height <= 4_010_000
    assert paths and all(not path.exists() for path in paths)


def test_source_preview_invalid_source_and_page(client):
    pdf = (SAMPLES / 'zaswiadczenie.pdf').read_bytes()
    upload = {'file': ('source.pdf', pdf, 'application/pdf')}
    assert client.post('/api/v1/forms/source-page?page=100', files=upload).status_code == 422
    assert client.post('/api/v1/forms/source-page?page=0', files=upload).status_code == 422
    assert client.post('/api/v1/forms/source-page', files={'file': ('a.pdf', b'%PDF-1.4\nbad', 'application/pdf')}).status_code == 422
    assert client.post('/api/v1/forms/source-page', files={'file': ('a.docx', (SAMPLES / 'zaswiadczenie.docx').read_bytes(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}).status_code == 415
    assert client.post('/api/v1/forms/source-page', files=[('file', ('a.pdf', pdf, 'application/pdf')), ('file', ('b.pdf', pdf, 'application/pdf'))]).status_code == 400


def test_source_preview_auth(client, monkeypatch):
    monkeypatch.setattr(main.settings, 'auth_enabled', True)
    response = client.post('/api/v1/forms/source-page', files={'file': ('source.pdf', (SAMPLES / 'zaswiadczenie.pdf').read_bytes(), 'application/pdf')})
    assert response.status_code == 401
