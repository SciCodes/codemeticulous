# Structured collection contract

Use `codemeticulous.CollectedSoftwareMetadata` as the boundary between agentic
collection and deterministic outbound conversion. Obtain its provider-neutral
JSON Schema with `collection_json_schema()` and validate provider output with
`validate_collection()`.

The contract contains:

- `sources`: unique retrieved source references with URI, kind, retrieval time,
  and optional media type, object version, and content hash;
- `metadata`: canonical `SoftwareMetadata` selected from the evidence;
- `fields`: one collection record per populated or explicitly missing canonical
  field;
- `requested_identifier`: the original identifier when one was supplied.

Each field uses a canonical path such as `title`, `publisher.name`, or
`creators[0].identifiers[0]`. Evidence records a normalized candidate value,
its source ID, whether it was retrieved or inferred, and an optional source
selector and raw value. Inferred evidence requires reasoning. Ambiguous fields
remain unselected. Conflicting fields retain distinct candidates, select one,
and name the authority rule.

The validator rejects unknown source IDs, duplicate sources or field paths,
invalid selections, selected evidence that differs from `SoftwareMetadata`,
populated fields marked missing, and populated canonical values without
selected provenance.

```python
from codemeticulous import collection_json_schema, convert, validate_collection

schema = collection_json_schema()
collected = validate_collection(provider_output)

result = convert(
    "collected-software-metadata",
    target,
    collected,
    target_version=version,
)
```

Do not add provenance fields to a target artifact. Preserve the validated
collection as a sidecar or execution result. Agent workflows must pass the
complete collection to conversion so contract validation cannot be bypassed.
Direct `software-metadata` input remains available for trusted non-agent
library callers.
