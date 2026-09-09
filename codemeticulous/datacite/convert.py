from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError

from codemeticulous.conversion import ConversionError, ConversionIssue, ConversionResult
from codemeticulous.datacite.models import (
    AffiliationItem,
    Contributor,
    ContributorType,
    Creator,
    DataCite,
    DateModel,
    DateType,
    Description,
    DescriptionType,
    NameIdentifier,
    Publisher,
    RelatedIdentifier,
    RelatedIdentifierType,
    RelationType,
    RightsListItem,
    Subject,
    Title,
    Types,
    NameType,
    ResourceTypeGeneral,
)
from codemeticulous.models import (
    Agent,
    Contribution,
    Identifier,
    License,
    RelatedResource,
    SoftwareMetadata,
)


ROLE_TYPES = {
    "contact": ContributorType.ContactPerson,
    "contact person": ContributorType.ContactPerson,
    "researcher": ContributorType.Researcher,
    "scientist": ContributorType.Researcher,
    "editor": ContributorType.Editor,
    "data curator": ContributorType.DataCurator,
    "data manager": ContributorType.DataManager,
    "project manager": ContributorType.ProjectManager,
    "project member": ContributorType.ProjectMember,
    "sponsor": ContributorType.Sponsor,
    "supervisor": ContributorType.Supervisor,
    "translator": ContributorType.Translator,
}


def _issue(path: str, message: str) -> ConversionIssue:
    return ConversionIssue(path=path, message=message)


def _concrete_year(value: date | str | None) -> int | None:
    if isinstance(value, datetime):
        return value.year
    if isinstance(value, date):
        return value.year
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).year
        except ValueError:
            return None
    return None


def _normalize_doi(value: str, path: str) -> str:
    candidate = value.strip()
    if candidate.lower().startswith("doi:"):
        candidate = candidate[4:]
    parsed = urlsplit(candidate)
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc.lower() not in {"doi.org", "dx.doi.org"}:
            raise ConversionError(f"Invalid DOI at {path}")
        candidate = parsed.path.lstrip("/")
    if re.fullmatch(r"10\.\d{4,9}/\S+", candidate) is None:
        raise ConversionError(f"Invalid DOI at {path}")
    return candidate


def _date(value: date | str | None, date_type: DateType) -> DateModel | None:
    if value is None:
        return None
    return DateModel(date=value, dateType=date_type)


def _agent_name_parts(
    agent: Agent, path: str, issues: list[ConversionIssue]
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": agent.name,
        "givenName": agent.given_names[0] if agent.given_names else None,
        "familyName": agent.family_names[0] if agent.family_names else None,
    }
    for field, values in (
        ("given_names", agent.given_names),
        ("family_names", agent.family_names),
    ):
        for index in range(1, len(values)):
            issues.append(
                _issue(
                    f"{path}.{field}[{index}]", "additional name values are unsupported"
                )
            )
    if agent.kind == "person":
        kwargs["nameType"] = NameType.Personal
    elif agent.kind == "organization":
        kwargs["nameType"] = NameType.Organizational
    else:
        issues.append(
            _issue(f"{path}.kind", "unknown agent kind has no DataCite name type")
        )
    return kwargs


def _name_identifiers(
    agent: Agent, path: str, issues: list[ConversionIssue]
) -> list[NameIdentifier] | None:
    result = []
    for index, identifier in enumerate(agent.identifiers):
        if not identifier.scheme:
            issues.append(
                _issue(
                    f"{path}.identifiers[{index}].scheme",
                    "identifier scheme is required by DataCite",
                )
            )
            continue
        result.append(
            NameIdentifier(
                nameIdentifier=identifier.value,
                nameIdentifierScheme=identifier.scheme,
            )
        )
    return result or None


def _affiliations(
    agent: Agent, path: str, issues: list[ConversionIssue]
) -> list[AffiliationItem] | None:
    result = []
    for index, affiliation in enumerate(agent.affiliations):
        kwargs: dict[str, Any] = {"name": affiliation.name}
        if affiliation.identifier:
            kwargs["affiliationIdentifier"] = affiliation.identifier.value
            if affiliation.identifier.scheme:
                kwargs["affiliationIdentifierScheme"] = affiliation.identifier.scheme
            else:
                issues.append(
                    _issue(
                        f"{path}.affiliations[{index}].identifier",
                        "affiliation identifier scheme is required by DataCite",
                    )
                )
                kwargs.pop("affiliationIdentifier")
        result.append(AffiliationItem(**kwargs))
    return result or None


