import csv
from typing import List, Set, Dict, Any, Optional

from models.venue import Venue


def is_duplicate_venue(venue_name: str, seen_names: Set[str]) -> bool:
    """
    Checks if a venue name is already registered.
    """
    return venue_name in seen_names


def is_complete_venue(venue: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    Validates if a venue dictionary contains all requested/required fields.
    """
    return all(key in venue and venue[key] is not None for key in required_keys)


def save_venues_to_csv(venues: List[Dict[str, Any]], filename: str, fieldnames: Optional[List[str]] = None):
    """
    Saves extracted records into a CSV database. Only columns specified in fieldnames are outputted.
    """
    if not venues:
        print("No venues to save.")
        return

    # Fallback to static model fields if none provided
    if not fieldnames:
        fieldnames = list(Venue.model_fields.keys())

    # Write dictionary items mapping strictly to fieldnames
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(venues)
        
    print(f"Saved {len(venues)} venues to '{filename}'.")
