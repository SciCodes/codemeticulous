# Completion report

Report the result in this order:

## Artifact

- output path
- validated provenance sidecar path or retained execution result
- target metadata standard, serialization, adapter, and exact version
- validation result and command used

## Retrieved fields

List each field, selected value, and source URL or persistent identifier.

## Inferred fields

List each field, value, retrieved evidence, and reasoning. Write `None` when no values were inferred.

## Ambiguous fields

List unresolved interpretations and their evidence. Do not hide them by choosing silently.

## Conflicting fields

For each conflict, list candidate values and sources, the selected value, and the field-specific authority rule used. Write `None` when no conflicts were observed.

## Missing fields

List metadata that could not be established, including whether it is optional or blocks the requested schema. Never use a placeholder as a substitute.

## Transformation and validation issues

Include every `codemeticulous` issue path and message, plus any repair and revalidation performed. If generation failed, state the failing stage and leave no claim that an artifact validated.
