# convert between codemeta and datacite metadata
# see: https://github.com/codemeta/codemeta/blob/master/crosswalks/DataCite.csv

from datetime import datetime
import re
from typing import Optional
from urllib.parse import urlparse

from pydantic2_schemaorg.CreativeWork import CreativeWork as SchemaOrgCreativeWork

from codemeticulous.models import CanonicalCodeMeta
from codemeticulous.extract import ActorExtractor, extract_doi_from_identifier
from codemeticulous.codemeta.models import (
    CodeMeta,
    Actor as CodeMetaActor,
    ActorListOrSingle as CodeMetaActorListOrSingle,
)
from codemeticulous.utils import (
    get_first_if_single_list,
    ensure_list,
    get_first_if_list,
    is_url,
)
from codemeticulous.datacite.models import (
    AffiliationItem,
    Contributor,
    ContributorType,
    Creator,
    DataCite,
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

CONTRIBUTOR_TYPE_MAP = {
    ContributorType.ContactPerson: {
        "contact",
        "contact person",
        "point of contact",
        "main contact",
        "primary contact",
    },
    ContributorType.DataCollector: {
        "data collector",
        "data collection",
        "collector of data",
        "field data collector",
        "data gatherer",
    },
    ContributorType.DataCurator: {
        "data curator",
        "data curation",
        "curator of data",
        "data organizer",
    },
    ContributorType.DataManager: {
        "data manager",
        "data management",
        "manager of data",
        "data admin",
    },
    ContributorType.Distributor: {
        "distributor",
        "distribution",
        "data distributor",
        "content distributor",
    },
    ContributorType.Editor: {
        "editor",
        "editing",
        "content editor",
        "text editor",
        "manuscript editor",
    },
    ContributorType.HostingInstitution: {
        "hosting institution",
        "host",
        "institution host",
        "hosting organization",
    },
    ContributorType.Producer: {
        "producer",
        "production",
        "data producer",
        "content producer",
    },
    ContributorType.ProjectLeader: {
        "project leader",
        "leader",
        "project head",
        "team leader",
        "head of project",
    },
    ContributorType.ProjectManager: {
        "project manager",
        "manager",
        "project administrator",
        "project supervisor",
    },
    ContributorType.ProjectMember: {
        "project member",
        "member",
        "team member",
        "participant",
    },
    ContributorType.RegistrationAgency: {
        "registration agency",
        "registrar",
        "agency registrar",
        "registry agency",
    },
    ContributorType.RegistrationAuthority: {
        "registration authority",
        "authority",
        "registry authority",
        "regulatory authority",
    },
    ContributorType.RelatedPerson: {
        "related person",
        "person related",
        "associated person",
        "affiliate",
    },
    ContributorType.Researcher: {"researcher", "research", "investigator", "scientist"},
    ContributorType.ResearchGroup: {
        "research group",
        "group",
        "team",
        "research team",
        "research unit",
    },
    ContributorType.RightsHolder: {
        "rights holder",
        "copyright holder",
        "intellectual property owner",
        "rights owner",
    },
    ContributorType.Sponsor: {
        "sponsor",
        "funding sponsor",
        "funder",
        "financial backer",
    },
    ContributorType.Supervisor: {"supervisor", "advisor", "overseer", "mentor"},
    ContributorType.Translator: {"translator", "translation"},
    ContributorType.WorkPackageLeader: {
        "work package leader",
        "package leader",
        "task leader",
        "subproject leader",
    },
}


# FIXME: this is horrible, break it up
def codemeta_actors_to_datacite(
    actors: CodeMetaActorListOrSingle,
    datacite_actor_model: Creator | Contributor | Publisher,
) -> Optional[list]:
    actors = ensure_list(actors)
    datacite_actors = []
    for actor in [a for a in actors if a.type_ != "Role"]:
        # after filtering out roles, we need to find the roles for this actor
        roles = [r for r in actors if r.id_ == actor.id_ and r.type_ == "Role"]
        extractor = ActorExtractor(actor, roles)
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
            # match roles to contributor types
            matched_roles = set()
            for role in extractor.role_names:
                normalized_role = (
                    role.lower().replace(" ", "").replace("-", "").replace("_", "")
                )
                for (
                    contributor_type,
                    synonyms,
                ) in CONTRIBUTOR_TYPE_MAP.items():
                    if normalized_role in {
                        s.lower().replace(" ", "").replace("-", "").replace("_", "")
                        for s in synonyms
                    }:
                        matched_roles.add(contributor_type)
            # if we have no matched roles, default to "Other"
            if not matched_roles:
                matched_roles.add(ContributorType.Other)

            for role_type in matched_roles:
                datacite_actors.append(
                    Contributor(
                        name=extractor.name,
                        nameType=(
                            "Organizational"
                            if extractor.is_organization
                            else "Personal"
                        ),
                        givenName=extractor.given_names,
                        familyName=extractor.family_names,
                        nameIdentifiers=[NameIdentifier(**i) for i in name_identifiers]
                        or None,
                        affiliation=[AffiliationItem(**a) for a in affiliations]
                        or None,
                        contributorType=role_type.value,
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
        elif hasattr(f, "name") and isinstance(f.name, str):
            formats.append(f.name)
    return formats or None


def canonical_to_datacite(
    data: CanonicalCodeMeta, ignore_existing_doi=False, **custom_fields
) -> DataCite:
    primary_doi = (
        extract_doi_from_identifier(data.identifier)
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
    return DataCite(
        **{
            **dict(
                doi=primary_doi,
                prefix=doi_prefix,
                suffix=doi_suffix,
                url=get_first_if_list(data.url),
                types=Types(
                    resourceType=data.applicationCategory,
                    resourceTypeGeneral="Software",
                ),
                creators=codemeta_actors_to_datacite(data.author, Creator),
                titles=[Title(title=data.name)],
                publisher=get_first_if_list(
                    codemeta_actors_to_datacite(data.publisher, Publisher)
                ),
                publicationYear=(
                    str(data.datePublished.year) if data.datePublished else None
                ),
                subjects=[
                    Subject(subject=subject) for subject in ensure_list(data.keywords)
                ]
                or None,
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
                version=str(data.version) if data.version else None,
                rightsList=codemeta_license_to_datacite_rights(data.license),
                descriptions=descriptions,
                # codemeta.funding is a plain string, can't really ensure that the string
                # is the required name field
                # fundingReferences=None,
            ),
            **custom_fields,
        }
    )


def datacite_to_canonical(data: DataCite) -> CanonicalCodeMeta:
    raise NotImplementedError(
        "DataCite metadata is not yet supported as an input format"
    )
