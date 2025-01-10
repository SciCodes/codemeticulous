import yaml
import json

from .utils import parse_dict_dates


class ByAliasExcludeNoneMixin:
    def dict(self, serialize=False):
        """Return a dictionary representation of the object

        If serialize is False, this will include some unserializable objects
        like datetimes. If serialize is True, it will return a dictionary that
        has been serialized to json and then back
        """
        if serialize:
            return json.loads(self.json())
        if hasattr(self, "model_dump"):
            return self.model_dump(by_alias=True, exclude_none=True)
        return super().dict(by_alias=True, exclude_none=True)

    def json(self):
        """return a serialized json string representation of the object"""
        if hasattr(self, "model_dump_json"):
            return self.model_dump_json(by_alias=True, exclude_none=True)
        return super().json(by_alias=True, exclude_none=True)

    def yaml(self):
        """return a serialized yaml string representation of the object"""
        json_dict = json.loads(self.json())
        return yaml.dump(parse_dict_dates(json_dict), sort_keys=False)
