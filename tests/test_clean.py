import json
from pathlib import Path

from .conftest import MODEL_MAP, discover_test_files, load_file


def pytest_generate_tests(metafunc):
    if "clean_test_case" in metafunc.fixturenames:
        test_cases = []
        test_ids = []
        test_data_dir = Path(__file__).parent / "data"
        for model_name in MODEL_MAP.keys():
            clean_files = discover_test_files(test_data_dir, model_name, "clean")
            # filter out expected files
            input_files = [f for f in clean_files if not f.stem.endswith(".expected")]
            for input_file in input_files:
                # expected file has the same stem with .expected before the extension
                expected_file = input_file.with_name(
                    f"{input_file.stem}.expected{input_file.suffix}"
                )
                if expected_file.exists():
                    test_cases.append((model_name, input_file, expected_file))
                    test_ids.append(f"{model_name}/clean/{input_file.name}")
                else:
                    raise FileNotFoundError(
                        f"Expected file '{expected_file}' not found for input '{input_file}'"
                    )
        metafunc.parametrize("clean_test_case", test_cases, ids=test_ids)


def test_clean(clean_test_case, load_model_data):
    model_name, input_file, expected_file = clean_test_case
    model_class, input_data = load_model_data(model_name, input_file)
    expected_data = load_file(expected_file)
    model_instance = model_class(**input_data)
    serialized_data = json.loads(model_instance.json())
    assert serialized_data == expected_data
