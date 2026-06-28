from pydantic import BaseModel
from typing import List, Dict

class FileSchema(BaseModel):
    name: str
    required_columns: List[str]

class SchemaConfig:
    """
    Configuration for expected columns in the input files.
    This provides basic validation. Subsets of these columns will be checked.
    """
    SALES = FileSchema(
        name="Sales",
        required_columns=["Project", "Tower", "Unit", "Customer Code", "Booking Value", "Sales Owner", "Status"]
    )
    
    CONSTRUCTION = FileSchema(
        name="Construction",
        required_columns=["Project", "Tower", "Milestone", "Planned Date", "Actual Progress", "Delay Reason", "Cost Impact"]
    )
    
    COLLECTIONS = FileSchema(
        name="Collections",
        required_columns=["Customer Code", "Milestone", "Demand Raised", "Due Date", "Amount Collected", "Overdue"]
    )
    
    AOP = FileSchema(
        name="AOP",
        required_columns=["Target Type", "Value", "Month"]
    )
    
    # Mapping for dynamic ingestion
    SCHEMAS = {
        "sales": SALES,
        "construction": CONSTRUCTION,
        "collections": COLLECTIONS,
        "aop": AOP
    }
