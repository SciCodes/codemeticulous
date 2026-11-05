from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from codemeticulous.cff.models import CitationFileFormat
from codemeticulous.codemeta.models import CodeMetaV3
from codemeticulous.conversion import ConversionError
from codemeticulous.datacite.xml import validate_datacite_xml
from codemeticulous.formats import require_version
from codemeticulous.models import SoftwareMetadata

VALIDATION_MODELS = {
    "codemeta": CodeMetaV3,
    "cff": CitationFileFormat,
    "software-metadata": SoftwareMetadata,
}


def validate_document(
    document: str | bytes | Mapping[str, Any], format_name: str, version: str
) -> None:
    normalized = require_version(format_name, version)
    if normalized == "datacite":
        if isinstance(document, Mapping):
            raise ValueError("DataCite validation expects an XML document")
        validate_datacite_xml(document, version)
        return

    try:
        if isinstance(document, Mapping):
            data = dict(document)
        elif normalized == "cff":
            data = yaml.safe_load(document)
        else:
            data = json.loads(document)
        VALIDATION_MODELS[normalized].model_validate(data)
    except (json.JSONDecodeError, yaml.YAMLError, ValidationError, TypeError) as exc:
        raise ValueError(f"Invalid {format_name} {version} document: {exc}") from exc


def validate_file(path: str | Path, format_name: str, version: str) -> None:
    try:
        document = Path(path).read_bytes()
    except OSError as exc:
        raise ValueError(f"Failed to load file: {path}. {exc}") from exc
    validate_document(document, format_name, version)


__all__ = ["validate_document", "validate_file"]
