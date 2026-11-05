# codemeticulous

`codemeticulous` validates and converts software metadata with Pydantic v2.
The neutral `SoftwareMetadata` model is the hub for the currently supported
outbound graph:

```text
codemeta -------------------\
software-metadata -----------> software-metadata -> codemeta
collected-software-metadata -/                    -> cff
                                                  -> datacite
```

CodeMeta 3.0, canonical `SoftwareMetadata` version 1, and the provenance-bearing
`CollectedSoftwareMetadata` contract are supported inputs. Target versions are CodeMeta 3.0, CFF 1.2.0, and
DataCite 4.5 or 4.6.
DataCite output is XML and is validated offline against the requested official
XSD. Conversions return a `ConversionResult`; its `value` is the target model
and its ordered `issues` describe non-fatal information loss.

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
    target_version="1.2.0",
)

print(result.value)
for issue in result.issues:
    print(issue.path, issue.message)
```

Input validation and target construction failures raise `ConversionError`.
Issues are warnings: they do not make a successful conversion fail.

## Structured agent collection

Agents and other metadata providers can return a canonical, provenance-bearing
collection without depending on a particular LLM SDK:

```python
from codemeticulous import collection_json_schema, convert, validate_collection

schema = collection_json_schema()  # Supply this to a structured-output provider.
collected = validate_collection(provider_output)

result = convert(
    "collected-software-metadata",
    "datacite.xml",
    collected,
    target_version="4.6",
)
```

The collection contract requires selected evidence for every populated
`SoftwareMetadata` field and preserves retrieved, inferred, ambiguous,
conflicting, and missing classifications separately from target serialization.
Passing the complete contract as `collected-software-metadata` validates that
boundary again immediately before conversion.
The CLI requires an explicit `--allow-unprovenanced` opt-out before it accepts
raw `software-metadata`; the Python API retains direct canonical input for
trusted library callers.

## Command line

```bash
codemeticulous convert --from codemeta --to datacite.xml --version 4.6 --output output/datacite.xml input.json

codemeticulous validate --format datacite.xml --version 4.6 output/datacite.xml
```

Conversion issues are printed to stderr while the target document is printed
to stdout. Invalid input, unsupported directions, validation failures, and
serialization failures exit nonzero. `validate` is independent of conversion
and supports format-specific validation for CodeMeta, CFF, and DataCite.

## Agent skill

`research-software-metadata` skill teaches an agent to resolve a
research software identifier, collect and reconcile source metadata with
field-level provenance, select a supported
metadata adapter, invoke the versioned library interface, validate the result,
and report conflicts or missing data without fabrication. CodeMeta JSON,
Citation File Format, and DataCite XML are the initial adapters rather than the
boundary of the skill.

Install the skill by running the command from anywhere inside the project with codemeticulous installed:

```bash
uv run codemeticulous skill install research-software-metadata
```

The command discovers the repository root with Git and installs the skill at
`.agents/skills/research-software-metadata`.

```bash
uv run codemeticulous skill install research-software-metadata --agent
```

| Coding agent | CLI option | Skill directory |
| --- | --- | --- |
| Codex | `--agent codex` (default) | `.agents/skills` |
| GitHub Copilot | `--agent copilot` | `.agents/skills` |
| Claude Code | `--agent claude` | `.claude/skills` |
| All supported agents | `--agent all` | `.agents/skills` and `.claude/skills` |

## Tests

```bash
uv run python -m pytest -q
```
