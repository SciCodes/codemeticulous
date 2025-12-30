from pydantic import BaseModel
from codemeticulous.standards import STANDARDS
from litellm import completion
import logging
import instructor
from codemeticulous.prompt_strategies import FewShotStrategy
from codemeticulous.summarize_schema import get_schema_summary

logging.basicConfig(level=logging.INFO)

# Toggle for additional llm debugging
# litellm._turn_on_debug()


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

    source_model_schema = get_schema_summary(source_model, llm_model, key, source_instance)

    # FIXME: create target schema summary and fix up prompts
    strategy = FewShotStrategy()
    messages = strategy.generate_system_prompt(source_instance)

    # TESTING: instructor structured output
    target_data = structured_completion(llm_model, messages, target_model, key)

    return target_data