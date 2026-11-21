"""Release lifecycle checks: shared worker bound, busy response, private temp files."""
import asyncio
from pathlib import Path

from conftest import SAMPLES
from formforge import main


def test_busy_conversion_keeps_bound_and_recovers(client):
    upload = {'file': ('sample.pdf', (SAMPLES / 'zaswiadczenie.pdf').read_bytes(), 'application/pdf')}
    semaphore = main.app.state.workers
    # Every configured worker occupied: next request must fail promptly, not spawn.
    for _ in range(main.settings.max_workers):
        client.portal.call(semaphore.acquire)
    try:
        response = client.post('/api/v1/forms/convert', files=upload)
        assert response.status_code == 429
        assert response.json()['error']['code'] == 'busy'
    finally:
        for _ in range(main.settings.max_workers):
            client.portal.call(asyncio.sleep, 0)
            semaphore.release()
    assert client.post('/api/v1/forms/convert', files=upload).status_code == 200


def test_two_real_concurrent_uploads_have_separate_temporary_inputs(monkeypatch, tmp_path):
    import httpx
    paths = []
    actual = main.run_worker

    async def observe(path, filename, extension):
        paths.append(path)
        return await actual(path, filename, extension)

    monkeypatch.setattr(main, 'run_worker', observe)

    async def check():
        async with main.lifespan(main.app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
                responses = await asyncio.gather(*(client.post('/api/v1/forms/convert', files={'file': ('same.pdf', (SAMPLES / 'zaswiadczenie.pdf').read_bytes(), 'application/pdf')}) for _ in range(2)))
                assert all(r.status_code == 200 and r.json()['coi_validation']['valid'] for r in responses)

    asyncio.run(check())
    assert len(paths) == 2 and paths[0].parent != paths[1].parent
    assert all(not Path(p).parent.exists() for p in paths)
