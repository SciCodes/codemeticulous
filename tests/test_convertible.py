from pathlib import Path

from codemeticulous.convert import convert
from .conftest import discover_test_files

CONVERSION_MAP = {
    "codemeta": {
        "cff": [
            # cff requires authors
            "codemetar.json",
            "context.json",
            "creator.json",
        ],
        "datacite": [
            # datacite metadata requires creators, title, publisher, publication year
            "chime.json",
        ],
    }
}


def pytest_generate_tests(metafunc):
    if "conversion_test_case" in metafunc.fixturenames:
        test_cases = []
        test_ids = []
        test_data_dir = Path(__file__).parent / "data"

        for source_name, target_maps in CONVERSION_MAP.items():
            for subdir in ["valid", "clean"]:
                input_files = discover_test_files(test_data_dir, source_name, subdir)
                for target_name, convertible_files in target_maps.items():
                    for file_path in input_files:
                        if not convertible_files or file_path.name in convertible_files:
                            test_cases.append((source_name, target_name, file_path))
                            test_ids.append(
                                f"convert {source_name} -> {target_name} ({file_path.name})"
                            )
        metafunc.parametrize("conversion_test_case", test_cases, ids=test_ids)


def test_conversion(conversion_test_case, load_model_data):
    source_name, target_name, file_path = conversion_test_case
    source_class, data, _ = load_model_data(source_name, file_path)
    source_instance = source_class(**data)
    # should succeed
    convert(source_name, target_name, source_instance)
