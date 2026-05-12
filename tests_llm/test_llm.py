import json
import re
import time
from pathlib import Path
from datetime import datetime

from .conftest import discover_test_files
from codemeticulous.convert import convert
from codemeticulous.ai_convert import convert_ai

# NOTE: testing is configured to only evaluate conversion from codemeta to compare against logical conversion
TEST_DATA_DIR = Path(__file__).parent.parent / "tests" / "data"

CONVERSION_MAP = {
    "codemeta": {
        "cff": [ # cff requires authors
            "codemetar.json",
            # "context.json",
            # "creator.json",
            # "chime.json"
        ],
        "datacite": [ # datacite metadata requires creators, title, publisher, publication year
            "chime.json",
            "artificial-anasazi.json",
            # "invenordm.json"
        ],
    }
}

PROVIDER_CONFIG = {
    "openrouter_llm": {
        "prefix": "openrouter/",
        "models": [
            # Advanced
            "google/gemini-2.5-pro",
            "openai/gpt-4o",
            "anthropic/claude-sonnet-4-6",
            "mistralai/mistral-large",
            # "deepseek/deepseek-chat",
            # Mid-tier
            # "google/gemini-2.0-flash-001",
            # "openai/gpt-4o-mini",
            # "qwen/qwen-2.5-72b-instruct",
            # "meta-llama/llama-3.3-70b-instruct",
            # Lightweight
            # "anthropic/claude-haiku-4-5",
        ]
    },
}


def pytest_generate_tests(metafunc):
    if "llm_model" in metafunc.fixturenames:
        models = [
            provider["prefix"] + model
            for provider in PROVIDER_CONFIG.values()
            for model in provider["models"]
        ]
        metafunc.parametrize("llm_model", models, ids=models)

    if "test_case" in metafunc.fixturenames:
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

        metafunc.parametrize("test_case", test_cases, ids=test_ids)


def fields_are_superset(baseline: dict, ai_result: dict, path: str = "") -> list[dict]:
    diffs = []

    for key, baseline_val in baseline.items():
        full_path = f"{path}.{key}" if path else key

        # 1st check to see if any fields in logical conversion isn't in the llm's conversion
        if key not in ai_result:
            diffs.append({
                "description": f"Missing field '{full_path}'",
                "logical": str(baseline_val),
                "llm": "(missing)",
            })
            continue

        ai_val = ai_result[key]

        if isinstance(baseline_val, dict) and isinstance(ai_val, dict):
            diffs.extend(fields_are_superset(baseline_val, ai_val, full_path))
        elif isinstance(baseline_val, list) and isinstance(ai_val, list):
            for i, b_item in enumerate(baseline_val):
                item_path = f"{full_path}[{i}]"
                if isinstance(b_item, dict):
                    matched = any(
                        not fields_are_superset(b_item, a_item)  # ignores priority in lists for certain fields
                        for a_item in ai_val
                        if isinstance(a_item, dict)
                    )
                    if not matched:
                        ai_dicts = [a for a in ai_val if isinstance(a, dict)]
                        if ai_dicts:
                            closest = min(ai_dicts, key=lambda a: len(fields_are_superset(b_item, a)))
                            sub_diffs = fields_are_superset(b_item, closest, item_path)
                            diffs.extend(sub_diffs)
                        else:
                            diffs.append({
                                "description": f"No dict items in LLM result for '{item_path}'",
                                "logical": str(b_item),
                                "llm": str(ai_val),
                            })
                else:  # deals with all other types other than dicts
                    if b_item not in ai_val:
                        diffs.append({
                            "description": f"Value at '{item_path}' doesn't match",
                            "logical": repr(b_item),
                            "llm": repr(ai_val),
                        })
    return diffs


def test_ai_convert(test_case, llm_model, run_log):
    source_format, target_format, file_path = test_case

    print(f"\n{llm_model} conversion from {source_format} to {target_format} with {file_path}")

    with open(file_path, "r") as f:
        source_data = json.load(f)

    baseline = convert(source_format, target_format, source_data)

    # track runtime per ai conversion
    start = time.time()
    llm_result, usage = convert_ai(llm_model, source_format, target_format, source_data) # note that if llm times out after 3 attempts, it won't be logged
    elapsed = round(time.time() - start, 2)

    assert llm_result is not None, "LLM conversion returned None"

    baseline_dict = baseline.dict(serialize=True)
    ai_dict = llm_result.dict(serialize=True)

    violations = fields_are_superset(baseline_dict, ai_dict)

    # grouping violations by top-level field name from the description
    violations_by_field: dict[str, list] = {}
    for v in violations:
        m = re.search(r"'([^']+)'", v["description"])
        top_field = re.split(r"[.\[]", m.group(1))[0] if m else "unknown"
        violations_by_field.setdefault(top_field, []).append(v)

    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file": file_path.name,
        "source:target": f"{source_format}:{target_format}",
        "runtime_sec": elapsed,
        # "cost": usage["cost"],
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "passed": len(violations) == 0,
    }

    # logs only top level fields that have differences from logical conversion
    for field, baseline_val in baseline_dict.items():
        field_violations = violations_by_field.get(field, [])
        if not field_violations:
            continue
        entry[f"{source_format}:{field}"] = {
            "target": f"{target_format}:{field}",
            "violations": [
                {
                    "desc": v["description"],
                    "expected": v["logical"],
                    "llm_output": v["llm"],
                }
                for v in field_violations
            ],
        }

    run_log.append(entry)

    # add full llm outputs that passed into a seperate log dump
    if len(violations) == 0:
        path = Path(__file__).parent / "logs" / "passed_cases.json"
        raw = path.read_text() if path.exists() else ""
        existing = json.loads(raw) if raw.strip() else []

        passed_case = {
            "file": file_path.name,
            "source:target": f"{source_format}:{target_format}",
            "source_metadata": source_data,
            "llm_output": ai_dict
        }

        existing.append(passed_case)
        path.write_text(json.dumps(existing, indent=2))

    assert not violations, (
        f"LLM result for '{file_path.name}' ({source_format} -> {target_format}) is missing {len(violations)} logical conversion fields:\n"
        + "\n\n".join(
            f"  {i+1}. {v['description']}\n"
            f"      logical: {v['logical']}\n"
            f"      llm:     {v['llm']}"
            for i, v in enumerate(violations)
        )
    )

