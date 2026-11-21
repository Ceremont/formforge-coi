import asyncio
import json
import os
import shutil
import signal
import sys
import tempfile
from typing import Literal
from contextlib import asynccontextmanager
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .coi_mapper import export_bundle
from .config import get_settings
from .errors import DocumentError
from .file_validator import MIMES, FileValidator
from .form_validator import FormValidator
from .models import PreviewRequest, ValidateRequest


ROOT = Path(__file__).resolve().parent
settings = get_settings()
templates = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app):
    app.state.workers = asyncio.Semaphore(settings.max_workers)
    yield


app = FastAPI(
    title="FormForge COI",
    version="1.0.0",
    description="Lokalne przetwarzanie formularzy i eksport COI FormDefinition. Walidacja schematu, reguł technicznych i jawne uwagi do potwierdzenia.",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class RequestLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        limit = settings.max_upload_mb * 1024 * 1024 + 64 * 1024
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > limit:
                return await JSONResponse({"error": {"code": "request_too_large", "message": "Przekroczono limit rozmiaru żądania."}}, status_code=413)(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


app.add_middleware(RequestLimitMiddleware)


@app.middleware("http")
async def headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; frame-src 'self' blob:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'",
    )
    return response


async def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not settings.auth_enabled:
        return
    if credentials is None:
        raise HTTPException(401, "Wymagany token JWT.", headers={"WWW-Authenticate": "Bearer"})
    try:
        jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, "Nieprawidłowy lub wygasły token JWT.", headers={"WWW-Authenticate": "Bearer"}) from exc


@app.exception_handler(DocumentError)
async def document_error(request, error):
    return JSONResponse({"error": {"code": error.code, "message": error.message}}, status_code=error.status)


@app.exception_handler(RequestValidationError)
async def request_error(request, error):
    # Never echo document contents or JWT input in validation errors.
    return JSONResponse(
        {
            "error": {
                "code": "invalid_request",
                "message": "Nieprawidłowy model formularza lub parametry żądania.",
                "details": [{"location": list(e["loc"]), "message": e["msg"]} for e in error.errors()],
            }
        },
        status_code=422,
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    return templates.get_template("index.html").render(max_upload_mb=settings.max_upload_mb, auth_enabled=settings.auth_enabled)


@app.get("/docs", include_in_schema=False)
async def docs():
    response = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="FormForge · Swagger",
        swagger_js_url="/swagger-static/swagger-ui-bundle.js",
        swagger_css_url="/swagger-static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.svg",
        swagger_ui_parameters={"validatorUrl": None},
    )
    # Swagger's bootstrap is inline. All assets are served locally.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"
    )
    return response


app.mount("/swagger-static", StaticFiles(directory=ROOT / "static" / "vendor" / "swagger-ui"), name="swagger-static")

if (ROOT.parent / "demo_samples").is_dir():
    app.mount("/demo_samples", StaticFiles(directory=ROOT.parent / "demo_samples"), name="demo_samples")


@app.get("/api/health")
async def health():
    languages = []
    if shutil.which("tesseract"):
        import pytesseract

        try:
            languages = pytesseract.get_languages(config="")
        except Exception:
            pass
    return {
        "status": "ok",
        "version": "1.0.0",
        "python": sys.version.split()[0],
        "offline": True,
        "ocr": {"available": bool(languages), "languages": languages},
        "auth_enabled": settings.auth_enabled,
        "coi_compatibility": "official_schema_and_business_rules_available",
        "target_import_verified": False,
        "max_upload_mb": settings.max_upload_mb,
        "processing_timeout": settings.processing_timeout,
    }


@app.get("/api/v1/formats")
async def formats():
    return {
        "supported": [{"extension": ext, "mime": mime, "requires_ocr": ext in ("jpg", "jpeg", "jpe", "png")} for ext, mime in MIMES.items()],
        "limitations": [{"extension": "doc", "reason": "Tekst Word 97–2003 bez renderowania. Odrzucane: szyfrowanie, makra, osadzone obiekty i starsze wersje."}],
        "unsupported": [],
    }


async def run_worker(path: Path, filename: str, extension: str, analysis_mode=None, export_format=None) -> dict:
    env = os.environ.copy()
    # pytesseract creates its own scratch files. Keep them in the request scope
    # so even SIGKILL during OCR cannot leave sources in the global temp folder.
    for key in ("TMPDIR", "TMP", "TEMP"):
        env[key] = str(path.parent)
    for key, value in settings.model_dump().items():
        if key.startswith("jwt_"):
            env.pop("FORMFORGE_" + key.upper(), None)
        else:
            env["FORMFORGE_" + key.upper()] = str(value)
    env["FORMFORGE_AUTH_ENABLED"] = "false"
    if export_format:
        env["FORMFORGE_EXPORT_FORMAT"] = export_format
    if analysis_mode:
        env["FORMFORGE_ANALYSIS_MODE"] = analysis_mode
        if analysis_mode == "local-ai-assisted" and not settings.local_model_path:
            env["FORMFORGE_LOCAL_MODEL_PATH"] = str(ROOT / "data/block_roles.json")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "formforge.worker",
        str(path),
        filename,
        extension,
        cwd=ROOT.parent,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=settings.processing_timeout)
        except TimeoutError as exc:
            raise DocumentError("Przekroczono czas przetwarzania dokumentu.", 408, "processing_timeout") from exc
        if process.returncode != 0 or not output:
            raise DocumentError("Proces analizy przekroczył zasoby lub zakończył się błędem.", 422, "worker_failed")
        payload = json.loads(output)
        if not payload["ok"]:
            raise DocumentError(payload["message"], payload["status"], payload["code"])
        return payload["result"]
    finally:
        # Also kill OCR descendants on cancellation, timeout, and normal completion.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


