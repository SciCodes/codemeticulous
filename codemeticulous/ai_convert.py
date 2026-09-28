"""Experimental metadata conversion through a configured LLM provider."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from codemeticulous.convert import VALIDATION_MODELS
from codemeticulous.generate_schemas import check_schema

logger = logging.getLogger(__name__)

PROMPT = """\
Convert the source metadata to the target format using the provided schemas.
Return only a JSON object that validates against the target Pydantic model.
Populate required fields and preserve source information where the target allows it.
"""


def build_prompt(source_schema: dict, target_schema: dict) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": "SOURCE SCHEMA:\n" + json.dumps(source_schema)},
        {"role": "user", "content": "TARGET SCHEMA:\n" + json.dumps(target_schema)},
    ]


def extract_json(llm_output: str) -> dict[str, Any]:
    """Read a JSON object, including one wrapped in a Markdown code fence."""
    text = llm_output.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


def structured_completion(
    llm_model: str, messages: list[dict[str, str]], target_model: type[BaseModel]
) -> tuple[BaseModel, dict[str, int]]:
    import litellm

    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    for attempt in range(3):
        response = litellm.completion(
            model=llm_model, messages=messages, temperature=0.3
        )
        response_usage = response.usage
        for key in usage:
            usage[key] += getattr(response_usage, key, 0) or 0

        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise ValueError("LLM response has no text content")
        output = extract_json(content)
        try:
            return target_model.model_validate(output), usage
        except ValidationError as exc:
            if attempt == 2:
                raise
            logger.warning("Target validation failed on attempt %s", attempt + 1)
            fields = [str(error["loc"][0]) for error in exc.errors() if error["loc"]]
            messages.extend(
                [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": (
                            "Correct only these invalid fields and return the full JSON object: "
                            + ", ".join(fields)
                            + "\nValidation errors:\n"
                            + str(exc)
                        ),
                    },
                ]
            )
    raise AssertionError("unreachable")


def convert_ai(
    llm_model: str,
    source_format: str,
    target_format: str,
    source_data: Mapping[str, Any] | BaseModel,
) -> tuple[BaseModel, dict[str, int]]:
    """Convert source metadata and return the target model with token usage."""
    source_model = VALIDATION_MODELS[source_format]
    target_model = VALIDATION_MODELS[target_format]
    if isinstance(source_data, Mapping):
        source = source_model.model_validate(source_data)
    elif isinstance(source_data, source_model):
        source = source_data
    else:
        raise TypeError(f"source_data must be a mapping or {source_model.__name__}")

    messages = build_prompt(check_schema(source_format), check_schema(target_format))
    messages.append(
        {
            "role": "user",
            "content": "SOURCE DATA:\n"
            + source.model_dump_json(by_alias=True, exclude_none=True),
        }
    )
    return structured_completion(llm_model, messages, target_model)
