from __future__ import annotations

import yaml
from pydantic import BaseModel

from codemeticulous.cff.models import CitationFileFormat
from codemeticulous.codemeta.models import CodeMetaV3
from codemeticulous.conversion import ConversionError
from codemeticulous.datacite.models import DataCite
from codemeticulous.datacite.xml import to_datacite_xml
from codemeticulous.formats import require_version


def serialize(value: BaseModel, format_name: str, version: str) -> str:
    normalized = require_version(format_name, version)
    if normalized == "codemeta":
        model = CodeMetaV3.model_validate(value, from_attributes=True)
        return model.model_dump_json(by_alias=True, exclude_none=True, indent=2)
    if normalized == "cff":
        model = CitationFileFormat.model_validate(value, from_attributes=True)
        return yaml.safe_dump(
            model.model_dump(by_alias=True, exclude_none=True, mode="json"),
            sort_keys=False,
        )
    if normalized == "datacite":
        model = DataCite.model_validate(value, from_attributes=True)
        return to_datacite_xml(model, version)
    if normalized == "software-metadata":
        return value.model_dump_json(exclude_none=True, indent=2)
    raise ConversionError(f"Unsupported format: {format_name}")


__all__ = ["serialize"]
