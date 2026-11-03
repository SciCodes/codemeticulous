# Supported adapter registry

This registry describes current implementations, not the scope of the skill. The
skill can support another research-software metadata standard when
`codemeticulous` provides its transformation, serialization, and validation
adapter and this registry records how to invoke it.

| Adapter | Standard | Supported versions | Serialized artifact |
| --- | --- | --- | --- |
| `codemeta.json` | CodeMeta | `3.0` | JSON-LD |
| `cff` | Citation File Format | `1.2.0` | YAML (`CITATION.cff`) |
| `datacite.xml` | DataCite Metadata Schema | `4.5`, `4.6` | XML |

The converter accepts CodeMeta 3.0, canonical SoftwareMetadata 1, or a validated
`CollectedSoftwareMetadata` contract as input. Agent workflows must use
`collected-software-metadata`; direct canonical input is reserved for trusted
non-agent callers and requires the CLI's explicit `--allow-unprovenanced`
opt-out. CFF and DataCite ingestion are not yet implemented as deterministic
fast paths.

## Invocation pattern

Use the adapter and version from the registry table. Keep the same explicit
version for conversion, serialization, and validation.

```console
codemeticulous convert --from collected-software-metadata --to TARGET --version VERSION --output OUTPUT WORK/collection.json
codemeticulous validate --format TARGET --version VERSION OUTPUT
```

Python API equivalent:

```python
from codemeticulous import convert, serialize, validate_document

result = convert(
    "collected-software-metadata",
    target,
    collected,
    target_version=version,
)
document = serialize(result.value, target, version)
validate_document(document, target, version)
```

## CodeMeta 3.0

Use target `codemeta.json`, version `3.0`, and an output such as
`OUTPUT/codemeta.json`.

## Citation File Format 1.2.0

Use target `cff`, version `1.2.0`, and output `OUTPUT/CITATION.cff`.
The target requires a title and at least one author. Map the canonical
`revision` to CFF `commit`; do not substitute a commit timestamp for
`date-released`. CFF can serialize only one license, so collect every applicable
license and report the converter's issue for each additional license. Canonical
`cites` relations become CFF references. Use `repository-code` for a source
repository and avoid duplicating it into `repository` without distinct
evidence. Email values must be plain addresses rather than Markdown links.

## DataCite XML 4.5 or 4.6

Use target `datacite.xml`, the user-requested version `4.5` or `4.6`, and an
output such as `OUTPUT/datacite.xml`. Never select the version implicitly.

DataCite XML requires an identifier, at least one creator, a publisher, a publication year, and a resource type. The current normalized model supplies the XML identifier from a DOI. If any required value cannot be established, stop and report it as missing rather than manufacturing a placeholder.

## Adding another adapter

Only register a target after `codemeticulous` can transform to it, serialize it,
and validate the declared version. Add its supported versions to the table,
confirm that the shared invocation pattern supports it, and add at least one
network-free evaluation scenario. Keep only target-specific required fields and
repair guidance in its section rather than duplicating commands or expanding
`SKILL.md`.

Conversion warnings identify loss or ambiguity. A validation error is not
permission to edit the generated artifact directly: fix the source ledger or
normalized converter input, regenerate, and revalidate.
