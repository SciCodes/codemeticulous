# convert between codemeta and datacite metadata
# see: https://github.com/codemeta/codemeta/blob/master/crosswalks/DataCite.csv

from datetime import datetime
import re
from typing import Optional
from urllib.parse import urlparse

from pydantic2_schemaorg.CreativeWork import CreativeWork as SchemaOrgCreativeWork

from codemeticulous.codemeta.extract import (
    CodeMetaActorExtractor,
    extract_doi_from_codemeta_identifier,
)
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
from codemeticulous.datacite.models import (
    AffiliationItem,
    Contributor,
    Creator,
    DataciteV45,
    DateModel,
    Description,
    NameIdentifier,
    Person,
    Publisher,
    RightsListItem,
    Subject,
    Title,
    Types,
)

IDENTIFIER_SCHEMES = {
    "orcid.org": "ORCID",
    "ror.org": "ROR",
    "isni.org": "ISNI",
}


def codemeta_actors_to_datacite(
    actors: CodeMetaActorListOrSingle,
    datacite_actor_model: Creator | Contributor | Publisher,
) -> Optional[list]:
    actors = ensure_list(actors)
    datacite_actors = []
    for actor in actors:
        extractor = CodeMetaActorExtractor(actor)
        # pull out identifier url, scheme, and scheme uri
        name_identifiers = []
        if extractor.identifiers:
            for identifier_url in extractor.identifiers:
                url_parts = urlparse(identifier_url)
                scheme = IDENTIFIER_SCHEMES.get(url_parts.netloc)
                if scheme:
                    name_identifiers.append(
                        dict(
                            nameIdentifier=identifier_url,
                            nameIdentifierScheme=scheme,
                            schemeUri=f"{url_parts.scheme}://{url_parts.netloc}",
                        )
                    )
        # pull out affiliation name, url, scheme, and scheme uri
        affiliations = []
        if extractor.affiliations:
            for affiliation_name, affiliation_url in extractor.affiliations:
                affiliation = dict(name=affiliation_name)
                if affiliation_url:
                    url_parts = urlparse(affiliation_url)
                    scheme = IDENTIFIER_SCHEMES.get(url_parts.netloc)
                    affiliation["affiliationIdentifier"] = affiliation_url
                    if scheme:
                        affiliation["affiliationIdentifierScheme"] = scheme
                        affiliation["schemeUri"] = (
                            f"{url_parts.scheme}://{url_parts.netloc}"
                        )
                affiliations.append(affiliation)
        # create the correct datacite actor
        if datacite_actor_model == Creator:
            datacite_actors.append(
                Creator(
                    name=extractor.name,
                    nameType=(
                        "Organizational" if extractor.is_organization else "Personal"
                    ),
                    givenName=extractor.given_names,
                    familyName=extractor.family_names,
                    nameIdentifiers=[NameIdentifier(**i) for i in name_identifiers]
                    or None,
                    affiliation=[AffiliationItem(**a) for a in affiliations] or None,
                )
            )
        elif datacite_actor_model == Contributor:
            datacite_actors.append(
                Contributor(
                    name=extractor.name,
                    nameType=(
                        "Organizational" if extractor.is_organization else "Personal"
                    ),
                    givenName=extractor.given_names,
                    familyName=extractor.family_names,
                    nameIdentifiers=[NameIdentifier(**i) for i in name_identifiers]
                    or None,
                    affiliation=[AffiliationItem(**a) for a in affiliations] or None,
                    contributorType="Other",  # FIXME: relies on extracting codemeta role
                )
            )
        elif datacite_actor_model == Publisher:
            datacite_actors.append(
                Publisher(
                    name=extractor.name,
                    publisherIdentifier=(
                        name_identifiers[0].get("nameIdentifier")
                        if name_identifiers
                        else None
                    ),
                    publisherIdentifierScheme=(
                        name_identifiers[0].get("nameIdentifierScheme")
                        if name_identifiers
                        else None
                    ),
                    schemeUri=(
                        name_identifiers[0].get("schemeUri")
                        if name_identifiers
                        else None
                    ),
                )
            )
    return datacite_actors or None


