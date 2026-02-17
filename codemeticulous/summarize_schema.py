import re
import csv
import json
import logging
import litellm
from pydantic import BaseModel
from pathlib import Path
from codemeticulous.standards import STANDARDS

def generate_desc(model_name: str, data, llm_model: str) -> str:
    prompt = f"""
    For a Pydantic model '{model_name}', we have a list of lists, each containing a field and their field type. 

    In one or two sentences, please provide brief descriptions of each field in relation to the model at the end of each sub-list.
    Your response should be in a valid array consisting of the field name, field type, and new descriptions.
    Please do not include outside explanatory text or unnecessary formatting syntax so your response can be piped into 'json.loads()'.

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


def check_schema(model: str, llm_model: str, instance_data: BaseModel = None): 
    pydantic_model = STANDARDS[model]["model"]
    schema_file = STANDARDS[model]["schema"]

    if schema_file is not None: # iterate through fields if there's an instance that calls for the schema to be pruned
        with open(schema_file, 'r') as f:
            schema = json.load(f)
        
        # TODO: prune if there's instance data
        return schema
    
    else: # check for schema_cache directory, return the data file if its exists
        cache_directory = Path(__file__).parent.parent / "schema_cache"
        file = cache_directory / f"{model}.csv"

        if file.exists():
            with open(file, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                field_descriptions = [row for row in reader]
            
            return {
                "model_name": model,
                "fields": field_descriptions
            }
            
        else: # if it doesn't exist, use LLM to generate a csv of schema information
            fields = []

            for field_name, model_field in pydantic_model.__fields__.items():
                # if there's an instance and the field isn't referenced in it, skip
                if instance_data is not None and getattr(instance_data, field_name) is None:
                    continue
                field_type = model_field.annotation
                field = [field_name, field_type]
                fields.append(field)

            llm_response = generate_desc(pydantic_model.__name__, fields, llm_model)
            match = re.search(r'\{.*\}|\[.*\]', llm_response, re.DOTALL) # clean up LLM response

            if match:
                llm_response = match.group(0)

            try:
                field_descriptions = json.loads(llm_response)

                # generate a csv retaining the final schema information and store to reuse
                with open(file, "w", newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Field Name", "Field Type", "Description"])
                    writer.writerows(field_descriptions)
                
                return {
                    "model_name": model,
                    "fields": field_descriptions
                }
            except Exception as e:
                logging.error(f"ERROR: failed to create list from llm response: ", e)  
                raise 