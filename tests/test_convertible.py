from pathlib import Path

from codemeticulous.cff.convert import codemeta_to_cff
from codemeticulous.datacite.convert import codemeta_to_datacite  # , cff_to_codemeta
from .conftest import discover_test_files

CONVERSION_MAP = {
    "codemeta": {
        "cff": {
            "func": codemeta_to_cff,
            # cff requires authors
            "files": [
                "codemetar.json",
                "context.json",
                "creator.json",
            ],
        },
        "datacite": {
            "func": codemeta_to_datacite,
            # datacite metadata requires creators, title, publisher, publication year
            "files": [
                "chime.json",
            ],
        },
    }
    # "cff": [cff_to_codemeta],
}


def pytest_generate_tests(metafunc):
    if "conversion_test_case" in metafunc.fixturenames:
        test_cases = []
        test_ids = []
        test_data_dir = Path(__file__).parent / "data"

        for model_name, functions_map in CONVERSION_MAP.items():
            for subdir in ["valid", "clean"]:
                input_files = discover_test_files(test_data_dir, model_name, subdir)
                for function_name, function_details in functions_map.items():
                    conversion_function = function_details.get("func")
                    compatible_files = function_details.get("files", [])
                    for file_path in input_files:
                        if not compatible_files or file_path.name in compatible_files:
                            test_cases.append(
                                (model_name, conversion_function, file_path)
                            )
                            test_ids.append(
                                f"{function_name}({model_name}/{subdir}/{file_path.name})"
                            )
        metafunc.parametrize("conversion_test_case", test_cases, ids=test_ids)


def test_conversion(conversion_test_case, load_model_data):
    model_name, conversion_function, file_path = conversion_test_case
    model_class, data, _ = load_model_data(model_name, file_path)
    model_instance = model_class(**data)
    # should succeed
    conversion_function(model_instance)
