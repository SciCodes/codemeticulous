"""Offline checks for AI response parsing and validation retries."""

import sys
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from codemeticulous.ai_convert import extract_json, structured_completion
from codemeticulous import generate_schemas


class Target(BaseModel):
    title: str


def test_extract_json_accepts_raw_and_fenced_objects():
    assert extract_json('{"title": "Example"}') == {"title": "Example"}
    assert extract_json('```json\n{"title": "Example"}\n```') == {"title": "Example"}
    with pytest.raises(ValueError, match="JSON object"):
        extract_json("[]")


def test_structured_completion_retries_invalid_target(monkeypatch):
    outputs = ['{"wrong": "value"}', '{"title": "Example"}']
    calls = []

    def completion(*, model, messages, temperature):
        calls.append(list(messages))
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
            choices=[SimpleNamespace(message=SimpleNamespace(content=outputs.pop(0)))],
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=completion))
    messages = [{"role": "user", "content": "Convert this"}]
    result, usage = structured_completion("fake-model", messages, Target)

    assert result == Target(title="Example")
    assert usage == {"prompt_tokens": 20, "completion_tokens": 10}
    assert len(calls) == 2
    assert calls[1][-1]["role"] == "user"
    assert "title" in calls[1][-1]["content"]


def test_schema_uses_model_when_cache_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(generate_schemas, "CACHE_DIR", tmp_path)
    schema = generate_schemas.check_schema("codemeta")
    assert "properties" in schema
    assert "name" in schema["properties"]