def _person_fields(
    agent: Agent, path: str, issues: list[ConversionIssue]
) -> dict[str, Any]:
    fields = _agent_name_parts(agent, path, issues)
    if agent.email:
        issues.append(_issue(f"{path}.email", "email is unsupported by DataCite"))
    if agent.url:
        issues.append(_issue(f"{path}.url", "agent URL is unsupported by DataCite"))
    fields["nameIdentifiers"] = _name_identifiers(agent, path, issues)
    fields["affiliation"] = _affiliations(agent, path, issues)
    return fields


def _creator(agent: Agent, path: str, issues: list[ConversionIssue]) -> Creator:
    return Creator(**_person_fields(agent, path, issues))


def _contributor_type(
    roles: list[str], path: str, issues: list[ConversionIssue]
) -> ContributorType:
    if not roles:
        return ContributorType.Other
    normalized = roles[0].strip().lower()
    result = ROLE_TYPES.get(normalized)
    if result is None:
        issues.append(
            _issue(
                f"{path}.roles[0]",
                "role is not representable as a DataCite contributor type",
            )
        )
        result = ContributorType.Other
    for index in range(1, len(roles)):
        issues.append(
            _issue(f"{path}.roles[{index}]", "additional roles are unsupported")
        )
    return result


def _contributor(
    contribution: Contribution, path: str, issues: list[ConversionIssue]
) -> Contributor:
    fields = _person_fields(contribution.agent, f"{path}.agent", issues)
    fields["contributorType"] = _contributor_type(contribution.roles, path, issues)
    return Contributor(**fields)


def _publisher(agent: Agent, path: str, issues: list[ConversionIssue]) -> Publisher:
    fields: dict[str, Any] = {"name": agent.name}
    for field in ("given_names", "family_names", "email", "url"):
        if getattr(agent, field):
            issues.append(
                _issue(f"{path}.{field}", "publisher field is unsupported by DataCite")
            )
    if agent.identifiers:
        first = agent.identifiers[0]
        fields["publisherIdentifier"] = first.value
        fields["publisherIdentifierScheme"] = first.scheme
        for index in range(1, len(agent.identifiers)):
            issues.append(
                _issue(
                    f"{path}.identifiers[{index}]",
                    "additional publisher identifiers are unsupported",
                )
            )
    for index in range(len(agent.affiliations)):
        issues.append(
            _issue(
                f"{path}.affiliations[{index}]",
                "publisher affiliations are unsupported",
            )
        )
    return Publisher(**fields)


def _identifier_type(
    identifier: Identifier, path: str, issues: list[ConversionIssue]
) -> RelatedIdentifierType | None:
    if not identifier.scheme:
        issues.append(
            _issue(
                f"{path}.scheme", "related identifier scheme is required by DataCite"
            )
        )
        return None
    normalized = identifier.scheme.lower()
    for item in RelatedIdentifierType:
        if item.value.lower() == normalized:
            return item
    issues.append(
        _issue(f"{path}.scheme", "related identifier scheme is unsupported by DataCite")
    )
    return None


def _related(
    resource: RelatedResource, index: int, issues: list[ConversionIssue]
) -> RelatedIdentifier | None:
    path = f"relations[{index}]"
    identifier = resource.identifier
    url_identifier = identifier is None and resource.url is not None
    if identifier is None and resource.url is not None:
        identifier = Identifier(value=resource.url, scheme="URL")
    if not identifier:
        issues.append(
            _issue(f"{path}.identifier", "related resource requires an identifier")
        )
        return None
    identifier_type = _identifier_type(identifier, f"{path}.identifier", issues)
    if identifier_type is None:
        return None
    relation = {
        "cites": RelationType.Cites,
        "requires": RelationType.Requires,
        "is_part_of": RelationType.IsPartOf,
        "has_part": RelationType.HasPart,
        "same_as": RelationType.IsIdenticalTo,
    }.get(resource.relation)
    if relation is None:
        issues.append(_issue(path, "relation is unsupported by DataCite"))
        return None
    if resource.title:
        issues.append(
            _issue(f"{path}.title", "related resource field is unsupported by DataCite")
        )
    if resource.resource_type:
        issues.append(
            _issue(
                f"{path}.resource_type",
                "related resource field is unsupported by DataCite",
            )
        )
    if resource.url and not url_identifier:
        issues.append(
            _issue(f"{path}.url", "related resource field is unsupported by DataCite")
        )
    for creator_index in range(len(resource.creators)):
        issues.append(
            _issue(
                f"{path}.creators[{creator_index}]",
                "related resource creators are unsupported by DataCite",
            )
        )
    return RelatedIdentifier(
        relatedIdentifier=identifier.value,
        relatedIdentifierType=identifier_type,
        relationType=relation,
    )


