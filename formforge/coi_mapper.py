from typing import Protocol

from .models import Form
from .mapping_config import ConfiguredAdapter as ConfiguredAdapter
from .coi_official import COIFormAdapter as COIFormAdapter


class OfficialAdapter(Protocol):
    """Implement using actual COI fixtures, then validate against their schema."""

    def map(self, form: Form) -> dict: ...
    def validate(self, payload: dict) -> None: ...


class COIJsonMapper:
    def __init__(self, official_adapter: OfficialAdapter | None = None):
        self.adapter = official_adapter

    def export(self, form: Form, official: bool = False) -> dict:
        if official:
            if self.adapter is None:
                raise ValueError("Brak oficjalnych materiałów COI i zweryfikowanego adaptera.")
            payload = self.adapter.map(form)
            self.adapter.validate(payload)
            return payload
        return {
            "format": "formforge-preview",
            "compatibility": {
                "status": "preview_incomplete",
                "official_coi": False,
                "message": "Wewnętrzny format FormForge do zgodności wstecznej. Oficjalny eksport COI jest dostępny osobno.",
                "missing_materials": ["Oficjalne pary formularz / JSON", "Schemat i reguły projektowania e-form", "Słowniki i dane inicjalne", "Zrzuty wzorcowych eUsług"],
            },
            "form": form.model_dump(mode="json"),
        }


def export_bundle(form: Form, export_format="official"):
    if export_format == "preview":
        return COIJsonMapper().export(form), {
            "status": "legacy_preview",
            "valid": False,
            "requires_confirmation": True,
            "errors": [],
            "warnings": [],
            "unsupported_features": [],
            "schema_valid": False,
            "business_rules_valid": False,
            "target_import_verified": False,
        }
    adapter = COIFormAdapter()
    payload = adapter.map(form)
    return payload, adapter.report(payload)
