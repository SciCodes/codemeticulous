from datetime import date

import pytest
from pydantic import ValidationError

from codemeticulous import (
    Agent,
    ConversionIssue,
    ConversionResult,
    Affiliation,
    Contribution,
    Identifier,
    License,
    RelatedResource,
    SoftwareMetadata,
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
