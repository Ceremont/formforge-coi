"""Strict recursive compatibility profile; published COI schema stays unchanged."""

from typing import Literal
from uuid import UUID
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class COIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_max_length=20000, populate_by_name=True)


class State(COIModel):
    type: Literal["SHOW", "READ_ONLY"]
    query: str = Field(min_length=1, max_length=8000)


class Option(COIModel):
    id: str
    name: str
    techName: str


class Consent(COIModel):
    description: str
    required: bool = False


class ConsentConfig(COIModel):
    consents: list[Consent] = Field(min_length=1, max_length=100)
    required: bool | None = None
    files: list[str] = Field(default_factory=list)


class COIField(COIModel):
    id: UUID
    type: Literal[
        "SECTION",
        "REPEATING_SECTION",
        "TEXT_FIELD",
        "TEXTAREA",
        "NUMBER",
        "SELECT",
        "RADIO",
        "CHECKBOX",
        "DATEPICKER",
        "FILE_UPLOADER",
        "CONSENT_SECTION",
        "TEXT_BLOCK",
        "INFO_SECTION",
    ]
    techName: str = Field(min_length=1, max_length=250)
    title: str = ""
    description: str = ""
    options: list[Option] = Field(default_factory=list, max_length=500)
    validation: list[str] = Field(default_factory=list, max_length=30)
    readOnly: bool = False
    repeatingSectionGrid: list["Question"] = Field(default_factory=list, max_length=5000, validation_alias=AliasChoices("repeatingSectionGrid", "repetingSectionGrid"))
    states: list[State] = Field(default_factory=list, max_length=20)
    questionOrder: int = Field(default=0, ge=0)
    tooltipMessage: str = ""
    dictionaryName: str | None = None
    defaultValue: str | list[str] | int | float | bool | None = None
    defaultValueType: Literal["EXTERNAL_SYSTEM"] | None = None
    searchEnabled: bool | None = None
    multiLevelTree: bool | None = None
    consentSectionConfig: ConsentConfig | None = None
    selectAllEnabled: bool | None = None


class Question(COIModel):
    x: int = Field(ge=0, le=2)
    y: int = Field(ge=0, le=100000)
    rows: int = Field(ge=1, le=100000)
    cols: int = Field(ge=1, le=3)
    field: COIField


class Tab(COIModel):
    id: UUID
    title: str = Field(min_length=1, max_length=255)
    type: Literal["MAIN", "FINISH"]
    questions: list[Question] = Field(min_length=1, max_length=2000)


class FlowLink(COIModel):
    id: UUID
    source: UUID
    target: UUID


class Flow(COIModel):
    links: list[FlowLink] = Field(min_length=1, max_length=5000)


class FormDefinition(COIModel):
    title: str = Field(min_length=1, max_length=255)
    tabs: list[Tab] = Field(min_length=2, max_length=100)
    flow: Flow
