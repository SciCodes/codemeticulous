from abc import ABC, abstractmethod

class PromptStrategy(ABC):
    @abstractmethod
    def generate_system_prompt(self, source_instance) -> list:
        pass

    
class DefaultPrompt(PromptStrategy):
    PROMPT = """
    Your task is to convert source metadata from one format to another using the provided schemas.

    INPUTS PROVIDED:
    - Source data: A Pydantic model instance containing the original metadata
    - Source schema: A JSON object containing the source Pydantic model's fields and descriptions
    - Target schema: The Pydantic model definition for the output format

    INSTRUCTIONS:
    1. Analyze the source data and understand its structure.
    2. Extract and map the relevant fields from the source data to the corresponding fields in the target format.
    3. Transform data types and structures as needed to match the target schema requirements which could either be one-to-one or complex transformations.
    4. Instantiate the target model using the mapped and transformed data, so that a new instance of the target Pyndantic model can be created.

    OUTPUT REQUIREMENTS:
    - Return ONLY a raw JSON without any further encoding such as escaping quotes.
    - Ensure all required fields in the target schema are populated
    - Use appropriate data types as defined in the target schema

    The final output must be an instance of the target model schema that can be successfully validated by Pydantic.
    """

    def generate_system_prompt(self, source_instance, source_schema, target_schema) -> list:

        return [
            {"role": "system", "content": self.PROMPT},
            {"role": "user", "content": "SOURCE_DATA:\n" + source_instance.json()},
            {"role": "user", "content": "SOURCE SCHEMA\n" + source_schema},
            {"role": "user", "content": "TARGET_MODEL:\n" + target_schema}
        ]