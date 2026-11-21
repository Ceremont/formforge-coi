"""Explicit local dictionaries; no official identities are guessed."""

import json
from hashlib import sha256
from pathlib import Path

from pydantic import TypeAdapter

from .layout_analyzer import fold
from .models import DictionaryReference


class DictionaryRegistry:
    def __init__(self, entries=()):
        self.entries = {entry.id: entry for entry in entries}
        if len(self.entries) != len(entries):
            raise ValueError("Duplicate dictionary IDs")

    @classmethod
    def from_file(cls, path):
        if not path:
            return cls()
        source = Path(path)
        if source.stat().st_size > 2_000_000:
            raise ValueError("Dictionary registry exceeds limit")
        return cls(TypeAdapter(list[DictionaryReference]).validate_python(json.loads(source.read_text())))


class DictionaryMatcher:
    def bind(self, fields, registry):
        used = {}
        for field in fields:
            exact = [
                entry
                for entry in registry.entries.values()
                if fold(field.label) in {fold(entry.title), *(fold(a) for a in entry.aliases)} or field.options and set(field.options) == set(entry.values)
            ]
            if len(exact) == 1:
                field.dictionary = exact[0].model_copy(deep=True)
                field.options = list(exact[0].values)
                used[exact[0].id] = field.dictionary
            elif field.options:
                identifier = "proposed_" + sha256("|".join(field.options).encode()).hexdigest()[:12]
                proposal = DictionaryReference(id=identifier, source="proposed", title=field.label, values=field.options)
                used[identifier] = proposal
                # Keep the source document reference; proposals are separately visible.
                if field.dictionary is None:
                    field.dictionary = proposal
            elif len(exact) > 1:
                field.requires_review = True
        return list(used.values())
