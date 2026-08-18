from datetime import date

from codemeticulous.codemeta.convert import (
    codemeta_to_software_metadata,
    software_metadata_to_codemeta,
)
from codemeticulous.codemeta.models import CodeMetaV3
from codemeticulous.models import (
    Agent,
    Affiliation,
    Contribution,
    Identifier,
    License,
    RelatedResource,
    SoftwareMetadata,
)


def test_codemeta_to_software_metadata_maps_semantic_values() -> None:
    source = CodeMetaV3.model_validate(
        {
            "@context": "https://w3id.org/codemeta/3.0",
            "@type": "SoftwareSourceCode",
            "@id": "https://example.org/tool",
            "name": "Tool",
            "description": "A useful tool",
            "author": {
                "@type": "Person",
                "@id": "https://orcid.org/0000-0000-0000-0001",
                "name": "Ada Lovelace",
                "givenName": "Ada",
                "familyName": "Lovelace",
                "email": "ada@example.org",
            },
            "contributor": {
                "@type": "Role",
                "roleName": "maintainer",
                "author": {"@type": "Organization", "name": "Example Lab"},
            },
            "publisher": {"@type": "Organization", "name": "Example Lab"},
            "identifier": {
                "@type": "PropertyValue",
                "propertyID": "doi",
                "value": "10.1234/tool",
            },
            "version": "1.2.3",
            "datePublished": "2024-06-01",
            "dateCreated": "2023-01-01",
            "dateModified": "2024-06-02",
            "keywords": ["research", "software"],
            "license": "https://spdx.org/licenses/MIT",
            "programmingLanguage": {"@type": "ComputerLanguage", "name": "Python"},
            "fileFormat": "application/zip",
            "fileSize": "10 MB",
            "codeRepository": "https://github.com/example/tool",
            "url": "https://example.org/tool",
            "citation": {
                "@type": "ScholarlyArticle",
                "name": "Tool paper",
                "@id": "10.1234/paper",
            },
            "futureField": "preserve as issue",
        }
    )

    result = codemeta_to_software_metadata(source)
    metadata = result.value

    assert metadata.title == "Tool"
    assert metadata.creators[0].identifiers[0].value == "https://orcid.org/0000-0000-0000-0001"
    assert metadata.contributors[0].roles == ["maintainer"]
    assert Identifier(value="10.1234/tool", scheme="doi") in metadata.identifiers
    assert metadata.date_released == date(2024, 6, 1)
    assert metadata.publication_year == 2024
    assert metadata.repository_code == "https://github.com/example/tool"
    assert metadata.programming_languages == ["Python"]
    assert metadata.licenses[0].url == "https://spdx.org/licenses/MIT"
    assert metadata.relations[0].relation == "cites"
    assert any(issue.path == "futureField" for issue in result.issues)


def test_untyped_author_string_is_explicitly_preserved() -> None:
    source = CodeMetaV3(name="Tool", author="Unknown author")

    result = codemeta_to_software_metadata(source)

    assert result.value.creators[0].kind == "unknown"
    assert result.value.creators[0].name == "Unknown author"
    assert (result.issues[0].path, result.issues[0].message) == (
        "author[0]",
        "untyped agent string mapped to kind 'unknown'",
    )


def test_unknown_agent_kind_reverses_to_string_with_issue() -> None:
    result = software_metadata_to_codemeta(
        SoftwareMetadata(
            title="Tool",
            creators=[Agent(kind="unknown", name="Unknown author")],
        )
    )

    assert result.value.to_jsonld()["author"] == ["Unknown author"]
    assert (result.issues[0].path, result.issues[0].message) == (
        "creators[0]",
        "unknown agent kind emitted as a string",
    )


