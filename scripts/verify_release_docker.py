"""Real final Compose/API checks; only inspect our isolated project."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'VERSION').read_text().strip()
DEST = ROOT / ('evaluation/coi-final' if VERSION=='1.0.0' else 'evaluation/ux-v11')
BASE = os.environ.get('FORMFORGE_BASE_URL', 'http://127.0.0.1:8766')


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def upload(path, endpoint='/api/v1/forms/convert'):
    from formforge.file_validator import MIMES
    boundary = 'formforge-release-boundary'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="unseen{path.suffix}"\r\nContent-Type: {MIMES[path.suffix[1:].lower()]}\r\n\r\n'.encode() + path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode())
    req = urllib.request.Request(BASE + endpoint, data=body, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=110) as response:
            data = response.read()
            return response.status, data if '/source-page' in endpoint else json.loads(data), time.perf_counter() - start
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read()), time.perf_counter() - start


def main():
    sys.path.insert(0, str(ROOT))
    health = json.load(urllib.request.urlopen(BASE + '/api/health', timeout=5))
    assert health['version'] == VERSION and {'pol', 'eng'} <= set(health['ocr']['languages'])
    cases = []
    for filename in ['zaswiadczenie.pdf', 'skan.pdf', 'zaswiadczenie.doc', 'zezwolenie.docx', 'zaswiadczenie.xlsx', 'zaswiadczenie.ods', 'zaswiadczenie.png', 'checkbox.jpg']:
        path = ROOT / 'demo_samples' / filename
        if not path.exists() and filename == 'checkbox.jpg':
            path = next((ROOT / 'demo_samples').glob('*.jpg'))
        status, data, elapsed = upload(path)
        assert status == 200 and data['coi_validation']['valid'], (filename, status, data.get('error'))
        cases.append(dict(case=path.name, http_status=status, seconds=round(elapsed, 3), fields=len(data['form']['fields']), valid=data['coi_validation']['valid']))
    # The one deliberately unsupported original remains rejected in Docker.
    source = next((ROOT / 'reference/coi-official/forms/08').glob('*.doc'), None)
    if source:
        status, data, elapsed = upload(source)
        assert status == 415 and data['error']['code'] == 'macros_rejected'
        cases.append(dict(case='08-embedded-doc', http_status=status, seconds=round(elapsed, 3), error_code=data['error']['code']))
    status, png, _ = upload(ROOT / 'demo_samples/wielostronicowy.pdf', '/api/v1/forms/source-page?page=2')
    # Endpoint has query string, decode PNG directly via a separate request helper below.
    assert status == 200 and isinstance(png, bytes) and png.startswith(b'\x89PNG')
    cid = command('docker', 'compose', '-p', os.environ.get('FORMFORGE_DOCKER_PROJECT','formforge-final-check'), '-f', os.environ.get('FORMFORGE_COMPOSE_FILE',str(ROOT/'docker-compose.yml')), 'ps', '-q', 'formforge')
    info = json.loads(command('docker', 'inspect', cid))[0]
    uid = command('docker', 'exec', cid, 'id', '-u')
    assert uid == '10001' and info['HostConfig']['ReadonlyRootfs']
    networks = info['NetworkSettings']['Networks']
    assert len(networks) == 1
    for name in networks:
        assert json.loads(command('docker', 'network', 'inspect', name))[0]['Internal']
    linkage = command('docker', 'exec', cid, 'ldd', '/opt/ocr/bin/tesseract')
    assert not any(x in linkage for x in ['libgomp', 'libtiff', 'libjbig', 'libcurl', 'libarchive'])
    (DEST / 'container-ocr-linkage.txt').write_text(linkage + '\n')
    inventory = command('docker', 'exec', cid, 'python', '-c', 'import importlib.metadata as m,json; print(json.dumps(sorted([dict(name=d.metadata["Name"],version=d.version,license=d.metadata.get("License-Expression") or d.metadata.get("License")) for d in m.distributions()],key=lambda x:x["name"].lower()),indent=2))')
    (DEST / 'container-python-inventory.json').write_text(inventory + '\n')
    packages = command('docker', 'exec', cid, 'dpkg-query', '-W', '-f=${Package}\t${Version}\n')
    (DEST / 'container-os-packages.txt').write_text(packages + '\n')
    temp = command('docker', 'exec', cid, 'python', '-c', 'import pathlib,json;print(json.dumps([p.name for p in pathlib.Path("/tmp").glob("formforge-*")]))')
    assert json.loads(temp) == []
    report = dict(status='passed', image='formforge-coi:'+VERSION, image_id=info['Image'], base_digest='sha256:c845af9399020c7e562969a13689e929074a10fd057acd1b1fad06a2fb068e97', build='real docker compose build in byte-identical ASCII temporary context; Unicode Buildx path error recorded', health=health, cases=cases, source_page_png=True, uid=uid, read_only=True, internal_processor_network=True, temp_directories_after=0, excluded_ocr_optional_libraries_absent=True, complete_native_sbom=False)
    (DEST / 'docker-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
