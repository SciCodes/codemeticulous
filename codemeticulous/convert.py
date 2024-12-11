from codemeticulous.codemeta.models import CodeMeta
from codemeticulous.datacite.models import DataciteV45
from codemeticulous.cff.models import CitationFileFormat
from codemeticulous.codemeta.convert import canonical_to_codemeta, codemeta_to_canonical
from codemeticulous.datacite.convert import canonical_to_datacite, datacite_to_canonical
from codemeticulous.cff.convert import canonical_to_cff, cff_to_canonical


STANDARDS = {
    "codemeta": {
        "model": CodeMeta,
        "format": "json",
        "to_canonical": codemeta_to_canonical,
        "from_canonical": canonical_to_codemeta,
    },
    "datacite": {
        "model": DataciteV45,
        "format": "json",
        "to_canonical": datacite_to_canonical,
        "from_canonical": canonical_to_datacite,
    },
    "cff": {
        "model": CitationFileFormat,
        "format": "yaml",
        "to_canonical": cff_to_canonical,
        "from_canonical": canonical_to_cff,
    },
}


def to_canonical(source_format: str, source_data):
    source_model = STANDARDS[source_format]["model"]
    if isinstance(source_data, dict):
        source_instance = source_model(**source_data)
    elif isinstance(source_data, source_model):
        source_instance = source_data

    source_to_canonical = STANDARDS[source_format]["to_canonical"]
    canonical_instance = source_to_canonical(source_instance)

    return canonical_instance


def from_canonical(target_format: str, canonical_instance, **custom_fields):
    canonical_to_target = STANDARDS[target_format]["from_canonical"]
    target_instance = canonical_to_target(canonical_instance, **custom_fields)

    return target_instance


def convert(source_format: str, target_format: str, source_data, **custom_fields):
    """
    Convert from one metadata standard to another, through the canonical representation.

    Args:
    - source_format: string representation of the source metadata standard. Currently supported: "codemeta"
    - target_format: string representation of the target metadata standard. Currently supported: "codemeta", "datacite", "cff"
    - source_data: dict or pydantic.BaseModel instance representing the source metadata
    - custom_fields: additional fields to add to the target metadata instance
    """
    canonical_instance = to_canonical(source_format, source_data)
    return from_canonical(target_format, canonical_instance, **custom_fields)
