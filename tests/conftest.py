import pytest
import json
import yaml
from pathlib import Path
from typing import Any, Literal

from codemeticulous.codemeta.models import CodeMeta
from codemeticulous.cff.models import CitationFileFormat

MODEL_MAP: dict[str, Any] = {
    "codemeta": CodeMeta,
    "cff": CitationFileFormat,
}


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    return Path(__file__).parent / "data"


def load_file(file_path: Path) -> tuple[Any, Literal["json", "yaml"]]:
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix in [".json", ".expected"]:
            return json.load(f), "json"
        elif file_path.suffix in [".yml", ".yaml", ".cff"]:
            return yaml.safe_load(f), "yaml"
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")


def discover_test_files(test_data_dir: Path, model_name: str, specifier: str):
    folder = test_data_dir / model_name / specifier
    file_patterns = ["*.json", "*.yml", "*.yaml", "*.cff"]
    files = []
    for pattern in file_patterns:
        files.extend(folder.glob(pattern))
    return files


@pytest.fixture
def load_model_data():
    def _load(model_name: str, file_path: Path):
        model_class = MODEL_MAP.get(model_name)
        if model_class is None:
            raise ValueError(f"Model '{model_name}' is not defined in MODEL_MAP.")
        data, file_type = load_file(file_path)
        return model_class, data, file_type

    return _load
