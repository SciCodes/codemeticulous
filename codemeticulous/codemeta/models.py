from __future__ import annotations

from typing import TypeAlias

from pydantic import Field
from pydantic_codemeta import (
    CodeMetaV3 as ProviderCodeMetaV3,
    Organization,
    Person,
    Role,
)


class CodeMetaV3(ProviderCodeMetaV3):
    """CodeMeta v3 model requiring the schema's name property."""

    name: str = Field(...)


Actor: TypeAlias = Role | Person | Organization
ActorList: TypeAlias = list[Actor]
ActorListOrSingle: TypeAlias = Actor | ActorList


__all__ = ["Actor", "ActorList", "ActorListOrSingle", "CodeMetaV3"]
