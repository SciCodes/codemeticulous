from datetime import date

import pytest
from pydantic import ValidationError

from codemeticulous.cff import DoiIdentifier, OtherIdentifier, SwhIdentifier, UrlIdentifier
from codemeticulous.cff.convert import software_metadata_to_cff
from codemeticulous.conversion import ConversionError
from codemeticulous.models import Affiliation, Agent, Contribution, Identifier, License, RelatedResource, SoftwareMetadata


def person(name: str = "Ada Lovelace") -> Agent:
    return Agent(kind="person", name=name, given_names=["Ada"], family_names=["Lovelace"])


def test_public_identifier_names_preserve_generated_validation() -> None:
    assert DoiIdentifier(type="doi", value="10.1234/demo").type == "doi"
    assert str(UrlIdentifier(type="url", value="https://example.com/id").value) == "https://example.com/id"
    assert SwhIdentifier(
        type="swh", value="swh:1:rev:0000000000000000000000000000000000000000"
    ).type == "swh"
    assert OtherIdentifier(type="other", value="local-id").value == "local-id"

    with pytest.raises(ValidationError):
        DoiIdentifier(type="doi", value="not-a-doi")


def test_maps_neutral_fields_and_repository_precedence() -> None:
    result = software_metadata_to_cff(
        SoftwareMetadata(
            title="Demo",
            description="An example",
            creators=[person()],
            date_released=date(2024, 1, 2),
            version="1.0",
            keywords=["example"],
            identifiers=[Identifier(value="10.1234/demo", scheme="doi")],
            repository="https://repo.example/item",
            repository_code="https://github.com/example/demo",
            repository_artifact="https://repo.example/download",
            url="https://example.com/demo",
            download_url="https://example.com/archive",
        )
    )
    cff = result.value
    assert cff.title == "Demo"
    assert cff.abstract == "An example"
    assert cff.authors[0].family_names == "Lovelace"
    assert cff.doi == "10.1234/demo"
    assert cff.date_released == date(2024, 1, 2)
    assert str(cff.repository_code) == "https://github.com/example/demo"
    assert str(cff.url) == "https://example.com/demo"
    assert [issue.path for issue in result.issues] == ["download_url"]


def test_creators_are_mandatory() -> None:
    with pytest.raises(ConversionError, match="creators"):
        software_metadata_to_cff(SoftwareMetadata(title="No authors"))


def test_typed_license_and_identifiers() -> None:
    result = software_metadata_to_cff(
        SoftwareMetadata(
            title="Demo",
            creators=[person()],
            identifiers=[
                Identifier(value="10.1234/demo", scheme="doi"),
                Identifier(value="swh:1:rev:0000000000000000000000000000000000000000", scheme="swh"),
                Identifier(value="https://example.com/id", scheme="url"),
            ],
            licenses=[License(identifier="MIT")],
        )
    )
    assert result.value.license.value == "MIT"
    assert [item.type for item in result.value.identifiers] == ["swh", "url"]


def test_representable_relations_become_references() -> None:
    result = software_metadata_to_cff(
        SoftwareMetadata(
            title="Demo",
            creators=[person()],
            relations=[
                RelatedResource(
                    relation="cites",
                    title="A paper",
                    resource_type="article",
                    identifier=Identifier(value="10.1234/paper", scheme="doi"),
                    creators=[person("Grace Hopper")],
                )
            ],
        )
    )
    reference = result.value.references[0]
    assert reference.title == "A paper"
    assert reference.doi == "10.1234/paper"
    assert reference.authors[0].given_names == "Ada"


def test_unrepresentable_relation_has_exact_path() -> None:
    result = software_metadata_to_cff(
        SoftwareMetadata(
            title="Demo",
            creators=[person()],
            relations=[RelatedResource(relation="cites", title="Missing authors")],
        )
    )
    assert [(issue.path, issue.message) for issue in result.issues] == [
        ("relations[0].creators", "CFF references require authors")
    ]


def test_unsupported_top_level_values_have_fixed_order() -> None:
    metadata = SoftwareMetadata(
        title="Demo",
        creators=[person()],
        publisher=Agent(kind="organization", name="Publisher"),
        contributors=[Contribution(agent=person())],
        category="library",
        publication_year=2024,
        date_created=date(2020, 1, 1),
        date_modified=date(2024, 1, 1),
        programming_languages=["Python"],
        formats=["source"],
        sizes=["1 MB"],
        release_notes=["first release"],
    )
    assert [issue.path for issue in software_metadata_to_cff(metadata).issues] == [
        "publisher", "contributors", "category", "publication_year", "date_created",
        "date_modified", "programming_languages", "formats", "sizes", "release_notes",
    ]


def test_agent_and_license_losses_are_indexed() -> None:
    creator = Agent(
        kind="organization",
        name="Team",
        identifiers=[Identifier(value="https://orcid.org/1", scheme="orcid"), Identifier(value="x")],
        affiliations=[Affiliation(name="Institute", identifier=Identifier(value="ror:1"))],
    )
    result = software_metadata_to_cff(
        SoftwareMetadata(
            title="Demo", creators=[creator],
            licenses=[License(name="custom"), License(identifier="MIT"), License(identifier="Apache-2.0")],
        )
    )
    assert [issue.path for issue in result.issues] == [
        "licenses[0]", "licenses[2]", "creators[0].identifiers[1]",
        "creators[0].affiliations[0]", "creators[0].affiliations[0].identifier",
    ]


def test_relation_type_and_requires_semantics_are_reported() -> None:
    result = software_metadata_to_cff(
        SoftwareMetadata(
            title="Demo", creators=[person()],
            relations=[RelatedResource(relation="requires", resource_type="mystery", title="Dependency", creators=[person()])],
        )
    )
    assert [issue.path for issue in result.issues] == [
        "relations[0].resource_type", "relations[0].relation"
    ]
    assert result.value.references[0].type.value == "generic"


def test_nested_target_validation_is_conversion_error() -> None:
    with pytest.raises(ConversionError, match="CitationFileFormat"):
        software_metadata_to_cff(
            SoftwareMetadata(title="Demo", creators=[Agent(kind="person", name="A", email="not-an-email")])
        )
