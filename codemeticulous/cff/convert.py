"""Conversion from the neutral metadata model to Citation File Format."""

from __future__ import annotations

from datetime import date
import re
from typing import Any

from pydantic import ValidationError

from codemeticulous.conversion import ConversionError, ConversionIssue, ConversionResult
from codemeticulous.models import (
    Agent,
    Identifier,
    License,
    RelatedResource,
    SoftwareMetadata,
)
from codemeticulous.cff.identifiers import (
    CffIdentifier,
    DoiIdentifier,
    OtherIdentifier,
    SwhIdentifier,
    UrlIdentifier,
)
from codemeticulous.cff.models import (
    CitationFileFormat,
    Entity,
    LicenseEnum,
    Person,
    Reference,
)


_DOI = re.compile(
    r"^(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}(?:\.\d+)?/[A-Za-z0-9:/_;\-.()\[\]\\]+)$"
)
_SWH = re.compile(r"^swh:1:(?:snp|rel|rev|dir|cnt):[0-9a-fA-F]{40}$")
_SPDX = {item.value for item in LicenseEnum}
_REFERENCE_TYPES = {
    "software": "software",
    "software-code": "software-code",
    "software_code": "software-code",
    "article": "article",
    "scholarlyarticle": "article",
    "book": "book",
    "blog": "blog",
    "website": "website",
}


def _issue(path: str, message: str) -> ConversionIssue:
    return ConversionIssue(path=path, message=message)


def _agent(agent: Agent, path: str, issues: list[ConversionIssue]) -> Person | Entity:
    kwargs: dict[str, Any] = {"name": agent.name}
    if agent.email:
        kwargs["email"] = agent.email
    if agent.url:
        kwargs["website"] = agent.url
    selected_orcid = False
    for index, identifier in enumerate(agent.identifiers):
        if (identifier.scheme or "").lower() == "orcid" and not selected_orcid:
            kwargs["orcid"] = identifier.value
            selected_orcid = True
        else:
            issues.append(
                _issue(
                    f"{path}.identifiers[{index}]",
                    "additional agent identifier is unsupported in CFF",
                )
            )
    if agent.kind == "person":
        kwargs.pop("name")
        if agent.affiliations:
            kwargs["affiliation"] = agent.affiliations[0].name
            for index in range(1, len(agent.affiliations)):
                issues.append(
                    _issue(
                        f"{path}.affiliations[{index}]",
                        "additional affiliation is unsupported in CFF",
                    )
                )
            for index, affiliation in enumerate(agent.affiliations):
                if affiliation.identifier:
                    issues.append(
                        _issue(
                            f"{path}.affiliations[{index}].identifier",
                            "affiliation identifier is unsupported in CFF",
                        )
                    )
        if agent.given_names:
            kwargs["given_names"] = " ".join(agent.given_names)
        if agent.family_names:
            kwargs["family_names"] = " ".join(agent.family_names)
        if not agent.given_names and not agent.family_names:
            kwargs["given_names"] = agent.name
        return Person(**kwargs)
    if agent.kind == "organization":
        for index, affiliation in enumerate(agent.affiliations):
            issues.append(
                _issue(
                    f"{path}.affiliations[{index}]",
                    "organization affiliation is unsupported in CFF",
                )
            )
            if affiliation.identifier:
                issues.append(
                    _issue(
                        f"{path}.affiliations[{index}].identifier",
                        "affiliation identifier is unsupported in CFF",
                    )
                )
        return Entity(**kwargs)
    issues.append(_issue(path, "unknown agent kind represented as a CFF entity"))
    for index, affiliation in enumerate(agent.affiliations):
        issues.append(
            _issue(
                f"{path}.affiliations[{index}]",
                "organization affiliation is unsupported in CFF",
            )
        )
        if affiliation.identifier:
            issues.append(
                _issue(
                    f"{path}.affiliations[{index}].identifier",
                    "affiliation identifier is unsupported in CFF",
                )
            )
    return Entity(**kwargs)


def _identifier(identifier: Identifier, path: str) -> CffIdentifier:
    scheme = (identifier.scheme or "").lower()
    value = identifier.value
    if scheme == "doi":
        match = _DOI.match(value)
        if not match:
            raise ConversionError(f"{path}: invalid DOI")
        return DoiIdentifier(type="doi", value=match.group(1))
    if scheme in {"swh", "softwareheritage"}:
        return SwhIdentifier(type="swh", value=value)
    if scheme in {"url", "uri"}:
        return UrlIdentifier(type="url", value=value)
    if scheme == "other":
        return OtherIdentifier(type="other", value=value)
    match = _DOI.match(value)
    if match:
        return DoiIdentifier(type="doi", value=match.group(1))
    if _SWH.match(value):
        return SwhIdentifier(type="swh", value=value)
    if value.startswith(("http://", "https://")):
        return UrlIdentifier(type="url", value=value)
    return OtherIdentifier(type="other", value=value)


