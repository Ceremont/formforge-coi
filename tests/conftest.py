from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from formforge.config import Settings
from formforge.main import app
from formforge.pipeline import convert

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "demo_samples"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_form():
    from formforge.models import Form

    return Form.model_validate(convert(SAMPLES / "zaswiadczenie.docx", "zaswiadczenie.docx", "docx", Settings())["form"])
