import litellm
import logging
import re
import json
import ast
from pydantic import BaseModel, ValidationError
from codemeticulous.standards import STANDARDS
from codemeticulous.prompt_strategies import DefaultPrompt
from codemeticulous.generate_schemas import check_schema

logging.basicConfig(level=logging.INFO)

# Toggle for additional llm debugging
# litellm._turn_on_debug()

def extract_json(llm_output: str) -> dict:
    # Try to extract JSON from markdown code block first
    json_match = re.search(r'```json\s*(.*?)\s*```', llm_output, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Fall back to extracting the first JSON object from the string
        json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
        json_str = json_match.group(0) if json_match else llm_output

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logging.error(f"ERROR: failed to decode JSON from LLM output: {json_str}")
        # Try to fix single-quoted keys/values produced by the LLM
        return ast.literal_eval(json_str)


def structured_completion(llm_model: str, messages: list, target_model: BaseModel) -> BaseModel | None:
    max_retries = 3 # sets limit on retries if llm's output has validation errors

    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=llm_model,
                messages=messages,
                temperature=0.3
            )
            output = extract_json(response.choices[0].message.content)
            validated_model = target_model(**output)
            return validated_model
        except ValidationError as e:
            logging.warning(f"Pydantic validation error on attempt {attempt + 1}: {e}")

            if attempt < max_retries - 1:
                failing_fields = [err["loc"][0] for err in e.errors() if err["loc"]]
                error_msg = {
                    "role": "user",
                    "content": f"""
                    The previous JSON output had validation errors. Return the same JSON with ONLY these fields corrected — do not change anything else:

                    Failing fields: {failing_fields}

                    Errors:
                    {str(e)}
                    """
                }
                messages.append({"role": "assistant", "content": response.choices[0].message.content})
                messages.append(error_msg)
            else:
                logging.error(f"ERROR: LLM had validation failures after {max_retries}")
                raise
        except Exception as e:
            logging.error(f"ERROR: LLM completion call failed: {e}")
            raise


def convert_ai(llm_model: str, source_format: str, target_format: str, source_data):
    """
    Automate metadata standard conversion using LLM and canonical representation.

    Args:
    - llm_model: LLM model string (e.g., "openrouter/openai/gpt-4o").
    - source_format: string representation of the source metadata standard.
    - target_format: string representation of the target metadata standard.
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
    source_schema_dict = check_schema(source_format, source_instance)
    source_schema = json.dumps(source_schema_dict, indent=2)

    target_schema = check_schema(target_format)
    target_schema = json.dumps(target_schema, indent=2)

    strategy = DefaultPrompt()
    messages = strategy.generate_system_prompt(source_instance, source_schema, target_schema)
    target_data = structured_completion(llm_model, messages, target_model)

    return target_data