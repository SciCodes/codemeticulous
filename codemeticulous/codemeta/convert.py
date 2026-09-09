from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic_codemeta import (
    CreativeWork,
    Organization,
    Person,
    PropertyValue,
    Role,
    ScholarlyArticle,
    SoftwareSourceCode,
)

from codemeticulous.codemeta.models import CodeMetaV3
from codemeticulous.conversion import ConversionError, ConversionIssue, ConversionResult
from codemeticulous.models import (
    Agent,
    Affiliation,
    Contribution,
    Identifier,
    License,
    RelatedResource,
    SoftwareMetadata,
)


RELATIONS = {
    "citation": "cites",
    "softwareRequirements": "requires",
    "isPartOf": "is_part_of",
    "hasPart": "has_part",
    "sameAs": "same_as",
}
REVERSE_RELATIONS = {value: key for key, value in RELATIONS.items()}
UNSUPPORTED_SOURCE_FIELDS = (
    "applicationSubCategory",
    "targetProduct",
    "runtimePlatform",
    "softwareHelp",
    "softwareVersion",
    "storageRequirements",
    "supportingData",
    "maintainer",
    "contIntegration",
    "continuousIntegration",
    "developmentStatus",
    "embargoDate",
    "embargoEndDate",
    "funding",
    "hasSourceCode",
    "isSourceCodeOf",
    "issueTracker",
    "readme",
    "referencePublication",
    "review",
    "encoding",
    "funder",
    "sponsor",
    "provider",
    "producer",
    "copyrightHolder",
    "copyrightYear",
    "editor",
    "installUrl",
    "memoryRequirements",
    "operatingSystem",
    "permissions",
    "processorRequirements",
    "isAccessibleForFree",
    "relatedLink",
    "position",
    "buildInstructions",
    "softwareSuggestions",
)


def _items(value: Any) -> list[Any]:
    return [] if value is None else value if isinstance(value, list) else [value]


def _issue(path: str, message: str) -> ConversionIssue:
    return ConversionIssue(path=path, message=message)


def _field_value(model: BaseModel, jsonld_name: str) -> Any:
    """Read a model field by its external JSON-LD name."""
    for name, field in type(model).model_fields.items():
        if name == jsonld_name or field.alias == jsonld_name:
            return getattr(model, name)
    return None


def _identifier(value: Any) -> Identifier | None:
    if isinstance(value, PropertyValue):
        if value.value is None:
            return None
        return Identifier(value=str(value.value), scheme=value.property_id)
    if isinstance(value, str):
        return Identifier(value=value)
    return None


def _source_identifiers(
    value: Any, path: str, issues: list[ConversionIssue]
) -> list[Identifier]:
    result = []
    for index, item in enumerate(_items(value)):
        identifier = _identifier(item)
        if identifier is None:
            issues.append(_issue(f"{path}[{index}]", "identifier is not representable"))
        else:
            result.append(identifier)
    return result


def _source_identifier(
    value: Any, path: str, issues: list[ConversionIssue]
) -> Identifier | None:
    values = _items(value)
    if len(values) > 1:
        for index in range(1, len(values)):
            issues.append(
                _issue(f"{path}[{index}]", "additional identifiers are unsupported")
            )
    if not values:
        return None
    identifier = _identifier(values[0])
    if identifier is None:
        issues.append(_issue(f"{path}[0]", "identifier is not representable"))
    return identifier


def _source_url(value: Any, path: str, issues: list[ConversionIssue]) -> str | None:
    values = _items(value)
    if not values:
        return None
    if len(values) > 1:
        for index in range(1, len(values)):
            issues.append(_issue(f"{path}[{index}]", "additional URLs are unsupported"))
    return str(values[0])


def _year(value: Any) -> int | None:
    if isinstance(value, (date, datetime)):
        return value.year
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).year
        except ValueError:
            if len(value) == 4 and value.isdigit():
                return int(value)
    return None


def _actor_index(values: list[Any]) -> dict[str, Any]:
    return {
        item.id: item
        for item in values
        if isinstance(item, (Person, Organization)) and item.id
    }


