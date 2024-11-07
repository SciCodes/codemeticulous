from datetime import datetime
import re
from typing import Optional

from pydantic2_schemaorg.PostalAddress import PostalAddress as SchemaOrgPostalAddress
from pydantic2_schemaorg.Person import Person as SchemaOrgPerson
from pydantic2_schemaorg.Organization import Organization as SchemaOrgOrganization

from codemeticulous.codemeta.models import (
    CodeMeta,
    Actor as CodeMetaActor,
    ActorListOrSingle as CodeMetaActorListOrSingle,
)
from codemeticulous.common.utils import make_list_if_single, get_first_if_list
from codemeticulous.cff.models import (
    CitationFileFormat,
    Person,
    Entity,
)

# CodeMeta = codemeta.CodeMeta


class CFFActorExtractor:
    """Extracts Citation File Format Person/Entity fields from a CodeMeta Actor"""

    def __init__(self, actor: CodeMetaActor):
        if not isinstance(actor, CodeMetaActor):
            raise ValueError(
                "actor must be a codemeta/schema.org Person, Organization, or Role"
            )
        # TODO: extract from Role, depends on structuring in codemeta.models.FlexibleRole
        self.actor = actor

    @property
    def is_person(self) -> bool:
        return isinstance(self.actor, SchemaOrgPerson)

    @property
    def is_organization(self) -> bool:
        return isinstance(self.actor, SchemaOrgOrganization)

    @property
    def address(self) -> Optional[str]:
        address = self.actor.address
        if isinstance(address, str):
            return address
        if isinstance(address, SchemaOrgPostalAddress):
            return address.streetAddress

    @property
    def affiliation(self) -> Optional[str]:
        affiliation = get_first_if_list(self.actor.affiliation)
        if affiliation:
            if isinstance(affiliation, str):
                return affiliation
            elif isinstance(affiliation, SchemaOrgOrganization):
                return self.actor.affiliation.name

    @property
    def alias(self) -> Optional[str]:
        return self.actor.alternateName

    @property
    def city(self) -> Optional[str]:
        if isinstance(self.actor.address, SchemaOrgPostalAddress):
            return self.actor.address.addressLocality

    @property
    def country(self) -> Optional[str]:
        if isinstance(self.actor.address, SchemaOrgPostalAddress):
            return self.actor.address.addressCountry

    @property
    def email(self) -> Optional[str]:
        return get_first_if_list(self.actor.email)

    @property
    def family_names(self) -> Optional[str]:
        return (
            self.actor.familyName.join(" ")
            if isinstance(self.actor.familyName, list)
            else self.actor.familyName
        )

    @property
    def given_names(self) -> Optional[str]:
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
    def orcid(self) -> Optional[str]:
        # try to extract orcid from identifier or @id
        if "orcid.org" in self.actor.id_:
            return self.actor.id_
        identifiers = make_list_if_single(self.actor.identifier)
        if not identifiers:
            return None
        for identifier in identifiers:
            if "orcid.org" in identifier:
                return identifier

    @property
    def post_code(self) -> Optional[str]:
        if isinstance(self.actor.address, SchemaOrgPostalAddress):
            return self.actor.address.postalCode

    @property
    def region(self) -> Optional[str]:
        if isinstance(self.actor.address, SchemaOrgPostalAddress):
            return self.actor.address.addressRegion

    @property
    def tel(self) -> Optional[str]:
        return get_first_if_list(self.actor.telephone)

    @property
    def website(self) -> Optional[str]:
        return get_first_if_list(self.actor.url)

    def as_entity(self) -> Entity:
        return Entity(
            address=self.address,
            alias=self.alias,
            city=self.city,
            country=self.country,
            email=self.email,
            fax=self.fax,
            orcid=self.orcid,
            post_code=self.post_code,
            region=self.region,
            tel=self.tel,
            website=self.website,
        )

    def as_person(self) -> Person:
        return Person(
            address=self.address,
            affiliation=self.affiliation,
            alias=self.alias,
            city=self.city,
            country=self.country,
            email=self.email,
            family_names=self.family_names,
            given_names=self.given_names,
            fax=self.fax,
            name_particle=self.name_particle,
            name_suffix=self.name_suffix,
            orcid=self.orcid,
            post_code=self.post_code,
            region=self.region,
            tel=self.tel,
            website=self.website,
        )

    def extract_person_or_entity(self) -> Person | Entity:
        if self.is_person:
            return self.as_person()
        elif self.is_organization:
            return self.as_entity()


def codemeta_actors_to_cff(actors: CodeMetaActorListOrSingle) -> list[Person | Entity]:
    actors = make_list_if_single(actors)
    cff_actors = []
    for actor in actors:
        actor_extractor = CFFActorExtractor(actor)
        person_or_entity = actor_extractor.extract_person_or_entity()
        if person_or_entity:
            cff_actors.append(person_or_entity)
    return cff_actors


def extract_doi_from_identifier(identifier) -> str:
    identifiers = make_list_if_single(identifier)
    doi_pattern = re.compile(
        r"^10\\.\\d{4,9}(\\.\\d+)?/[A-Za-z0-9:/_;\\-\\.\\(\\)\\[\\]\\\\]+$"
    )
    for identifier in identifiers:
        if isinstance(identifier, str):
            match = doi_pattern.search(identifier)
            if match:
                return match.group(0)


def codemeta_to_cff(data: CodeMeta) -> CitationFileFormat:
    return CitationFileFormat(
        cff_version="1.2.0",
        message="If you use this software, please cite it as below.",
        abstract=data.description,
        authors=codemeta_actors_to_cff(data.author),
        date_released=(
            data.datePublished.date()
            if isinstance(data.datePublished, datetime)
            else data.datePublished
        ),
        doi=extract_doi_from_identifier(data.identifier),
        # identifiers=None, # TODO:
        keywords=make_list_if_single(data.keywords) or None,
        # license=None # TODO:
        # license_url=None # TODO:
        # preferred_citation=None, # TODO:
        # references=None, # TODO:
        # repository=None # these are tricky, could be in url
        # repository_artifact=None # these are tricky, could be in url
        repository_code=data.codeRepository,
        title=data.name,
        type="software",
        # url=None, # these are tricky, could be in url
        version=data.version,
    )


def cff_to_codemeta(data: CitationFileFormat) -> CodeMeta:
    raise NotImplementedError
