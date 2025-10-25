"""restaurant discovery module for generating yelp and opentable URLs."""

from typing import Dict, List, Optional
from urllib.parse import quote_plus


class RestaurantIdentifier:
    """represents a restaurant with its associated URLs across platforms."""

    def __init__(
        self,
        name: str,
        location: str,
        yelp_url: Optional[str] = None,
        opentable_url: Optional[str] = None
    ) -> None:
        """initialize restaurant identifier.

        args:
            name: restaurant name
            location: city or address
            yelp_url: direct yelp business URL (if known)
            opentable_url: direct opentable restaurant URL (if known)
        """
        self.name = name
        self.location = location
        self.yelp_url = yelp_url
        self.opentable_url = opentable_url

    def to_dict(self) -> Dict[str, Optional[str]]:
        """convert to dictionary representation.

        returns:
            dict with name, location, and platform URLs
        """
        return {
            "name": self.name,
            "location": self.location,
            "yelp_url": self.yelp_url,
            "opentable_url": self.opentable_url
        }


def generate_yelp_search_url(restaurant_name: str, location: str) -> str:
    """generate yelp search URL for a restaurant.

    args:
        restaurant_name: name of the restaurant
        location: city or address to search in

    returns:
        yelp search URL string
    """
    encoded_name = quote_plus(restaurant_name)
    encoded_location = quote_plus(location)
    return f"https://www.yelp.com/search?find_desc={encoded_name}&find_loc={encoded_location}"


def generate_opentable_search_url(restaurant_name: str, location: str) -> str:
    """generate opentable search URL for a restaurant.

    args:
        restaurant_name: name of the restaurant
        location: city or address to search in

    returns:
        opentable search URL string
    """
    # opentable uses a different format: location first, then query
    encoded_name = quote_plus(restaurant_name)
    encoded_location = quote_plus(location)
    return f"https://www.opentable.com/s?term={encoded_name}&corrid=&covers=2&currentview=list&dateTime=2025-01-01T19:00:00&latitude=0&longitude=0&metroId=&originCorrelationId=&pageType=0&term={encoded_location}"


def create_restaurant_identifiers(
    restaurants: List[Dict[str, str]]
) -> List[RestaurantIdentifier]:
    """create restaurant identifiers from a list of restaurant data.

    args:
        restaurants: list of dicts with keys:
            - name: restaurant name (required)
            - location: city or address (required)
            - yelp_url: direct yelp URL (optional)
            - opentable_url: direct opentable URL (optional)

    returns:
        list of RestaurantIdentifier objects
    """
    identifiers = []

    for restaurant in restaurants:
        name = restaurant.get("name", "")
        location = restaurant.get("location", "")

        if not name or not location:
            continue

        identifier = RestaurantIdentifier(
            name=name,
            location=location,
            yelp_url=restaurant.get("yelp_url"),
            opentable_url=restaurant.get("opentable_url")
        )

        identifiers.append(identifier)

    return identifiers


def generate_search_urls_for_identifiers(
    identifiers: List[RestaurantIdentifier]
) -> List[RestaurantIdentifier]:
    """generate search URLs for identifiers missing direct URLs.

    args:
        identifiers: list of RestaurantIdentifier objects

    returns:
        updated list with search URLs populated
    """
    for identifier in identifiers:
        if not identifier.yelp_url:
            identifier.yelp_url = generate_yelp_search_url(
                identifier.name,
                identifier.location
            )

        if not identifier.opentable_url:
            identifier.opentable_url = generate_opentable_search_url(
                identifier.name,
                identifier.location
            )

    return identifiers


def discover_restaurants(
    restaurant_names: List[str],
    location: str,
    direct_urls: Optional[Dict[str, Dict[str, str]]] = None
) -> List[RestaurantIdentifier]:
    """discover restaurant URLs across yelp and opentable platforms.

    args:
        restaurant_names: list of restaurant names to discover
        location: common location (city or address) for all restaurants
        direct_urls: optional dict mapping restaurant names to their direct URLs:
            {
                "Restaurant Name": {
                    "yelp_url": "https://...",
                    "opentable_url": "https://..."
                }
            }

    returns:
        list of RestaurantIdentifier objects with URLs populated
    """
    direct_urls = direct_urls or {}

    restaurant_data = []
    for name in restaurant_names:
        data = {
            "name": name,
            "location": location
        }

        # add direct URLs if available
        if name in direct_urls:
            data.update(direct_urls[name])

        restaurant_data.append(data)

    identifiers = create_restaurant_identifiers(restaurant_data)
    return generate_search_urls_for_identifiers(identifiers)
