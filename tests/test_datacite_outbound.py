from datetime import date

import pytest

from codemeticulous.conversion import ConversionError
from codemeticulous.datacite.convert import software_metadata_to_datacite
from codemeticulous.datacite.models import (
    ContributorType,
    DateType,
    RelationType,
    ResourceTypeGeneral,
)
from codemeticulous.models import (
    Affiliation,
    Agent,
    Contribution,
    Identifier,
    License,
    RelatedResource,
    SoftwareMetadata,
)


def test_software_metadata_maps_to_datacite_semantically() -> None:
    value = SoftwareMetadata(
        title="Research Tool",
        description="A useful tool",
        creators=[
            Agent(
                kind="person",
                name="Ada Lovelace",
                given_names=["Ada"],
                family_names=["Lovelace"],
                identifiers=[Identifier(value="0000-0001", scheme="ORCID")],
            )
        ],
        contributors=[
            Contribution(
                agent=Agent(kind="organization", name="Example Lab"),
                roles=["researcher"],
            )
        ],
        publisher=Agent(
            kind="organization",
            name="Example Press",
            identifiers=[Identifier(value="ror-1", scheme="ROR")],
        ),
        identifiers=[
            Identifier(value="10.1234/tool", scheme="doi"),
            Identifier(value="tool-1", scheme="internal"),
        ],
        publication_year=2024,
        date_created=date(2023, 1, 1),
        category="Research software",
        keywords=["research"],
        licenses=[License(name="MIT", url="https://spdx.org/licenses/MIT")],
        programming_languages=["Python"],
        formats=["application/zip"],
        sizes=["10 MB"],
        relations=[
            RelatedResource(
                relation="cites",
                identifier=Identifier(value="10.1234/paper", scheme="DOI"),
            )
        ],
    )

    result = software_metadata_to_datacite(value)
    target = result.value

    assert target.titles[0].title == "Research Tool"
    assert target.types.resourceTypeGeneral is ResourceTypeGeneral.Software
    assert target.publicationYear == "2024"
    assert target.creators[0].nameIdentifiers[0].nameIdentifierScheme == "ORCID"
    assert target.contributors[0].contributorType is ContributorType.Researcher
    assert target.publisher.publisherIdentifierScheme == "ROR"
    assert target.dates[0].dateType is DateType.Created
    assert target.rightsList[0].rights == "MIT"
    assert target.relatedIdentifiers[0].relationType is RelationType.Cites
    assert target.alternateIdentifiers[0].alternateIdentifier == "tool-1"


@pytest.mark.parametrize(
    "value, message",
    [
        (
            SoftwareMetadata(
                title="Tool", publisher=Agent(kind="organization", name="Press")
            ),
            "DataCite requires at least one creator",
        ),
        (
            SoftwareMetadata(title="Tool", creators=[Agent(kind="person", name="Ada")]),
            "DataCite requires a publisher",
        ),
        (
            SoftwareMetadata(
                title="Tool",
                creators=[Agent(kind="person", name="Ada")],
                publisher=Agent(kind="organization", name="Press"),
            ),
            "DataCite requires a concrete publication year",
        ),
    ],
)
def test_datacite_required_values_raise_conversion_error(
    value: SoftwareMetadata, message: str
) -> None:
    with pytest.raises(ConversionError, match=message):
        software_metadata_to_datacite(value)


def test_publication_year_precedes_date_and_dates_can_derive_year() -> None:
    explicit = software_metadata_to_datacite(
        SoftwareMetadata(
            title="Tool",
            creators=[Agent(kind="person", name="Ada")],
            publisher=Agent(kind="organization", name="Press"),
            publication_year=2020,
            date_released=date(2024, 1, 1),
        )
    )
    derived = software_metadata_to_datacite(
        SoftwareMetadata(
            title="Tool",
            creators=[Agent(kind="person", name="Ada")],
            publisher=Agent(kind="organization", name="Press"),
            date_released=date(2024, 1, 1),
        )
    )

    assert explicit.value.publicationYear == "2020"
    assert derived.value.publicationYear == "2024"


def test_created_or_modified_dates_do_not_derive_publication_year() -> None:
    with pytest.raises(ConversionError, match="concrete publication year"):
        software_metadata_to_datacite(
            SoftwareMetadata(
                title="Tool",
                creators=[Agent(kind="person", name="Ada")],
                publisher=Agent(kind="organization", name="Press"),
                date_created=date(2024, 1, 1),
            )
        )


def test_doi_resolvers_normalize_and_invalid_doi_is_indexed() -> None:
    normalized = software_metadata_to_datacite(
        SoftwareMetadata(
            title="Tool",
            creators=[Agent(kind="person", name="Ada")],
            publisher=Agent(kind="organization", name="Press"),
            publication_year=2024,
            identifiers=[
                Identifier(value="https://doi.org/10.1234/tool", scheme="DOI")
            ],
        )
    )
    assert normalized.value.doi == "10.1234/tool"
    assert normalized.value.prefix == "10.1234"

    with pytest.raises(ConversionError, match=r"identifiers\[0\]"):
        software_metadata_to_datacite(
            SoftwareMetadata(
                title="Tool",
                creators=[Agent(kind="person", name="Ada")],
                publisher=Agent(kind="organization", name="Press"),
                publication_year=2024,
                identifiers=[Identifier(value="not-a-doi", scheme="doi")],
            )
        )

    with pytest.raises(ConversionError, match=r"identifiers\[1\]"):
        software_metadata_to_datacite(
            SoftwareMetadata(
                title="Tool",
                creators=[Agent(kind="person", name="Ada")],
                publisher=Agent(kind="organization", name="Press"),
                publication_year=2024,
                identifiers=[
                    Identifier(value="10.1234/valid", scheme="doi"),
                    Identifier(value="10.invalid", scheme="doi"),
                ],
            )
        )


