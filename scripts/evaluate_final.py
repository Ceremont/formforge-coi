"""Separate final benchmark; historical experiments are read-only inputs."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import evaluate_v03 as runner

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "evaluation/coi-final"
runner.DEST = DEST


def recognition_hashes():
    # API health/version and UI integration may change in 0.5/1.0. Extraction,
    # model, mapping, validation, settings and data must remain unchanged.
    return {name: sha for name, sha in runner.hashes().items() if name != "formforge/main.py"}


def expected_hashes(freeze):
    expected = dict(json.loads(freeze.read_text())["files"])
    patch = DEST / "mapping-hotfix.json"
    if patch.exists():
        data = json.loads(patch.read_text())
        assert data["file"] == "formforge/coi_official.py" and expected[data["file"]] == data["before"]
        expected[data["file"]] = data["after"]
    return expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["freeze", "known", "development", "promoted", "secondary", "unknown"])
    args = parser.parse_args()
    for name in ["results", "exports", "comparisons"]:
        (DEST / name).mkdir(exist_ok=True, parents=True)
    freeze = DEST / "engine-freeze.json"
    if args.phase == "freeze":
        if freeze.exists():
            raise SystemExit("Preserve the final freeze. Use a new experiment for recognition changes.")
        freeze.write_text(
            json.dumps(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "files": recognition_hashes(),
                    "scope": "Python recognition/model/mapping/validation/settings/data; API main.py and later UI/version/deployment changes tracked separately",
                },
                indent=2,
            )
            + "\n"
        )
        return
    if not freeze.exists() or expected_hashes(freeze) != recognition_hashes():
        raise SystemExit("Recognition engine changed since freeze")
    records = []
    if args.phase == "known":
        for i in range(1, 10):
            group = f"{i:02}"
            directory = ROOT / "reference/coi-official/forms" / group
            reference = next(directory.glob("*.json"), None)
            for source in sorted(directory.iterdir()):
                if source.suffix.lower() == ".json" or "wizualizac" in source.name.lower():
                    continue
                records.append(runner.evaluate(source, group + "-" + source.suffix.lower()[1:], "reference" if reference else "previously_evaluated", reference=reference))
                (DEST / "known-results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    else:
        directory = (
            ROOT / "evaluation/engine-v03/new-documents"
            if args.phase == "development"
            else DEST / ({"promoted": "promoted-development-documents", "secondary": "secondary-audit-documents"}.get(args.phase, "unknown-documents"))
        )
        manifest = json.loads((directory / "manifest.json").read_text())
        if args.phase == "unknown":
            lock = json.loads((directory / "annotation-lock.json").read_text())
            assert hashlib.sha256(freeze.read_bytes()).hexdigest() == lock["freeze_sha256"]
            assert hashlib.sha256((directory / "annotations.json").read_bytes()).hexdigest() == lock["annotation_sha256"]
        for case in manifest["cases"]:
            source = directory / case["file"]
            assert hashlib.sha256(source.read_bytes()).hexdigest() == case["sha256"], case["id"]
            identifier = case["id"] if args.phase == "development" else "final-" + case["id"]
            records.append(runner.evaluate(source, identifier, "new_external" if args.phase == "unknown" else "development_after_v03"))
            (DEST / (args.phase + "-results.json")).write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
