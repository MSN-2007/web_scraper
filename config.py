# config.py

# Universal extraction schema definition.
# Define what fields to search and extract in simple language.
# Toggle "active": True to scrape a field, or False to deactivate it.
EXTRACTION_SCHEMA = {
    "name": {
        "active": True,
        "type": "str",
        "description": "The official brand, website, business, or venue name."
    },
    "colors": {
        "active": True,
        "type": "str",
        "description": "The main color palette (primary, secondary, backgrounds, text colors) as hex/rgb values."
    },
    "typography": {
        "active": True,
        "type": "str",
        "description": "Font families, font sizes, weights, and text styling details used across the page."
    },
    "components": {
        "active": True,
        "type": "str",
        "description": "Key UI components identified (e.g. hero section, navigation bars, cards, grid items, CTA buttons)."
    },
    "spacing_and_grid": {
        "active": False,
        "type": "str",
        "description": "Grid alignments, margins, padding system, and spacing rules observed."
    },
    "logo_url": {
        "active": False,
        "type": "str",
        "description": "The source URL of the official brand logo image."
    },
    "assets_list": {
        "active": False,
        "type": "str",
        "description": "Urls of key images, icons, illustrations, and visual assets used."
    },
    "address": {
        "active": False,
        "type": "str",
        "description": "The complete physical address, location description, or landmark."
    },
    "phone_number": {
        "active": False,
        "type": "str",
        "description": "The contact telephone or phone number."
    },
    "email": {
        "active": False,
        "type": "str",
        "description": "The contact email address."
    },
    "website": {
        "active": False,
        "type": "str",
        "description": "The official website link or URL."
    }
}

# Default search configurations (can be overridden in the Web UI or TUI)
BASE_URL = "https://datoms.io/cold-storage-monitoring/"
CSS_SELECTOR = "body"

# Minimum required keys for a record to be considered complete
REQUIRED_KEYS = ["name"]
