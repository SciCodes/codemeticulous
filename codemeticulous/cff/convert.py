# convert between codemeta and cff
# see: https://github.com/codemeta/codemeta/blob/master/crosswalks/Citation%20File%20Format%201.2.0.csv
# and: https://github.com/codemeta/codemeta/blob/master/crosswalks/Citation_File_Format_1.2.0.README.md

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
from codemeticulous.common.utils import (
    get_first_if_single_list,
    ensure_list,
    get_first_if_list,
    is_url,
)
from codemeticulous.cff.models import (
    CitationFileFormat,
    Identifier1 as DoiIdentifier,
    Identifier2 as UrlIdentifier,
    Identifier3 as SwhIdentifier,
    Identifier4 as OtherIdentifier,
    Person,
    Entity,
    LicenseEnum,
    Reference,
)


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
    """convert a list of CodeMeta actors (Person, Organization, Role) to a list of
    CFF Person or Entity objects
    """
    actors = ensure_list(actors)
    cff_actors = []
    for actor in actors:
        actor_extractor = CFFActorExtractor(actor)
        person_or_entity = actor_extractor.extract_person_or_entity()
        if person_or_entity:
            cff_actors.append(person_or_entity)
    return cff_actors


def codemeta_license_to_cff(codemeta_license) -> tuple[list[str], list[str]]:
    """extracts any SPDX licenses from a CodeMeta license field
    as well as any non-SPDX licenses if they are a url.

    returns a tuple of lists containing SPDX IDs and URLs respectively"""
    licenses = ensure_list(codemeta_license)
    cff_licenses = []
    cff_license_urls = []
    spdx_url_pattern = re.compile(r"https://spdx\.org/licenses/([A-Za-z0-9\-_\.]+)")
    spdx_ids = {l.value for l in LicenseEnum}
    for l in licenses:
        license_str = l if isinstance(l, str) else l.name
        if isinstance(license_str, str):
            match = spdx_url_pattern.match(license_str)
            spdx_id = match.group(1) if match else license_str
            if spdx_id in spdx_ids:
                cff_licenses.append(spdx_id)
            elif is_url(license_str):
                cff_license_urls.append(license_str)
    return cff_licenses, cff_license_urls


def extract_identifiers_from_codemeta(
    data: CodeMeta, primary_doi=None
) -> list[DoiIdentifier, UrlIdentifier, SwhIdentifier, OtherIdentifier]:
    """extracts a list of cff identifiers (url, doi, swh, other) from a CodeMeta object"""
    # flatten all possible identifier fields into a single list
    possible_identifiers = []
    for field in [data.identifier, data.isPartOf, data.hasPart, data.sameAs, data.url]:
        if field is not None:
            if isinstance(field, list):
                possible_identifiers.extend(field)
            else:
                possible_identifiers.append(field)
    # pull out urls from non-string fields
    possible_identifier_strs = []
    for possible_identifier in possible_identifiers:
        if isinstance(possible_identifier, str):
            possible_identifier_strs.append(possible_identifier)
        else:
            values = (
                getattr(possible_identifier, "id_", None)
                or getattr(possible_identifier, "propertyID", None)
                or getattr(possible_identifier, "url", None)
                or getattr(possible_identifier, "value", None)
            )
            possible_identifier_strs.extend([val for val in ensure_list(values) if val is not None])
    # try to match possible identifiers to known types (doi, url, swh) and put the rest in other
    doi_pattern = re.compile(
        r"(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}(?:\.\d+)?/[A-Za-z0-9:/_;\-\.\(\)\[\]\\]+)$"
    )
    swh_pattern = re.compile(r"^swh:1:(snp|rel|rev|dir|cnt):[0-9a-fA-F]{40}$")
    identifiers = []
    for possible_identifier_str in possible_identifier_strs:
        if possible_identifier_str is None:
            continue
        doi_match = doi_pattern.search(possible_identifier_str)
        swh_match = swh_pattern.search(possible_identifier_str)
        if doi_match:
            # skip primary DOI if it is present
            if primary_doi and doi_match.group(1) == primary_doi:
                continue
            identifiers.append(DoiIdentifier(type="doi", value=doi_match.group(1)))
        elif swh_match:
            identifiers.append(SwhIdentifier(type="swh", value=swh_match.group(0)))
        elif is_url(possible_identifier_str):
            identifiers.append(UrlIdentifier(type="url", value=possible_identifier_str))
        else:
            identifiers.append(
                OtherIdentifier(type="other", value=possible_identifier_str)
            )
    # remove duplicate values
    seen = set()
    identifiers = [id_ for id_ in identifiers if id_.value not in seen and not seen.add(id_.value)]
    return identifiers or None


def codemeta_references_to_cff(citation, softwareRequirements) -> list[Reference]:
    """returns a list of references which is a combination of
    softwareRequirements and citation fields"""
    # flatten all possible reference fields into a single list
    possible_references = []
    for field in [citation, softwareRequirements]:
        if field is not None:
            if isinstance(field, list):
                possible_references.extend(field)
            else:
                possible_references.append(field)
    references = []
    type_map = {
        "SoftwareSourceCode": "software-code",
        "SoftwareApplication": "software",
        "ScholarlyArticle": "article",
        "Article": "article",
        "WebPage": "website",
        "WebSite": "website",
        "Book": "book",
        "BlogPosting": "blog",
    }
    # if the possible reference has the required fields, then make a reference out of it
    for possible_ref in possible_references:
        if not isinstance(possible_ref, str):
            try:
                ref = Reference(
                    type=type_map.get(possible_ref.type_, "generic"),
                    title=possible_ref.name,
                    authors=codemeta_actors_to_cff(possible_ref.author),
                )
                references.append(ref)
            except:
                pass
    return references or None


def extract_main_url_from_codemeta(data: CodeMeta) -> str:
    """get the main url from a CodeMeta object, preferring url, downloadUrl, installUrl, and then
    relatedLink in that order
    """
    return get_first_if_list(
        data.url or data.downloadUrl or data.installUrl or data.relatedLink
    )


def extract_doi_from_codemeta_identifier(identifier) -> str:
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


def codemeta_to_cff(data: CodeMeta) -> CitationFileFormat:
    """Extract all possible Citation File Format fields from a CodeMeta object based
    on the CodeMeta crosswalk and return a CitationFileFormat object
    """
    licenses, license_urls = codemeta_license_to_cff(data.license)
    primary_doi = extract_doi_from_codemeta_identifier(data.identifier)
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
        doi=primary_doi,
        identifiers=extract_identifiers_from_codemeta(data, primary_doi=primary_doi),
        keywords=ensure_list(data.keywords) or None,
        license=get_first_if_single_list(licenses) or None,
        license_url=get_first_if_single_list(license_urls) or None,
        # we cannot confidently say anything in citation should be the preferred-citation
        preferred_citation=None,
        references=codemeta_references_to_cff(data.citation, data.softwareRequirements),
        # repository or repository-artifact could be in codemeta url, downloadUrl, installUrl,
        # or relatedLink, but the semantics do not match up, so there is no reliable way to
        # extract this information
        repository=None,
        repository_artifact=None,
        repository_code=data.codeRepository,
        title=data.name,
        type="software",
        url=extract_main_url_from_codemeta(data),
        version=data.version,
    )


def cff_to_codemeta(data: CitationFileFormat) -> CodeMeta:
    raise NotImplementedError
