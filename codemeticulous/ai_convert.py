from pydantic import BaseModel, ValidationError
from codemeticulous.standards import STANDARDS
import litellm
from litellm import completion
import os
import re
import json
import logging

console = logging.getLogger(__name__)

# For additional llm debugging
# litellm._turn_on_debug()

INSTRUCTION_PROMPT = """
You are a metadata conversion specialist. Your task is to convert source metadata from one format to another using the provided schemas.

INPUTS PROVIDED:
- Source data: A Pydantic model instance containing the original metadata
- Target schema: The Pydantic model definition for the output format

INSTRUCTIONS:
1. Analyze the source data and understand its structure.
2. Map the relevant fields from the source data to the corresponding fields in the target format.
3. Transform data types and structures as needed to match the target schema requirements which could either be one-to-one or complex transformations.
4. Instantiate the target model using the mapped and transformed data, so that a new instance of the target Pyndantic model can be created.

OUTPUT REQUIREMENTS:
- Return ONLY a valid JSON object that conforms exactly to the target schema
- Do not include any explanatory text, comments, or additional formatting
- Ensure all required fields in the target schema are populated and **IN ORDER**.
- Use appropriate data types as defined in the target schema

The final output must be an instance of the target model schema that can be successfully validated by Pydantic.
"""

def generate_prompts(source_instance, target_model: BaseModel) -> list:
    target_schema = target_model.schema_json(indent=2)
    logging.info("TARGET SCHEMA: " + target_model.__name__)
    logging.info(f"Schema length: {len(target_schema)} characters")

    return [
        {"role": "system", "content": INSTRUCTION_PROMPT},
        {"role": "user", "content": "SOURCE_DATA:\n" + source_instance.json()},
        {"role": "user", "content": "TARGET_MODEL_SCHEMA:\n" + target_schema},
    ]

def get_completion(llm_model: str, messages: list) -> str :
    # TODO: make this dynamic based on LLM provider (i.e. ollama, huggingface, etc) by adding chunking slider?
    try:
        response = litellm.completion(
            model=llm_model,
            messages=messages,
        )
    except Exception as e:
        logging.error(f"Error during LLM completion: {e}")
        raise e

    llm_response = response.choices[0].message.content
    return llm_response

def extract_json(llm_output: str) -> dict:
    # Try to extract JSON from markdown code block and disregard it
    json_match = re.search(r'```json\s*(.*?)\s*```', llm_output, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1)
    else:
        # If no code block found, assume the whole string is JSON obj
        json_str = llm_output
    
    logging.info(f"Extracted JSON string: {json_str}")
    return json.loads(json_str)


def convert_ai(key: str, llm_model: str, source_format: str, target_format: str, source_data):
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

    # Creates pydantic model instance of source data
    if isinstance(source_data, dict):
        source_instance = source_model(**source_data)
    elif isinstance(source_data, source_model):
        source_instance = source_data

    #TODO: temporary workaround for openrouter api key handling
    os.environ["OPENROUTER_API_KEY"] = key

    # TODO: split input prompts + maybe adding multishot capability
    messages = generate_prompts(source_instance, target_model)

    llm_output = get_completion(llm_model, messages)

    extracted_data = extract_json(llm_output)

    # Convert into a dict object and validate against target model
    try:
        target_data = target_model(**extracted_data)
    except ValidationError as e:
        logging.error(f"Validation failed: {e}")
        raise e
    
    return target_data