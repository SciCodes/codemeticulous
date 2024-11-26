# convert between codemeta and datacite metadata
# see: https://github.com/codemeta/codemeta/blob/master/crosswalks/DataCite.csv

from datetime import datetime
import re
from typing import Optional
from urllib.parse import urlparse

from pydantic2_schemaorg.PostalAddress import PostalAddress as SchemaOrgPostalAddress
from pydantic2_schemaorg.Person import Person as SchemaOrgPerson
from pydantic2_schemaorg.Organization import Organization as SchemaOrgOrganization

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
        # FIXME: turn list of urls into list of relatedIdentifiers
        # relatedIdentifiers=data.relatedLink,
        sizes=[data.fileSize] if data.fileSize else None,
        # FIXME: get from programmingLanguage and fileFormat
        # formats=None,
        version=str(data.version),
        # FIXME: turn license into rights
        # rightsList=[data.license],
        descriptions=descriptions,
        # codemeta.funding is a plain string, can't really ensure that the string
        # is the required name field
        # fundingReferences=None,
    )


def datacite_to_codemeta(data: DataciteV45) -> CodeMeta:
    raise NotImplementedError
