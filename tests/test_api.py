import asyncio
import os
import sys
import time

import jwt
import pytest

from conftest import SAMPLES
from formforge.errors import DocumentError
from formforge.file_validator import MIMES
from formforge import main


def test_health_ui_swagger(client):
    health = client.get("/api/health")
    assert health.status_code == 200 and health.json()["offline"] is True
    assert "3.14" in health.json()["python"]
    html = client.get("/")
    assert html.status_code == 200 and "Podgląd eForm" in html.text
    docs = client.get("/docs")
    assert docs.status_code == 200 and "https://cdn" not in docs.text
    assert "unsafe-inline" in docs.headers["content-security-policy"]
    assert client.get("/swagger-static/swagger-ui-bundle.js").status_code == 200
    assert "/api/v1/forms/convert" in client.get("/openapi.json").json()["paths"]
    assert any(f["extension"] == "ods" for f in client.get("/api/v1/formats").json()["supported"])


@pytest.mark.parametrize("extension", ["pdf", "docx", "xlsx", "ods", "png"])
def test_api_complete_round_trip(client, extension):
    response = client.post("/api/v1/forms/convert", files={"file": ("zaswiadczenie." + extension, (SAMPLES / f"zaswiadczenie.{extension}").read_bytes(), MIMES[extension])})
    assert response.status_code == 200, response.text
    data = response.json()
    assert any(f["field_type"] == "pesel" for f in data["form"]["fields"])
    assert set(data["export"]) == {"title", "tabs", "flow"}
    assert data["coi_validation"]["valid"] is True
    assert len(data["stages"]) == 7
    preview = client.post("/api/v1/forms/preview", json={"form": data["form"]})
    assert preview.status_code == 200 and "form-model" in preview.json()["html"]
    validation = client.post("/api/v1/forms/validate", json={"form": data["form"], "values": {}})
    assert validation.status_code == 200 and not validation.json()["valid"]
    assert any(i["code"] == "required" for i in validation.json()["value_issues"])
    data["form"]["fields"][0]["label"] = "Etykieta poprawiona"
    regenerated = client.post("/api/v1/forms/validate", json={"form": data["form"]})
    assert any(f["title"] == "Etykieta poprawiona" for _, _, f, _ in __import__("formforge.coi_validation", fromlist=["fields_with_context"]).fields_with_context(regenerated.json()["export"]))


def test_api_errors(client):
    assert client.post("/api/v1/forms/convert").status_code == 422
    assert client.post("/api/v1/forms/convert", files={"file": ("../x.pdf", b"%PDF-1.4", "application/pdf")}).status_code == 400
    assert client.post("/api/v1/forms/convert", files={"file": ("x.doc", b"old doc", "application/msword")}).status_code == 415
    damaged = client.post("/api/v1/forms/convert", files={"file": ("x.pdf", b"%PDF-1.4\nbad", "application/pdf")})
    assert damaged.status_code == 422 and damaged.json()["error"]["message"]
    assert client.post("/api/v1/forms/preview", json={"form": {}}).status_code == 422


def test_exactly_one_file(client):
    data = (SAMPLES / "zaswiadczenie.pdf").read_bytes()
    response = client.post("/api/v1/forms/convert", files=[("file", ("a.pdf", data, "application/pdf")), ("file", ("b.pdf", data, "application/pdf"))])
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "single_file_required"


def test_invalid_rule_is_422(client, sample_form):
    payload = sample_form.model_dump(mode="json")
    payload["fields"][0]["validation"] = [{"kind": "max_length", "value": "arbitrary text"}]
    assert client.post("/api/v1/forms/validate", json={"form": payload}).status_code == 422


@pytest.mark.parametrize("fail", [True, False])
def test_temporary_source_cleanup(client, monkeypatch, fail):
    captured = []

    async def worker(path, filename, extension):
        captured.append(path)
        assert path.exists()
        if fail:
            raise DocumentError("Test kontrolowanej awarii")
        return {"stages": []}

    monkeypatch.setattr(main, "run_worker", worker)
    response = client.post("/api/v1/forms/convert", files={"file": ("test.pdf", (SAMPLES / "zaswiadczenie.pdf").read_bytes(), "application/pdf")})
    assert response.status_code == (422 if fail else 200)
    assert captured and not captured[0].exists() and not captured[0].parent.exists()


def test_hard_processing_timeout_kills_worker(monkeypatch, tmp_path):
    original = asyncio.create_subprocess_exec
    captured = []

    async def spawn(*args, **kwargs):
        process = await original(sys.executable, "-c", "import time; time.sleep(30)", **kwargs)
        captured.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(main.settings, "processing_timeout", 1)
    with pytest.raises(DocumentError) as exc:
        asyncio.run(main.run_worker(tmp_path / "x.pdf", "x.pdf", "pdf"))
    assert exc.value.code == "processing_timeout"
    assert captured[0].returncode is not None
    with pytest.raises(ProcessLookupError):
        os.kill(captured[0].pid, 0)


def test_oversized_request_before_multipart(client, monkeypatch):
    monkeypatch.setattr(main.settings, "max_upload_mb", 1)
    response = client.post("/api/v1/forms/convert", content=b"x" * (1024 * 1024 + 65537))
    assert response.status_code == 413


@pytest.mark.parametrize("kind", ["missing", "expired", "wrong_aud", "none", "valid"])
def test_jwt_verification(client, monkeypatch, sample_form, kind):
    monkeypatch.setattr(main.settings, "auth_enabled", True)
    monkeypatch.setattr(main.settings, "jwt_secret", "a-real-test-secret-with-at-least-32-characters")
    claims = {"sub": "reviewer", "iat": int(time.time()) - 10, "exp": int(time.time()) + 60, "iss": main.settings.jwt_issuer, "aud": main.settings.jwt_audience}
    if kind == "expired":
        claims["exp"] = int(time.time()) - 1
    if kind == "wrong_aud":
        claims["aud"] = "wrong"
    token = jwt.encode(claims, "" if kind == "none" else main.settings.jwt_secret, algorithm="none" if kind == "none" else "HS256")
    response = client.post("/api/v1/forms/validate", json={"form": sample_form.model_dump(mode="json")}, headers={} if kind == "missing" else {"Authorization": "Bearer " + token})
    assert response.status_code == (200 if kind == "valid" else 401)


def test_preview_escapes_user_html(client, sample_form):
    sample_form.title = "<script>alert(1)</script>"
    response = client.post("/api/v1/forms/preview", json={"form": sample_form.model_dump(mode="json")})
    assert response.status_code == 200
    html = response.json()["html"]
    assert "<script>alert(1)</script>" not in html
    assert "\\u003cscript\\u003e" in html
