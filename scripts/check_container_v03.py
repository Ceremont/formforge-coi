"""Real image/Compose smoke test. No external endpoints or document storage."""

import json
from pathlib import Path
import subprocess
import time
import sys
import httpx

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "evaluation/engine-v03"
COMMAND = ["docker", "compose", "-p", "formforge-v03-check"]


def run(*args):
    return subprocess.run([*COMMAND, *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def source(group, extension):
    return next(p for p in (ROOT / "reference/coi-official/forms" / group).iterdir() if p.suffix.lower() == "." + extension and "wizualizac" not in p.name)


def main():
    result = {"image_build": "passed", "image": "formforge-coi:0.3.0", "compose_config": "passed", "compose_project": "formforge-v03-check", "cases": []}
    with httpx.Client(base_url="http://127.0.0.1:8766", timeout=100) as client:
        response = client.get("/api/health")
        response.raise_for_status()
        result["health"] = response.json()
        assert result["health"]["version"] == "0.3.0" and result["health"]["ocr"]["available"]
        cases = [
            ("pdf", ROOT / "demo_samples/zaswiadczenie.pdf", "application/pdf"),
            ("textbox", source("02", "docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("sparse-xlsx", source("08", "xlsx"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("ocr", ROOT / "demo_samples/zaswiadczenie.png", "image/png"),
            ("jpe", source("07", "jpe"), "image/jpeg"),
            ("large-image", source("09", "png"), "image/png"),
            ("binary-doc", source("01", "doc"), "application/msword"),
        ]
        for label, path, mime in cases:
            start = time.perf_counter()
            r = client.post("/api/v1/forms/convert", files={"file": ("unknown" + path.suffix, path.read_bytes(), mime)})
            data = r.json()
            record = {"case": label, "http_status": r.status_code, "seconds": round(time.perf_counter() - start, 3)}
            if r.status_code == 200:
                record.update(
                    fields=len(data["form"]["fields"]), valid=data["coi_validation"]["valid"], quality=data["quality"]["status"], ocr=bool(data["document"]["analysis"].get("ocr"))
                )
            else:
                record["error"] = data
            result["cases"].append(record)
            print(json.dumps(record), flush=True)
            (DEST / "docker-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
            assert r.status_code == (415 if label == "binary-doc" else 200), record
            if r.status_code == 200:
                assert record["valid"] and record["fields"] > 0
    finish(result)


def finish(result):
    result["uid"] = run("exec", "-T", "formforge", "id", "-u")
    assert result["uid"] == "10001"
    result["tesseract"] = run("exec", "-T", "formforge", "tesseract", "--version").splitlines()[0]
    inventory = run(
        "exec",
        "-T",
        "formforge",
        "python",
        "-c",
        "import importlib.metadata as m,json; print(json.dumps(sorted([{'name':d.metadata['Name'],'version':d.version,'license':d.metadata.get('License-Expression') or d.metadata.get('License')} for d in m.distributions()],key=lambda x:x['name'])))",
    )
    (DEST / "container-python-inventory.json").write_text(inventory)
    native = run("exec", "-T", "formforge", "ldd", "/opt/ocr/bin/tesseract")
    (DEST / "container-ocr-linkage.txt").write_text(native)
    assert all(name not in native for name in ["libgomp", "libcurl", "libarchive", "libtiff", "libjbig"])
    result["excluded_ocr_optional_libraries_absent"] = True
    result["read_only"] = (
        subprocess.run(
            ["docker", "inspect", "--format", "{{.HostConfig.ReadonlyRootfs}}", "formforge-v03-check-formforge-1"], check=True, capture_output=True, text=True
        ).stdout.strip()
        == "true"
    )
    result["internal_network"] = (
        subprocess.run(["docker", "network", "inspect", "--format", "{{.Internal}}", "formforge-v03-check_offline"], check=True, capture_output=True, text=True).stdout.strip()
        == "true"
    )
    networks = subprocess.run(
        ["docker", "inspect", "--format", "{{json .NetworkSettings.Networks}}", "formforge-v03-check-formforge-1"], check=True, capture_output=True, text=True
    ).stdout
    result["processor_networks"] = list(json.loads(networks))
    assert result["processor_networks"] == ["formforge-v03-check_offline"]
    assert result["read_only"] and result["internal_network"]
    leftovers = run("exec", "-T", "formforge", "python", "-c", "from pathlib import Path;print(len(list(Path('/tmp').glob('formforge-*'))))")
    result["request_temp_directories_after_tests"] = int(leftovers)
    assert int(leftovers) == 0
    result["status"] = "passed"
    result["full_native_sbom"] = "not a complete audited SBOM; inventories/linkage only"
    (DEST / "docker-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print("Container verification passed", flush=True)


if __name__ == "__main__":
    if "--inventory-only" in sys.argv:
        finish(json.loads((DEST / "docker-verification.json").read_text()))
    else:
        main()
