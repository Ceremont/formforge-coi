"""Semantic, UUID-independent comparison. Evaluation only, never used in conversion.

Conditions are compared by executing both JSONata expressions over the finite
domains of their referenced choice fields, including an unanswered value. This
is equivalence on those scenarios, not a proof for arbitrary JSONata programs.
"""

import copy
import itertools
import re
from difflib import SequenceMatcher
import jsonata
from .coi_validation import CONTAINERS, INPUTS, fields_with_context, nested
from .layout_analyzer import fold


def canonical(title):
    text = fold(title).replace("_", " ").replace("pelnomonictwo", "pelnomocnictwo")
    text = re.sub(r"\bplik\b|\bz\b|\bsekcja\b", " ", text)
    if text.startswith("teryt"):
        return "teryt address cascade"
    return " ".join(re.findall(r"[a-z0-9]+", text))


def nodes(payload):
    result = []

    def visit(tab, parent, questions, prefix):
        for i, question in sorted(enumerate(questions), key=lambda iq: (iq[1]["y"], iq[1]["x"])):
            field = question["field"]
            path = f"{prefix}/{i}"
            result.append({"field": field, "section": canonical(parent["title"]) if parent else "", "tab": tab["title"], "path": path})
            visit(tab, field, nested(field), path + "/field/repeatingSectionGrid")

    for ti, tab in enumerate(payload["tabs"]):
        if tab["type"] != "FINISH":
            visit(tab, None, tab["questions"], f"tabs/{ti}/questions")
    return result


def pair_nodes(expected, actual):
    """Greedy unique pairing, exact section identity before label similarity."""
    candidates = []
    for i, e in enumerate(expected):
        for j, a in enumerate(actual):
            ef, af = e["field"], a["field"]
            if (ef["type"] in CONTAINERS) != (af["type"] in CONTAINERS):
                continue
            if e["section"] != a["section"]:
                continue
            et, at = canonical(ef["title"]), canonical(af["title"])
            similarity = SequenceMatcher(None, et, at).ratio()
            if ef["type"] == af["type"] and ef["type"] in ("FILE_UPLOADER", "CONSENT_SECTION", "TEXT_BLOCK"):
                unique = all(sum(n["section"] == e["section"] and n["field"]["type"] == ef["type"] for n in collection) == 1 for collection in (expected, actual))
                if unique:
                    similarity = max(similarity, 0.8)  # Unambiguous role within an already matched section.
            if similarity < 0.65:
                continue
            # Repeated address labels: distinguish domestic and foreign states.
            en = any("$not" in s["query"] for s in ef.get("states", []))
            an = any("$not" in s["query"] for s in af.get("states", []))
            candidates.append((similarity + (0.1 if en == an else 0) - abs(i - j) * 0.00001, i, j))
    matched_e, matched_a, pairs = set(), set(), []
    for score, i, j in sorted(candidates, reverse=True):
        if i not in matched_e and j not in matched_a:
            pairs.append((expected[i], actual[j], round(min(score, 1), 3)))
            matched_e.add(i)
            matched_a.add(j)
    return pairs, [e for i, e in enumerate(expected) if i not in matched_e], [a for j, a in enumerate(actual) if j not in matched_a]


def condition_check(expected_payload, actual_payload, pairs):
    mapping = {e["field"]["id"]: a["field"]["id"] for e, a, _ in pairs}
    reference_fields = [f for _, _, f, _ in fields_with_context(expected_payload)]
    results = []
    for e, a, _ in pairs:
        ef, af = e["field"], a["field"]
        for state in ef.get("states", []):
            query = state["query"]
            counterpart = next((s["query"] for s in af.get("states", []) if s["type"] == state["type"]), None)
            item = {"field": ef["title"], "section": e["section"], "type": state["type"], "reference_query": query, "generated_query": counterpart}
            deps = [f for f in reference_fields if re.search(r"['\"]" + re.escape(f["techName"]) + r"['\"]\s+in (?:field\.techName|fieldTechName)", query)]
            if not counterpart:
                item["status"] = "missing"
            elif not deps or any(f["id"] not in mapping for f in deps):
                item["status"] = "unrecognized_dependency"
            else:
                domains = [[""] + (["Polska", "Niemcy"] if f.get("dictionaryName") == "Kraje" else [o["id"] for o in f.get("options", [])]) for f in deps]
                try:
                    left = jsonata.Jsonata(query, timeout=200, stack=100)
                    right = jsonata.Jsonata(counterpart, timeout=200, stack=100)
                    scenarios = list(itertools.product(*domains))
                    if len(scenarios) > 256:
                        raise ValueError("Scenario limit")
                    differences = []
                    for values in scenarios:
                        ed, ad = copy.deepcopy(expected_payload), copy.deepcopy(actual_payload)
                        ev = {f["id"]: ([v] if v else []) for f, v in zip(deps, values)}
                        av = {mapping[k]: v for k, v in ev.items()}
                        for payload, answers in [(ed, ev), (ad, av)]:
                            for _, _, f, _ in fields_with_context(payload):
                                if f["id"] in answers:
                                    f["__userAnswer"] = answers[f["id"]]
                        if bool(left.evaluate(ed)) != bool(right.evaluate(ad)):
                            differences.append(values)
                    item.update(status="different" if differences else "equivalent_on_choice_domains", scenarios=len(scenarios), differing_answers=differences)
                except Exception as exc:
                    item.update(status="unrecognized_expression", reason=type(exc).__name__)
            results.append(item)
    # Reference states on an unmatched component must count as missing too.
    matched = set(mapping)
    for e in nodes(expected_payload):
        if e["field"]["id"] not in matched:
            for state in e["field"].get("states", []):
                results.append({"field": e["field"]["title"], "reference_query": state["query"], "status": "missing_component"})
    return results


