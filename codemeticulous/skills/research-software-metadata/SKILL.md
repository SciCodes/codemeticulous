---
name: research-software-metadata
description: Resolve a research software URL or persistent identifier, reconcile metadata with provenance, and generate validated output in a requested supported metadata standard and version. Use for research software metadata generation and transformation, not generic citation writing.
---

# Research Software Metadata

Generate metadata through this pipeline:

`identifier/URL -> resolve object -> discover evidence -> collect SoftwareMetadata + provenance -> select adapter -> transform -> validate requested schema/version -> output`

## Required inputs

Require all of these before generating an artifact:

- a research software URL, DOI, or other persistent identifier;
- target metadata standard and serialization;
- an explicit supported target version;
- optional output path.

Never choose a standard, serialization, or version silently. Read the adapter registry in [supported-formats.md](references/supported-formats.md) to confirm current support and obtain the exact transformation and validation commands. If the requested target is not registered, report it as unsupported rather than substituting another standard. If the identifier cannot be resolved, stop with a clear report; do not guess which object the user meant.

## Workflow

1. Read [source-discovery.md](references/source-discovery.md), resolve the identifier, and collect relevant records. Prefer version-specific records when the request identifies a release.
2. Reconcile each field independently. Treat a source as authoritative only for fields it owns: for example, a repository release for source/version details and a DOI registration record for DOI deposit details. Record all material conflicts.
3. Produce and validate the [`CollectedSoftwareMetadata` contract](references/collection-contract.md). Every populated canonical field must select evidence from a registered source. Keep **retrieved** and **agent-inferred** values distinct; an inference must name its evidence and reasoning.
4. Preserve the validated collection as the provenance sidecar. Do not invent mandatory values. Record unknowns as missing; if the requested target requires one, report that generation cannot complete.
5. Pass the complete collection to the registered `codemeticulous` transformation as `collected-software-metadata`. Do not bypass contract validation by passing raw `SoftwareMetadata`. Treat conversion issues as reportable information loss, not as ignorable noise.
6. Run the registered validator against the same standard, serialization, and explicit version. If validation fails, repair the collected or normalized source value, rerun transformation, and validate again. Never patch a generated artifact merely to silence validation, and never drop or fabricate data silently.
7. Write the artifact only after validation succeeds. Use [report-template.md](references/report-template.md) for the final response and classify fields as retrieved, inferred, ambiguous, conflicting, or missing.

The skill orchestrates discovery, reconciliation, adapter selection, and judgment only. Do not implement transformation, serialization, schema validation, identifier parsing, or reusable normalization in skill-side scripts. Add new standards and generally useful deterministic behavior to `codemeticulous` with offline unit tests, then register the adapter in [supported-formats.md](references/supported-formats.md).

## Examples

- "Generate `codemeta.json` for `https://github.com/example/software` using version 3.0."
- "Create `CITATION.cff` for `https://github.com/example/software` using version 1.2.0."
- "Create DataCite XML metadata for DOI `10.xxxx/example` using DataCite schema version 4.6."
- "Generate metadata for DOI `10.xxxx/example` using the requested supported standard and schema version."
