import json
import math
import requests
from typing import List, Dict, Optional


def miles_to_meters(miles: float) -> float:
    """Convert miles to meters."""
    return miles * 1609.34


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    Returns distance in miles.
    """
    # Earth's radius in miles
    R = 3959.0

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate latitude and longitude ranges."""
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def query_overpass_api(latitude: float, longitude: float, radius_meters: float) -> List[Dict]:
    """
    Query Overpass API for restaurants within a radius.
    Returns raw results from the API.
    """
    overpass_url = "http://overpass-api.de/api/interpreter"

    # Overpass QL query to find restaurants
    # amenity=restaurant covers most restaurants
    # amenity=fast_food covers fast food places
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="restaurant"](around:{radius_meters},{latitude},{longitude});
      node["amenity"="fast_food"](around:{radius_meters},{latitude},{longitude});
    );
    out body;
    """

    response = requests.post(overpass_url, data={'data': overpass_query})
    response.raise_for_status()

    return response.json().get('elements', [])


def find_restaurants(latitude: float, longitude: float, distance: float = 10, extract_info: bool = False) -> Dict:
    """
    Find restaurants within a specified radius of a given location.

    Args:
        latitude: User's latitude
        longitude: User's longitude
        distance: Search radius in miles (default: 10)
        extract_info: Whether to extract detailed info using extraction agent (default: False)

    Returns:
        Dict containing:
            - 'status': 'success' or 'error'
            - 'count': number of restaurants found
            - 'restaurants': list of restaurant dicts with name, address, distance, etc.
            - 'error': error message (if status is 'error')
            - 'extracted_info': list of RestaurantInfo dicts (if extract_info=True)
    """
    # Validate inputs
    if not validate_coordinates(latitude, longitude):
        return {
            'status': 'error',
            'error': 'Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180.'
        }

    if distance <= 0:
        return {
            'status': 'error',
            'error': 'Distance must be greater than 0.'
        }

    try:
        # Convert distance to meters for Overpass API
        radius_meters = miles_to_meters(distance)

        # Query Overpass API
        raw_results = query_overpass_api(latitude, longitude, radius_meters)

        # Process results
        restaurants = []
        for element in raw_results:
            tags = element.get('tags', {})
            elem_lat = element.get('lat')
            elem_lon = element.get('lon')

            if elem_lat is None or elem_lon is None:
                continue

            # Calculate precise distance
            precise_distance = haversine_distance(latitude, longitude, elem_lat, elem_lon)

            # Filter out if beyond exact radius
            if precise_distance > distance:
                continue

            # Extract restaurant information
            restaurant = {
                'name': tags.get('name', 'Unnamed Restaurant'),
                'latitude': elem_lat,
                'longitude': elem_lon,
                'distance_miles': round(precise_distance, 2),
                'cuisine': tags.get('cuisine', 'Unknown'),
                'address': tags.get('addr:street', 'Address not available'),
                'city': tags.get('addr:city', ''),
                'amenity_type': tags.get('amenity', 'restaurant')
            }

            restaurants.append(restaurant)

        # Sort by distance
        restaurants.sort(key=lambda x: x['distance_miles'])

        # prepare response
        response = {
            'status': 'success',
            'count': len(restaurants),
            'restaurants': restaurants,
            'query': {
                'latitude': latitude,
                'longitude': longitude,
                'radius_miles': distance
            }
        }

    except requests.RequestException as e:
        return {
            'status': 'error',
            'error': f'API request failed: {str(e)}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': f'Unexpected error: {str(e)}'
        }


if __name__ == "__main__":
    # Example usage
    result = find_restaurants(37.7749, -122.4194, distance=5)  # San Francisco coordinates
    print(json.dumps(result, indent=2))