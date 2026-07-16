# config.py

# Universal extraction schema definition.
# Define what fields to search and extract in simple language.
# Toggle "active": True to scrape a field, or False to deactivate it.
EXTRACTION_SCHEMA = {
    "name": {
        "active": True,
        "type": "str",
        "description": "The official name of the business, hospital, clinic, or venue."
    },
    "address": {
        "active": True,
        "type": "str",
        "description": "The complete physical address, location description, or landmark."
    },
    "phone_number": {
        "active": True,
        "type": "str",
        "description": "The telephone or contact phone number."
    },
    "timings": {
        "active": True,
        "type": "str",
        "description": "Working hours or operation timings (e.g., Open 24 Hrs, 9:00 AM - 5:00 PM)."
    },
    "rating": {
        "active": False,
        "type": "float",
        "description": "The numerical user rating score (e.g., 4.5) out of 5 stars."
    },
    "reviews_count": {
        "active": False,
        "type": "int",
        "description": "The total number of customer reviews or ratings."
    },
    "website": {
        "active": False,
        "type": "str",
        "description": "The official website link or URL."
    },
    "email": {
        "active": False,
        "type": "str",
        "description": "The contact email address."
    },
    "price": {
        "active": False,
        "type": "str",
        "description": "Pricing details, costs, fees, or price range info."
    },
    "services": {
        "active": False,
        "type": "str",
        "description": "Specific services, facilities, specialties, or products offered."
    },
    "description": {
        "active": False,
        "type": "str",
        "description": "A concise description summarizing their offerings or business."
    }
}

# Default search configurations (can be overridden in the Web UI)
BASE_URL = "https://www.justdial.com/Zahirabad/Hospitals-in-Zaheerabad-Main-Road/nct-10253670"
CSS_SELECTOR = "div.resultbox"

# Minimum required keys for a record to be considered complete
REQUIRED_KEYS = ["name"]
