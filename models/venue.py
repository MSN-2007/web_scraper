from pydantic import BaseModel, create_model
from typing import Optional, Any, Dict


class Venue(BaseModel):
    """
    Fallback static representation of a Venue.
    """
    name: str
    address: Optional[str] = None
    rating: Optional[float] = None
    phone_number: Optional[str] = None
    timings: Optional[str] = None
    reviews_count: Optional[int] = None
    website: Optional[str] = None
    email: Optional[str] = None
    price: Optional[str] = None
    services: Optional[str] = None
    description: Optional[str] = None


def get_dynamic_venue_model(schema_config: Dict[str, Any]) -> Any:
    """
    Creates and returns a dynamic Pydantic model class containing only active fields.
    
    Args:
        schema_config (Dict[str, Any]): The schema configuration from config.py.
        
    Returns:
        Type[BaseModel]: A dynamically generated Pydantic model.
    """
    fields = {}
    
    for field_name, info in schema_config.items():
        if info.get("active", False):
            # Determine python type from configuration type string
            type_str = info.get("type", "str")
            if type_str == "float":
                field_type = float
            elif type_str == "int":
                field_type = int
            elif type_str == "bool":
                field_type = bool
            else:
                field_type = str
            
            # Keep 'name' as required (represented by Ellipsis '...'),
            # all other active fields are optional with default None.
            if field_name == "name":
                fields[field_name] = (field_type, ...)
            else:
                fields[field_name] = (Optional[field_type], None)
                
    # If no fields were selected, fallback to name at least
    if not fields:
        fields["name"] = (str, ...)
        
    return create_model("DynamicVenue", **fields)
