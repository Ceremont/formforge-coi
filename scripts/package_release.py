"""Package reviewable source/data/evidence without environments, caches or secrets."""

import hashlib
import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / "FormForge-COI-Official-full.zip"
    excluded = {".venv", ".git", ".pytest_cache", ".ruff_cache", "__pycache__", ".codex", ".agents", ".aws", "node_modules", "tmp"}
    files = []
    for current, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(name for name in dirs if name not in excluded)
        for name in sorted(names):
            path = Path(current) / name
            relative = path.relative_to(ROOT)
            if path.is_symlink() or name == ".DS_Store" or name.endswith((".zip", ".zip.tmp", ".pyc")) or "failure" in name:
                continue
            if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
                continue
            files.append((path, relative))
    manifest = {
        "project": "FormForge official COI adapter and evaluation",
        "dependencies_included": False,
        "setup": "See README.md and requirements*.lock; install dependencies before offline use.",
        "files": [{"path": rel.as_posix(), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path, rel in files],
    }
    temporary = target.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in files:
            archive.write(path, "FormForge-COI/" + relative.as_posix())
        archive.writestr("FormForge-COI/ARCHIVE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        assert "FormForge-COI/evaluation/holdout-v1/manifest.json" in archive.namelist()
        assert "FormForge-COI/docs/DEFENSE_3MIN_PL.md" in archive.namelist()
        assert "FormForge-COI/docs/COI_COMPATIBILITY_REPORT.md" in archive.namelist()
        assert "FormForge-COI/evaluation/coi-v1/independent-results.json" in archive.namelist()
        assert "FormForge-COI/formforge/data/coi_schema.json" in archive.namelist()
    temporary.replace(target)
    print(
        json.dumps(
            {
                "archive": str(target),
                "files": len(files) + 1,
                "megabytes": round(target.stat().st_size / 1024 / 1024, 2),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "integrity": "passed",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
