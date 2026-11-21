"""Optional tiny CPU block classifier: locally trained multinomial Naive Bayes.

No endpoints, downloads, pickle, executable model code, or fabricated text.
"""

import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from pydantic import Field

from .layout_analyzer import fold
from .models import Model


class Proposal(Model):
    block_id: str
    role: Literal["heading", "instruction", "legal", "information", "text"]
    score: float = Field(ge=0, le=1)


class LocalModel(Model):
    format: Literal["formforge-naive-bayes-v1"]
    license: Literal["MIT"]
    provenance: str
    counts: dict[str, dict[str, int]]
    documents: dict[str, int]


def tokens(text):
    return re.findall(r"[a-z0-9]+", fold(text))[:200]


def train(examples):
    counts = defaultdict(Counter)
    documents = Counter()
    for text, role in examples:
        counts[role].update(tokens(text))
        documents[role] += 1
    return LocalModel(
        format="formforge-naive-bayes-v1", license="MIT", provenance="Self-authored development text; no evaluation documents", counts=dict(counts), documents=dict(documents)
    )


def assist(document, path):
    original = document.model_copy(deep=True)
    if not path:
        return document.model_copy(update={"warnings": document.warnings + ["Model lokalny nie został wskazany; użyto trybu deterministic."]})
    try:
        source = Path(path)
        if source.stat().st_size > 2_000_000:
            raise ValueError("Model too large")
        model = LocalModel.model_validate_json(source.read_text())
        vocabulary = {word for counts in model.counts.values() for word in counts}
        if not vocabulary or not model.documents:
            raise ValueError("Empty model")
        proposals = []
        for block in document.blocks:
            if block.kind != "text" or block.metadata.get("label_input_pair"):
                continue
            words = tokens(block.text)
            scores = {
                role: math.log(model.documents[role] / sum(model.documents.values()))
                + sum(math.log((counts.get(word, 0) + 1) / (sum(counts.values()) + len(vocabulary))) for word in words)
                for role, counts in model.counts.items()
            }
            ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            if not ranked:
                continue
            # Margin is an algorithm score; no calibrated probability is claimed.
            margin = 1 - math.exp(-max(0, ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else ranked[0][1])))
            proposal = Proposal(block_id=block.id, role=ranked[0][0], score=margin)
            proposals.append(proposal.model_dump())
            # Conservative: only classify explicit lengthy prose; never invent fields.
            if proposal.score > 0.85 and len(words) > 12 and proposal.role in ("legal", "instruction"):
                block.kind = proposal.role
                block.metadata["local_ai_proposal"] = proposal.model_dump()
        return document.model_copy(
            update={"analysis": {**document.analysis, "local_ai": {"model": model.format, "proposals": proposals, "score_semantics": "uncalibrated_margin"}}}
        )
    except OSError, ValueError, KeyError, ZeroDivisionError:
        return original.model_copy(update={"warnings": original.warnings + ["Model lokalny jest niedostępny lub niepoprawny; użyto deterministic."]})
