"""Score explicitly annotated source inventories; no fabricated full COI truth."""

import json
from pathlib import Path
import re
import sys
import hashlib
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def score(case, result):
    from formforge.layout_analyzer import fold

    fields = result["detected_form"]["fields"]
    fields = [f for f in fields if "predicted_filter" not in case or re.search(case["predicted_filter"], fold(f["label"]))]
    expected = case.get("expected", []) + [dict(a, key=f"repeat{i}_{j}") for i, a in enumerate(case.get("repeated_expected", [])) for j in range(a["count"])]
    candidates = []
    for i, e in enumerate(expected):
        for j, f in enumerate(fields):
            if re.search(e["pattern"], fold(f["label"])):
                candidates.append((int(e["type"] == f["field_type"]), i, j))
    used_e = set()
    used_f = set()
    pairs = []
    for correct, i, j in sorted(candidates, reverse=True):
        if i not in used_e and j not in used_f:
            used_e.add(i)
            used_f.add(j)
            pairs.append({"expected": expected[i]["key"], "actual": fields[j]["label"], "type_correct": bool(correct)})
    precision = len(pairs) / max(1, len(fields))
    recall = len(pairs) / max(1, len(expected))
    sections = case.get("expected_sections")
    section_accuracy = section_f1 = None
    if sections:

        def canonical(s):
            return " ".join(re.findall(r"[a-z]+", fold(s)))

        actual = [s["title"] for s in result["form"]["sections"]]
        used = set()
        matched = 0
        for name in sections:
            choices = sorted((SequenceMatcher(None, canonical(name), canonical(s)).ratio(), i) for i, s in enumerate(actual) if i not in used)
            if choices and choices[-1][0] >= 0.85:
                used.add(choices[-1][1])
                matched += 1
        section_accuracy = matched / len(sections)
        section_f1 = 2 * matched / max(1, len(sections) + len(actual))
    return {
        "scope": case.get("scope", "Explicit source controls; see pre-prediction annotation protocol"),
        "expected_fields": len(expected),
        "predicted_fields": len(fields),
        "matched_fields": len(pairs),
        "field_precision": precision,
        "field_recall": recall,
        "field_f1": 2 * precision * recall / max(1e-9, precision + recall),
        "field_type_accuracy": sum(p["type_correct"] for p in pairs) / max(1, len(pairs)),
        "section_accuracy": section_accuracy,
        "section_f1": section_f1,
        "matches": pairs,
        "missing": [e["key"] for i, e in enumerate(expected) if i not in used_e],
        "extra": [f["label"] for j, f in enumerate(fields) if j not in used_f],
    }


def main():
    dest = ROOT / "evaluation/engine-v03"
    lock = json.loads((dest / "new-documents/annotation-lock.json").read_text())
    if hashlib.sha256((dest / "new-documents/annotations.json").read_bytes()).hexdigest() != lock["annotation_sha256"]:
        raise SystemExit("Pre-prediction new-document annotation changed; preserve the original evaluation")
    if hashlib.sha256((dest / "engine-freeze.json").read_bytes()).hexdigest() != lock["engine_freeze_sha256"]:
        raise SystemExit("Pre-prediction engine freeze changed; preserve the original evaluation")
    records = []
    for case in json.loads((dest / "annotations-known.json").read_text())["cases"]:
        for version, path in [("baseline", ROOT / "evaluation/coi-v1/results" / f"{case['id']}.json"), ("v03", dest / "results" / f"{case['id']}.json")]:
            records.append({"id": case["id"], "version": version, **score(case, json.loads(path.read_text()))})
    (dest / "annotated-known-metrics.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
    records = []
    for case in json.loads((dest / "new-documents/annotations.json").read_text())["cases"]:
        for version, path in [("baseline", dest / "baseline-new" / f"{case['id']}.json"), ("v03", dest / "results" / f"{case['id']}.json")]:
            if path.exists():
                records.append({"id": case["id"], "version": version, **score(case, json.loads(path.read_text()))})
    (dest / "new-field-metrics.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print("Wrote annotated metrics with explicit scope and unmatched elements")


if __name__ == "__main__":
    main()
