from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class _ConversionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConversionIssue(_ConversionModel):
    path: str
    message: str


T = TypeVar("T")


class ConversionResult(_ConversionModel, Generic[T]):
    value: T
    issues: tuple[ConversionIssue, ...] = ()


class ConversionError(ValueError):
    """Raised when a conversion cannot produce canonical metadata."""


__all__ = ["ConversionError", "ConversionIssue", "ConversionResult"]
