import pytest
from pydantic_codemeta import CodeMetaV3

from codemeticulous.convert import convert
from codemeticulous.conversion import ConversionError
from codemeticulous import convert as public_convert
from codemeticulous.cff.models import CitationFileFormat
from codemeticulous.datacite.models import DataCite
from codemeticulous.models import SoftwareMetadata


def test_top_level_convert_is_callable() -> None:
    assert public_convert is convert


def test_convert_returns_software_metadata_with_issues() -> None:
    result = convert(
        "codemeta",
        "software-metadata",
        {"@type": "SoftwareSourceCode", "name": "Tool", "author": "Unknown author"},
    )

    assert result.value.title == "Tool"
    assert result.issues[0].path == "author[0]"


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
    )

    assert result.value.publicationYear == "2024"
    assert [issue.path for issue in result.issues] == [
        "author[0]",
        "download_url",
        "creators[0].kind",
    ]


def test_convert_rejects_unsupported_directions() -> None:
    with pytest.raises(ConversionError):
        convert("datacite", "software-metadata", {})
    with pytest.raises(ConversionError):
        convert("codemeta", "unknown", {})


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
    )

    assert isinstance(result.value, expected_type)
