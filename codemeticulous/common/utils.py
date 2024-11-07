def map_dict_keys(d: dict, key_map: dict):
    return _map_keys(d, key_map)


def _map_keys(obj, key_map: dict):
    if isinstance(obj, dict):
        return {key_map.get(k, k): _map_keys(v, key_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_map_keys(v, key_map) for v in obj]
    return obj


def get_first_if_list(value):
    if isinstance(value, list):
        return value[0]
    return value


def make_list_if_single(value):
    if isinstance(value, list):
        return value
    elif value is None:
        return []
    return [value]
