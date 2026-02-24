# codemeticulous

`codemeticulous` validates and converts software metadata with Pydantic v2.
The neutral `SoftwareMetadata` model is the hub for the currently supported
outbound graph:

```text
codemeta -> software-metadata
         -> codemeta
         -> cff
         -> datacite
```

CodeMeta v3 is the only supported input format. CFF and DataCite ingestion is
deferred. Conversions return a `ConversionResult`; its `value` is the target
model and its ordered `issues` describe non-fatal information loss.

## Installation

```bash
pip install codemeticulous
```

For development, install with [uv](https://docs.astral.sh/uv/):

```bash
uv sync --group dev
```

## Python API

```python
from codemeticulous import convert

result = convert(
    "codemeta",
    "cff",
    {
        "@type": "SoftwareSourceCode",
        "name": "My Tool",
        "author": {"@type": "Person", "name": "Example Author"},
    },
)

print(result.value)
for issue in result.issues:
    print(issue.path, issue.message)
```

Input validation and target construction failures raise `ConversionError`.
Issues are warnings: they do not make a successful conversion fail.

## Command line

```bash
codemeticulous convert --from codemeta --to cff codemeta.json > CITATION.cff
codemeticulous validate --format cff CITATION.cff
```

Conversion issues are printed to stderr while the target document is printed
to stdout. Invalid input, unsupported directions, validation failures, and
serialization failures exit nonzero. `validate` is independent of conversion
and supports format-specific validation for CodeMeta, CFF, and DataCite.

## Tests

```bash
uv run python -m pytest -q
```

## Experimental AI mode

AI conversion can use a configured LLM provider to convert between CodeMeta, CFF,
and DataCite. Set the provider's API key in your environment, then run:

```bash
codemeticulous ai-convert --model <provider/model> --from codemeta --to cff codemeta.json > CITATION.cff
```

Run `codemeticulous generate-schemas --model <provider/model>` to refresh the
schema descriptions used in prompts.
