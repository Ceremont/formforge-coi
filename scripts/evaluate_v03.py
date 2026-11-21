"""Versioned V03 evaluation; never mutates the frozen coi-v1 benchmark."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEST = ROOT / "evaluation/engine-v03"


def hashes():
    files = sorted((ROOT / "formforge").glob("*.py")) + sorted((ROOT / "formforge/data").glob("*.json"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def evaluate(path, case, category, extension=None, reference=None):
    from formforge.config import Settings
    from formforge.file_validator import FileValidator, MIMES
    from formforge.errors import DocumentError
    from formforge.coi_compare import compare

    settings = Settings(_env_file=None)
    extension = extension or path.suffix.lower().lstrip(".")
    record = {"id": case, "category": category, "source": str(path.relative_to(ROOT)), "extension": extension, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    start = perf_counter()
    try:
        canonical = FileValidator(settings).validate(path.name, "application/msword" if extension == "doc" else MIMES.get(extension, "application/octet-stream"), path.read_bytes())
        env = {k: v for k, v in os.environ.items() if not k.startswith("FORMFORGE_")}
        env.update(FORMFORGE_EXPORT_FORMAT="official", FORMFORGE_ANALYSIS_MODE="deterministic", OMP_THREAD_LIMIT="1")
        with tempfile.TemporaryDirectory(prefix="formforge-eval-") as temporary:
            source = Path(temporary) / ("unknown." + canonical)
            source.write_bytes(path.read_bytes())
            env.update(TMPDIR=temporary, TMP=temporary, TEMP=temporary)
            process = subprocess.Popen(
                [sys.executable, "-m", "formforge.worker", str(source), source.name, canonical],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                start_new_session=True,
            )
            try:
                stdout, _ = process.communicate(timeout=settings.processing_timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise
        response = json.loads(stdout)
        if not response["ok"]:
            record.update(status="rejected", error=response)
        else:
            data = response["result"]
            validation = data["coi_validation"]
            (DEST / "results" / f"{case}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
            (DEST / "exports" / f"{case}.json").write_text(json.dumps(data["export"], ensure_ascii=False, indent=2))
            record.update(
                status="converted",
                canonical_format=canonical,
                fields=len(data["form"]["fields"]),
                raw_fields=len(data["detected_form"]["fields"]),
                schema_valid=validation["schema_valid"],
                business_rules_valid=validation["business_rules_valid"],
                valid=validation["valid"],
                quality=data["quality"],
                ocr=bool(data["document"]["analysis"].get("ocr")),
                pages=len(data["document"]["pages"]),
            )
            if reference:
                comparison = compare(json.loads(reference.read_text()), data["export"])
                (DEST / "comparisons" / f"{case}.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2))
                record["metrics"] = {k: v for k, v in comparison.items() if k not in ("matches", "conditions", "missing", "extra")}
    except DocumentError as exc:
        record.update(status="rejected", error={"status": exc.status, "code": exc.code, "message": exc.message})
    except subprocess.TimeoutExpired:
        record.update(status="timeout", error={"status": 408, "code": "processing_timeout"})
    except Exception as exc:
        record.update(status="evaluation_failed", error=type(exc).__name__ + ": " + str(exc)[:200])
    record["processing_seconds"] = round(perf_counter() - start, 3)
    print(json.dumps({k: record.get(k) for k in ["id", "status", "valid", "fields", "processing_seconds"]}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["known", "freeze", "new"])
    parser.add_argument("--groups", nargs="*")
    args = parser.parse_args()
    for folder in ["results", "exports", "comparisons"]:
        (DEST / folder).mkdir(parents=True, exist_ok=True)
    freeze = DEST / "engine-freeze.json"
    if args.phase == "freeze":
        if freeze.exists():
            raise SystemExit("Do not overwrite a frozen version")
        freeze.write_text(json.dumps({"timestamp_utc": datetime.now(timezone.utc).isoformat(), "files": hashes(), "previous_forms_are_development_data": True}, indent=2))
        print("V03 engine frozen before new external documents")
        return
    records = []
    if not freeze.exists() or json.loads(freeze.read_text())["files"] != hashes():
        raise SystemExit("Evaluation requires the unchanged frozen V03 engine; use a new version for engine changes")
    if args.phase == "known":
        for group in args.groups or [f"{i:02}" for i in range(1, 10)]:
            directory = ROOT / "reference/coi-official/forms" / group
            ref = next(directory.glob("*.json"), None)
            for source in sorted(directory.iterdir()):
                if source.suffix.lower() == ".json" or "wizualizac" in source.name.lower():
                    continue
                records.append(evaluate(source, group + "-" + source.suffix.lower()[1:], "reference" if ref else "previously_evaluated", reference=ref))
                (DEST / (args.phase + "-results.json")).write_text(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        lock = json.loads((DEST / "new-documents/annotation-lock.json").read_text())
        if hashlib.sha256(freeze.read_bytes()).hexdigest() != lock["engine_freeze_sha256"]:
            raise SystemExit("Engine freeze no longer matches the pre-prediction annotation lock")
        if hashlib.sha256((DEST / "new-documents/annotations.json").read_bytes()).hexdigest() != lock["annotation_sha256"]:
            raise SystemExit("New source annotations no longer match their pre-prediction lock")
        manifest = json.loads((DEST / "new-documents/manifest.json").read_text())
        for case in manifest["cases"]:
            source = DEST / "new-documents" / case["file"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != case["sha256"]:
                raise SystemExit(f"New source changed: {case['id']}")
            records.append(evaluate(source, case["id"], "new_external"))
            (DEST / "new-results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
