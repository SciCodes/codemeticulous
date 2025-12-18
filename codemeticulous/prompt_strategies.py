from abc import ABC, abstractmethod
from pydantic import BaseModel

class PromptStrategy(ABC):
    @abstractmethod
    def generate_system_prompt(self, source_instance) -> list:
        pass

    
class ZeroShotStrategy(PromptStrategy):
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

    def generate_system_prompt(self, source_instance) -> list:
        return [
            {"role": "system", "content": self.INSTRUCTION_PROMPT},
            {"role": "user", "content": "SOURCE_DATA:\n" + source_instance.json()},
        ]
        
    
class FewShotStrategy(PromptStrategy):
    FEW_SHOT_PROMPT = """
    You are a metadata conversion specialist. Your task is to convert source metadata from one format to another using the provided schemas.

    INPUTS PROVIDED:
    - Source data: A Pydantic model instance containing the original metadata that needs to be converted to the target format.

    INSTRUCTIONS:
    1. Analyze the source data and understand its structure.
    2. Extract relevant fields from the source data and map them to the corresponding fields in the target response format.
    4. Instantiate the target model using the mapped and transformed data, so that a new instance of the target Pyndantic model can be created.

    OUTPUT REQUIREMENTS:
    - Return ONLY a valid JSON object that conforms exactly to the target response schema.
    - Do not include any explanatory text, comments, or additional formatting
    - Ensure all required fields in the target response schema are populated and no extra fields are included.
    - Use appropriate data types as defined in the target response schema

    The final output must be an instance of the target response schema that can be successfully validated by Pydantic.
    
    EXAMPLES:
    Here are some examples of how to map fields from a source to a target schema.

    **Example 1: Simple Mapping**

    *   **Source Field:** `name` (string)
    *   **Target Field:** `title` (string)
    *   **Action:** Direct copy.

    **Example 2: Field Transformation**

    *   **Source Field:** `publication_year` (integer)
    *   **Target Field:** `datePublished` (string, ISO 8601 format)
    *   **Action:** Convert the year to a full date string, e.g., `2023` becomes `"2023-01-01"`.

    **Example 3: Handling Missing Fields**

    *   **Source Field:** `contact` (optional)
    *   **Target Field:** `contactPoint` (required)
    *   **Action:** If `contact` is missing in the source, provide a default value or an empty structure for `contactPoint` if the schema allows it, e.g., `{"email": "not available"}`.

    Now, apply these principles to the conversion task below.
    """

    def generate_system_prompt(self, source_instance) -> list:
        return [
            {"role": "system", "content": self.FEW_SHOT_PROMPT},
            {"role": "user", "content": "SOURCE_DATA:\n" + source_instance.json()},
        ]

    
# TODO: implement C-o-T strategy to test for poor llm models
class ChainOfThought(PromptStrategy):
    pass