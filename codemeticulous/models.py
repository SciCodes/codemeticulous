from __future__ import annotations

from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@" r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


class _CanonicalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Identifier(_CanonicalModel):
    value: str
    scheme: str | None = None


class Affiliation(_CanonicalModel):
    name: str
    identifier: Identifier | None = None


class Agent(_CanonicalModel):
    kind: Literal["person", "organization", "unknown"]
    name: str
    given_names: list[str] = Field(default_factory=list)
    family_names: list[str] = Field(default_factory=list)
    email: str | None = None
    url: str | None = None
    identifiers: list[Identifier] = Field(default_factory=list)
    affiliations: list[Affiliation] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and not _EMAIL.fullmatch(value):
            raise ValueError("email must be a plain email address")
        return value


class Contribution(_CanonicalModel):
    agent: Agent
    roles: list[str] = Field(default_factory=list)


class License(_CanonicalModel):
    identifier: str | None = None
    name: str | None = None
    url: str | None = None


class RelatedResource(_CanonicalModel):
    relation: str
    identifier: Identifier | None = None
    title: str | None = None
    resource_type: str | None = None
    url: str | None = None
    creators: list[Agent] = Field(default_factory=list)


class SoftwareMetadata(_CanonicalModel):
    title: str
    description: str | None = None
    publisher: Agent | None = None
    version: str | None = None
    revision: str | None = None
    category: str | None = None
    date_released: date | str | None = None
    date_created: date | str | None = None
    date_modified: date | str | None = None
    url: str | None = None
    repository: str | None = None
    repository_code: str | None = None
    repository_artifact: str | None = None
    download_url: str | None = None
    publication_year: int | None = None
    creators: list[Agent] = Field(default_factory=list)
    contributors: list[Contribution] = Field(default_factory=list)
    identifiers: list[Identifier] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    licenses: list[License] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    formats: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    release_notes: list[str] = Field(default_factory=list)
    relations: list[RelatedResource] = Field(default_factory=list)


__all__ = [
    "Agent",
    "Affiliation",
    "Contribution",
    "Identifier",
    "License",
    "RelatedResource",
    "SoftwareMetadata",
]