def _agent(
    value: Any,
    path: str,
    issues: list[ConversionIssue],
    concrete_by_id: dict[str, Any],
) -> Agent | None:
    if isinstance(value, Role):
        nested = value.author
        if isinstance(nested, str):
            nested = concrete_by_id.get(nested)
        elif getattr(nested, "id", None) in concrete_by_id:
            nested = concrete_by_id[nested.id]
        if nested is None and value.id:
            nested = concrete_by_id.get(value.id)
        if nested is None:
            issues.append(_issue(path, "role has no resolvable actor"))
            return None
        return _agent(nested, f"{path}.author", issues, concrete_by_id)

    if isinstance(value, str):
        issues.append(_issue(path, "untyped agent string mapped to kind 'unknown'"))
        return Agent(kind="unknown", name=value)
    if not isinstance(value, (Person, Organization)):
        issues.append(_issue(path, "agent is not representable"))
        return None

    kind = "person" if isinstance(value, Person) else "organization"
    name = value.name or ""
    if not name:
        issues.append(_issue(f"{path}.name", "agent name is missing"))
    identifiers = _source_identifiers(value.identifier, f"{path}.identifier", issues)
    if value.id:
        identifiers.append(Identifier(value=value.id))
        issues.append(_issue(f"{path}.@id", "node identity is not represented"))

    affiliations = []
    for index, affiliation in enumerate(_items(getattr(value, "affiliation", None))):
        if isinstance(affiliation, Organization):
            affiliations.append(
                Affiliation(
                    name=affiliation.name or "",
                    identifier=_source_identifier(
                        affiliation.identifier,
                        f"{path}.affiliation[{index}].identifier",
                        issues,
                    ),
                )
            )
        elif isinstance(affiliation, str):
            affiliations.append(Affiliation(name=affiliation))
        else:
            issues.append(
                _issue(
                    f"{path}.affiliation[{index}]", "affiliation is not representable"
                )
            )

    return Agent(
        kind=kind,
        name=name,
        given_names=[
            str(item) for item in _items(getattr(value, "given_name", None))
        ],
        family_names=[
            str(item) for item in _items(getattr(value, "family_name", None))
        ],
        email=value.email,
        url=_source_url(value.url, f"{path}.url", issues),
        identifiers=identifiers,
        affiliations=affiliations,
    )


def _agent_key(agent: Agent) -> tuple[str, str]:
    identity = agent.identifiers[0].value if agent.identifiers else agent.name
    return agent.kind or "unknown", identity


def _actor_values(
    value: Any,
    path: str,
    issues: list[ConversionIssue],
    include_role_agents: bool = False,
) -> tuple[list[Agent], list[Contribution]]:
    values = _items(value)
    concrete_by_id = _actor_index(values)
    agents: list[Agent] = []
    contributions: list[Contribution] = []
    creator_keys: set[tuple[str, str]] = set()
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        if isinstance(item, Role):
            agent = _agent(item, item_path, issues, concrete_by_id)
            if agent is not None:
                contributions.append(
                    Contribution(
                        agent=agent,
                        roles=[item.role_name] if item.role_name else [],
                    )
                )
                if include_role_agents and _agent_key(agent) not in creator_keys:
                    agents.append(agent)
                    creator_keys.add(_agent_key(agent))
            continue
        agent = _agent(item, item_path, issues, concrete_by_id)
        if agent is None:
            continue
        key = _agent_key(agent)
        if key in creator_keys:
            continue
        creator_keys.add(key)
        agents.append(agent)
    if not include_role_agents and contributions:
        role_keys = {_agent_key(contribution.agent) for contribution in contributions}
        agents = [agent for agent in agents if _agent_key(agent) not in role_keys]
    return agents, contributions


def _related(
    value: Any, relation: str, path: str, issues: list[ConversionIssue]
) -> RelatedResource:
    if isinstance(value, str):
        return RelatedResource(relation=relation, url=value)
    if not isinstance(value, CreativeWork):
        raise ConversionError(f"Unsupported related resource at {path}")
    identifier = _source_identifier(
        value.identifier, f"{path}.identifier", issues
    ) or _identifier(value.id)
    if value.id:
        issues.append(_issue(f"{path}.@id", "node identity is not represented"))
    return RelatedResource(
        relation=relation,
        identifier=identifier,
        title=value.name,
        resource_type=value.type,
        url=_source_url(value.url, f"{path}.url", issues),
        creators=_actor_values(value.author, f"{path}.author", issues)[0],
    )


def _licenses(value: Any, issues: list[ConversionIssue]) -> list[License]:
    result = []
    for index, item in enumerate(_items(value)):
        if isinstance(item, str):
            result.append(License(url=item))
        elif isinstance(item, CreativeWork):
            identifier = _source_identifier(
                item.identifier, f"license[{index}].identifier", issues
            )
            result.append(
                License(
                    identifier=identifier.value if identifier else None,
                    name=item.name,
                    url=_source_url(item.url, f"license[{index}].url", issues),
                )
            )
        else:
            issues.append(_issue(f"license[{index}]", "license is not representable"))
    return result


