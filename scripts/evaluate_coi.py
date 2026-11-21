"""Reproducible reference evaluation and frozen independent format matrix.

Run references, freeze, then independent. No reference content is available to
the conversion worker other than the input document itself.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEST = ROOT / "evaluation/coi-v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def engine():
    paths = sorted((ROOT / "formforge").glob("*.py")) + sorted((ROOT / "formforge/data").glob("*.json"))
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in paths if p.name != "coi_compare.py"}


def sources(group):
    return sorted(p for p in (ROOT / "reference/coi-official/forms" / group).iterdir() if p.suffix.lower() != ".json" and "wizualizac" not in p.name.lower())


def evaluate(group):
    from formforge.coi_compare import compare
    from formforge.coi_validation import validate_coi
    from formforge.config import Settings
    from formforge.errors import DocumentError
    from formforge.file_validator import FileValidator, MIMES

    records = []
    refs = list((ROOT / "reference/coi-official/forms" / group).glob("*.json"))
    expected = json.loads(refs[0].read_text()) if refs else None
    if expected:
        (DEST / f"{group}-reference-validation.json").write_text(json.dumps(validate_coi(expected), ensure_ascii=False, indent=2))
    for source in sources(group):
        extension = source.suffix.lower().lstrip(".")
        start = perf_counter()
        record = {"group": group, "source": source.relative_to(ROOT).as_posix(), "extension": extension, "sha256": digest(source)}
        try:
            FileValidator(Settings()).validate(source.name, MIMES.get(extension, "application/octet-stream"), source.read_bytes())
            env = {k: v for k, v in os.environ.items() if not k.startswith("FORMFORGE_")}
            env.update(FORMFORGE_EXPORT_FORMAT="official", FORMFORGE_ANALYSIS_MODE="deterministic", OMP_THREAD_LIMIT="1")
            process = subprocess.run(
                [sys.executable, "-m", "formforge.worker", str(source), "unknown." + extension, extension], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120
            )
            response = json.loads(process.stdout)
            if not response["ok"]:
                record.update(status="rejected", error=response)
            else:
                data = response["result"]
                name = group + "-" + extension
                (DEST / "exports" / (name + ".json")).write_text(json.dumps(data["export"], ensure_ascii=False, indent=2))
                (DEST / "results" / (name + ".json")).write_text(json.dumps(data, ensure_ascii=False, indent=2))
                report = data["coi_validation"]
                record.update(
                    status="converted",
                    fields=len(data["form"]["fields"]),
                    raw_fields=len(data["detected_form"]["fields"]),
                    schema_valid=report["schema_valid"],
                    business_rules_valid=report["business_rules_valid"],
                    valid=report["valid"],
                    errors=report["errors"],
                    warnings=report["warnings"],
                    review_count=sum(p["requires_confirmation"] for p in report["provenance"].values()),
                    ocr=bool(data["document"]["analysis"].get("ocr")),
                    normalization=data["normalization"],
                )
                if expected:
                    comparison = compare(expected, data["export"])
                    (DEST / "comparisons" / (name + ".json")).write_text(json.dumps(comparison, ensure_ascii=False, indent=2))
                    record["metrics"] = {k: v for k, v in comparison.items() if k not in ("matches", "conditions", "extra", "missing")}
                else:
                    record["metrics"] = {
                        k: None for k in ("field_precision", "field_recall", "field_f1", "field_type_accuracy", "structural_similarity", "conditional_rules_coverage")
                    }
                    record["ground_truth"] = "No official FormDefinition supplied; these metrics are not measurable without annotation."
        except DocumentError as exc:
            record.update(status="rejected", error={"status": exc.status, "code": exc.code, "message": exc.message})
        except subprocess.TimeoutExpired:
            record.update(status="timeout")
        except Exception as exc:
            record.update(status="evaluation_failed", error=type(exc).__name__ + ": " + str(exc)[:200])
        record["processing_seconds"] = round(perf_counter() - start, 3)
        print(json.dumps({k: record[k] for k in ("group", "extension", "status", "processing_seconds")}, ensure_ascii=False), flush=True)
        records.append(record)
        (DEST / (group + "-results.json")).write_text(json.dumps(records, ensure_ascii=False, indent=2))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["references", "freeze", "independent"])
    args = parser.parse_args()
    for name in ("exports", "results", "comparisons"):
        (DEST / name).mkdir(parents=True, exist_ok=True)
    freeze = DEST / "engine-freeze.json"
    if args.phase == "references" and freeze.exists() and json.loads(freeze.read_text())["files"] != engine():
        raise SystemExit("coi-v1 is frozen and read-only for this engine. Use scripts/evaluate_v03.py known.")
    if args.phase == "freeze":
        if freeze.exists():
            raise SystemExit("Freeze already exists. Preserve the independent result rather than overwrite it.")
        freeze.write_text(
            json.dumps(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "development_forms": ["01", "05"],
                    "independent_forms": ["02", "03", "04", "06", "07", "08", "09"],
                    "files": engine(),
                },
                indent=2,
            )
        )
        print("Engine frozen before independent predictions")
        return
    if args.phase == "independent":
        if not freeze.exists() or json.loads(freeze.read_text())["files"] != engine():
            raise SystemExit("Independent evaluation requires an unchanged frozen engine")
        groups = ["02", "03", "04", "06", "07", "08", "09"]
    else:
        groups = ["01", "05"]
    all_records = [r for group in groups for r in evaluate(group)]
    (DEST / (args.phase + "-results.json")).write_text(json.dumps(all_records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
