"""Exact paired fixture verification. Fails closed when no official cases exist."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from formforge.config import Settings
    from formforge.file_validator import FileValidator
    from formforge.mapping_config import ConfiguredAdapter
    from formforge.models import Form
    from formforge.pipeline import convert

    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    args = parser.parse_args()
    cases = json.loads(args.fixtures.read_text()).get("cases", [])
    if not cases:
        raise SystemExit("No official paired fixtures supplied; compatibility remains preview_incomplete")
    adapter = ConfiguredAdapter.from_file(args.mapping)
    if set(adapter.config.verified_fixture_ids) != {case["id"] for case in cases}:
        raise SystemExit("Mapping fixture identifiers must match the actual fixture manifest")
    for case in cases:
        source = args.fixtures.parent / case["input"]
        expected = json.loads((args.fixtures.parent / case["expected"]).read_text())
        extension = FileValidator(Settings()).validate(source.name, case["mime"], source.read_bytes())
        form = Form.model_validate(convert(source, source.name, extension, Settings())["form"])
        actual = adapter.map(form)
        adapter.validate(actual)
        if actual != expected:
            raise SystemExit("Official fixture mismatch: " + case["id"])
        print("PASS " + case["id"])


if __name__ == "__main__":
    main()
