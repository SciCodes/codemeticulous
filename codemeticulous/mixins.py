import yaml
import json

from .utils import parse_dict_dates


class ByAliasExcludeNoneMixin:
    def dict(self):
        if hasattr(self, "model_dump"):
            return self.model_dump(by_alias=True, exclude_none=True)
        return super().dict(by_alias=True, exclude_none=True)

    def json(self):
        if hasattr(self, "model_dump_json"):
            return self.model_dump_json(by_alias=True, exclude_none=True)
        return super().json(by_alias=True, exclude_none=True)

    def yaml(self):
        json_dict = json.loads(self.json())
        return yaml.dump(parse_dict_dates(json_dict), sort_keys=False)
