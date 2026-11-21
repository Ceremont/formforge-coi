"""Run real format readers and export sample results; not imported by the app."""

import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from formforge.config import Settings
    from formforge.pipeline import convert

    samples = ROOT / "demo_samples"
    output = ROOT / "output" / "demo_exports"
    output.mkdir(parents=True, exist_ok=True)
    expected = json.loads((samples / "expected_fields.json").read_text())
    rows = []
    for name, spec in expected.items():
        for extension in ("pdf", "docx", "xlsx", "ods"):
            path = samples / f"{name}.{extension}"
            start = perf_counter()
            result = convert(path, path.name, extension, Settings())
            found = {field["label"] for field in result["form"]["fields"]}
            wanted = set(spec["expected_labels"])
            row = {
                "file": path.name,
                "pages": len(result["form"]["pages"]),
                "fields": len(found),
                "expected_matched": len(wanted & found),
                "expected_total": len(wanted),
                "duration_ms": round((perf_counter() - start) * 1000, 1),
            }
            assert row["expected_matched"] == row["expected_total"], row
            rows.append(row)
            (output / f"{name}.{extension}.json").write_text(json.dumps(result["export"], ensure_ascii=False, indent=2))
    for name in ("zaswiadczenie.png", "zaswiadczenie.jpg", "skan.pdf"):
        path = samples / name
        result = convert(path, path.name, path.suffix[1:], Settings())
        assert any(field["field_type"] == "pesel" for field in result["form"]["fields"]), path.name
        rows.append({"file": name, "pages": len(result["form"]["pages"]), "fields": len(result["form"]["fields"]), "ocr": "executed", "has_pesel": True})
        (output / f"{name}.json").write_text(json.dumps(result["export"], ensure_ascii=False, indent=2))
    (ROOT / "docs" / "sample-verification.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