@app.post("/api/v1/forms/convert", dependencies=[Depends(authenticate)])
async def convert_form(
    request: Request,
    file: UploadFile = File(...),
    analysis_mode: Literal["deterministic", "local-ai-assisted"] | None = None,
    export_format: Literal["official", "preview"] | None = None,
):
    try:
        from starlette.datastructures import UploadFile as StarletteUploadFile

        multipart = await request.form()
        uploads = [value for _, value in multipart.multi_items() if isinstance(value, StarletteUploadFile)]
        if len(uploads) != 1:
            raise DocumentError("Prześlij dokładnie jeden plik formularza.", 400, "single_file_required")
        data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        filename = file.filename or ""
        extension = FileValidator(settings).validate(filename, file.content_type or "", data)
        try:
            await asyncio.wait_for(app.state.workers.acquire(), timeout=1)
        except TimeoutError as exc:
            raise DocumentError("Wszystkie procesy są zajęte. Spróbuj ponownie za chwilę.", 429, "busy") from exc
        try:
            with tempfile.TemporaryDirectory(prefix="formforge-") as directory:
                path = Path(directory) / f"input.{extension}"
                path.write_bytes(data)
                del data
                if export_format:
                    result = await run_worker(path, filename, extension, analysis_mode, export_format)
                else:
                    result = await run_worker(path, filename, extension, analysis_mode) if analysis_mode else await run_worker(path, filename, extension)
            result["stages"].insert(0, {"stage": "file_validation", "status": "completed", "duration_ms": None})
            return result
        finally:
            app.state.workers.release()
    finally:
        await file.close()


@app.post("/api/v1/forms/validate", dependencies=[Depends(authenticate)])
async def validate_form(request: ValidateRequest):
    validator = FormValidator()
    issues = validator.inspect(request.form)
    value_issues = validator.values(request.form, request.values) if request.values is not None else []
    export, coi_report = export_bundle(request.form, request.export_format)
    from .quality_review import review

    return {
        "valid": not any(i.severity == "error" for i in issues + value_issues) and (request.export_format == "preview" or coi_report["valid"]),
        "form": request.form.model_dump(mode="json"),
        "issues": [i.model_dump() for i in issues],
        "value_issues": [i.model_dump() for i in value_issues],
        "export": export,
        "coi_validation": coi_report,
        "quality_review": review(request.form, issues, coi_report),
    }


@app.post("/api/v1/forms/source-page", dependencies=[Depends(authenticate)])
async def source_page(request: Request, file: UploadFile = File(...), page: int = Query(1, ge=1, le=100)):
    """Request-scoped, isolated PDF raster for source-coordinate review."""
    acquired = False
    process = None
    try:
        uploads = await request.form()
        if sum(hasattr(value, "filename") for _, value in uploads.multi_items()) != 1:
            raise DocumentError("Prześlij dokładnie jeden plik.", 400, "single_file_required")
        data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        extension = FileValidator(settings).validate(file.filename or "", file.content_type or "", data)
        if extension != "pdf":
            raise DocumentError("Podgląd stron obsługuje PDF. Dla innych formatów użyj widoku tekstu lub obrazu.", 415, "source_format")
        try:
            await asyncio.wait_for(app.state.workers.acquire(), timeout=1)
            acquired = True
        except TimeoutError as exc:
            raise DocumentError("Procesy są zajęte. Ponów podgląd za chwilę.", 429, "busy") from exc
        with tempfile.TemporaryDirectory(prefix="formforge-source-") as directory:
            source, target = Path(directory) / "source.pdf", Path(directory) / "page.png"
            source.write_bytes(data)
            del data
            env = {k: v for k, v in os.environ.items() if not k.startswith("FORMFORGE_JWT_")}
            env.update(TMPDIR=directory, TMP=directory, TEMP=directory)
            process = await asyncio.create_subprocess_exec(sys.executable, str(ROOT.parent / "deploy/render_source.py"), str(source), str(target), str(page), str(settings.max_pages), str(settings.worker_memory_mb), env=env, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
            try:
                await asyncio.wait_for(process.wait(), timeout=12)
            except TimeoutError as exc:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()
                raise DocumentError("Podgląd przekroczył limit czasu. Możesz otworzyć lokalny oryginał PDF.", 408, "source_timeout") from exc
            if process.returncode or not target.exists():
                raise DocumentError("Nie można wyrenderować tej strony PDF. Sprawdź numer strony lub otwórz oryginał.", 422, "source_render_failed")
            image_data = target.read_bytes()
        return Response(image_data, media_type="image/png")
    finally:
        if process is not None and process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()
        if acquired:
            app.state.workers.release()
        await file.close()


@app.post("/api/v1/forms/preview", dependencies=[Depends(authenticate)])
async def preview_form(request: PreviewRequest):
    html = templates.get_template("eform.html").render(form=request.form.model_dump(mode="json"))
    export, coi_report = export_bundle(request.form, request.export_format)
    return {"html": html, "export": export, "coi_validation": coi_report}


@app.get("/api/v1/coi/schema")
async def coi_schema():
    from .coi_validation import schema

    return schema()


@app.get("/api/v1/dictionaries")
async def dictionaries(q: str = ""):
    from .dictionaries import search_catalog

    return {"items": search_catalog(q[:200]), "values_available": False, "source": "supplied COI catalog descriptions; target platform resolves values"}


@app.post("/api/v1/forms/coi-validate", dependencies=[Depends(authenticate)])
async def validate_official_json(payload: dict):
    from .coi_validation import validate_coi

    return validate_coi(payload)
