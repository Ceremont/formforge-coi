import re

from .layout_analyzer import fold
from .models import ConditionalRule


class ConditionalRulesBuilder:
    pattern = re.compile(r'Jeżeli\s+[„"]([^”"]+)[”"]\s*=\s*[„"]([^”"]+)[”"],?\s+(pokaż sekcję|pokaż|wymagaj)\s+[„"]([^”"]+)[”"]', re.I)
    natural = re.compile(
        r'(?:Jeżeli|Jeśli|W przypadku gdy)\s+(?:wybierzesz|zaznaczysz|wybrano|zaznaczono)\s+[„"]([^”"]+)[”"][,:]?\s+(?:podaj|wpisz|wypełnij)\s+[„"]([^”"]+)[”"]', re.I
    )

    def apply(self, document, fields, sections):
        recognized = set()
        labels = {}
        for field in fields:
            labels.setdefault(fold(field.label), []).append(field)
        for block in document.blocks:
            match = self.pattern.search(block.text)
            natural = self.natural.search(block.text)
            if not match and natural:
                value, target_label = natural.groups()
                parents = [f for f in fields if value in f.options]
                targets = labels.get(fold(target_label), [])
                if len(parents) == len(targets) == 1 and parents[0].id != targets[0].id:
                    # The graph safety check below handles both source syntaxes.
                    parent_label = parents[0].label
                    action = "pokaż"
                    match_values = (parent_label, value, action, target_label)
                else:
                    continue
            elif match:
                match_values = match.groups()
            else:
                continue
            parent_label, value, action, target_label = match_values
            parents = labels.get(fold(parent_label), [])
            targets = [s for s in sections if fold(s.title) == fold(target_label)] if action.lower() == "pokaż sekcję" else labels.get(fold(target_label), [])
            if len(parents) != 1 or len(targets) != 1:
                continue
            parent, target = parents[0], targets[0]
            if not (value in parent.options or parent.field_type == "checkbox" and value.lower() in ("true", "false")):
                continue
            if target.id == parent.id or action.lower() == "pokaż sekcję" and parent.section == target.id:
                continue
            condition = ConditionalRule(
                field_id=parent.id,
                value=(value.lower() == "true") if parent.field_type == "checkbox" else value,
                action="require" if action.lower() == "wymagaj" else "show",
                evidence=block.text,
                requires_review=bool(natural),
            )
            rules = target.required_conditions if action.lower() == "wymagaj" else target.conditions
            rules.append(condition)
            if natural and hasattr(target, "requires_review"):
                target.requires_review = True
            # Validate the combined graph before accepting an inferred dependency.
            graph = {f.id: [c.field_id for c in f.conditions + f.required_conditions + next(s.conditions for s in sections if s.id == f.section)] for f in fields}

            def reaches(node, goal, seen):
                if node == goal:
                    return True
                if node in seen or len(seen) > 32:
                    return False
                return any(reaches(p, goal, seen | {node}) for p in graph[node])

            affected = [target.id]
            if action.lower() == "pokaż sekcję":
                affected = [f.id for f in fields if f.section == target.id]
            if any(reaches(parent.id, node, set()) for node in affected):
                rules.pop()
                if hasattr(target, "requires_review"):
                    target.requires_review = True
                continue
            recognized.add(block.id)
        return recognized