def test_role_resolves_same_field_sibling_without_duplicate_creator() -> None:
    source = CodeMetaV3.model_validate(
        {
            "@type": "SoftwareSourceCode",
            "name": "Tool",
            "author": [
                {"@type": "Person", "@id": "person-1", "name": "Ada"},
                {
                    "@type": "Role",
                    "roleName": "maintainer",
                    "author": {"@id": "person-1"},
                },
            ],
        }
    )

    result = codemeta_to_software_metadata(source)

    assert [agent.name for agent in result.value.creators] == ["Ada"]
    assert result.value.contributors[0].agent.name == "Ada"
    assert result.value.contributors[0].roles == ["maintainer"]


def test_contributor_role_replaces_concrete_sibling_contribution() -> None:
    source = CodeMetaV3.model_validate(
        {
            "@type": "SoftwareSourceCode",
            "name": "Tool",
            "contributor": [
                {"@type": "Person", "@id": "p1", "name": "Ada"},
                {"@type": "Role", "@id": "p1", "roleName": "maintainer"},
            ],
        }
    )

    result = codemeta_to_software_metadata(source)

    assert len(result.value.contributors) == 1
    assert result.value.contributors[0].agent.name == "Ada"
    assert result.value.contributors[0].roles == ["maintainer"]


def test_unknown_role_is_skipped_with_a_deterministic_issue() -> None:
    source = CodeMetaV3(
        name="Tool",
        author={"@type": "Role", "roleName": "maintainer"},
    )

    result = codemeta_to_software_metadata(source)

    assert result.value.creators == []
    assert (result.issues[0].path, result.issues[0].message) == (
        "author[0]",
        "role has no resolvable actor",
    )


def test_nested_role_only_author_is_creator_and_contribution() -> None:
    source = CodeMetaV3(
        name="Tool",
        author={
            "@type": "Role",
            "roleName": "maintainer",
            "author": {"@type": "Person", "name": "Ada"},
        },
    )

    result = codemeta_to_software_metadata(source)

    assert [agent.name for agent in result.value.creators] == ["Ada"]
    assert result.value.contributors[0].roles == ["maintainer"]


def test_loss_issues_are_indexed_and_ordered() -> None:
    result = codemeta_to_software_metadata(
        CodeMetaV3(
            name="Tool",
            author="Unknown author",
            url=["https://example.org/tool", "https://example.org/other"],
            downloadUrl=["https://example.org/download", "https://example.org/other-download"],
            futureField=True,
        )
    )

    assert [(issue.path, issue.message) for issue in result.issues] == [
        ("author[0]", "untyped agent string mapped to kind 'unknown'"),
        ("url[1]", "additional URLs are unsupported"),
        ("downloadUrl[1]", "additional URLs are unsupported"),
        ("futureField", "unknown CodeMeta field is not mapped"),
    ]


def test_nested_identifiers_select_first_and_report_rest() -> None:
    source = CodeMetaV3.model_validate(
        {
            "@type": "SoftwareSourceCode",
            "name": "Tool",
            "author": {
                "@type": "Person",
                "name": "Ada",
                "affiliation": {
                    "@type": "Organization",
                    "name": "Lab",
                    "identifier": [
                        {"@type": "PropertyValue", "value": "lab-1"},
                        {"@type": "PropertyValue", "value": "lab-2"},
                    ],
                },
            },
            "citation": {
                "@type": "CreativeWork",
                "name": "Paper",
                "identifier": [
                    {"@type": "PropertyValue", "value": "paper-1"},
                    {"@type": "PropertyValue", "value": "paper-2"},
                ],
            },
            "license": {
                "@type": "CreativeWork",
                "identifier": [
                    {"@type": "PropertyValue", "value": "license-1"},
                    {"@type": "PropertyValue", "value": "license-2"},
                ],
            },
        }
    )

    result = codemeta_to_software_metadata(source)
    pairs = [(issue.path, issue.message) for issue in result.issues]

    assert result.value.creators[0].affiliations[0].identifier.value == "lab-1"
    assert result.value.relations[0].identifier.value == "paper-1"
    assert result.value.licenses[0].identifier == "license-1"
    assert pairs == [
        (
            "author[0].affiliation[0].identifier[1]",
            "additional identifiers are unsupported",
        ),
        ("citation[0].identifier[1]", "additional identifiers are unsupported"),
        ("license[0].identifier[1]", "additional identifiers are unsupported"),
    ]


