from codemeticulous.codemeta.models import CodeMeta


class CanonicalCodeMeta(CodeMeta):
    """
    CodeMeta extension used as an internal, canonical data model to prevent ambiguity and lossiness

    Anything that can be lost in translation from one format to another should be captured here
    """

    pass
