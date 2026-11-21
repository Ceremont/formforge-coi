"""Verify the actual clean ZIP, then run tests and HTTP conversion from its contents."""
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    archive_path = ROOT / 'FormForge-COI-v1.0.0-release.zip'
    with tempfile.TemporaryDirectory(prefix='formforge-package-') as directory:
        destination = Path(directory)
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.testzip() is None
            for item in archive.infolist():
                assert (destination / item.filename).resolve().is_relative_to(destination.resolve())
            manifest = json.loads(archive.read('FormForge-COI/ARCHIVE_MANIFEST.json'))
            for record in manifest['files']:
                data = archive.read('FormForge-COI/'+record['path'])
                assert hashlib.sha256(data).hexdigest() == record['sha256']
                assert not record['path'].startswith(('reference/','output/','.git/','.venv/'))
                assert not record['path'].endswith(('.pem','.key','.p12','.pfx'))
                if record['path'].endswith(('.py','.md','.js','.json','.toml','.yml')):
                    assert not re.search(rb'/Users/[A-Za-z0-9._-]+/',data), record['path']
                    assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',data), record['path']
            archive.extractall(destination)
        checkout = destination / 'FormForge-COI'
        assert not (checkout/'reference').exists()
        # Same installed dev environment, actual unpacked source and samples, no organizer pack.
        result = subprocess.run([sys.executable,'-m','pytest','-q'],cwd=checkout,capture_output=True,text=True,timeout=120,env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'})
        assert result.returncode == 0, result.stdout + result.stderr
        summary = next(line for line in reversed(result.stdout.splitlines()) if re.search(r'\d+ passed',line))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        server = subprocess.Popen([sys.executable,'-m','uvicorn','formforge.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=checkout,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                try:
                    health = json.load(urllib.request.urlopen(base+'/api/health',timeout=1))
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Unpacked source server failed')
            assert health['version'] == '1.0.0'
            assert b'FormForge' in urllib.request.urlopen(base).read()
            path = checkout / 'demo_samples/zaswiadczenie.pdf'
            boundary='package-release-check'
            body=f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="unseen.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
            data=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/v1/forms/convert',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary}),timeout=90))
            assert data['coi_validation']['valid'] and data['form']['fields']
        finally:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        report=dict(status='passed',archive_crc_and_file_sha256=True,files=len(manifest['files']),raw_originals_absent=True,secrets_and_personal_developer_paths_absent=True,unpacked_tests=summary,unpacked_ui_api_conversion=True,dependency_environment='Existing installed Python3.14 dev dependencies; no internet/install in this check. Source/sample/runtime assets are taken from the unpacked ZIP.',code_sha256={str(p.relative_to(checkout)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (checkout/'formforge').rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        (ROOT/'evaluation/coi-final/package-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='code_sha256'},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
