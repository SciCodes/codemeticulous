from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from codemeticulous import (
    Affiliation,
    Agent,
    CollectedSoftwareMetadata,
    Contribution,
    ConversionIssue,
    ConversionResult,
    Evidence,
    FieldCollection,
    Identifier,
    License,
    RelatedResource,
    SoftwareMetadata,
    SourceReference,
    collection_json_schema,
    validate_collection,
)

SOURCE = SourceReference(
    id="release",
    uri="https://example.org/releases/1.0/codemeta.json",
    kind="repository-release",
    retrieved_at=datetime(2026, 10, 19, tzinfo=UTC),
    media_type="application/ld+json",
    object_version="1.0",
)


def _retrieved(path: str, value) -> FieldCollection:
    return FieldCollection(
        path=path,
        status="retrieved",
        evidence=(
            Evidence(
                source_id=SOURCE.id,
                value=value,
                acquisition="retrieved",
                selector=f"$.{path}",
                raw_value=value,
            ),
        ),
        selected_evidence=0,
    )


def test_collection_validates_selected_evidence_and_complete_provenance() -> None:
    collection = CollectedSoftwareMetadata(
        requested_identifier="https://doi.org/10.1234/tool",
        metadata=SoftwareMetadata(title="Tool", version="1.0"),
        sources=(SOURCE,),
        fields=(
            _retrieved("title", "Tool"),
            _retrieved("version", "1.0"),
            FieldCollection(path="publisher", status="missing"),
        ),
    )

    assert validate_collection(collection) is collection
    assert collection.fields[0].evidence[0].source_id == "release"


def test_collection_schema_is_provider_neutral() -> None:
    schema = collection_json_schema()

    assert schema["title"] == "CollectedSoftwareMetadata"
    assert {"metadata", "sources", "fields"} <= set(schema["properties"])


def test_inferred_evidence_requires_reasoning() -> None:
    with pytest.raises(ValidationError, match="inferred evidence requires reasoning"):
        Evidence(
            source_id="release",
            value=2026,
            acquisition="inferred",
            raw_value="2026-10-19",
        )


def test_collection_rejects_unknown_evidence_source() -> None:
    with pytest.raises(ValidationError, match="references unknown sources: missing"):
        CollectedSoftwareMetadata(
            metadata=SoftwareMetadata(title="Tool"),
            sources=(SOURCE,),
            fields=(
                FieldCollection(
                    path="title",
                    status="retrieved",
                    evidence=(
                        Evidence(
                            source_id="missing",
                            value="Tool",
                            acquisition="retrieved",
                        ),
                    ),
                    selected_evidence=0,
                ),
            ),
        )


def test_collection_rejects_selected_value_that_differs_from_metadata() -> None:
    with pytest.raises(ValidationError, match="does not match SoftwareMetadata"):
        CollectedSoftwareMetadata(
            metadata=SoftwareMetadata(title="Tool"),
            sources=(SOURCE,),
            fields=(_retrieved("title", "Other tool"),),
        )


def test_collection_requires_provenance_for_populated_fields() -> None:
    with pytest.raises(ValidationError, match="version"):
        CollectedSoftwareMetadata(
            metadata=SoftwareMetadata(title="Tool", version="1.0"),
            sources=(SOURCE,),
            fields=(_retrieved("title", "Tool"),),
        )


def test_conflict_preserves_candidates_and_authority_selection() -> None:
    collection = CollectedSoftwareMetadata(
        metadata=SoftwareMetadata(title="Tool", publication_year=2026),
        sources=(
            SOURCE,
            SourceReference(
                id="doi",
                uri="https://api.datacite.org/dois/10.1234/tool",
                kind="doi-registration",
                retrieved_at=datetime(2026, 10, 19, tzinfo=UTC),
            ),
        ),
        fields=(
            _retrieved("title", "Tool"),
            FieldCollection(
                path="publication_year",
                status="conflicting",
                evidence=(
                    Evidence(
                        source_id="release",
                        value=2025,
                        acquisition="retrieved",
                    ),
                    Evidence(
                        source_id="doi",
                        value=2026,
                        acquisition="retrieved",
                    ),
                ),
                selected_evidence=1,
                authority_rule="DOI registration owns the deposit publication year",
            ),
        ),
    )

    assert collection.metadata.publication_year == 2026
    assert collection.fields[1].status == "conflicting"


