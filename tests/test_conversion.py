import json
from importlib.resources import files
from pathlib import Path

import pytest
from pydantic_codemeta import CodeMetaV3

from codemeticulous import convert as public_convert
from codemeticulous import serialize, validate_document
from codemeticulous.cff.models import CitationFileFormat
from codemeticulous.convert import convert
from codemeticulous.conversion import ConversionError
from codemeticulous.datacite.models import (
    DataCite,
    RelatedIdentifier,
    RelatedIdentifierType,
    RelationType,
)
from codemeticulous.datacite.xml import _schema_path
from codemeticulous.models import Agent, Identifier, SoftwareMetadata

CODEMETA = {
    "@context": "https://w3id.org/codemeta/3.0",
    "@type": "SoftwareSourceCode",
    "@id": "https://doi.org/10.1234/example",
    "identifier": "https://doi.org/10.1234/example",
    "name": "Example Tool",
    "author": {
        "@type": "Person",
        "givenName": "Ada",
        "familyName": "Lovelace",
        "name": "Ada Lovelace",
    },
    "publisher": {"@type": "Organization", "name": "Example Archive"},
    "datePublished": "2024-01-02",
    "description": "A reproducible example.",
    "keywords": ["research software"],
    "license": "https://spdx.org/licenses/MIT",
}


def test_codemeta_json_serializes_and_validates_explicit_version() -> None:
    result = convert(
        "codemeta.json",
        "codemeta.json",
        CODEMETA,
        target_version="3.0",
    )

    document = serialize(result.value, "codemeta.json", "3.0")
    validate_document(document, "codemeta.json", "3.0")

    assert json.loads(document)["@context"] == "https://w3id.org/codemeta/3.0"


@pytest.mark.parametrize("version", ["4.5", "4.6"])
def test_datacite_xml_serializes_and_validates_against_xsd(version: str) -> None:
    result = convert(
        "codemeta",
        "datacite.xml",
        CODEMETA,
        target_version=version,
    )

    document = serialize(result.value, "datacite.xml", version)
    validate_document(document, "datacite.xml", version)

    assert f"kernel-{version}/metadata.xsd" in document
    assert '<identifier identifierType="DOI">10.1234/example</identifier>' in document
    assert 'resourceTypeGeneral="Software"' in document


@pytest.mark.parametrize("version", ["4.5", "4.6"])
def test_datacite_xsd_uses_top_level_schema_resource(version: str) -> None:
    expected = Path(str(files("schema").joinpath("datacite", version, "metadata.xsd")))

    assert _schema_path(version) == expected
    assert expected.is_file()


def test_datacite_versions_produce_distinct_documents() -> None:
    result_45 = convert("codemeta", "datacite", CODEMETA, target_version="4.5")
    result_46 = convert("codemeta", "datacite", CODEMETA, target_version="4.6")

    xml_45 = serialize(result_45.value, "datacite.xml", "4.5")
    xml_46 = serialize(result_46.value, "datacite.xml", "4.6")

    assert xml_45 != xml_46
    with pytest.raises(ValueError, match="does not declare requested"):
        validate_document(xml_45, "datacite.xml", "4.6")


def test_datacite_46_specific_values_are_rejected_by_45() -> None:
    result = convert("codemeta", "datacite", CODEMETA, target_version="4.6")
    record = result.value.model_copy(
        update={
            "relatedIdentifiers": [
                RelatedIdentifier(
                    relatedIdentifier="31253.11.sciencedb.13238",
                    relatedIdentifierType=RelatedIdentifierType.CSTR,
                    relationType=RelationType.IsTranslationOf,
                )
            ]
        }
    )

    xml_46 = serialize(record, "datacite.xml", "4.6")
    validate_document(xml_46, "datacite.xml", "4.6")
    with pytest.raises(ConversionError, match="Invalid DataCite 4.5 XML"):
        serialize(record, "datacite.xml", "4.5")


def test_version_is_required_and_unsupported_versions_fail_clearly() -> None:
    with pytest.raises(TypeError):
        convert("codemeta", "codemeta", CODEMETA)
    with pytest.raises(ConversionError, match="Unsupported codemeta.json version"):
        convert("codemeta", "codemeta.json", CODEMETA, target_version="2.0")


def test_datacite_xml_refuses_to_fabricate_missing_identifier() -> None:
    source = dict(CODEMETA)
    source.pop("@id")
    source.pop("identifier")
    result = convert("codemeta", "datacite.xml", source, target_version="4.6")

    with pytest.raises(ConversionError, match="requires a DOI identifier"):
        serialize(result.value, "datacite.xml", "4.6")


