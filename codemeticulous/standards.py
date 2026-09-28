"""Models and serialization formats supported by experimental AI conversion."""

from codemeticulous.cff.models import CitationFileFormat
from codemeticulous.codemeta.models import CodeMetaV3
from codemeticulous.datacite.models import DataCite

STANDARDS = {
    "codemeta": {
        "model": CodeMetaV3,
        "format": "json",
        "schema": None,
    },
    "datacite": {
        "model": DataCite,
        "format": "json",
        "schema": "schema/datacite/schema46.json",
    },
    "cff": {
        "model": CitationFileFormat,
        "format": "yaml",
        "schema": "schema/cff/1.2.0/schema.json",
    },
}
