from codemeticulous.codemeta.models import CodeMeta
from codemeticulous.datacite.models import DataCite
from codemeticulous.cff.models import CitationFileFormat
from litellm import completion
import json
import os

STANDARDS = {
    "codemeta": {
        "model": CodeMeta,
        "format": "json"
    },
    "datacite": {
        "model": DataCite,
        "format": "json"
    },
    "cff": {
        "model": CitationFileFormat,
        "format": "yaml"
    },
}

def convert_ai(model: str, key: str, source_format: str, target_format: str, source_data):
    """
    Automate metadata standard conversion using LLM and canonical representation.

    Args:
    - source_format: string representation of the source metadata standard.
    - target_format: string representation of the target metadata standard.
    - model: LLM model string (e.g., "openrouter/openai/gpt-4o")
    - source_data: dict or pydantic.BaseModel instance representing the source metadata
    - custom_fields: additional fields to add to the target metadata instance
    """
    
    # Build prompt messages using pydantic schemas and the source data
    source_model = STANDARDS[source_format]["model"]
    target_model = STANDARDS[target_format]["model"]

    # Creates pydantic model instance of source data -- might be unnecessary
    if isinstance(source_data, dict):
        source_instance = source_model(**source_data)
    elif isinstance(source_data, source_model):
        source_instance = source_data

    messages = prompt_generator(source_instance, source_model, target_model)

    # FIXME: adjust configuration for LiteLLM's standard env var lookup
    os.environ['OPENROUTER_API_KEY'] = key

    # Call the LLM via litellm completion function
    response = completion(
        model=model, # need to add guardrails to ensure that model string is valid before attempting a completion call
        messages=messages,
    )

    # Extract assistant text from LLM response
    assistant_text = response.get("choices", [{}])[0].get("message", {}).get("content") if isinstance(response, dict) else response

    #TODO: Output response and see how it can be parsed + validated
    print("LLM response:", assistant_text)


def prompt_generator(source_dict, source_model, target_model) -> list:
    system = ( # Defining the model's 
        "You are a metadata conversion assistant using strictly the source and target schema models. ALWAYS return JSON only."
        "Do not include any explanatory text outside the JSON.\n"
        "If a source property cannot be mapped, add it to 'unmapped_properties' and explain in 'unmapped_explanations'.\n"
        "RESPONSE FORMAT (JSON only):\n"
        '{"converted": {...}, "unmapped_properties": ["property"], "unmapped_explanations": {"property":"reason"} }\n'

    )

    user = ( # Generating user query with given input for conversion
        "Convert the SOURCE_DATA to match TARGET_MODEL_SCHEMA.\n"
        "SOURCE_DATA:\n" + json.dumps(source_dict) + "\n\n"
        "SOURCE_MODEL_SCHEMA:\n" + json.dumps(source_model.schema()) + "\n\n"
        "TARGET_MODEL_SCHEMA:\n" + json.dumps(target_model.schema()) + "\n\n"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