def test_top_level_convert_is_callable() -> None:
    assert public_convert is convert


def test_convert_returns_software_metadata_with_issues() -> None:
    result = convert(
        "codemeta",
        "software-metadata",
        {"@type": "SoftwareSourceCode", "name": "Tool", "author": "Unknown author"},
        target_version="1",
    )

    assert result.value.title == "Tool"
    assert result.issues[0].path == "author[0]"


def test_convert_accepts_canonical_software_metadata_input() -> None:
    source = SoftwareMetadata(
        title="Tool",
        creators=[Agent(kind="person", name="Ada")],
        publisher=Agent(kind="organization", name="Archive"),
        publication_year=2026,
        identifiers=[Identifier(value="10.1234/tool", scheme="DOI")],
    )

    result = convert(
        "software-metadata",
        "datacite.xml",
        source,
        target_version="4.6",
    )

    assert isinstance(result.value, DataCite)
    assert result.value.doi == "10.1234/tool"


def test_convert_accepts_and_validates_structured_collection_input() -> None:
    result = convert(
        "collected-software-metadata",
        "software-metadata",
        {
            "requested_identifier": "https://example.org/tool",
            "metadata": {"title": "Tool"},
            "sources": [
                {
                    "id": "landing-page",
                    "uri": "https://example.org/tool",
                    "kind": "project-page",
                    "retrieved_at": "2026-10-19T00:00:00Z",
                }
            ],
            "fields": [
                {
                    "path": "title",
                    "status": "retrieved",
                    "evidence": [
                        {
                            "source_id": "landing-page",
                            "value": "Tool",
                            "acquisition": "retrieved",
                        }
                    ],
                    "selected_evidence": 0,
                }
            ],
        },
        target_version="1",
    )

    assert result.value.title == "Tool"


def test_convert_rejects_collection_with_unprovenanced_metadata() -> None:
    with pytest.raises(ConversionError, match="lack selected provenance"):
        convert(
            "collected-software-metadata",
            "software-metadata",
            {
                "metadata": {"title": "Tool", "version": "1.0"},
                "sources": [
                    {
                        "id": "landing-page",
                        "uri": "https://example.org/tool",
                        "kind": "project-page",
                        "retrieved_at": "2026-10-19T00:00:00Z",
                    }
                ],
                "fields": [
                    {
                        "path": "title",
                        "status": "retrieved",
                        "evidence": [
                            {
                                "source_id": "landing-page",
                                "value": "Tool",
                                "acquisition": "retrieved",
                            }
                        ],
                        "selected_evidence": 0,
                    }
                ],
            },
            target_version="1",
        )


def test_convert_aggregates_input_and_output_issues() -> None:
    result = convert(
        "codemeta",
        "datacite",
        {
            "@type": "SoftwareSourceCode",
            "name": "Tool",
            "author": "Unknown author",
            "publisher": {"@type": "Organization", "name": "Press"},
            "datePublished": "2024-01-01",
            "downloadUrl": "https://example.org/download",
        },
        target_version="4.6",
    )

    assert result.value.publicationYear == "2024"
    assert [issue.path for issue in result.issues] == [
        "author[0]",
        "download_url",
        "creators[0].kind",
    ]


def test_convert_rejects_unsupported_directions() -> None:
    with pytest.raises(ConversionError):
        convert("datacite", "software-metadata", {}, target_version="1")
    with pytest.raises(ConversionError):
        convert("codemeta", "unknown", {}, target_version="1")


@pytest.mark.parametrize(
    ("target", "expected_type"),
    [
        ("software-metadata", SoftwareMetadata),
        ("codemeta", CodeMetaV3),
        ("cff", CitationFileFormat),
        ("datacite", DataCite),
    ],
)
def test_convert_supports_each_target(target: str, expected_type: type) -> None:
    result = convert(
        "codemeta",
        target,
        {
            "@type": "SoftwareSourceCode",
            "name": "Tool",
            "author": {"@type": "Person", "name": "Ada"},
            "publisher": {"@type": "Organization", "name": "Press"},
            "datePublished": "2024-01-01",
        },
        target_version={
            "software-metadata": "1",
            "codemeta": "3.0",
            "cff": "1.2.0",
            "datacite": "4.6",
        }[target],
    )

    assert isinstance(result.value, expected_type)
