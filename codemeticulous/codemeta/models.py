from __future__ import annotations

from typing import Optional, Any
from datetime import date, datetime

from pydantic.v1 import Field, AnyUrl, BaseModel, validator, root_validator
from pydantic2_schemaorg.SoftwareSourceCode import SoftwareSourceCode
from pydantic2_schemaorg.Person import Person
from pydantic2_schemaorg.Organization import Organization
from pydantic2_schemaorg.ComputerLanguage import ComputerLanguage
from pydantic2_schemaorg.DataFeed import DataFeed
from pydantic2_schemaorg.ScholarlyArticle import ScholarlyArticle
from pydantic2_schemaorg.Review import Review
from pydantic2_schemaorg.PropertyValue import PropertyValue
from pydantic2_schemaorg.Role import Role

from codemeticulous.codemeta.types import (
    CreativeWorkType,
    MediaObjectType,
    SoftwareApplicationType,
)
from codemeticulous.common.utils import map_dict_keys
from codemeticulous.common.mixins import ByAliasExcludeNoneMixin


class FlexibleRole(Role):
    """extends Role to allow for additional fields

    FIXME: structuring this would be helpful so that "roled" authors/contributors can be
    reliably extracted from a CodeMeta object. This is a bit of a hack for now.

    it is unclear how exactly this is supposed to work but it seems that the
    intent is to wrap authors/contributors in a Role e.g.:
    {
        "@type": "Role",
        "roleName": "author",
        "schema:author": {
            "@type": "Person",
            "name": "John Doe"
        }
    }
    """

    class Config:
        extra = "allow"


