"""Frozen one-to-one evaluation of the real isolated engine, not demo lookup."""

import argparse
import asyncio
import hashlib
import json
import math
import re
import resource
import statistics
import sys
import tempfile
import time
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower().replace("ł", "l"))
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in text if not unicodedata.combining(c))))


def section_name(text):
    return re.sub(r"^(?:[a-z]|[ivx]+|[0-9]+)\s+", "", normalize(text))


def match_fields(expected, predicted, threshold):
    edges = []
    for i, target in enumerate(expected):
        for j, actual in enumerate(predicted):
            if target["page"] != actual["page"]:
                continue
            score = SequenceMatcher(None, normalize(target["label"]), normalize(actual["label"])).ratio()
            if score >= threshold:
                edges.append((score, i, j))
    used_expected = set()
    used_actual = set()
    matches = []
    for score, i, j in sorted(edges, reverse=True):
        if i not in used_expected and j not in used_actual:
            matches.append((i, j, score))
            used_expected.add(i)
            used_actual.add(j)
    return matches


def main():
    from formforge.config import Settings
    from formforge.file_validator import FileValidator, MIMES
    from formforge.main import run_worker
    from formforge.models import Form

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation/holdout-v1")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/accuracy-results.json")
    args = parser.parse_args()
    manifest = json.loads((args.dataset / "manifest.json").read_text())
    for name, expected_hash in manifest["engine_sha256"].items():
        actual = hashlib.sha256((ROOT / "formforge" / name).read_bytes()).hexdigest()
        if actual != expected_hash:
            raise SystemExit(f"Frozen engine changed: {name}. Do not tune on this holdout; create a new external evaluation instead.")
    records = []
    tp = fp = fn = correct_type = correct_section = 0
    ocr_hit = ocr_total = 0
    valid_json = 0
    for case in manifest["cases"]:
        source = args.dataset / case["file"]
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != case["sha256"]:
            raise SystemExit("Dataset file changed: " + case["file"])
        extension = source.suffix[1:]
        FileValidator(Settings()).validate(source.name, MIMES[extension], data)
        start = time.perf_counter()
        error = None
        result = None
        try:
            with tempfile.TemporaryDirectory(prefix="formforge-evaluate-") as directory:
                path = Path(directory) / ("input." + extension)
                path.write_bytes(data)
                result = asyncio.run(run_worker(path, source.name, extension))
            assert not Path(directory).exists()
            Form.model_validate(result["export"]["form"])
            valid_json += 1
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        duration = time.perf_counter() - start
        predicted = result["form"]["fields"] if result else []
        pairs = match_fields(case["fields"], predicted, manifest["matching_policy"]["label_similarity_threshold"])
        matched_e = {i for i, _, _ in pairs}
        matched_p = {j for _, j, _ in pairs}
        local_type = sum(case["fields"][i]["field_type"] == predicted[j]["field_type"] for i, j, _ in pairs)
        section_titles = {s["id"]: s["title"] for s in result["form"]["sections"]} if result else {}
        local_section = sum(section_name(case["fields"][i]["section"]) == section_name(section_titles[predicted[j]["section"]]) for i, j, _ in pairs)
        tp += len(pairs)
        fp += len(predicted) - len(pairs)
        fn += len(case["fields"]) - len(pairs)
        correct_type += local_type
        correct_section += local_section
        coverage = None
        if case["ocr"]:
            reference = Counter(normalize(" ".join(f["label"] + " " + f["section"] for f in case["fields"])).split())
            # Section text appears once per physical section, not once per field.
            reference = Counter(normalize(" ".join(f["label"] for f in case["fields"]) + " " + " ".join({f["section"] for f in case["fields"]})).split())
            recognized = Counter(normalize(" ".join(b["text"] for b in result["document"]["blocks"] if b["kind"] != "blank")).split()) if result else Counter()
            hits = sum((reference & recognized).values())
            total = sum(reference.values())
            ocr_hit += hits
            ocr_total += total
            coverage = hits / max(1, total)
        record = {
            "file": case["file"],
            "expected": len(case["fields"]),
            "predicted": len(predicted),
            "true_positive": len(pairs),
            "false_positive": len(predicted) - len(pairs),
            "false_negative": len(case["fields"]) - len(pairs),
            "type_correct": local_type,
            "section_correct": local_section,
            "ocr_coverage": coverage,
            "json_valid": error is None,
            "seconds": round(duration, 4),
            "error": error,
            "missed": [f["label"] for i, f in enumerate(case["fields"]) if i not in matched_e],
            "extra": [f["label"] for j, f in enumerate(predicted) if j not in matched_p],
            "type_errors": [
                {"label": case["fields"][i]["label"], "expected": case["fields"][i]["field_type"], "actual": predicted[j]["field_type"]}
                for i, j, _ in pairs
                if case["fields"][i]["field_type"] != predicted[j]["field_type"]
            ],
        }
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    times = sorted(r["seconds"] for r in records)
    report = {
        "dataset": manifest["dataset"],
        "policy": manifest["policy"],
        "matching_policy": manifest["matching_policy"],
        "engine_sha256": manifest["engine_sha256"],
        "counts": {"documents": len(records), "true_positive": tp, "false_positive": fp, "false_negative": fn},
        "metrics": {
            "field_precision": precision,
            "field_recall": recall,
            "field_f1": 2 * precision * recall / max(1e-12, precision + recall),
            "field_type_accuracy_on_matches": correct_type / max(1, tp),
            "section_grouping_accuracy_on_matches": correct_section / max(1, tp),
            "ocr_token_coverage": ocr_hit / max(1, ocr_total),
            "internal_json_validity": valid_json / max(1, len(records)),
            "median_seconds": statistics.median(times),
            "p95_seconds": times[min(len(times) - 1, math.ceil(0.95 * len(times)) - 1)],
            "max_child_rss_mb_observed": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024),
        },
        "limitations": [
            "Self-authored synthetic dataset independent of demo templates; not externally blinded or official COI.",
            "One-to-one greedy label similarity with fixed threshold; localization/required/options accuracy not claimed.",
            "Type and section accuracy are conditional on matched fields; misses counted separately.",
            "OCR coverage is partial annotated source-token recall, not complete page transcription or character error rate.",
            "RSS is maximum child high-water mark observed, not peak aggregate server memory.",
            "No tuning of engine after the first final holdout result.",
        ],
        "cases": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report["metrics"], indent=2))


if __name__ == "__main__":
    main()
