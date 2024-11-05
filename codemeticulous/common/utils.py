def map_dict_keys(d: dict, key_map: dict):
    return _map_keys(d, key_map)


def _map_keys(obj, key_map: dict):
    if isinstance(obj, dict):
        return {key_map.get(k, k): _map_keys(v, key_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_map_keys(v, key_map) for v in obj]
    return obj
