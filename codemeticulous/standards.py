from codemeticulous.cff import CitationFileFormat, software_metadata_to_cff
from codemeticulous.codemeta import (
    CodeMetaV3,
    codemeta_to_software_metadata,
    software_metadata_to_codemeta,
)
from codemeticulous.datacite import DataCite, software_metadata_to_datacite

STANDARDS = {
    "codemeta": {
        "model": CodeMetaV3,
        "format": "json",
        "to_canonical": codemeta_to_software_metadata,
        "from_canonical": software_metadata_to_codemeta,
    },
    "datacite": {
        "model": DataCite,
        "format": "json",
        "from_canonical": software_metadata_to_datacite,
    },
    "cff": {
        "model": CitationFileFormat,
        "format": "yaml",
        "from_canonical": software_metadata_to_cff,
    },
}
