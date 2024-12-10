from datetime import date, datetime
from urllib.parse import urlparse


def map_dict_keys(d: dict, key_map: dict):
    """recursively map keys in a dictionary based on a given key map"""
    return _map_keys(d, key_map)


def _map_keys(obj, key_map: dict):
    if isinstance(obj, dict):
        return {key_map.get(k, k): _map_keys(v, key_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_map_keys(v, key_map) for v in obj]
    return obj


def get_first_if_list(value):
    """return the first element of a list, or the value if it is not a list"""
    if isinstance(value, list):
        return value[0]
    return value


def get_first_if_single_list(value):
    """return the first element of a list if it is a single-element list,
    or the value if it is not, including if it is a multi-element list
    """
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def ensure_list(value):
    """return a list containing the value if it is not a list,
    or the value if it is already a list"""
    if isinstance(value, list):
        return value
    elif value is None:
        return []
    return [value]


def is_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def parse_dict_dates(obj):
    """recursively convert date and datetime objects to ISO format strings"""
    if isinstance(obj, dict):
        return {k: parse_dict_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [parse_dict_dates(v) for v in obj]
    elif isinstance(obj, str):
        try:
            if "T" in obj:  # possibly a datetime
                return datetime.fromisoformat(obj)
            else:  # possibly a date
                return date.fromisoformat(obj)
        except ValueError:
            pass  # not a date
    return obj
