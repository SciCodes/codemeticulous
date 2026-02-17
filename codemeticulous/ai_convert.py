import litellm
import logging
import re
import json
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from codemeticulous.standards import STANDARDS
from codemeticulous.prompt_strategies import DefaultPrompt
from codemeticulous.summarize_schema import check_schema

logging.basicConfig(level=logging.INFO)
load_dotenv()

# Toggle for additional llm debugging
# litellm._turn_on_debug()


def extract_json(llm_output: str) -> dict:
    # Try to extract JSON from markdown code block and disregard it
    json_match = re.search(r'```json\s*(.*?)\s*```', llm_output, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1)
    else:
        # If no code block found, assume the whole string is JSON obj
        json_str = llm_output
    return json.loads(json_str)


def structured_completion(llm_model: str, messages: list, target_model: BaseModel) -> BaseModel | None:
    try:
        response = litellm.completion(
            model=llm_model,
            messages=messages,
        )
        output = extract_json(response.choices[0].message.content)
        # logging.info(output)
    except Exception as e:
        logging.error(f"ERROR: structured output failed: {e}") 
        raise

    try:
        return target_model(**output)
    except ValidationError as e: #TODO: add llm retries if there's validation errors
        logging.error(f"Pydantic validation error: {e}")
        raise


def convert_ai(llm_model: str, source_format: str, target_format: str, source_data):
    """
    Automate metadata standard conversion using LLM and canonical representation.

    Args:
    - llm_model: LLM model string (e.g., "openrouter/openai/gpt-4o").
    - source_format: string representation of the source metadata standard.
    - target_format: string representation of the target metadata standard.
    - model: LLM model string (e.g., "openrouter/openai/gpt-4o")
    - source_data: dict or pydantic.BaseModel instance representing the source metadata
    """
    
    # Build prompt messages using pydantic schemas and the source data
    source_model = STANDARDS[source_format]["model"]
    target_model = STANDARDS[target_format]["model"]

    # Creates pydantic model instance of source data
    if isinstance(source_data, dict):
        source_instance = source_model(**source_data)
    elif isinstance(source_data, source_model):
        source_instance = source_data

    # Create summarized schema of source pydantic model according to data instance
    source_schema_dict = check_schema(source_format, llm_model, source_instance)
    source_schema = json.dumps(source_schema_dict, indent=2)

    target_schema = check_schema(target_format, llm_model)
    target_schema = json.dumps(target_schema, indent=2)
    # logging.info(target_schema)

    strategy = DefaultPrompt()
    messages = strategy.generate_system_prompt(source_instance, source_schema, target_schema)
    target_data = structured_completion(llm_model, messages, target_model)

    return target_data