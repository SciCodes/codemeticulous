import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from .conftest import VALIDATION_MODELS, discover_test_files


def _test_cases(specifier: str) -> list:
    test_data_dir = Path(__file__).parent / "data"
    return [
        pytest.param(
            model_name,
            file_path,
            id=f"{model_name}/{specifier}/{file_path.name}",
        )
        for model_name in VALIDATION_MODELS
        for file_path in discover_test_files(test_data_dir, model_name, specifier)
    ]


@pytest.mark.parametrize(("model_name", "file_path"), _test_cases("valid"))
def test_valid_fixture(model_name, file_path, load_model_data) -> None:
    model_class, data, file_type = load_model_data(model_name, file_path)
    model_instance = model_class(**data)

    if file_type == "json":
        serialized_data = json.loads(
            model_instance.model_dump_json(by_alias=True, exclude_none=True)
        )
    else:
        serialized_data = yaml.safe_load(model_instance.yaml())

    assert serialized_data == data


@pytest.mark.parametrize(("model_name", "file_path"), _test_cases("invalid"))
def test_invalid_fixture(model_name, file_path, load_model_data) -> None:
    model_class, data, _ = load_model_data(model_name, file_path)

    with pytest.raises(ValidationError):
        model_class(**data)
