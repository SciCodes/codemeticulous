import json
from pathlib import Path

import yaml

from .conftest import STANDARDS, discover_test_files


def pytest_generate_tests(metafunc):
    if "valid_test_case" in metafunc.fixturenames:
        test_cases = []
        test_ids = []
        test_data_dir = Path(__file__).parent / "data"
        for model_name in STANDARDS.keys():
            valid_files = discover_test_files(test_data_dir, model_name, "valid")
            for file_path in valid_files:
                test_cases.append((model_name, file_path))
                test_ids.append(f"{model_name}/valid/{file_path.name}")
        metafunc.parametrize("valid_test_case", test_cases, ids=test_ids)


def test_valid(valid_test_case, load_model_data):
    model_name, file_path = valid_test_case
    model_class, data, file_type = load_model_data(model_name, file_path)
    model_instance = model_class(**data)
    # if the file type was json, compare with the json representation
    if file_type == "json":
        serialized_data = json.loads(model_instance.json())
    # if the file type was yaml, compare with the yaml representation,
    # mostly for the yaml dates
    elif file_type == "yaml":
        serialized_data = yaml.safe_load(model_instance.yaml())
    assert serialized_data == data