def _software_metadata_to_datacite(
    value: SoftwareMetadata,
) -> ConversionResult[DataCite]:
    issues: list[ConversionIssue] = []
    if not value.creators:
        raise ConversionError("DataCite requires at least one creator")
    if value.publisher is None:
        raise ConversionError("DataCite requires a publisher")
    publication_year = value.publication_year
    if publication_year is None:
        publication_year = _concrete_year(value.date_released)
    if publication_year is None:
        raise ConversionError("DataCite requires a concrete publication year")

    descriptions = []
    if value.description:
        descriptions.append(
            Description(
                description=value.description, descriptionType=DescriptionType.Abstract
            )
        )
    descriptions.extend(
        Description(description=note, descriptionType=DescriptionType.TechnicalInfo)
        for note in value.release_notes
    )
    rights = []
    for index, item in enumerate(value.licenses):
        if not item.identifier and not item.name and not item.url:
            issues.append(
                _issue(f"licenses[{index}]", "empty license is not representable")
            )
            continue
        rights.append(
            RightsListItem(
                rights=item.name, rightsUri=item.url, rightsIdentifier=item.identifier
            )
        )
    identifiers = list(value.identifiers)
    for index, identifier in enumerate(identifiers):
        if (identifier.scheme or "").lower() == "doi":
            identifiers[index] = Identifier(
                value=_normalize_doi(identifier.value, f"identifiers[{index}]"),
                scheme=identifier.scheme,
            )
    doi_index = next(
        (
            index
            for index, item in enumerate(identifiers)
            if (item.scheme or "").lower() == "doi"
        ),
        None,
    )
    doi = identifiers[doi_index].value if doi_index is not None else None
    doi_prefix = doi.split("/", 1)[0] if doi and "/" in doi else None
    doi_suffix = doi.split("/", 1)[1] if doi and "/" in doi else None
    alternate_identifiers = []
    for index, identifier in enumerate(identifiers):
        if index == doi_index:
            continue
        if (identifier.scheme or "").lower() == "doi":
            issues.append(
                _issue(
                    f"identifiers[{index}]",
                    "additional DOI demoted to an alternate identifier",
                )
            )
        alternate_identifiers.append(
            {
                "alternateIdentifier": identifier.value,
                "alternateIdentifierType": identifier.scheme or "Other",
            }
        )

    dates = [
        item
        for item in (
            _date(value.date_released, DateType.Available),
            _date(value.date_created, DateType.Created),
            _date(value.date_modified, DateType.Updated),
        )
        if item is not None
    ]
    if value.repository:
        issues.append(_issue("repository", "repository is unsupported by DataCite"))
    if value.repository_code:
        issues.append(
            _issue("repository_code", "repository_code is unsupported by DataCite")
        )
    if value.repository_artifact:
        issues.append(
            _issue(
                "repository_artifact", "repository_artifact is unsupported by DataCite"
            )
        )
    if value.download_url:
        issues.append(_issue("download_url", "download URL is unsupported by DataCite"))

    creators = [
        _creator(agent, f"creators[{index}]", issues)
        for index, agent in enumerate(value.creators)
    ]
    contributors = [
        _contributor(item, f"contributors[{index}]", issues)
        for index, item in enumerate(value.contributors)
    ]
    related = [
        item
        for index, resource in enumerate(value.relations)
        if (item := _related(resource, index, issues)) is not None
    ]

    payload: dict[str, Any] = {
        "doi": doi,
        "prefix": doi_prefix,
        "suffix": doi_suffix,
        "url": value.url,
        "types": Types(
            resourceType=value.category,
            resourceTypeGeneral=ResourceTypeGeneral.Software,
        ),
        "creators": creators,
        "titles": [Title(title=value.title)],
        "publisher": _publisher(value.publisher, "publisher", issues),
        "publicationYear": str(publication_year),
        "subjects": [Subject(subject=item) for item in value.keywords] or None,
        "contributors": contributors or None,
        "dates": dates or None,
        "alternateIdentifiers": alternate_identifiers or None,
        "relatedIdentifiers": related or None,
        "sizes": value.sizes or None,
        "formats": [*value.programming_languages, *value.formats] or None,
        "version": value.version,
        "rightsList": rights or None,
        "descriptions": descriptions or None,
    }
    try:
        result = DataCite.model_validate(payload)
    except ValidationError as exc:
        raise ConversionError(f"Unable to construct DataCite: {exc}") from exc
    return ConversionResult(value=result, issues=tuple(issues))


def software_metadata_to_datacite(
    value: SoftwareMetadata,
) -> ConversionResult[DataCite]:
    """Convert canonical software metadata to a validated DataCite record."""

    try:
        return _software_metadata_to_datacite(value)
    except ConversionError:
        raise
    except ValidationError as exc:
        raise ConversionError(f"Unable to construct DataCite: {exc}") from exc


__all__ = ["software_metadata_to_datacite"]
