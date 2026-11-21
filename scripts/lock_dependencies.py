"""Export installed runtime closure separately from test/development tools."""

import importlib.metadata as metadata
import json
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def main():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    pending = [Requirement(item).name for item in project["dependencies"]]
    runtime = {}
    notices = []
    while pending:
        name = canonicalize_name(pending.pop())
        if name in runtime:
            continue
        dist = metadata.distribution(name)
        runtime[name] = dist.version
        license_name = dist.metadata.get("License-Expression") or dist.metadata.get("License")
        if name == "odfpy":
            license_name = "Apache-2.0 (selected from dual license)"
        if name == "jinja2":
            license_name = "BSD-3-Clause"
        notices.append({"name": name, "version": dist.version, "license": license_name, "classifiers": dist.metadata.get_all("Classifier", [])})
        for item in dist.requires or []:
            requirement = Requirement(item)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    (ROOT / "requirements.lock").write_text(
        "# Runtime only. Generated from installed and tested Python 3.14 environment.\n" + "\n".join(f"{name}=={version}" for name, version in sorted(runtime.items())) + "\n"
    )
    pending = [Requirement(item).name for item in project["optional-dependencies"]["dev"]]
    dev = {}
    while pending:
        name = canonicalize_name(pending.pop())
        if name in runtime or name in dev:
            continue
        dist = metadata.distribution(name)
        dev[name] = dist.version
        for item in dist.requires or []:
            requirement = Requirement(item)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    (ROOT / "requirements-dev.lock").write_text("-r requirements.lock\n" + "\n".join(f"{name}=={version}" for name, version in sorted(dev.items())) + "\n")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "runtime-licenses.json").write_text(json.dumps(sorted(notices, key=lambda n: n["name"]), indent=2), encoding="utf-8")
    print(f"Locked {len(runtime)} runtime packages and {len(dev)} development packages")


if __name__ == "__main__":
    main()
