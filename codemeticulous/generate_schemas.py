"""Generate and load compact schema descriptions for AI prompts."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from codemeticulous.convert import VALIDATION_MODELS

CACHE_DIR = Path(__file__).parent.parent / "schema_cache"


def llm_descriptions(
    model_name: str, fields: list[list[str]], llm_model: str
) -> list[list[str]]:
    import litellm

    prompt = (
        f"Describe each field of the {model_name} Pydantic model. "
        "Return only a JSON array of [field_name, intuitive_type, brief_description] arrays, "
        "in the same order. Use plain names such as Text, URL, Date, and Person.\n"
        f"Fields: {json.dumps(fields)}"
    )
    response = litellm.completion(
        model=llm_model, messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise ValueError("LLM response has no text content")
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    rows = json.loads(fenced.group(1) if fenced else text)
    if not isinstance(rows, list) or any(
        not isinstance(row, list) or len(row) != 3 for row in rows
    ):
        raise ValueError("LLM response must contain three values per schema field")
    return rows


def generate_schemas(llm_model: str) -> None:
    """Refresh cached schema descriptions for each supported format."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for format_name, model in VALIDATION_MODELS.items():
        fields = [
            [name, str(field.annotation)] for name, field in model.model_fields.items()
        ]
        rows = llm_descriptions(model.__name__, fields, llm_model)
        with (CACHE_DIR / f"{format_name}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow(["Field", "Type", "Description"])
            writer.writerows(rows)


def check_schema(format_name: str) -> dict[str, object]:
    """Load the descriptions included with the project."""
    if format_name not in VALIDATION_MODELS:
        raise ValueError(f"Unsupported format: {format_name}")
    path = CACHE_DIR / f"{format_name}.csv"
    if not path.exists():
        return VALIDATION_MODELS[format_name].model_json_schema(by_alias=True)
    with path.open(newline="", encoding="utf-8") as file:
        fields = [
            row for row in csv.DictReader(file) if row.get("Field") or row.get("field")
        ]
    return {"model_name": format_name, "fields": fields}