def _licenses(
    value: list[License], issues: list[ConversionIssue]
) -> tuple[str | None, str | None]:
    selected: tuple[str | None, str | None] | None = None
    selected_index: int | None = None
    for index, license_ in enumerate(value):
        candidate = license_.identifier or license_.name
        if candidate:
            candidate = (
                candidate.rsplit("/", 1)[-1]
                if candidate.startswith("https://spdx.org/licenses/")
                else candidate
            )
        if candidate in _SPDX:
            selected = (candidate, None)
        elif license_.url:
            selected = (None, license_.url)
        else:
            issues.append(
                _issue(f"licenses[{index}]", "license is not representable in CFF")
            )
            continue
        selected_index = index
        break
    if selected is not None and selected_index is not None:
        for index in range(selected_index + 1, len(value)):
            if value[index].identifier or value[index].name or value[index].url:
                issues.append(
                    _issue(
                        f"licenses[{index}]", "additional license is unsupported in CFF"
                    )
                )
    return selected or (None, None)


def _reference(
    resource: RelatedResource, path: str, issues: list[ConversionIssue]
) -> Reference | None:
    if resource.relation not in {"cites", "requires"}:
        issues.append(
            _issue(path, f"relation {resource.relation!r} is not representable in CFF")
        )
        return None
    if not resource.title:
        issues.append(_issue(f"{path}.title", "CFF references require a title"))
        return None
    if not resource.creators:
        issues.append(_issue(f"{path}.creators", "CFF references require authors"))
        return None
    type_name = _REFERENCE_TYPES.get((resource.resource_type or "").lower())
    if type_name is None:
        type_name = "generic"
        if resource.resource_type:
            issues.append(
                _issue(
                    f"{path}.resource_type",
                    "unsupported resource type mapped to CFF generic reference",
                )
            )
    if resource.relation == "requires":
        issues.append(
            _issue(
                f"{path}.relation",
                "CFF reference does not preserve requires dependency semantics",
            )
        )
    kwargs: dict[str, Any] = {
        "title": resource.title,
        "type": type_name,
        "authors": [
            _agent(agent, f"{path}.creators[{i}]", issues)
            for i, agent in enumerate(resource.creators)
        ],
    }
    if resource.url:
        kwargs["url"] = resource.url
    if resource.identifier:
        mapped = _identifier(resource.identifier, f"{path}.identifier")
        if mapped.type == "doi":
            kwargs["doi"] = mapped.value
        elif mapped.type == "url":
            kwargs["url"] = mapped.value
        else:
            issues.append(
                _issue(
                    f"{path}.identifier",
                    "identifier type is not representable on a CFF reference",
                )
            )
    return Reference(**kwargs)


def _convert(value: SoftwareMetadata) -> ConversionResult[CitationFileFormat]:
    """Convert neutral software metadata to CFF, retaining deterministic issues."""
    if not value.creators:
        raise ConversionError("creators: CFF requires at least one author")

    issues: list[ConversionIssue] = []
    unsupported = (
        ("publisher", value.publisher),
        ("contributors", value.contributors),
        ("category", value.category),
        ("publication_year", value.publication_year),
        ("date_created", value.date_created),
        ("date_modified", value.date_modified),
        ("programming_languages", value.programming_languages),
        ("formats", value.formats),
        ("sizes", value.sizes),
        ("release_notes", value.release_notes),
    )
    for path, item in unsupported:
        if item:
            issues.append(_issue(path, "canonical value is not representable in CFF"))
    identifiers: list[CffIdentifier] = []
    doi: str | None = None
    for index, item in enumerate(value.identifiers):
        mapped = _identifier(item, f"identifiers[{index}]")
        if mapped.type == "doi" and doi is None:
            doi = mapped.value
        else:
            if mapped.type == "doi":
                issues.append(
                    _issue(
                        f"identifiers[{index}]",
                        "only the first DOI is supported as the primary CFF DOI",
                    )
                )
            identifiers.append(mapped)

    license_, license_url = _licenses(value.licenses, issues)
    url = value.url or value.download_url
    if value.url and value.download_url:
        issues.append(
            _issue("download_url", "url takes precedence over download_url in CFF")
        )

    references: list[Reference] = []
    for index, relation in enumerate(value.relations):
        reference = _reference(relation, f"relations[{index}]", issues)
        if reference is not None:
            references.append(reference)

    date_released: date | None = value.date_released  # type: ignore[assignment]
    if isinstance(value.date_released, str):
        try:
            date_released = date.fromisoformat(value.date_released)
        except ValueError as exc:
            raise ConversionError(
                "date_released: value is not a valid ISO date"
            ) from exc

    payload: dict[str, Any] = {
        "cff_version": "1.2.0",
        "message": "If you use this software, please cite it using the metadata from this file.",
        "title": value.title,
        "type": "software",
        "abstract": value.description,
        "authors": [
            _agent(agent, f"creators[{i}]", issues)
            for i, agent in enumerate(value.creators)
        ],
        "date_released": date_released,
        "doi": doi,
        "identifiers": identifiers or None,
        "version": value.version,
        "keywords": value.keywords or None,
        "license": license_,
        "license_url": license_url,
        "repository": value.repository,
        "repository_code": value.repository_code,
        "repository_artifact": value.repository_artifact,
        "url": url,
        "references": references or None,
    }
    try:
        result = CitationFileFormat(**payload)
    except ValidationError as exc:
        raise ConversionError(f"Unable to construct CitationFileFormat: {exc}") from exc
    return ConversionResult(value=result, issues=tuple(issues))


def software_metadata_to_cff(
    value: SoftwareMetadata,
) -> ConversionResult[CitationFileFormat]:
    try:
        return _convert(value)
    except ConversionError:
        raise
    except ValidationError as exc:
        raise ConversionError(f"Unable to construct CitationFileFormat: {exc}") from exc


__all__ = ["software_metadata_to_cff"]
