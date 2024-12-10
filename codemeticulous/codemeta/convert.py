from codemeticulous.models import CanonicalCodeMeta
from codemeticulous.codemeta.models import CodeMeta


def canonical_to_codemeta(data: CanonicalCodeMeta) -> CodeMeta:
    return CodeMeta(**data.dict())


def codemeta_to_canonical(data: CodeMeta) -> CanonicalCodeMeta:
    return CanonicalCodeMeta(**data.dict())
