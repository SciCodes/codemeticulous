from codemeticulous.codemeta.models import CodeMeta
from codemeticulous.datacite.models import DataCite
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
        "model": DataCite,
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