class CodeMeta(ByAliasExcludeNoneMixin, BaseModel):
    """CodeMeta v3 schema (supports v2 fields aliased to v3)
    see: https://codemeta.github.io/terms/
    and: https://github.com/codemeta/codemeta-generator/blob/master/js/validation/
    """

    context: Any = Field(default="https://w3id.org/codemeta/3.0", alias="@context")
    type_: str = Field(default="SoftwareSourceCode", alias="@type")

    name: str

    codeRepository: Optional[AnyUrl]
    programmingLanguage: Optional[ComputerLanguage | str | list[ComputerLanguage | str]]
    runtimePlatform: Optional[str | list[str]]
    targetProduct: Optional[
        list[SoftwareApplicationType | str] | SoftwareApplicationType | str
    ]
    applicationCategory: Optional[list[str | AnyUrl] | str | AnyUrl]
    applicationSubCategory: Optional[list[str | AnyUrl] | str | AnyUrl]
    downloadUrl: Optional[list[AnyUrl] | AnyUrl]
    fileSize: Optional[str]
    installUrl: Optional[list[AnyUrl] | AnyUrl]
    memoryRequirements: Optional[list[str | AnyUrl] | str | AnyUrl]
    operatingSystem: Optional[list[str] | str]
    permissions: Optional[list[str] | str]
    processorRequirements: Optional[list[str] | str]
    releaseNotes: Optional[list[str | AnyUrl] | str | AnyUrl]
    softwareHelp: Optional[list[CreativeWorkType] | CreativeWorkType]
    softwareRequirements: Optional[
        list[SoftwareSourceCode | str | AnyUrl] | SoftwareSourceCode | str | AnyUrl
    ]
    softwareVersion: Optional[str]
    storageRequirements: Optional[list[str | AnyUrl] | str | AnyUrl]
    supportingData: Optional[list[DataFeed] | DataFeed]
    author: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    citation: Optional[list[CreativeWorkType | AnyUrl] | CreativeWorkType | AnyUrl]
    contributor: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    copyrightHolder: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    copyrightYear: Optional[list[int] | int]
    creator: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    dateCreated: Optional[date | datetime]
    dateModified: Optional[date | datetime]
    datePublished: Optional[date | datetime]
    editor: Optional[list[Person] | Person]
    encoding: Optional[list[MediaObjectType] | MediaObjectType]
    fileFormat: Optional[list[str | AnyUrl] | str | AnyUrl]
    funder: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    keywords: Optional[list[str] | str]
    license: Optional[list[CreativeWorkType | AnyUrl] | CreativeWorkType | AnyUrl]
    producer: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    provider: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    publisher: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    sponsor: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    version: Optional[list[int | float | str] | int | float | str]
    isAccessibleForFree: Optional[bool]
    isPartOf: Optional[list[CreativeWorkType] | CreativeWorkType]
    hasPart: Optional[list[CreativeWorkType] | CreativeWorkType]
    position: Optional[list[int | str] | int | str]
    identifier: Optional[
        list[PropertyValue | str | AnyUrl] | PropertyValue | str | AnyUrl
    ]
    description: Optional[str]
    sameAs: Optional[list[AnyUrl] | AnyUrl]
    url: Optional[list[AnyUrl] | AnyUrl]
    relatedLink: Optional[list[AnyUrl] | AnyUrl]
    review: Optional[Review]

    # CodeMeta-specific terms
    # these are more loosely defined than the schema.org/SoftwareSourceCode properties above
    hasSourceCode: Optional[
        list[SoftwareSourceCode | str | AnyUrl] | SoftwareSourceCode | str | AnyUrl
    ]
    isSourceCodeOf: Optional[
        list[SoftwareApplicationType | str | AnyUrl]
        | SoftwareApplicationType
        | str
        | AnyUrl
    ]
    softwareSuggestions: Optional[
        list[SoftwareSourceCode | str | AnyUrl] | SoftwareSourceCode | str | AnyUrl
    ]
    maintainer: Optional[
        list[FlexibleRole | Person | Organization]
        | FlexibleRole
        | Person
        | Organization
    ]
    contIntegration: Optional[list[AnyUrl] | AnyUrl]
    continuousIntegration: Optional[list[AnyUrl] | AnyUrl]
    buildInstructions: Optional[list[AnyUrl] | AnyUrl]
    developmentStatus: Optional[str]
    embargoDate: Optional[date | datetime]
    embargoEndDate: Optional[date | datetime]
    funding: Optional[list[str] | str]
    issueTracker: Optional[list[AnyUrl] | AnyUrl]
    referencePublication: Optional[
        list[ScholarlyArticle | str | AnyUrl] | ScholarlyArticle | str | AnyUrl
    ]
    readme: Optional[list[AnyUrl] | AnyUrl]

    @validator("type_")
    def validate_type(cls, v):
        if v not in ["SoftwareSourceCode", "SoftwareApplication"]:
            raise ValueError(
                "@type must be 'SoftwareSourceCode' or 'SoftwareApplication'"
            )
        return v

    @root_validator(pre=True)
    def map_type_and_id(cls, values):
        # codemeta allows "type" instead of "@type" and "id" instead of "@id"
        # we will map it to "@type" and "@id" for consistency
        return map_dict_keys(values, {"type": "@type", "id": "@id"})

    @root_validator(pre=True)
    def coalesce_embargo_end_date(cls, values):
        embargo_date = values.get("embargoDate")
        embargo_end_date = values.get("embargoEndDate")
        if embargo_date and embargo_end_date:
            raise ValueError(
                "'embargoDate' field is removed in CodeMeta v3, use 'embargoEndDate' instead"
            )
        # if embargoDate is present but embargoEndDate is not, do this automatically
        if embargo_date:
            values["embargoEndDate"] = embargo_date
            del values["embargoDate"]
        return values

    @root_validator(pre=True)
    def coalesce_continuous_integration(cls, values):
        cont_integration = values.get("contIntegration")
        continuous_integration = values.get("continuousIntegration")
        if cont_integration and continuous_integration:
            raise ValueError(
                "'contIntegration' field is removed in CodeMeta v3, use 'continuousIntegration' instead"
            )
        # if contIntegration is present but continuousIntegration is not, do this automatically
        if cont_integration:
            values["continuousIntegration"] = cont_integration
            del values["contIntegration"]
        return values

    @root_validator(pre=True)
    def coalesce_creator_author(cls, values):
        author = values.get("author")
        creator = values.get("creator")
        if author and creator:
            raise ValueError(
                "'creator' field is removed in CodeMeta v3, use 'author' instead"
            )
        # if creator is present but author is not, do this automatically
        if creator:
            values["author"] = creator
            del values["creator"]
        return values

    class Config:
        # type can be "type" or "@type"
        allow_population_by_field_name = True
