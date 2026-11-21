"""Scoped source-quality scores; annotation locks and historical runs preserved."""

from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEST = ROOT / "evaluation/coi-final"


def score(case, result):
    from formforge.layout_analyzer import fold

    fields = result["detected_form"]["fields"]
    if case.get("predicted_filter"):
        fields = [f for f in fields if re.search(case["predicted_filter"], fold(f["label"]))]
    expected = case.get("expected", []) + [dict(e, key=f"repeat{i}_{j}") for i, e in enumerate(case.get("repeated_expected", [])) for j in range(e["count"])]
    candidates = []
    for i, entry in enumerate(expected):
        for j, field in enumerate(fields):
            if entry.get("page") is not None and entry["page"] != field["source_reference"]["page"]:
                continue
            if re.search(entry["pattern"], fold(field["label"])):
                candidates.append((int(entry["type"] == field["field_type"]), i, j))
    used_e, used_f, matches = set(), set(), []
    for correct, i, j in sorted(candidates, reverse=True):
        if i not in used_e and j not in used_f:
            used_e.add(i)
            used_f.add(j)
            matches.append({"expected": expected[i]["key"], "actual": fields[j]["label"], "type_correct": bool(correct)})
    section_recall = section_f1 = None
    if case.get("expected_sections"):

        def canonical(s):
            return " ".join(re.findall(r"[a-z]+", fold(s)))

        actual = [s["title"] for s in result["form"]["sections"]]
        used, count = set(), 0
        for name in case["expected_sections"]:
            choices = sorted((SequenceMatcher(None, canonical(name), canonical(s)).ratio(), i) for i, s in enumerate(actual) if i not in used)
            if choices and choices[-1][0] >= 0.85:
                used.add(choices[-1][1])
                count += 1
        section_recall = count / len(case["expected_sections"])
        section_f1 = 2 * count / max(1, len(case["expected_sections"]) + len(actual))
    return {
        "scope": case.get("scope"),
        "expected": len(expected),
        "predicted": len(fields),
        "matched": len(matches),
        "precision": len(matches) / max(1, len(fields)),
        "recall": len(matches) / max(1, len(expected)),
        "f1": 2 * len(matches) / max(1, len(fields) + len(expected)),
        "type_accuracy": sum(m["type_correct"] for m in matches) / max(1, len(matches)),
        "section_accuracy": section_recall,
        "section_f1": section_f1,
        "condition_coverage": None,
        "matches": matches,
        "missing": [e["key"] for i, e in enumerate(expected) if i not in used_e],
        "extra": [f["label"] for j, f in enumerate(fields) if j not in used_f],
    }


def main():
    records = []
    for case in json.loads((ROOT / "evaluation/engine-v03/annotations-known.json").read_text())["cases"]:
        for version, directory in [("v03", ROOT / "evaluation/engine-v03/results"), ("final", DEST / "results")]:
            records.append({"id": case["id"], "category": "known_scoped", "version": version, **score(case, json.loads((directory / (case["id"] + ".json")).read_text()))})
    for case in json.loads((ROOT / "evaluation/engine-v03/new-documents/annotations.json").read_text())["cases"]:
        for version, directory in [("v03", ROOT / "evaluation/engine-v03/results"), ("final", DEST / "results")]:
            records.append({"id": case["id"], "category": "development_after_v03", "version": version, **score(case, json.loads((directory / (case["id"] + ".json")).read_text()))})
    for folder, category in [
        ("promoted-development-documents", "promoted_development"),
        ("secondary-audit-documents", "secondary_audit"),
        ("unknown-documents", "prospective_r3_holdout"),
    ]:
        directory = DEST / folder
        lock = json.loads((directory / "annotation-lock.json").read_text())
        assert hashlib.sha256((directory / "annotations.json").read_bytes()).hexdigest() == lock["annotation_sha256"]
        if category == "prospective_r3_holdout":
            assert hashlib.sha256((DEST / "engine-freeze.json").read_bytes()).hexdigest() == lock["freeze_sha256"]
        for case in json.loads((directory / "annotations.json").read_text())["cases"]:
            case_id = "final-" + case["id"]
            baseline_dir = DEST / (
                {"promoted_development": "trials/r1-before-blank-table-fix/baseline-v03", "secondary_audit": "trials/r2-before-numbered-caption-fix/baseline-v03"}.get(
                    category, "baseline-v03"
                )
            )
            for version, path in [("v03", baseline_dir / (case_id + ".json")), ("final", DEST / "results" / (case_id + ".json"))]:
                if path.exists():
                    records.append({"id": case_id, "category": category, "version": version, **score(case, json.loads(path.read_text()))})
    (DEST / "field-metrics.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    for r in records:
        print(r["id"], r["version"], f"F1={r['f1']:.3f}", f"matched={r['matched']}/{r['expected']}")


if __name__ == "__main__":
    main()