def test_software_metadata_to_codemeta_reconstructs_jsonld_types() -> None:
    creator = Agent(
        kind="person",
        name="Ada Lovelace",
        affiliations=[Affiliation(name="Analytical Engine Lab")],
        identifiers=[Identifier(value="10.1234/ada", scheme="doi")],
    )
    metadata = SoftwareMetadata(
        title="Tool",
        creators=[creator],
        contributors=[Contribution(agent=creator, roles=["maintainer"])],
        identifiers=[Identifier(value="10.1234/tool", scheme="doi")],
        licenses=[License(name="MIT", url="https://spdx.org/licenses/MIT")],
        relations=[
            RelatedResource(
                relation="cites",
                title="Tool paper",
                identifier=Identifier(value="10.1234/paper", scheme="doi"),
            )
        ],
    )

    result = software_metadata_to_codemeta(metadata)
    payload = result.value.to_jsonld()

    assert payload["@context"] == "https://w3id.org/codemeta/3.0"
    assert payload["@type"] == "SoftwareSourceCode"
    assert "@id" not in payload
    assert payload["name"] == "Tool"
    assert payload["author"][0]["@type"] == "Person"
    assert payload["author"][0]["affiliation"]["@type"] == "Organization"
    assert payload["author"][0]["identifier"][0]["@type"] == "PropertyValue"
    assert payload["contributor"][0]["@type"] == "Role"
    assert payload["identifier"][0]["@type"] == "PropertyValue"
    assert payload["license"][0]["@type"] == "CreativeWork"
    assert payload["citation"]["@type"] == "CreativeWork"


def test_relations_use_neutral_names_and_preserve_resource_types() -> None:
    url_payload = software_metadata_to_codemeta(
        SoftwareMetadata(
            title="Tool",
            relations=[RelatedResource(relation="cites", url="https://example.org/paper")],
        )
    ).value.to_jsonld()
    assert url_payload["citation"] == "https://example.org/paper"

    metadata = SoftwareMetadata(
        title="Tool",
        relations=[
            RelatedResource(
                relation="cites", resource_type="WebApplication", title="Web app"
            ),
            RelatedResource(
                relation="requires", resource_type="SoftwareSourceCode", title="Source"
            ),
        ],
    )

    payload = software_metadata_to_codemeta(metadata).value.to_jsonld()

    assert payload["citation"]["@type"] == "WebApplication"
    assert payload["softwareRequirements"]["@type"] == "SoftwareSourceCode"


def test_year_only_is_not_fabricated_and_conflicts_are_reported() -> None:
    year_only = software_metadata_to_codemeta(
        SoftwareMetadata(title="Tool", publication_year=2024)
    )
    assert "datePublished" not in year_only.value.to_jsonld()
    assert (year_only.issues[0].path, year_only.issues[0].message) == (
        "publication_year",
        "year-only value has no CodeMeta date representation",
    )

    conflict = software_metadata_to_codemeta(
        SoftwareMetadata(
            title="Tool", publication_year=2023, date_released="2024-01-01"
        )
    )
    assert conflict.issues[0].path == "publication_year"


def test_unsupported_relation_is_reported_per_element() -> None:
    result = software_metadata_to_codemeta(
        SoftwareMetadata(
            title="Tool",
            relations=[RelatedResource(
                relation="unknown_relation", url="https://example.org/x"
            )],
        )
    )

    assert (result.issues[0].path, result.issues[0].message) == (
        "relations[0]",
        "unsupported relation 'unknown_relation'",
    )
