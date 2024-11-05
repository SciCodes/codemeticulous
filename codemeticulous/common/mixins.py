class ByAliasExcludeNoneMixin:
    def dict(self):
        return super().dict(by_alias=True, exclude_none=True)

    def json(self):
        return super().json(by_alias=True, exclude_none=True)
