import json
import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LOGS_DIR = Path(__file__).parent / "logs"


@pytest.fixture
def run_log(llm_model):
    results = []
    yield results

    LOGS_DIR.mkdir(exist_ok=True)
    model_name = llm_model.replace("/", "-")
    json_path = LOGS_DIR / f"{model_name}.json"

    existing = json.loads(json_path.read_text()) if json_path.exists() else []
    existing.extend(results)
    json_path.write_text(json.dumps(existing, indent=2))


def discover_test_files(test_data_dir: Path, model_name: str, specifier: str):
    folder = test_data_dir / model_name / specifier
    file_patterns = ["*.json", "*.yml", "*.yaml", "*.cff"]
    files = []
    for pattern in file_patterns:
        files.extend(folder.glob(pattern))
    return files
