from codemeticulous.models import CanonicalCodeMeta
from codemeticulous.codemeta.models import CodeMeta


def canonical_to_codemeta(data: CanonicalCodeMeta, **custom_fields) -> CodeMeta:
    return CodeMeta(**{**data.dict(), **custom_fields})


def codemeta_to_canonical(data: CodeMeta) -> CanonicalCodeMeta:
    return CanonicalCodeMeta(**data.dict())
