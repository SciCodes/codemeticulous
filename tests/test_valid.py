import json
from pathlib import Path

from .conftest import MODEL_MAP, discover_test_files


def pytest_generate_tests(metafunc):
    if "valid_test_case" in metafunc.fixturenames:
        test_cases = []
        test_ids = []
        test_data_dir = Path(__file__).parent / "data"
        for model_name in MODEL_MAP.keys():
            valid_files = discover_test_files(test_data_dir, model_name, "valid")
            for file_path in valid_files:
                test_cases.append((model_name, file_path))
                test_ids.append(f"{model_name}/valid/{file_path.name}")
        metafunc.parametrize("valid_test_case", test_cases, ids=test_ids)


def test_valid(valid_test_case, load_model_data):
    model_name, file_path = valid_test_case
    model_class, data = load_model_data(model_name, file_path)
    model_instance = model_class(**data)
    serialized_data = json.loads(model_instance.json())
    assert serialized_data == data
