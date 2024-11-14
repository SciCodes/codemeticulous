import pytest
from pathlib import Path
from pydantic.v1 import ValidationError

from .conftest import MODEL_MAP, discover_test_files


def pytest_generate_tests(metafunc):
    if "invalid_test_case" in metafunc.fixturenames:
        test_cases = []
        test_ids = []
        test_data_dir = Path(__file__).parent / "data"
        for model_name in MODEL_MAP.keys():
            invalid_files = discover_test_files(test_data_dir, model_name, "invalid")
            for file_path in invalid_files:
                test_cases.append((model_name, file_path))
                test_ids.append(f"{model_name}/invalid/{file_path.name}")
        metafunc.parametrize("invalid_test_case", test_cases, ids=test_ids)


def test_invalid(invalid_test_case, load_model_data):
    model_name, file_path = invalid_test_case
    model_class, data = load_model_data(model_name, file_path)
    with pytest.raises(ValidationError):
        model_class(**data)
