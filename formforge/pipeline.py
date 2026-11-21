from pathlib import Path
from time import perf_counter

from .coi_mapper import COIJsonMapper, export_bundle
from .config import Settings
from .extractors import DocumentExtractor
from .field_detector import FieldDetector
from .form_validator import FormValidator
from .layout_analyzer import LayoutAnalyzer
from .structure_builder import FormStructureBuilder


def convert(path: Path, filename: str, extension: str, settings: Settings) -> dict:
    stages = []

    def run(name, action):
        start = perf_counter()
        result = action()
        stages.append({"stage": name, "status": "completed", "duration_ms": round((perf_counter() - start) * 1000, 2)})
        return result

    document = run("extraction", lambda: DocumentExtractor(settings).extract(path, filename, extension))
    analyzed = run("layout", lambda: LayoutAnalyzer().analyze(document))
    if settings.analysis_mode == "local-ai-assisted":
        from .local_ai import assist

        analyzed = assist(analyzed, settings.local_model_path)
    fields = run("field_detection", lambda: FieldDetector().detect(analyzed))
    form = run("structure", lambda: FormStructureBuilder().build(analyzed, fields))
    detected_form = form.model_dump(mode="json")
    normalization = {"applied": False}
    if settings.export_format == "official":
        from .coi_standardizer import standardize

        form, normalization = standardize(form, analyzed)
    from .dictionaries import DictionaryRegistry, DictionaryMatcher

    try:
        form.dictionaries = DictionaryMatcher().bind(form.fields, DictionaryRegistry.from_file(settings.dictionary_registry_path))
    except ValueError, OSError:
        form.warnings.append("Nie udało się załadować lokalnego rejestru słowników; zachowano opcje z dokumentu.")
    issues = run("validation", lambda: FormValidator().inspect(form))
    export, coi_report = run("json_mapping", lambda: export_bundle(form, settings.export_format))
    return {
        "form": form.model_dump(mode="json"),
        "detected_form": detected_form,
        "export": export,
        "preview_export": COIJsonMapper().export(form),
        "coi_validation": coi_report,
        "normalization": normalization,
        "issues": [i.model_dump() for i in issues],
        "document": analyzed.model_dump(mode="json"),
        "stages": stages,
    }