def test_additional_doi_download_and_empty_license_report_loss() -> None:
    result = software_metadata_to_datacite(
        SoftwareMetadata(
            title="Tool",
            creators=[Agent(kind="person", name="Ada")],
            publisher=Agent(kind="organization", name="Press"),
            publication_year=2024,
            identifiers=[
                Identifier(value="10.1234/one", scheme="doi"),
                Identifier(value="10.1234/two", scheme="doi"),
            ],
            download_url="https://example.org/download",
            licenses=[License()],
        )
    )

    assert result.value.rightsList is None
    assert [(issue.path, issue.message) for issue in result.issues] == [
        ("licenses[0]", "empty license is not representable"),
        ("identifiers[1]", "additional DOI demoted to an alternate identifier"),
        ("download_url", "download URL is unsupported by DataCite"),
    ]


def test_affiliation_without_scheme_is_omitted_with_issue() -> None:
    result = software_metadata_to_datacite(
        SoftwareMetadata(
            title="Tool",
            creators=[
                Agent(
                    kind="person",
                    name="Ada",
                    affiliations=[
                        # DataCite cannot represent this identifier without a scheme.
                        Affiliation(name="Lab", identifier=Identifier(value="lab-id"))
                    ],
                )
            ],
            publisher=Agent(kind="organization", name="Press"),
            publication_year=2024,
        )
    )

    assert result.value.creators[0].affiliation[0].affiliationIdentifier is None
    assert result.issues[0].path == "creators[0].affiliations[0].identifier"


def test_related_resource_schemes_are_case_insensitive_and_types_are_reported() -> None:
    result = software_metadata_to_datacite(
        SoftwareMetadata(
            title="Tool",
            creators=[Agent(kind="person", name="Ada")],
            publisher=Agent(kind="organization", name="Press"),
            publication_year=2024,
            relations=[
                RelatedResource(
                    relation="cites",
                    identifier=Identifier(value="10.1234/paper", scheme="doi"),
                    title="Paper",
                    resource_type="dAtAsEt",
                )
            ],
        )
    )

    assert result.value.relatedIdentifiers[0].relatedIdentifierType.value == "DOI"
    assert (result.issues[0].path, result.issues[0].message) == (
        "relations[0].title",
        "related resource field is unsupported by DataCite",
    )
    assert (result.issues[1].path, result.issues[1].message) == (
        "relations[0].resource_type",
        "related resource field is unsupported by DataCite",
    )


def test_unknown_related_resource_type_reports_indexed_loss() -> None:
    result = software_metadata_to_datacite(
        SoftwareMetadata(
            title="Tool",
            creators=[Agent(kind="person", name="Ada")],
            publisher=Agent(kind="organization", name="Press"),
            publication_year=2024,
            relations=[
                RelatedResource(
                    relation="cites",
                    identifier=Identifier(value="10.1234/paper", scheme="doi"),
                    title="Paper",
                    resource_type="UnknownType",
                )
            ],
        )
    )

    assert [(issue.path, issue.message) for issue in result.issues] == [
        ("relations[0].title", "related resource field is unsupported by DataCite"),
        (
            "relations[0].resource_type",
            "related resource field is unsupported by DataCite",
        ),
    ]


def test_nested_validation_errors_become_conversion_errors() -> None:
    malformed = SoftwareMetadata.model_construct(
        title="Tool",
        creators=[Agent(kind="person", name="Ada")],
        publisher=Agent(kind="organization", name="Press"),
        publication_year=2024,
        sizes=[None],
    )

    with pytest.raises(ConversionError, match="Unable to construct DataCite"):
        software_metadata_to_datacite(malformed)


def test_loss_issues_have_exact_paths() -> None:
    result = software_metadata_to_datacite(
        SoftwareMetadata(
            title="Tool",
            creators=[Agent(kind="unknown", name="Unknown", given_names=["A", "B"])],
            publisher=Agent(kind="organization", name="Press"),
            publication_year=2024,
            contributors=[
                Contribution(
                    agent=Agent(kind="person", name="Other"),
                    roles=["not-a-datacite-role"],
                )
            ],
            relations=[
                RelatedResource(
                    relation="unsupported",
                    identifier=Identifier(value="x", scheme="DOI"),
                )
            ],
        )
    )

    assert [(issue.path, issue.message) for issue in result.issues] == [
        ("creators[0].given_names[1]", "additional name values are unsupported"),
        ("creators[0].kind", "unknown agent kind has no DataCite name type"),
        (
            "contributors[0].roles[0]",
            "role is not representable as a DataCite contributor type",
        ),
        ("relations[0]", "relation is unsupported by DataCite"),
    ]
