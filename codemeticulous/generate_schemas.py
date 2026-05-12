import re
import csv
import json
import logging
import litellm
from pathlib import Path
from codemeticulous.standards import STANDARDS


def llm_descriptions(model_name: str, data, llm_model: str) -> str:
    prompt = f"""
    For a Pydantic model '{model_name}', we have a list of lists, each containing a field and their field type. 

    Please provide:
    1. A more intuitive, human-readable type for each field (e.g., convert "typing.Optional[str]" to "Text", "typing.List[str]" to "List of Text", URLs to "URL", dates to "Date", etc.)
    2. A brief 1-2 sentence description of each field in relation to the model

    When determining intuitive types and descriptions:
    - For example with CodeMeta, reference Schema.org vocabulary where applicable (e.g., use Schema.org terms like "Text", "URL", "Date", "Person", "Organization")
    - Simplify Python typing syntax to be more readable (Optional means the field can be null, List means multiple values)
    - Use semantic type names that reflect the meaning rather than the implementation to be more intuitive.

    Your response should be a valid JSON array where each element is a list containing: [field_name, intuitive_type, description].
    Do not include outside explanatory text or formatting syntax so your response can be piped into 'json.loads()'.

    Here is the data:
    {data}
    """

    try:
        response = litellm.completion(
            messages=[{"role": "user", "content": prompt}],
            model=llm_model
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR: structured output failed: {e}") 
        raise

# TODO: move toggle to use defined schema json files here
def generate_schemas(llm_model: str):
    # iterate through all schemas in STANDARDS and create csv files to cache
    for format, info in STANDARDS.items():
        pydantic_model = info["model"]
        cache_directory = Path(__file__).parent.parent / "schema_cache"
        file = cache_directory / f"{format}.csv"

        if file.exists():
            continue

        fields = []

        for field_name, model_field in pydantic_model.__fields__.items():
            field_type = model_field.annotation
            field = [field_name, field_type]
            fields.append(field)

        llm_response = llm_descriptions(pydantic_model.__name__, fields, llm_model)
        match = re.search(r'\{.*\}|\[.*\]', llm_response, re.DOTALL) # clean up LLM response

        if match:
            llm_response = match.group(0)

        try:
            field_descriptions = json.loads(llm_response)

            # generate a csv retaining the final schema information and store to reuse
            with open(file, "w", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Field", "Type", "Description"])
                writer.writerows(field_descriptions)
        except Exception as e:
            logging.error(f"ERROR: failed to create list from llm response: ", e)  
            raise             


def check_schema(model: str, flag: bool = False): 
    schema_file = STANDARDS[model]["schema"]

    if flag and schema_file is not None: # iterate through fields if there's an instance that calls for the schema to be pruned
        with open(schema_file, 'r') as f:
            schema = json.load(f)
        
        return schema
    
    else: # check for schema_cache directory, return the data file if its exists
        cache_directory = Path(__file__).parent.parent / "schema_cache"
        file = cache_directory / f"{model}.csv"

        if file.exists():
            with open(file, 'r') as f:
                reader = csv.DictReader(f)
                fields = [dict(row) for row in reader]

            return {
                "model_name": model,
                "fields": fields
            }
            
        else: # if it doesn't exist, use LLM to generate a csv of schema information
            logging.info("ERROR: schemas were not generated yet, call uv run codemeticulous generate-schemas.")
            raise