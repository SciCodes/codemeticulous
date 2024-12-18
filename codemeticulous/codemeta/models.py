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
from pydantic2_schemaorg.CreativeWork import CreativeWork
from pydantic2_schemaorg.MediaObject import MediaObject
from pydantic2_schemaorg.SoftwareApplication import SoftwareApplication

from codemeticulous.utils import map_dict_keys
from codemeticulous.mixins import ByAliasExcludeNoneMixin


class VersionedLanguage(ComputerLanguage):
    """extends ComputerLanguage to allow for additional fields"""

    version: Optional[str]


Actor = Role | Person | Organization
ActorList = list[Actor]
ActorListOrSingle = Actor | ActorList

TextOrUrl = str | AnyUrl
TextOrUrlList = list[TextOrUrl]
TextOrUrlListOrSingle = TextOrUrl | TextOrUrlList

Software = SoftwareSourceCode | SoftwareApplication | str | AnyUrl
SoftwareList = list[Software]
SoftwareListOrSingle = Software | SoftwareList


class CodeMetaV3(ByAliasExcludeNoneMixin, BaseModel):
    """CodeMeta v3 schema (supports v2 fields aliased to v3)
    see: https://codemeta.github.io/terms/
    and: https://github.com/codemeta/codemeta-generator/blob/master/js/validation/
    """

    context: Any = Field(default="https://w3id.org/codemeta/3.0", alias="@context")
    type_: str = Field(default="SoftwareSourceCode", alias="@type")
    id_: Optional[str] = Field(alias="@id")

    name: str

    codeRepository: Optional[AnyUrl]
    programmingLanguage: Optional[
        VersionedLanguage | str | list[VersionedLanguage | str]
    ]
    runtimePlatform: Optional[str | list[str]]
    targetProduct: Optional[list[SoftwareApplication | str] | SoftwareApplication | str]
    applicationCategory: Optional[TextOrUrlListOrSingle]
    applicationSubCategory: Optional[TextOrUrlListOrSingle]
    downloadUrl: Optional[list[AnyUrl] | AnyUrl]
    fileSize: Optional[str]
    installUrl: Optional[list[AnyUrl] | AnyUrl]
    memoryRequirements: Optional[TextOrUrlListOrSingle]
    operatingSystem: Optional[list[str] | str]
    permissions: Optional[list[str] | str]
    processorRequirements: Optional[list[str] | str]
    releaseNotes: Optional[TextOrUrlListOrSingle]
    softwareHelp: Optional[list[CreativeWork | AnyUrl] | CreativeWork | AnyUrl]
    softwareRequirements: Optional[SoftwareListOrSingle]
    softwareVersion: Optional[str]
    storageRequirements: Optional[TextOrUrlListOrSingle]
    supportingData: Optional[list[DataFeed] | DataFeed]
    author: Optional[ActorListOrSingle]
    citation: Optional[list[CreativeWork | AnyUrl] | CreativeWork | AnyUrl]
    contributor: Optional[ActorListOrSingle]
    copyrightHolder: Optional[ActorListOrSingle]
    copyrightYear: Optional[list[int] | int]
    creator: Optional[ActorListOrSingle]
    dateCreated: Optional[date | datetime]
    dateModified: Optional[date | datetime]
    datePublished: Optional[date | datetime]
    editor: Optional[list[Person] | Person]
    encoding: Optional[list[MediaObject] | MediaObject]
    fileFormat: Optional[TextOrUrlListOrSingle]
    funder: Optional[ActorListOrSingle]
    keywords: Optional[list[str] | str]
    license: Optional[list[CreativeWork | AnyUrl] | CreativeWork | AnyUrl]
    producer: Optional[ActorListOrSingle]
    provider: Optional[ActorListOrSingle]
    publisher: Optional[ActorListOrSingle | list[str] | str]
    sponsor: Optional[ActorListOrSingle]
    version: Optional[list[int | float | str] | int | float | str]
    isAccessibleForFree: Optional[bool]
    isPartOf: Optional[list[CreativeWork | AnyUrl] | CreativeWork | AnyUrl]
    hasPart: Optional[list[CreativeWork | AnyUrl] | CreativeWork | AnyUrl]
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
    hasSourceCode: Optional[SoftwareListOrSingle]
    isSourceCodeOf: Optional[
        list[SoftwareApplication | str | AnyUrl] | SoftwareApplication | str | AnyUrl
    ]
    softwareSuggestions: Optional[SoftwareListOrSingle]
    maintainer: Optional[ActorListOrSingle]
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

    @validator(
        "softwareHelp",
        "citation",
        "license",
        "isPartOf",
        "hasPart",
        pre=True,
        each_item=True,
    )
    def validate_creative_work(cls, v):
        if v is None:
            return v
        elif isinstance(v, list):
            return [cls.validate_sub_type(item, CreativeWork) for item in v]
        else:
            return cls.validate_sub_type(v, CreativeWork)

    @validator("encoding", pre=True, each_item=True)
    def validate_media_object(cls, v):
        if v is None:
            return v
        elif isinstance(v, list):
            return [cls.validate_sub_type(item, MediaObject) for item in v]
        else:
            return cls.validate_sub_type(v, MediaObject)

    @validator(
        "targetProduct",
        "softwareRequirements",
        "hasSourceCode",
        "isSourceCodeOf",
        "softwareSuggestions",
        pre=True,
        each_item=True,
    )
    def validate_software_application(cls, v):
        if v is None:
            return v
        elif isinstance(v, list):
            return [cls.validate_sub_type(item, SoftwareApplication) for item in v]
        else:
            return cls.validate_sub_type(v, SoftwareApplication)

    @root_validator(pre=True)
    def map_type_and_id(cls, values):
        # codemeta allows "type" instead of "@type" and "id" instead of "@id"
        # we will map it to "@type" and "@id" for consistency
        return map_dict_keys(values, {"type": "@type", "id": "@id"})

    @root_validator(pre=True)
    def collapse_jsonld_context(cls, values):
        # everything should be within the codemeta context, so we flatten the @context
        # and remove jsonld prefixes
        context = values.get("@context")
        if isinstance(context, dict):
            prefixes = list(context.keys())
            for key in list(values.keys()):
                for prefix in prefixes:
                    if key.startswith(f"{prefix}:"):
                        values[key.replace(f"{prefix}:", "")] = values.pop(key)
                        break
        # always remove @context so it gets set to the default codemeta v3 context
        values.pop("@context", None)
        return values

    @root_validator(pre=True)
    def fix_role_node_link(cls, values):
        """roles aren't terribly well documented, but they appear to be done by linking
        a Role to a Person or Organization node with "@id" or "contributor"/"author". The
        Codemeta generator uses the key "schema:author" and "contributor", but it seems better
        to use the node @id that actually exists in a schema.org Role

        see https://github.com/codemeta/codemeta/issues/240
        """
        KEYS = ["author", "contributor", "schema:author", "schema:contributor"]

        def transform_role(role_item):
            if isinstance(role_item, dict) and (
                role_item.get("type") == "Role" or role_item.get("@type") == "Role"
            ):
                for key in KEYS:
                    if key in role_item:
                        role_item["@id"] = role_item.pop(key)
                        break
            return role_item

        for field in ["author", "contributor"]:
            if field in values:
                if isinstance(values[field], list):
                    values[field] = [
                        transform_role(role_item) for role_item in values[field]
                    ]
                else:
                    values[field] = transform_role(values[field])
        return values

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

    @classmethod
    def validate_sub_type(cls, value, base_class):
        """Ensure that the value is a sub-type of the given base_class using
        the "@type" field as a discriminator.

        e.g. { "@type": "Blog" , ... } should be validated as a Blog object
        which is a sub-type of CreativeWork

        This is necessary because pydantic does not support 'automatic' polymorphism
        like this, and creating massive union types for every possible sub-type is
        extremely innefficient as opposed to the dynamic importing done here
        """
        if isinstance(value, dict):
            type_ = value.get("@type") or value.get("type") or base_class.__name__
            try:
                module_name = f"pydantic2_schemaorg.{type_}"
                module = __import__(module_name, fromlist=[type_])
                ModelClass = getattr(module, type_)
                if not issubclass(ModelClass, base_class):
                    raise TypeError(f"{type_} is not a sub-type of {base_class}")
                return ModelClass(**value)
            except ImportError:
                return base_class(**value)
        elif isinstance(value, (str, AnyUrl)):
            return value
        else:
            raise ValueError(f"Invalid type for {base_class.__name__}")

    class Config:
        allow_population_by_field_name = True


CodeMeta = CodeMetaV3