def codemeta_to_software_metadata(
    data: CodeMetaV3,
) -> ConversionResult[SoftwareMetadata]:
    issues: list[ConversionIssue] = []
    if data.id:
        issues.append(_issue("@id", "node identity is not represented"))
    creators, creator_contributions = _actor_values(
        data.author, "author", issues, include_role_agents=True
    )
    contributor_agents, contributor_contributions = _actor_values(
        data.contributor, "contributor", issues
    )
    relations = []
    for field, relation in RELATIONS.items():
        relations.extend(
            _related(item, relation, f"{field}[{index}]", issues)
            for index, item in enumerate(_items(_field_value(data, field)))
        )

    category = data.application_category
    if isinstance(category, list):
        if len(category) > 1:
            issues.extend(
                _issue(
                    f"applicationCategory[{i}]", "additional categories are unsupported"
                )
                for i in range(1, len(category))
            )
        category = category[0] if category else None

    publisher = None
    if data.publisher:
        publisher_values = _items(data.publisher)
        publisher = _agent(publisher_values[0], "publisher[0]", issues, {})
        if len(publisher_values) > 1:
            issues.extend(
                _issue(f"publisher[{i}]", "additional publishers are unsupported")
                for i in range(1, len(publisher_values))
            )

    metadata = SoftwareMetadata(
        title=data.name,
        description=data.description,
        creators=creators,
        contributors=creator_contributions
        + contributor_contributions
        + [Contribution(agent=a) for a in contributor_agents],
        publisher=publisher,
        version=str(data.version) if data.version is not None else None,
        category=category,
        date_released=data.date_published,
        date_created=data.date_created,
        date_modified=data.date_modified,
        publication_year=_year(data.date_published),
        url=_source_url(data.url, "url", issues),
        repository_code=data.code_repository,
        download_url=_source_url(data.download_url, "downloadUrl", issues),
        identifiers=_source_identifiers(data.identifier, "identifier", issues),
        keywords=[str(item) for item in _items(data.keywords)],
        licenses=_licenses(data.license, issues),
        programming_languages=[
            getattr(item, "name", str(item))
            for item in _items(data.programming_language)
        ],
        formats=[str(item) for item in _items(data.file_format)],
        sizes=[str(item) for item in _items(data.file_size)],
        release_notes=[str(item) for item in _items(data.release_notes)],
        relations=relations,
    )
    if data.id:
        metadata.identifiers.insert(0, Identifier(value=data.id))
    for field in UNSUPPORTED_SOURCE_FIELDS:
        if _field_value(data, field) is not None:
            issues.append(
                _issue(field, "CodeMeta field is not mapped to SoftwareMetadata")
            )
    for field in sorted(data.model_extra or {}):
        if data.model_extra[field] is not None:
            issues.append(_issue(field, "unknown CodeMeta field is not mapped"))
    return ConversionResult(value=metadata, issues=tuple(issues))


def _provider_agent(
    agent: Agent, path: str, issues: list[ConversionIssue]
) -> Person | Organization | str:
    if agent.kind == "unknown":
        issues.append(_issue(path, "unknown agent kind emitted as a string"))
        return agent.name
    target = Person if agent.kind == "person" else Organization
    kwargs: dict[str, Any] = {"name": agent.name}
    if agent.email:
        kwargs["email"] = agent.email
    if agent.url:
        kwargs["url"] = agent.url
    if agent.given_names:
        kwargs["given_name"] = (
            agent.given_names if len(agent.given_names) > 1 else agent.given_names[0]
        )
    if agent.family_names:
        kwargs["family_name"] = (
            agent.family_names if len(agent.family_names) > 1 else agent.family_names[0]
        )
    if agent.identifiers:
        kwargs["identifier"] = [
            (
                PropertyValue(property_id=item.scheme, value=item.value)
                if item.scheme
                else item.value
            )
            for item in agent.identifiers
        ]
    if agent.affiliations:
        if target is Person:
            affiliation = agent.affiliations[0]
            affiliation_identifier = (
                PropertyValue(
                    property_id=affiliation.identifier.scheme,
                    value=affiliation.identifier.value,
                )
                if affiliation.identifier
                else None
            )
            kwargs["affiliation"] = Organization(
                name=affiliation.name,
                identifier=affiliation_identifier,
            )
            for index in range(1, len(agent.affiliations)):
                issues.append(
                    _issue(
                        f"{path}.affiliations[{index}]",
                        "additional affiliations are unsupported",
                    )
                )
        else:
            issues.extend(
                _issue(
                    f"{path}.affiliations[{index}]",
                    "organization affiliations are unsupported",
                )
                for index in range(len(agent.affiliations))
            )
    return target(**kwargs)


