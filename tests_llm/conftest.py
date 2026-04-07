import csv
import pytest
from datetime import datetime
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
    log_path = LOGS_DIR / f"{model_name}.csv"

    write_header = not log_path.exists()
    with open(log_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "model", "source", "target", "file", "runtime", "passed", "violations", "logical", "llm"])
        if write_header:
            writer.writeheader()
        writer.writerows(results)


def discover_test_files(test_data_dir: Path, model_name: str, specifier: str):
    folder = test_data_dir / model_name / specifier
    file_patterns = ["*.json", "*.yml", "*.yaml", "*.cff"]
    files = []
    for pattern in file_patterns:
        files.extend(folder.glob(pattern))
    return files
