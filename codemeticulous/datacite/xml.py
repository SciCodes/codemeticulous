from __future__ import annotations

from enum import Enum
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from lxml import etree

from codemeticulous.conversion import ConversionError
from codemeticulous.datacite.models import DataCite

DATACITE_NAMESPACE = "http://datacite.org/schema/kernel-4"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
SUPPORTED_XML_VERSIONS = ("4.5", "4.6")


def _value(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _attributes(**values: Any) -> dict[str, str]:
    return {key: _value(value) for key, value in values.items() if value is not None}


def _element(
    parent: etree._Element,
    name: str,
    text: Any = None,
    attributes: dict[str, str] | None = None,
) -> etree._Element:
    child = etree.SubElement(parent, f"{{{DATACITE_NAMESPACE}}}{name}")
    if attributes:
        for key, value in attributes.items():
            child.set(key, value)
    if text is not None:
        child.text = _value(text)
    return child


def _language(attributes: dict[str, str], language: str | None) -> None:
    if language:
        attributes[f"{{{XML_NAMESPACE}}}lang"] = language


def _person(parent: etree._Element, person: Any, *, contributor: bool) -> None:
    element_name = "contributor" if contributor else "creator"
    attributes = (
        _attributes(contributorType=person.contributorType) if contributor else {}
    )
    element = _element(parent, element_name, attributes=attributes)
    name_attributes = _attributes(nameType=person.nameType)
    _language(name_attributes, person.lang)
    _element(
        element,
        "contributorName" if contributor else "creatorName",
        person.name,
        name_attributes,
    )
    if person.givenName is not None:
        _element(element, "givenName", person.givenName)
    if person.familyName is not None:
        _element(element, "familyName", person.familyName)
    for identifier in person.nameIdentifiers or ():
        _element(
            element,
            "nameIdentifier",
            identifier.nameIdentifier,
            _attributes(
                nameIdentifierScheme=identifier.nameIdentifierScheme,
                schemeURI=identifier.schemeUri,
            ),
        )
    for affiliation in person.affiliation or ():
        _element(
            element,
            "affiliation",
            affiliation.name,
            _attributes(
                affiliationIdentifier=affiliation.affiliationIdentifier,
                affiliationIdentifierScheme=affiliation.affiliationIdentifierScheme,
                schemeURI=affiliation.schemeUri,
            ),
        )


def _schema_path(version: str) -> Path:
    if version not in SUPPORTED_XML_VERSIONS:
        choices = ", ".join(SUPPORTED_XML_VERSIONS)
        raise ValueError(
            f"Unsupported DataCite XML version: {version}. Supported: {choices}"
        )
    resource = files("schema").joinpath("datacite", version, "metadata.xsd")
    return Path(str(resource))


@lru_cache(maxsize=None)
def _schema(version: str) -> etree.XMLSchema:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.XMLSchema(etree.parse(str(_schema_path(version)), parser))


def validate_datacite_xml(document: str | bytes, version: str) -> None:
    schema_url = f"https://schema.datacite.org/meta/kernel-{version}/metadata.xsd"
    try:
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        root = etree.fromstring(
            document.encode("utf-8") if isinstance(document, str) else document,
            parser,
        )
        actual_location = root.get(f"{{{XSI_NAMESPACE}}}schemaLocation", "")
        if schema_url not in actual_location.split():
            raise ValueError(
                f"schemaLocation does not declare requested DataCite version {version}"
            )
        _schema(version).assertValid(root)
    except (etree.XMLSyntaxError, etree.DocumentInvalid, OSError) as exc:
        raise ValueError(f"Invalid DataCite {version} XML: {exc}") from exc


def to_datacite_xml(value: DataCite, version: str) -> str:
    _schema_path(version)
    if value.doi is None:
        raise ConversionError("DataCite XML requires a DOI identifier")
    unsupported = [
        name
        for name in ("relatedItems", "geoLocations", "fundingReferences", "container")
        if getattr(value, name) is not None
    ]
    if unsupported:
        raise ConversionError(
            "DataCite XML serialization does not yet support: " + ", ".join(unsupported)
        )

    schema_url = f"https://schema.datacite.org/meta/kernel-{version}/metadata.xsd"
    root = etree.Element(
        f"{{{DATACITE_NAMESPACE}}}resource",
        nsmap={None: DATACITE_NAMESPACE, "xsi": XSI_NAMESPACE},
    )
    root.set(
        f"{{{XSI_NAMESPACE}}}schemaLocation",
        f"{DATACITE_NAMESPACE} {schema_url}",
    )

    _element(root, "identifier", value.doi, {"identifierType": "DOI"})
    creators = _element(root, "creators")
    for creator in value.creators:
        _person(creators, creator, contributor=False)

    titles = _element(root, "titles")
    for title in value.titles:
        attributes = _attributes(titleType=title.titleType)
        _language(attributes, title.lang)
        _element(titles, "title", title.title, attributes)

    publisher_attributes = _attributes(
        publisherIdentifier=value.publisher.publisherIdentifier,
        publisherIdentifierScheme=value.publisher.publisherIdentifierScheme,
        schemeURI=value.publisher.schemeUri,
    )
    _language(publisher_attributes, value.publisher.lang)
    _element(root, "publisher", value.publisher.name, publisher_attributes)
    _element(root, "publicationYear", value.publicationYear)
    _element(
        root,
        "resourceType",
        value.types.resourceType,
        _attributes(resourceTypeGeneral=value.types.resourceTypeGeneral),
    )

    if value.subjects:
        subjects = _element(root, "subjects")
        for subject in value.subjects:
            attributes = _attributes(
                subjectScheme=subject.subjectScheme,
                schemeURI=subject.schemeUri,
                valueURI=subject.valueUri,
                classificationCode=subject.classificationCode,
            )
            _language(attributes, subject.lang)
            _element(subjects, "subject", subject.subject, attributes)

    if value.contributors:
        contributors = _element(root, "contributors")
        for contributor in value.contributors:
            _person(contributors, contributor, contributor=True)

    if value.dates:
        dates = _element(root, "dates")
        for item in value.dates:
            _element(
                dates,
                "date",
                item.date,
                _attributes(
                    dateType=item.dateType, dateInformation=item.dateInformation
                ),
            )
    if value.language is not None:
        _element(root, "language", value.language)
    if value.alternateIdentifiers:
        identifiers = _element(root, "alternateIdentifiers")
        for item in value.alternateIdentifiers:
            _element(
                identifiers,
                "alternateIdentifier",
                item.alternateIdentifier,
                _attributes(
                    alternateIdentifierType=item.alternateIdentifierType,
                ),
            )
    if value.relatedIdentifiers:
        identifiers = _element(root, "relatedIdentifiers")
        for item in value.relatedIdentifiers:
            _element(
                identifiers,
                "relatedIdentifier",
                item.relatedIdentifier,
                _attributes(
                    relatedIdentifierType=item.relatedIdentifierType,
                    relationType=item.relationType,
                    relatedMetadataScheme=item.relatedMetadataScheme,
                    schemeURI=item.schemeUri,
                    schemeType=item.schemeType,
                    resourceTypeGeneral=item.resourceTypeGeneral,
                ),
            )
    if value.sizes:
        sizes = _element(root, "sizes")
        for item in value.sizes:
            _element(sizes, "size", item)
    if value.formats:
        formats = _element(root, "formats")
        for item in value.formats:
            _element(formats, "format", item)
    if value.version is not None:
        _element(root, "version", value.version)
    if value.rightsList:
        rights = _element(root, "rightsList")
        for item in value.rightsList:
            attributes = _attributes(
                rightsURI=item.rightsUri,
                rightsIdentifier=item.rightsIdentifier,
                rightsIdentifierScheme=item.rightsIdentifierScheme,
                schemeURI=item.schemeUri,
            )
            _language(attributes, item.lang)
            _element(rights, "rights", item.rights, attributes)
    if value.descriptions:
        descriptions = _element(root, "descriptions")
        for item in value.descriptions:
            attributes = _attributes(descriptionType=item.descriptionType)
            _language(attributes, item.lang)
            _element(descriptions, "description", item.description, attributes)

    document = etree.tostring(
        root, encoding="UTF-8", xml_declaration=True, pretty_print=True
    ).decode("utf-8")
    try:
        validate_datacite_xml(document, version)
    except ValueError as exc:
        raise ConversionError(str(exc)) from exc
    return document


__all__ = [
    "DATACITE_NAMESPACE",
    "SUPPORTED_XML_VERSIONS",
    "to_datacite_xml",
    "validate_datacite_xml",
]