def codemeta_license_to_datacite_rights(
    codemeta_license: Optional[
        list[SchemaOrgCreativeWork | str] | SchemaOrgCreativeWork | str
    ],
) -> Optional[list[RightsListItem]]:
    licenses = ensure_list(codemeta_license)
    rights_list = []
    license_url = None
    license_name = None
    for l in licenses:
        # plain string licenses should always be urls
        if isinstance(l, str) and is_url(l):
            license_url = l
        elif hasattr(l, "url") and is_url(l.url):
            license_url = l.url
        elif hasattr(l, "name"):
            license_name = l.name
        # FIXME: build a lookup table for spdx/osi licenses so we can figure out
        # what license is being used and fill out all fields
        rights_list.append(RightsListItem(rights=license_name, rightsUri=license_url))
    return rights_list or None


def codemeta_language_fileformat_to_datacite_format(
    programming_language, file_format
) -> list[str]:
    possible_formats = ensure_list(programming_language) + ensure_list(file_format)
    formats = []
    for f in possible_formats:
        if isinstance(f, str):
            formats.append(f)
        elif hasattr(f, "name"):
            formats.append(f.name)
    return formats or None


def codemeta_to_datacite(data: CodeMeta, ignore_existing_doi=False) -> DataciteV45:
    primary_doi = (
        extract_doi_from_codemeta_identifier(data.identifier)
        if not ignore_existing_doi
        else None
    )
    doi_prefix, doi_suffix = primary_doi.split("/") if primary_doi else (None, None)
    # build descriptions
    descriptions = []
    if data.description:
        descriptions.append(
            Description(description=data.description, descriptionType="Abstract")
        )
    if data.releaseNotes:
        release_notes = ensure_list(data.releaseNotes)
        descriptions.extend(
            [
                Description(description=note, descriptionType="TechnicalInfo")
                for note in release_notes
            ]
        )
    return DataciteV45(
        doi=primary_doi,
        prefix=doi_prefix,
        suffix=doi_suffix,
        url=get_first_if_list(data.url),
        types=Types(resourceTypeGeneral="Software"),
        creators=codemeta_actors_to_datacite(data.author, Creator),
        titles=[Title(title=data.name)],
        publisher=get_first_if_list(
            codemeta_actors_to_datacite(data.publisher, Publisher)
        ),
        publicationYear=str(data.datePublished.year) if data.datePublished else None,
        subjects=[Subject(subject=subject) for subject in ensure_list(data.keywords)],
        contributors=codemeta_actors_to_datacite(data.contributor, Contributor),
        dates=[
            DateModel(
                date=date.date() if isinstance(date, datetime) else date,
                dateType=date_type,
            )
            for date, date_type in [
                (data.dateCreated, "Created"),
                (data.dateModified, "Updated"),
            ]
            if date is not None
        ],
        # we have no way of knowing what the relationships are for relatedLinks since
        # they are just urls
        # TODO: though, it may be possible to use the following codemeta fields:
        # hasPart, isPartOf, readme, sameAs, review, releaseNotes
        # relatedIdentifiers=data.relatedLink,
        sizes=[data.fileSize] if data.fileSize else None,
        formats=codemeta_language_fileformat_to_datacite_format(
            data.programmingLanguage, data.fileFormat
        ),
        version=str(data.version),
        rightsList=codemeta_license_to_datacite_rights(data.license),
        descriptions=descriptions,
        # codemeta.funding is a plain string, can't really ensure that the string
        # is the required name field
        # fundingReferences=None,
    )


def datacite_to_codemeta(data: DataciteV45) -> CodeMeta:
    raise NotImplementedError
