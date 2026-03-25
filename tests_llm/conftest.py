import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def pytest_addoption(parser):
    parser.addoption(
        "--llm-model",
        default="openrouter/google/gemini-2.5-pro", #FIXME: configure this
        help="LLM model string to use for ai_convert tests (default: openrouter/openai/gpt-4o)",
    )


@pytest.fixture(scope="session")
def llm_model(request):
    return request.config.getoption("--llm-model")


def discover_test_files(test_data_dir: Path, model_name: str, specifier: str):
    folder = test_data_dir / model_name / specifier
    file_patterns = ["*.json", "*.yml", "*.yaml", "*.cff"]
    files = []
    for pattern in file_patterns:
        files.extend(folder.glob(pattern))
    return files