def test_ambiguous_field_cannot_populate_canonical_metadata() -> None:
    with pytest.raises(
        ValidationError, match="ambiguous fields cannot select evidence"
    ):
        FieldCollection(
            path="publication_year",
            status="ambiguous",
            evidence=(
                Evidence(
                    source_id="release",
                    value=2026,
                    acquisition="retrieved",
                ),
            ),
            selected_evidence=0,
        )


def test_missing_field_cannot_be_populated() -> None:
    with pytest.raises(ValidationError, match="missing field version is populated"):
        CollectedSoftwareMetadata(
            metadata=SoftwareMetadata(title="Tool", version="1.0"),
            sources=(SOURCE,),
            fields=(
                _retrieved("title", "Tool"),
                FieldCollection(path="version", status="missing"),
            ),
        )


def test_software_metadata_requires_title() -> None:
    with pytest.raises(ValidationError):
        SoftwareMetadata()


def test_canonical_model_forbids_source_specific_extras() -> None:
    with pytest.raises(ValidationError):
        SoftwareMetadata(title="Tool", context="https://example.org/context")


def test_list_defaults_are_independent() -> None:
    first = SoftwareMetadata(title="One")
    second = SoftwareMetadata(title="Two")

    first.creators.append(Agent(kind="person", name="Author"))
    assert second.creators == []
    assert first.keywords == []


def test_canonical_values_are_source_independent() -> None:
    metadata = SoftwareMetadata(
        title="Tool",
        date_released=date(2024, 1, 1),
        identifiers=[Identifier(value="10.1234/example", scheme="doi")],
    )

    assert metadata.title == "Tool"
    assert metadata.identifiers[0].value == "10.1234/example"


def test_complete_canonical_metadata_is_snake_case_and_typed() -> None:
    creator = Agent(
        kind="person",
        name="Ada Lovelace",
        affiliations=[
            Affiliation(
                name="Analytical Engine Lab",
                identifier=Identifier(value="org-1", scheme="local"),
            )
        ],
    )
    metadata = SoftwareMetadata(
        title="Analytical Engine",
        repository="https://example.org/repository",
        repository_code="https://example.org/source",
        repository_artifact="pkg://analytical-engine",
        publication_year=1843,
        creators=[creator],
        contributors=[Contribution(agent=creator, roles=["maintainer"])],
        licenses=[License(name="MIT", url="https://spdx.org/licenses/MIT")],
        relations=[
            RelatedResource(
                relation="is_part_of",
                identifier=Identifier(value="10.1234/paper", scheme="doi"),
                creators=[creator],
            )
        ],
    )

    payload = metadata.model_dump()
    assert payload["repository_code"] == "https://example.org/source"
    assert payload["repository_artifact"] == "pkg://analytical-engine"
    assert payload["publication_year"] == 1843
    assert payload["relations"][0]["identifier"]["scheme"] == "doi"
    with pytest.raises(ValidationError):
        RelatedResource(
            relation="is_part_of",
            identifier={"value": "x", "unexpected": True},
        )


def test_conversion_result_and_issue_are_immutable() -> None:
    issue = ConversionIssue(path="creators[0]", message="missing email")
    result = ConversionResult[SoftwareMetadata](
        value=SoftwareMetadata(title="Tool"), issues=(issue,)
    )

    with pytest.raises(ValidationError):
        issue.message = "changed"
    with pytest.raises(ValidationError):
        result.value = SoftwareMetadata(title="Other")
