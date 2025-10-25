"""research agent for generating comprehensive restaurant reports using reka's research sdk."""

import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, UTC
from openai import OpenAI


def build_research_prompt(restaurant: Dict) -> str:
    """construct a detailed research prompt for a single restaurant.

    args:
        restaurant: dict containing restaurant data with keys:
            - name: restaurant name
            - address: street address
            - city: city name
            - cuisine: cuisine type
            - latitude: location latitude
            - longitude: location longitude

    returns:
        formatted prompt string for reka api
    """
    location_str = f"{restaurant.get('name', 'Unknown Restaurant')}"
    if restaurant.get('address'):
        location_str += f", {restaurant['address']}"
    if restaurant.get('city'):
        location_str += f", {restaurant['city']}"

    prompt = f"""Research the restaurant: {location_str}

Please provide a comprehensive report covering:

1. Menu & Cuisine: Signature dishes, popular items, dietary options, cuisine style
2. Pricing: Price range, value for money, average meal cost
3. Customer Experience: Review sentiment from Google, Yelp, TripAdvisor; common praise/complaints
4. Health & Safety: Health inspection scores, violations, cleanliness ratings
5. Recognition: Awards, Michelin stars, certifications, media mentions
6. Business Information: Establishment date, ownership, operating hours, current status

Please cite all sources and provide specific, factual information."""

    return prompt


def research_restaurant(restaurant: Dict, api_key: Optional[str] = None) -> Dict:
    """execute reka api call to research a single restaurant.

    args:
        restaurant: dict containing restaurant data
        api_key: reka api key (defaults to REKA_API_KEY env var)

    returns:
        dict containing:
            - restaurant_id: unique identifier
            - restaurant_name: name of restaurant
            - research_content: main research findings
            - reasoning_steps: list of reka's reasoning steps
            - citations: list of citation dicts with title, url, indices
            - timestamp: iso format timestamp
            - status: 'success' or 'failed'
            - error: error message if failed (optional)
    """
    # get api key from environment if not provided
    if api_key is None:
        api_key = os.getenv('REKA_API_KEY')

    if not api_key:
        return {
            'restaurant_id': restaurant.get('id', 'unknown'),
            'restaurant_name': restaurant.get('name', 'Unknown'),
            'status': 'failed',
            'error': 'REKA_API_KEY not set',
            'timestamp': datetime.now(UTC).isoformat()
        }

    # validate required fields
    if not restaurant.get('name'):
        return {
            'restaurant_id': restaurant.get('id', 'unknown'),
            'restaurant_name': 'Unknown',
            'status': 'failed',
            'error': 'restaurant name is required',
            'timestamp': datetime.now(UTC).isoformat()
        }

    try:
        # initialize openai-compatible client for reka
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.reka.ai/v1"
        )

        # build research prompt
        prompt = build_research_prompt(restaurant)

        # call reka api
        response = client.chat.completions.create(
            model="reka-flash-research",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4096
        )

        # extract content and reasoning
        message = response.choices[0].message
        content = message.content

        # extract reasoning steps if available
        reasoning_steps: List = []
        if hasattr(message, 'reasoning_steps'):
            reasoning_steps = message.reasoning_steps or []

        # extract citations if available
        citations: List = []
        if hasattr(message, 'citations'):
            citations = message.citations or []

        return {
            'restaurant_id': restaurant.get('id', 'unknown'),
            'restaurant_name': restaurant.get('name', 'Unknown'),
            'research_content': content,
            'reasoning_steps': reasoning_steps,
            'citations': citations,
            'timestamp': datetime.now(UTC).isoformat(),
            'status': 'success'
        }

    except Exception as e:
        return {
            'restaurant_id': restaurant.get('id', 'unknown'),
            'restaurant_name': restaurant.get('name', 'Unknown'),
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now(UTC).isoformat()
        }


def extract_location_context(restaurant: Dict) -> str:
    """build location string for better search context.

    args:
        restaurant: dict containing restaurant data

    returns:
        formatted location string
    """
    parts = []

    if restaurant.get('name'):
        parts.append(restaurant['name'])
    if restaurant.get('address'):
        parts.append(restaurant['address'])
    if restaurant.get('city'):
        parts.append(restaurant['city'])
    if restaurant.get('cuisine') and restaurant['cuisine'] != 'Unknown':
        parts.append(f"({restaurant['cuisine']} cuisine)")

    return ', '.join(parts) if parts else 'Unknown Location'


if __name__ == "__main__":
    # example usage
    test_restaurant = {
        'id': '1',
        'name': "Tony's Pizza Napoletana",
        'address': '1570 Stockton St',
        'city': 'San Francisco',
        'cuisine': 'Italian',
        'latitude': 37.8008,
        'longitude': -122.4098
    }

    result = research_restaurant(test_restaurant)
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"\nResearch for: {result['restaurant_name']}")
        print(f"\nContent:\n{result['research_content'][:500]}...")
        print(f"\nCitations: {len(result.get('citations', []))}")
    else:
        print(f"Error: {result.get('error')}")
