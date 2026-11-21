"""Short-lived subprocess; stdout is a single JSON response, never document logs."""

import json
import os
import sys
from pathlib import Path

from .config import Settings
from .errors import DocumentError


def main():
    # The parent supplies non-secret effective settings through environment.
    # Do not reload the parent's dotenv file (which may contain JWT secrets).
    settings = Settings(_env_file=None)
    os.environ["OMP_THREAD_LIMIT"] = "1"
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (settings.processing_timeout, settings.processing_timeout + 1))
        if sys.platform.startswith("linux"):
            limit = settings.worker_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        from .pipeline import convert

        result = convert(Path(sys.argv[1]), sys.argv[2], sys.argv[3], settings)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
    except DocumentError as error:
        print(json.dumps({"ok": False, "message": error.message, "status": error.status, "code": error.code}))
    except Exception:
        print(json.dumps({"ok": False, "message": "Przetwarzanie dokumentu nie powiodło się.", "status": 422, "code": "processing_failed"}))


if __name__ == "__main__":
    main()
