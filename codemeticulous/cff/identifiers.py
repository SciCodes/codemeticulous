"""Stable, descriptive names for generated CFF identifier models."""

from typing import TypeAlias

from .models import Identifier1, Identifier2, Identifier3, Identifier4


DoiIdentifier: TypeAlias = Identifier1
UrlIdentifier: TypeAlias = Identifier2
SwhIdentifier: TypeAlias = Identifier3
OtherIdentifier: TypeAlias = Identifier4

CffIdentifier: TypeAlias = (
    DoiIdentifier | UrlIdentifier | SwhIdentifier | OtherIdentifier
)

__all__ = [
    "CffIdentifier",
    "DoiIdentifier",
    "OtherIdentifier",
    "SwhIdentifier",
    "UrlIdentifier",
]
