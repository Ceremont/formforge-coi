"""Create the clean competition source ZIP with an explicit redistribution boundary."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = {'README.md','ARCHITECTURE.md','LICENSE','THIRD_PARTY_NOTICES.md','CHANGELOG.md','RELEASE_NOTES.md','VERSION','Dockerfile','docker-compose.yml','.dockerignore','.gitignore','.env.example','pyproject.toml','requirements.lock','requirements-dev.lock'}
TREES = ['formforge','deploy','config','demo_samples','scripts','tests','docs']
EXCLUDED = {'.venv','.git','__pycache__','.pytest_cache','.ruff_cache','node_modules','.codex','.agents','.aws','output','tmp'}
EVIDENCE = {
 'baseline.json','engine-freeze.json','mapping-hotfix.json','known-results.json','unknown-results.json','development-results.json','promoted-results.json','secondary-results.json','field-metrics.json','aggregate-metrics.json','v04-verification.json','v05-verification.json','docker-verification.json','offline-verification.json','browser-verification.json','release-verification.json','performance.json','presentation-verification.json','container-ocr-linkage.txt','container-python-inventory.json','container-os-packages.txt','package-verification.json'
}


def selected():
    files = {ROOT / name for name in TOP}
    for tree in TREES:
        for path in (ROOT / tree).rglob('*'):
            if not path.is_file() or path.is_symlink() or set(path.relative_to(ROOT).parts) & EXCLUDED:
                continue
            if path.name in {'.DS_Store'} or path.suffix in {'.pyc','.zip','.pem','.key','.p12','.pfx'} or path.name.endswith('.zip.tmp'):
                continue
            if path.name.startswith('.env') and path.name != '.env.example':
                continue
            # Only the new own slide deck is distributed; old task/reference PDF copies never enter.
            if tree == 'docs' and path.suffix.lower() == '.pdf' and path.name != 'FormForge_COI_1.0_Presentation_PL.pdf':
                continue
            files.add(path)
    directory = ROOT / 'evaluation/coi-final'
    files.update(directory / name for name in EVIDENCE if (directory / name).is_file())
    for name in ['exports','comparisons','annotations-known','unknown-documents','promoted-development-documents','secondary-audit-documents']:
        files.update(p for p in (directory / name).rglob('*.json') if p.is_file())
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def main():
    target = ROOT / 'FormForge-COI-v1.0.0-release.zip'
    files = selected()
    assert all(p.is_file() and not p.is_symlink() for p in files)
    manifest = dict(project='FormForge COI — HackNation Competition Edition', version='1.0.0', git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), git_branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(), dependencies_included=False, raw_organizer_and_external_originals_included=False, historical_experiments='Preserved in Git, omitted raw traces/originals from this clean source ZIP. Summary evidence/annotations and generated submission exports retained.', setup='See README and QUICK_START_PL; install/build once before offline runtime.', files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    temporary = target.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in files:
            archive.write(path,'FormForge-COI/'+path.relative_to(ROOT).as_posix())
        archive.writestr('FormForge-COI/ARCHIVE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert not any('/reference/' in n or '/.env/' in n or n.endswith('/.env') for n in names)
        assert not any('/evaluation/' in n and n.lower().endswith(('.pdf','.doc','.docx','.xlsx','.ods','.jpg','.png')) for n in names)
        for record in manifest['files']:
            data = archive.read('FormForge-COI/'+record['path'])
            assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256']
        for required in ['formforge/data/coi_schema.json','deploy/render_source.py','docs/FINAL_COMPETITION_REPORT.md','docs/FormForge_COI_1.0_Presentation_PL.pdf','requirements.lock','demo_samples/zaswiadczenie.doc']:
            assert 'FormForge-COI/'+required in names
    temporary.replace(target)
    print(json.dumps(dict(archive=target.name,files=len(files)+1,megabytes=round(target.stat().st_size/1024/1024,2),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),integrity='passed',raw_sources_included=False),indent=2))


if __name__ == '__main__':
    main()
