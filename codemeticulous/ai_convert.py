from pydantic import BaseModel
from codemeticulous.standards import STANDARDS
from litellm import completion
import logging
import instructor

console = logging.getLogger(__name__)

# Toggle for additional llm debugging
# litellm._turn_on_debug()

INSTRUCTION_PROMPT = """
You are a metadata conversion specialist. Your task is to convert source metadata from one format to another using the provided schemas.

INPUTS PROVIDED:
- Source data: A Pydantic model instance containing the original metadata

INSTRUCTIONS:
1. Analyze the source data and understand its structure.
2. Map the relevant fields from the source data to the corresponding fields in the target response format.
3. Transform data types and structures as needed to match the target schema requirements which could either be one-to-one or complex transformations.
4. Instantiate the target model using the mapped and transformed data, so that a new instance of the target Pyndantic model can be created.

OUTPUT REQUIREMENTS:
- Return ONLY a valid JSON object that conforms exactly to the target response schema
- Do not include any explanatory text, comments, or additional formatting
- Ensure all required fields in the target response schema are populated and in order.
- Use appropriate data types as defined in the target response schema

The final output must be an instance of the target response schema that can be successfully validated by Pydantic.
"""

def generate_prompts(source_instance, target_model: BaseModel) -> list:
    target_schema = target_model.schema_json(indent=2)
    logging.info("TARGET SCHEMA: " + target_model.__name__)
    logging.info(f"Schema length: {len(target_schema)} characters")

    return [
        {"role": "system", "content": INSTRUCTION_PROMPT},
        {"role": "user", "content": "SOURCE_DATA:\n" + source_instance.json()},
    ]

def structured_completion(llm_model: str, messages: list, target_model: BaseModel, key: str) -> BaseModel | None:
    client = instructor.from_litellm(completion)

    try:
        response = client.chat.completions.create(
            model=llm_model,
            response_model=target_model,
            messages=messages,
            api_key=key,
            retries=3
        )
        return response
    except Exception as e:
        logging.error(f"ERROR: structured output failed: {e}") 
        raise

def convert_ai(key: str, llm_model: str, source_format: str, target_format: str, source_data):
    """
    Automate metadata standard conversion using LLM and canonical representation.

    Args:
    - key: API key for LLM authorization.
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

    messages = generate_prompts(source_instance, target_model)

    # TESTING: instructor structured output
    target_data = structured_completion(llm_model, messages, target_model, key)

    return target_data