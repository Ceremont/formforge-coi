"""Run INSIDE the built image with docker --network none; no dev packages."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def main():
    server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'formforge.main:app', '--host', '127.0.0.1', '--port', '8000', '--no-access-log'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                health = json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=1))
                break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('offline server failed')
        assert health['version'] == os.environ.get('FORMFORGE_EXPECTED_VERSION','1.0.0')
        blocked = []
        for host in ['1.1.1.1', '8.8.8.8']:
            try:
                connection = socket.create_connection((host, 443), timeout=1)
                connection.close()
                raise AssertionError('Unexpected external route')
            except OSError as error:
                blocked.append(dict(destination=host, blocked=True, errno=error.errno))
        from formforge.file_validator import MIMES
        cases = []
        for filename in ['zaswiadczenie.pdf', 'zaswiadczenie.doc', 'zaswiadczenie.png']:
            path = Path('/app/demo_samples') / filename
            boundary = 'offline-formforge-boundary'
            body = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="unseen{path.suffix}"\r\nContent-Type: {MIMES[path.suffix[1:]]}\r\n\r\n'.encode() + path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
            start = time.perf_counter()
            req = urllib.request.Request('http://127.0.0.1:8000/api/v1/forms/convert?analysis_mode=local-ai-assisted', data=body, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.load(response)
            assert data['coi_validation']['valid'] and data['form']['fields']
            assert data['document']['analysis']['local_ai']
            cases.append(dict(file=filename, valid=True, fields=len(data['form']['fields']), seconds=round(time.perf_counter()-start, 3), local_model=True))
        assert not list(Path('/tmp').glob('formforge-*'))
        print(json.dumps(dict(status='passed', network_mode='none', uid=os.getuid(), external_connections=blocked, health=health, cases=cases, temp_cleanup=True, installation='Already-built image. Build-time downloads not claimed offline.', runtime_external_services=False), indent=2))
    finally:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


if __name__ == '__main__':
    main()