def _provider_related(
    resource: RelatedResource, path: str, issues: list[ConversionIssue]
) -> Any:
    kwargs: dict[str, Any] = {"name": resource.title}
    if resource.url:
        kwargs["url"] = resource.url
    if resource.identifier:
        kwargs["identifier"] = PropertyValue(
            property_id=resource.identifier.scheme,
            value=resource.identifier.value,
        )
    if resource.creators:
        kwargs["author"] = [
            _provider_agent(agent, f"{path}.creators[{i}]", issues)
            for i, agent in enumerate(resource.creators)
        ]
    if resource.relation == "requires":
        return SoftwareSourceCode(**kwargs)
    if resource.resource_type == "ScholarlyArticle":
        return ScholarlyArticle(**kwargs)
    return CreativeWork(type=resource.resource_type or "CreativeWork", **kwargs)


def software_metadata_to_codemeta(
    data: SoftwareMetadata,
) -> ConversionResult[CodeMetaV3]:
    issues: list[ConversionIssue] = []
    payload: dict[str, Any] = {
        "@context": "https://w3id.org/codemeta/3.0",
        "@type": "SoftwareSourceCode",
        "name": data.title,
        "description": data.description,
        "version": data.version,
        "applicationCategory": data.category,
        "datePublished": data.date_released,
        "dateCreated": data.date_created,
        "dateModified": data.date_modified,
        "url": data.url,
        "codeRepository": data.repository_code,
        "downloadUrl": data.download_url,
        "keywords": data.keywords,
        "programmingLanguage": data.programming_languages,
        "fileFormat": data.formats,
        "fileSize": data.sizes[0] if data.sizes else None,
        "releaseNotes": data.release_notes,
    }
    if data.publication_year:
        if data.date_released and _year(data.date_released) != data.publication_year:
            issues.append(
                _issue(
                    "publication_year", "publication year conflicts with date_released"
                )
            )
        elif not data.date_released:
            issues.append(
                _issue(
                    "publication_year",
                    "year-only value has no CodeMeta date representation",
                )
            )
    if data.repository:
        issues.append(_issue("repository", "generic repository has no CodeMeta field"))
    if data.repository_artifact:
        issues.append(
            _issue("repository_artifact", "repository artifact has no CodeMeta field")
        )

    payload["author"] = [
        _provider_agent(agent, f"creators[{i}]", issues)
        for i, agent in enumerate(data.creators)
    ] or None
    payload["contributor"] = []
    for i, contribution in enumerate(data.contributors):
        agent = _provider_agent(contribution.agent, f"contributors[{i}].agent", issues)
        if contribution.roles:
            payload["contributor"].append(
                Role(author=agent, role_name=contribution.roles[0])
            )
            for role_index in range(1, len(contribution.roles)):
                issues.append(
                    _issue(
                        f"contributors[{i}].roles[{role_index}]",
                        "additional role is unsupported",
                    )
                )
        else:
            payload["contributor"].append(agent)
    payload["contributor"] = payload["contributor"] or None
    if data.publisher:
        payload["publisher"] = _provider_agent(data.publisher, "publisher", issues)
    payload["identifier"] = [
        (
            PropertyValue(property_id=item.scheme, value=item.value)
            if item.scheme
            else item.value
        )
        for item in data.identifiers
    ] or None
    payload["license"] = [
        CreativeWork(name=item.name, identifier=item.identifier, url=item.url)
        for item in data.licenses
    ] or None

    relation_values: dict[str, list[Any]] = {}
    for relation_index, resource in enumerate(data.relations):
        field = REVERSE_RELATIONS.get(resource.relation)
        path = f"relations[{relation_index}]"
        if field is None:
            issues.append(_issue(path, f"unsupported relation {resource.relation!r}"))
            continue
        if (
            not any(
                (
                    resource.identifier,
                    resource.title,
                    resource.resource_type,
                    resource.creators,
                )
            )
            and resource.url
        ):
            relation_values.setdefault(field, []).append(resource.url)
        else:
            relation_values.setdefault(field, []).append(
                _provider_related(resource, path, issues)
            )

    for field, values in relation_values.items():
        payload[field] = values[0] if len(values) == 1 else values

    if not data.sizes:
        payload.pop("fileSize", None)
    payload = {key: value for key, value in payload.items() if value is not None}
    try:
        result = CodeMetaV3.model_validate(payload)
    except ValidationError as exc:
        raise ConversionError(f"Unable to construct CodeMetaV3: {exc}") from exc
    return ConversionResult(value=result, issues=tuple(issues))


__all__ = ["codemeta_to_software_metadata", "software_metadata_to_codemeta"]
