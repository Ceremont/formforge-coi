"""Run the preserved 0.3 Git code on the new final sources, without retuning."""

import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "evaluation/coi-final"


def main():
    target = DEST / "baseline-v03"
    target.mkdir(exist_ok=True)
    records = []
    archive = subprocess.run(["git", "archive", "aaa8148", "formforge", "config"], cwd=ROOT, check=True, capture_output=True).stdout
    with tempfile.TemporaryDirectory(prefix="formforge-baseline-code-") as checkout:
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(checkout, filter="data")
        cases = json.loads((DEST / "unknown-documents/manifest.json").read_text())["cases"]
        for case in cases:
            path = DEST / "unknown-documents" / case["file"]
            extension = path.suffix[1:]
            start = perf_counter()
            with tempfile.TemporaryDirectory(prefix="formforge-baseline-input-") as temporary:
                uploaded = Path(temporary) / ("unknown." + extension)
                uploaded.write_bytes(path.read_bytes())
                env = {k: v for k, v in os.environ.items() if not k.startswith("FORMFORGE_")}
                env.update(FORMFORGE_EXPORT_FORMAT="official", FORMFORGE_ANALYSIS_MODE="deterministic", OMP_THREAD_LIMIT="1", TMPDIR=temporary, TMP=temporary, TEMP=temporary)
                worker = subprocess.Popen(
                    [sys.executable, "-m", "formforge.worker", str(uploaded), uploaded.name, extension],
                    cwd=checkout,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    start_new_session=True,
                )
                try:
                    stdout, _ = worker.communicate(timeout=90)
                    response = json.loads(stdout)
                    record = {"id": "final-" + case["id"], "status": "converted" if response["ok"] else "rejected", "baseline_commit": "aaa8148"}
                    if response["ok"]:
                        (target / (record["id"] + ".json")).write_text(json.dumps(response["result"], ensure_ascii=False, indent=2) + "\n")
                        record.update(fields=len(response["result"]["detected_form"]["fields"]), valid=response["result"]["coi_validation"]["valid"])
                    else:
                        record["error"] = response
                except subprocess.TimeoutExpired:
                    os.killpg(worker.pid, signal.SIGKILL)
                    worker.communicate()
                    record = {"id": "final-" + case["id"], "status": "timeout", "baseline_commit": "aaa8148"}
            record["processing_seconds"] = round(perf_counter() - start, 3)
            records.append(record)
            (DEST / "baseline-v03-results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
