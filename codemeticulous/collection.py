from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from codemeticulous.models import SoftwareMetadata

CollectionStatus = Literal[
    "retrieved",
    "inferred",
    "ambiguous",
    "conflicting",
    "missing",
]
AcquisitionMethod = Literal["retrieved", "inferred"]

_FIELD_PATH = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])*(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])*)*$"
)
_SEGMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(.*)$")
_INDEX = re.compile(r"\[(\d+)\]")
_MISSING = object()


class _CollectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceReference(_CollectionModel):
    """A retrieved source made available to a metadata collector."""

    id: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    retrieved_at: datetime
    media_type: str | None = None
    object_version: str | None = None
    content_hash: str | None = None


class Evidence(_CollectionModel):
    """A normalized candidate value tied to a retrieved source."""

    source_id: str = Field(min_length=1)
    value: JsonValue
    acquisition: AcquisitionMethod
    selector: str | None = None
    raw_value: JsonValue | None = None
    reasoning: str | None = None

    @model_validator(mode="after")
    def require_inference_reasoning(self) -> Self:
        if self.acquisition == "inferred" and not (
            self.reasoning and self.reasoning.strip()
        ):
            raise ValueError("inferred evidence requires reasoning")
        return self


class FieldCollection(_CollectionModel):
    """Provenance and selection state for one canonical metadata field."""

    path: str = Field(min_length=1)
    status: CollectionStatus
    evidence: tuple[Evidence, ...] = ()
    selected_evidence: int | None = None
    authority_rule: str | None = None

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        if not _FIELD_PATH.fullmatch(self.path):
            raise ValueError(f"invalid canonical field path: {self.path}")

        if self.selected_evidence is not None and not (
            0 <= self.selected_evidence < len(self.evidence)
        ):
            raise ValueError("selected_evidence does not reference an evidence item")

        if self.status == "missing":
            if self.evidence or self.selected_evidence is not None:
                raise ValueError("missing fields cannot contain or select evidence")
            return self

        if not self.evidence:
            raise ValueError(f"{self.status} fields require evidence")

        if self.status == "ambiguous" and self.selected_evidence is not None:
            raise ValueError("ambiguous fields cannot select evidence")

        if self.status in {"retrieved", "inferred", "conflicting"}:
            if self.selected_evidence is None:
                raise ValueError(f"{self.status} fields require selected evidence")

        if self.status == "retrieved":
            selected = self.evidence[self.selected_evidence]  # type: ignore[index]
            if selected.acquisition != "retrieved":
                raise ValueError("retrieved fields must select retrieved evidence")

        if self.status == "inferred":
            selected = self.evidence[self.selected_evidence]  # type: ignore[index]
            if selected.acquisition != "inferred":
                raise ValueError("inferred fields must select inferred evidence")

        if self.status == "conflicting":
            distinct_values = {
                json.dumps(item.value, sort_keys=True, separators=(",", ":"))
                for item in self.evidence
            }
            if len(distinct_values) < 2:
                raise ValueError("conflicting fields require distinct candidate values")
            if not (self.authority_rule and self.authority_rule.strip()):
                raise ValueError("conflicting fields require an authority rule")

        return self


class CollectedSoftwareMetadata(_CollectionModel):
    """Canonical software metadata together with auditable field evidence."""

    metadata: SoftwareMetadata
    sources: tuple[SourceReference, ...] = Field(min_length=1)
    fields: tuple[FieldCollection, ...] = Field(min_length=1)
    requested_identifier: str | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source IDs must be unique")

        field_paths = [field.path for field in self.fields]
        if len(field_paths) != len(set(field_paths)):
            raise ValueError("canonical field paths must be unique")

        known_sources = set(source_ids)
        metadata = self.metadata.model_dump(
            mode="json", exclude_none=True, exclude_defaults=True
        )

        selected_paths: list[str] = []
        for field in self.fields:
            unknown_sources = {
                item.source_id
                for item in field.evidence
                if item.source_id not in known_sources
            }
            if unknown_sources:
                names = ", ".join(sorted(unknown_sources))
                raise ValueError(
                    f"field {field.path} references unknown sources: {names}"
                )

            canonical_value = _resolve_path(metadata, field.path)
            if field.status == "missing":
                if canonical_value not in (_MISSING, None, "", [], {}):
                    raise ValueError(
                        f"missing field {field.path} is populated in SoftwareMetadata"
                    )
                continue

            if field.selected_evidence is None:
                if canonical_value not in (_MISSING, None, "", [], {}):
                    raise ValueError(
                        f"unselected field {field.path} is populated in SoftwareMetadata"
                    )
                continue

            if canonical_value is _MISSING:
                raise ValueError(
                    f"selected field {field.path} does not exist in SoftwareMetadata"
                )
            selected_value = field.evidence[field.selected_evidence].value
            if selected_value != canonical_value:
                raise ValueError(
                    f"selected evidence for {field.path} does not match SoftwareMetadata"
                )
            selected_paths.append(field.path)

        uncovered = sorted(
            path
            for path in _leaf_paths(metadata)
            if not any(_path_covers(selected, path) for selected in selected_paths)
        )
        if uncovered:
            raise ValueError(
                "populated SoftwareMetadata fields lack selected provenance: "
                + ", ".join(uncovered)
            )
        return self


def validate_collection(
    value: CollectedSoftwareMetadata | Mapping[str, Any],
) -> CollectedSoftwareMetadata:
    """Validate provider output against the structured collection contract."""

    if isinstance(value, CollectedSoftwareMetadata):
        return value
    return CollectedSoftwareMetadata.model_validate(dict(value))


def collection_json_schema() -> dict[str, Any]:
    """Return the provider-neutral JSON schema for structured collection."""

    return CollectedSoftwareMetadata.model_json_schema()


def _resolve_path(value: Any, path: str) -> Any:
    current = value
    for segment in path.split("."):
        match = _SEGMENT.fullmatch(segment)
        if match is None or not isinstance(current, Mapping):
            return _MISSING
        name, indexes = match.groups()
        if name not in current:
            return _MISSING
        current = current[name]
        position = 0
        for index_match in _INDEX.finditer(indexes):
            if index_match.start() != position:
                return _MISSING
            index = int(index_match.group(1))
            if not isinstance(current, list) or index >= len(current):
                return _MISSING
            current = current[index]
            position = index_match.end()
        if position != len(indexes):
            return _MISSING
    return current


def _leaf_paths(value: Any, prefix: str = "") -> set[str]:
    if isinstance(value, Mapping):
        paths: set[str] = set()
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            paths.update(_leaf_paths(item, child))
        return paths or ({prefix} if prefix else set())
    if isinstance(value, list):
        paths = set()
        for index, item in enumerate(value):
            paths.update(_leaf_paths(item, f"{prefix}[{index}]"))
        return paths or ({prefix} if prefix else set())
    return {prefix} if prefix else set()


def _path_covers(parent: str, child: str) -> bool:
    return (
        child == parent
        or child.startswith(parent + ".")
        or child.startswith(parent + "[")
    )


__all__ = [
    "AcquisitionMethod",
    "CollectedSoftwareMetadata",
    "CollectionStatus",
    "Evidence",
    "FieldCollection",
    "SourceReference",
    "collection_json_schema",
    "validate_collection",
]
