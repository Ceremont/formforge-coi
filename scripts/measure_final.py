"""Separate-process, single-run CPU measurements; no benchmark-driven tuning."""
import json
import resource
import subprocess
import sys
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def worker(filename):
    from formforge import ocr
    from formforge.config import Settings
    from formforge.pipeline import convert

    elapsed = []
    original = ocr.recognize

    def measured(*args, **kwargs):
        start = perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            elapsed.append(perf_counter() - start)

    path = ROOT / 'demo_samples' / filename
    start = perf_counter()
    with patch.object(ocr, 'recognize', measured):
        result = convert(path, 'unseen' + path.suffix, path.suffix[1:], Settings())
    total = perf_counter() - start
    stages = {s['stage']: s['duration_ms'] / 1000 for s in result['stages']}
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return dict(file=filename, fields=len(result['form']['fields']), extraction_s=stages['extraction'], ocr_s=round(sum(elapsed), 4), analysis_s=round(sum(v for k, v in stages.items() if k != 'extraction'), 4), total_s=round(total, 4), python_peak_rss_mib=round(rss / (1024**2 if sys.platform == 'darwin' else 1024), 2), json_valid=result['coi_validation']['valid'])


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(json.dumps(worker(sys.argv[1])))
    else:
        import platform
        cases = [json.loads(subprocess.run([sys.executable, __file__, f], check=True, capture_output=True, text=True, timeout=100).stdout) for f in ['zaswiadczenie.pdf', 'zezwolenie.docx', 'zgloszenie.xlsx', 'zaswiadczenie.png', 'wielostronicowy.pdf']]
        report = dict(protocol='One warm-installed separate Python process per own synthetic document. No optimization or accuracy tuning. OCR is a subset of extraction, not an additional duration. RSS includes Python/PDFium but not concurrent Tesseract child peak; not combined system peak. Import time precedes total timer; no HTTP/queue/browser included. No production throughput claim.', platform=platform.platform(), machine=platform.machine(), python=platform.python_version(), cases=cases)
        target = ROOT / 'evaluation/coi-final/performance.json'
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(report, ensure_ascii=False, indent=2))
