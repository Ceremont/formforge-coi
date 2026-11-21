"""Schema-backed mapping infrastructure, not an invented COI schema."""

import copy
import json
from pathlib import Path

from pydantic import Field

from .models import Model


class Binding(Model):
    source: str = Field(pattern=r"^/(?:[^/]+/)*[^/]+$")
    target: str = Field(pattern=r"^/(?:[^/]+/)*[^/]+$")


class MappingConfig(Model):
    enabled: bool = False
    schema_file: str | None = None
    bindings: list[Binding] = Field(default_factory=list, max_length=200)
    verified_fixture_ids: list[str] = Field(default_factory=list, max_length=1000)
    note: str = ""


def parts(pointer):
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.lstrip("/").split("/")]


class ConfiguredAdapter:
    """Can be wired only after real paired regressions exist. API stays preview."""

    def __init__(self, config, schema):
        from jsonschema import Draft202012Validator
        from referencing import Registry
        from referencing.exceptions import NoSuchResource

        if not config.enabled or not config.bindings or not config.verified_fixture_ids:
            raise ValueError("Mapping requires explicit enablement and verified fixture identifiers")

        def references(node):
            if isinstance(node, dict):
                for key in ("$ref", "$dynamicRef", "$recursiveRef"):
                    if key in node and not node[key].startswith("#"):
                        raise ValueError("Remote or external schema references are forbidden")
                for item in node.values():
                    references(item)
            elif isinstance(node, list):
                for item in node:
                    references(item)

        references(schema)
        Draft202012Validator.check_schema(schema)

        def deny_retrieval(uri):
            raise NoSuchResource(ref=uri)

        self.config, self.validator = config, Draft202012Validator(schema, registry=Registry(retrieve=deny_retrieval))

    @classmethod
    def from_file(cls, path):
        source = Path(path)
        if source.stat().st_size > 2_000_000:
            raise ValueError("Mapping file too large")
        config = MappingConfig.model_validate_json(source.read_text())
        if not config.schema_file:
            raise ValueError("No official schema supplied")
        schema_path = (source.parent / config.schema_file).resolve()
        if schema_path.stat().st_size > 2_000_000:
            raise ValueError("Schema too large")
        return cls(config, json.loads(schema_path.read_text()))

    def map(self, form):
        source = form.model_dump(mode="json")
        result = {}
        for binding in self.config.bindings:
            value = source
            for part in parts(binding.source):
                value = value[int(part)] if isinstance(value, list) else value[part]
            target = result
            keys = parts(binding.target)
            for key in keys[:-1]:
                target = target.setdefault(key, {})
            if keys[-1] in target:
                raise ValueError("Duplicate mapping target")
            target[keys[-1]] = copy.deepcopy(value)
        return result

    def validate(self, payload):
        self.validator.validate(payload)
