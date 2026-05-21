import litellm
import logging
import re
import json
import ast
from pathlib import Path
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


def structured_completion(llm_model: str, messages: list, target_model: BaseModel) -> tuple[BaseModel | None, dict]:
    max_retries = 3 # sets limit on retries if llm's output has validation errors
    prompt_tokens = 0
    completion_tokens = 0

    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=llm_model,
                messages=messages,
                temperature=0.3
            )
            # try: 
            #     total_cost += litellm.completion_cost(completion_response=response)
            # except Exception:
            #     pass
            prompt_tokens += getattr(response.usage, "prompt_tokens", 0) or 0
            completion_tokens += getattr(response.usage, "completion_tokens", 0) or 0

            output = extract_json(response.choices[0].message.content)
            validated_model = target_model(**output)
            usage = {
                # "cost": round(total_cost, 6),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
            return validated_model, usage
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


def get_examples(crosswalk: str, num: int = 1):
    PATH = Path(__file__).parent.parent / "tests_llm" / "logs" / "passed_cases.json"
    raw = PATH.read_text() if PATH.exists() else ""
    cases = json.loads(raw) if raw.strip() else []
    return [c for c in cases if c["source:target"] == crosswalk][:num] #TODO: randomize example selection


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
    else:
        raise TypeError(
             f"source_data must be a dict or an instance of {source_model.__name__}; "
             f"got {type(source_data).__name__}"
         )

    # Create summarized schema of source pydantic model according to data instance
    source_schema_dict = check_schema(source_format, source_instance)
    source_schema = json.dumps(source_schema_dict, indent=2)

    target_schema = check_schema(target_format)
    target_schema = json.dumps(target_schema, indent=2)

    strategy = DefaultPrompt()
    messages = strategy.generate_system_prompt(source_schema, target_schema)

    # inject few shot examples of past conversions, then end with the actual source data
    examples = get_examples(f"{source_format}:{target_format}")
    if examples:
        messages.append({"role": "system", "content": f"Here are some examples of correct conversions between {source_format} and {target_format}:"})
    
    for ex in examples:
        messages.append({"role": "user", "content": "SOURCE_DATA:\n" + json.dumps(ex["source_metadata"])})
        messages.append({"role": "assistant", "content": json.dumps(ex["llm_output"])})

    messages.append({"role": "user", "content": "SOURCE_DATA:\n" + source_instance.json()})
    target_data, usage = structured_completion(llm_model, messages, target_model)

    return target_data, usage