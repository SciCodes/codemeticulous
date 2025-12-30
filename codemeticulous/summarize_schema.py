from pydantic import BaseModel
import re
import json
import csv
import litellm

def generate_desc(model_name: str, data, llm_model: str, api_key: str):
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
            api_key=api_key,
            model=llm_model
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR: structured output failed: {e}") 
        raise


def get_schema_summary(source_model: type[BaseModel], llm_model: str, api_key: str, instance_data: BaseModel = None):
    # Generate a nested list of fields and their types
    fields = []

    for field_name, model_field in source_model.__fields__.items():
        # if there's an instance and the field isn't referenced in it, skip
        if instance_data is not None and getattr(instance_data, field_name) is None:
            continue
        
        field_type = model_field.annotation
        field = [field_name, field_type]
        fields.append(field)

    llm_response = generate_desc(source_model.__name__, fields, llm_model, api_key) # Call to LLM to generate field's description

    match = re.search(r'\{.*\}|\[.*\]', llm_response, re.DOTALL) # Clean up reponse in case it's wrapped around any unnecessary text/syntax

    if match:
        llm_response = match.group(0)

    try:
        output = json.loads(llm_response)

        filename = f"{source_model.__name__}.csv"

        # Create a csv retaining the final schema information
        with open(filename, "w", newline='') as csvfile:
          csvwriter = csv.writer(csvfile)
          csvwriter.writerow(["Field Name", "Field Type", "Description"])
          csvwriter.writerows(output)

    except Exception as e:
        print(f"ERROR: failed to create list from llm response: ", e)