def compare(expected, actual):
    en, an = nodes(expected), nodes(actual)
    pairs, missing, extra = pair_nodes(en, an)
    ei = [n for n in en if n["field"]["type"] in INPUTS]
    ai = [n for n in an if n["field"]["type"] in INPUTS]
    ip = [(e, a, s) for e, a, s in pairs if e["field"]["type"] in INPUTS and a["field"]["type"] in INPUTS]
    precision, recall = len(ip) / max(1, len(ai)), len(ip) / max(1, len(ei))
    sections_e = {canonical(n["field"]["title"]) for n in en if n["field"]["type"] in CONTAINERS}
    sections_a = {canonical(n["field"]["title"]) for n in an if n["field"]["type"] in CONTAINERS}
    section_f1 = 2 * len(sections_e & sections_a) / max(1, len(sections_e) + len(sections_a))
    # Order concordance over pairs inside the same section (no UUID sorting).
    concordant, total = 0, 0
    for (e, a, _), (f, b, _) in itertools.combinations(ip, 2):
        if e["section"] == f["section"]:
            total += 1
            concordant += (ei.index(e) < ei.index(f)) == (ai.index(a) < ai.index(b))
    order = concordant / max(1, total)
    types_e, types_a = [t["type"] for t in expected["tabs"]], [t["type"] for t in actual["tabs"]]
    tabs = SequenceMatcher(None, types_e, types_a).ratio()

    def edges(p):
        ids = {t["id"]: i for i, t in enumerate(p["tabs"])}
        return {(ids.get(link["source"], -1), ids.get(link["target"], -1)) for link in p["flow"]["links"]}

    ee, ae = edges(expected), edges(actual)
    flow = len(ee & ae) / max(1, len(ee | ae))
    states = condition_check(expected, actual, pairs)

    def describe(n):
        return {"section": n["section"], "title": n["field"]["title"], "type": n["field"]["type"]}

    differences = []
    for e, a, score in ip:
        ef, af = e["field"], a["field"]
        detail = {"reference": describe(e), "generated": describe(a), "match_score": score}
        detail["differences"] = {
            k: {"expected": ef.get(k), "actual": af.get(k)} for k in ("type", "validation", "dictionaryName", "defaultValue", "readOnly") if ef.get(k) != af.get(k)
        }
        detail["options_equal"] = [o["name"] for o in ef.get("options", [])] == [o["name"] for o in af.get("options", [])]
        differences.append(detail)
    return {
        "expected_interactive_fields": len(ei),
        "generated_interactive_fields": len(ai),
        "matched_fields": len(ip),
        "field_precision": precision,
        "field_recall": recall,
        "field_f1": 2 * precision * recall / max(1e-9, precision + recall),
        "field_type_accuracy": sum(e["field"]["type"] == a["field"]["type"] for e, a, _ in ip) / max(1, len(ip)),
        "structural_similarity": (section_f1 + order + tabs + flow) / 4,
        "structural_components": {"section_f1": section_f1, "within_section_order": order, "tab_types": tabs, "flow_edges": flow},
        "conditional_rules_coverage": sum(s["status"] == "equivalent_on_choice_domains" for s in states) / max(1, len(states)),
        "conditions": states,
        "missing": [describe(n) for n in missing],
        "extra": [describe(n) for n in extra],
        "matches": differences,
        "uuid_comparison": False,
    }
