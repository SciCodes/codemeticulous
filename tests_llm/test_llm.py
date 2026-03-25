import json
from pytest_check import check
from pathlib import Path

from .conftest import discover_test_files
from codemeticulous.convert import convert
from codemeticulous.ai_convert import convert_ai

# NOTE: testing is currently configured to only evaluate converting from codemeta
TEST_DATA_DIR = Path(__file__).parent.parent / "tests" / "data"

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
    if "ai_test_case" in metafunc.fixturenames:
        test_cases = []
        test_ids = []

        for source_format, target_maps in CONVERSION_MAP.items(): # just codemeta -> other formats
            input_files = []
            for subdir in ["valid", "clean"]:
                input_files.extend(discover_test_files(TEST_DATA_DIR, source_format, subdir))
            for target_name, convertible_files in target_maps.items():
                for file_path in input_files:
                    if file_path.name in convertible_files:
                        test_cases.append((source_format, target_name, file_path))
                        test_ids.append(f"convert {source_format} -> {target_name} ({file_path.name})")

        metafunc.parametrize("ai_test_case", test_cases, ids=test_ids)


def fields_are_superset(baseline: dict, ai_result: dict, path: str = "") -> list[str]:
    diffs = []

    for key, baseline_val in baseline.items():
        full_path = f"{path}.{key}" if path else key

        # 1st check to see if any fields in logical convesion isn't in the llm's conversion
        if key not in ai_result:
            diffs.append(f"Missing field '{full_path}' in AI conversion")
            continue
        ai_val = ai_result[key]
        if isinstance(baseline_val, dict) and isinstance(ai_val, dict):
            diffs.extend(fields_are_superset(baseline_val, ai_val, full_path))
        elif isinstance(baseline_val, list) and isinstance(ai_val, list):
            for i, b_item in enumerate(baseline_val):
                item_path = f"{full_path}[{i}]"
                if isinstance(b_item, dict):
                    matched = any(
                        not fields_are_superset(b_item, a_item) # ignores priority in lists for certain fields
                        for a_item in ai_val
                        if isinstance(a_item, dict)
                    )
                    if not matched:
                        diffs.append(
                            f"No match found in AI result for baseline item at '{item_path}':\n"
                            f"    baseline: {b_item}\n"
                            f"    ai result: {ai_val}"
                        )
                else:
                    if b_item not in ai_val:
                        diffs.append(
                            f"Baseline value at '{item_path}' not found in AI result list:\n"
                            f"    baseline: {b_item!r}\n"
                            f"    ai result: {ai_val!r}"
                        )
    return diffs


# FIXME: refactor to implement soft assert some complex fields, display diff for manual review
def test_ai_convert(ai_test_case, llm_model):
    source_format, target_format, file_path = ai_test_case

    print(f"Testing conversion from {source_format} to {target_format} with {file_path}")

    with open(file_path, "r") as f:
        source_data = json.load(f)

    baseline = convert(source_format, target_format, source_data)
    ai_result = convert_ai(llm_model, source_format, target_format, source_data)

    assert ai_result is not None, "AI conversion returned None"

    baseline_dict = baseline.dict(serialize=True)
    ai_dict = ai_result.dict(serialize=True)

    print(ai_dict)

    violations = fields_are_superset(baseline_dict, ai_dict)
    assert not violations, (
        f"AI result for '{file_path.name}' ({source_format} -> {target_format}) is missing {len(violations)} baseline fields:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
