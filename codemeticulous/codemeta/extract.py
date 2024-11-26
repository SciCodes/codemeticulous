from abc import ABC
import re
from typing import Optional

from pydantic2_schemaorg.PostalAddress import PostalAddress
from pydantic2_schemaorg.Person import Person
from pydantic2_schemaorg.Organization import Organization

from codemeticulous.codemeta.models import (
    Actor as CodeMetaActor,
)
from codemeticulous.common.utils import (
    ensure_list,
    get_first_if_list,
    is_url,
)


class CodeMetaActorExtractor:

    def __init__(self, actor: CodeMetaActor):
        if not isinstance(actor, CodeMetaActor):
            raise ValueError(
                "actor must be a codemeta/schema.org Person, Organization, or Role"
            )
        # TODO: extract from Role, depends on structuring in codemeta.models.FlexibleRole
        self.actor = actor

    @property
    def is_person(self) -> bool:
        return isinstance(self.actor, Person)

    @property
    def is_organization(self) -> bool:
        return isinstance(self.actor, Organization)

    @property
    def address(self) -> Optional[str]:
        address = self.actor.address
        if isinstance(address, str):
            return address
        if isinstance(address, PostalAddress):
            return address.streetAddress

    @property
    def primary_affiliation_name(self) -> Optional[str]:
        affiliation = get_first_if_list(self.actor.affiliation)
        if affiliation:
            if isinstance(affiliation, str):
                return affiliation
            elif isinstance(affiliation, Organization):
                return self.actor.affiliation.name

    @property
    def alias(self) -> Optional[str]:
        return self.actor.alternateName

    @property
    def city(self) -> Optional[str]:
        if isinstance(self.actor.address, PostalAddress):
            return self.actor.address.addressLocality

    @property
    def country(self) -> Optional[str]:
        if isinstance(self.actor.address, PostalAddress):
            return self.actor.address.addressCountry

    @property
    def email(self) -> Optional[str]:
        return get_first_if_list(self.actor.email)

    @property
    def name(self) -> str:
        if self.family_names and self.given_names:
            return self.family_names + ", " + self.given_names
        return self.actor.name

    @property
    def family_names(self) -> Optional[str]:
        if hasattr(self.actor, "familyName"):
            return (
                self.actor.familyName.join(" ")
                if isinstance(self.actor.familyName, list)
                else self.actor.familyName
            )

    @property
    def given_names(self) -> Optional[str]:
        if hasattr(self.actor, "givenName"):
            return (
                self.actor.givenName.join(" ")
                if isinstance(self.actor.givenName, list)
                else self.actor.givenName
            )

    @property
    def fax(self) -> Optional[str]:
        return get_first_if_list(self.actor.faxNumber)

    @property
    def name_particle(self) -> Optional[str]:
        return get_first_if_list(self.actor.additionalName)

    @property
    def name_suffix(self) -> Optional[str]:
        return get_first_if_list(self.actor.honorificSuffix)

    @property
    def identifiers(self) -> Optional[list[str]]:
        # return any url identifiers
        identifiers = [self.actor.id_]
        identifiers.extend(ensure_list(self.actor.identifier))
        return [identifier for identifier in identifiers if is_url(identifier)]

    @property
    def affiliations(self) -> Optional[list[tuple[str, Optional[str]]]]:
        # return list of affiliations with optional identifiers
        # (name, identifier)
        if self.is_organization:
            return None
        affiliations = ensure_list(self.actor.affiliation)
        affiliation_list = []
        for affiliation in affiliations:
            if isinstance(affiliation, Organization):
                possible_identifiers = [affiliation.id_]
                possible_identifiers.extend(ensure_list(affiliation.identifier))
                possible_identifiers.extend(ensure_list(affiliation.url))
                identifier = next(
                    (
                        identifier
                        for identifier in possible_identifiers
                        if is_url(identifier)
                    ),
                    None,
                )
                affiliation_list.append((affiliation.name, identifier))
            elif isinstance(affiliation, str):
                affiliation_list.append((affiliation, None))

    @property
    def orcid(self) -> Optional[str]:
        # try to extract orcid from identifier or @id
        if self.actor.id_ and "orcid.org" in self.actor.id_:
            return self.actor.id_
        identifiers = ensure_list(self.actor.identifier)
        if not identifiers:
            return None
        for identifier in identifiers:
            if "orcid.org" in identifier:
                return identifier

    @property
    def post_code(self) -> Optional[str]:
        if isinstance(self.actor.address, PostalAddress):
            return self.actor.address.postalCode

    @property
    def region(self) -> Optional[str]:
        if isinstance(self.actor.address, PostalAddress):
            return self.actor.address.addressRegion

    @property
    def tel(self) -> Optional[str]:
        return get_first_if_list(self.actor.telephone)

    @property
    def website(self) -> Optional[str]:
        return get_first_if_list(self.actor.url)


def extract_doi_from_codemeta_identifier(identifier) -> Optional[str]:
    """extracts the primary DOI from the CodeMeta identifier field"""
    identifiers = ensure_list(identifier)
    doi_pattern = re.compile(
        r"(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}(?:\.\d+)?/[A-Za-z0-9:/_;\-\.\(\)\[\]\\]+)$"
    )
    for identifier in identifiers:
        if not isinstance(identifier, str):
            identifier = (
                getattr(identifier, "id_", None)
                or getattr(identifier, "propertyID", None)
                or getattr(identifier, "url", None)
                or getattr(identifier, "value", None)
            )
        if isinstance(identifier, str):
            match = doi_pattern.search(identifier)
            if match:
                return match.group(1)
    return None
