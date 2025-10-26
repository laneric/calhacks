"""restaurant information extraction using web scraping and claude haiku."""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from anthropic import Anthropic

from agents.scraping.menu_scraper import MenuScraper
from agents.scraping.restaurant_discovery import RestaurantIdentifier
from agents.extraction.extraction_cache import ExtractionCache


@dataclass
class RestaurantInfo:
    """structured restaurant information extracted from web sources."""

    restaurant_name: str
    cuisine: List[str]
    popular_dishes: List[str]
    common_allergens: List[str]
    price_range: str  # "$", "$$", "$$$", "$$$$"
    number_of_reviews: Optional[int]
    average_stars: Optional[float]
    hours: Optional[str]
    dietary_options: List[str]
    ambiance: Optional[str]
    reservations_required: Optional[bool]
    extraction_source: str  # 'yelp', 'opentable', 'combined', 'geo_only'
    extracted_at: str
    status: str  # 'success', 'partial', 'failed'
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """convert to dictionary.

        returns:
            dict representation of restaurant info
        """
        return asdict(self)


def build_extraction_prompt(
    restaurant_name: str,
    scraped_data: Dict[str, Any],
    geo_data: Optional[Dict[str, Any]] = None
) -> str:
    """build claude haiku prompt for extracting structured restaurant information.

    args:
        restaurant_name: name of the restaurant
        scraped_data: combined data from yelp and/or opentable
        geo_data: optional basic data from geo agent

    returns:
        formatted prompt string for claude haiku
    """
    prompt = f"""extract structured information about the restaurant "{restaurant_name}" from the provided data.

analyze the following data sources and extract the requested fields:

"""

    # add scraped data
    if scraped_data.get('yelp'):
        prompt += "=== YELP DATA ===\n"
        prompt += json.dumps(scraped_data['yelp'], indent=2)
        prompt += "\n\n"

    if scraped_data.get('opentable'):
        prompt += "=== OPENTABLE DATA ===\n"
        prompt += json.dumps(scraped_data['opentable'], indent=2)
        prompt += "\n\n"

    # add geo data as fallback
    if geo_data:
        prompt += "=== GEO DATA (FALLBACK) ===\n"
        prompt += json.dumps(geo_data, indent=2)
        prompt += "\n\n"

    prompt += """extract the following fields and return them in JSON format:

{
  "cuisine": ["list of cuisine types"],
  "popular_dishes": ["list of popular/signature dishes"],
  "common_allergens": ["list of common allergens found in menu items"],
  "price_range": "$, $$, $$$, or $$$$",
  "number_of_reviews": integer or null,
  "average_stars": float or null,
  "hours": "operating hours string or null",
  "dietary_options": ["vegetarian", "vegan", "gluten-free", etc.],
  "ambiance": "brief description or null",
  "reservations_required": true/false/null
}

rules:
- if a field is not available in the data, use null or empty array as appropriate
- for cuisine, extract all mentioned cuisine types
- for popular_dishes, prioritize dishes mentioned multiple times in reviews or highlighted on menu
- for common_allergens, look for common allergens like dairy, nuts, shellfish, gluten, soy, eggs
- for price_range, use $ symbols ($ = under $10, $$ = $10-25, $$$ = $25-50, $$$$ = over $50)
- for dietary_options, only include options explicitly mentioned or clearly available
- for ambiance, keep it concise (e.g., "casual", "fine dining", "family-friendly")
- return only the JSON object, no additional text

JSON output:"""

    return prompt


def extract_restaurant_info(
    restaurant_name: str,
    identifier: Optional[RestaurantIdentifier] = None,
    geo_data: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    use_cache: bool = True,
    scraper: Optional[MenuScraper] = None,
    cache: Optional[ExtractionCache] = None
) -> RestaurantInfo:
    """extract structured restaurant information using scraping + claude haiku.

    args:
        restaurant_name: name of the restaurant
        identifier: restaurant identifier with yelp/opentable urls
        geo_data: optional basic data from geo agent (fallback if scraping fails)
        api_key: anthropic api key (defaults to ANTHROPIC_API_KEY env var)
        use_cache: whether to use extraction cache
        scraper: optional menu scraper instance
        cache: optional extraction cache instance

    returns:
        RestaurantInfo object with extracted data
    """
    # initialize cache
    if cache is None:
        cache = ExtractionCache()

    # check cache first
    if use_cache:
        cached_entry = cache.get(restaurant_name, "combined")
        if cached_entry and cached_entry.extraction_data:
            print(f"[Extraction] using cached data for {restaurant_name}")
            return RestaurantInfo(**cached_entry.extraction_data)

    # get api key
    if api_key is None:
        api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        return RestaurantInfo(
            restaurant_name=restaurant_name,
            cuisine=[],
            popular_dishes=[],
            common_allergens=[],
            price_range="",
            number_of_reviews=None,
            average_stars=None,
            hours=None,
            dietary_options=[],
            ambiance=None,
            reservations_required=None,
            extraction_source="none",
            extracted_at=datetime.now(UTC).isoformat(),
            status="failed",
            error="ANTHROPIC_API_KEY not set"
        )

    # attempt to scrape data
    scraped_data: Dict[str, Any] = {}
    extraction_source = "geo_only"

    if identifier and scraper is None:
        scraper = MenuScraper(use_cache=use_cache)

    if identifier and scraper:
        try:
            menu_results = scraper.scrape_restaurant(
                identifier=identifier,
                scrape_yelp=True,
                scrape_opentable=True,
                include_reviews=True
            )

            if menu_results.get('yelp'):
                scraped_data['yelp'] = menu_results['yelp'].raw_data
                extraction_source = "yelp"

            if menu_results.get('opentable'):
                scraped_data['opentable'] = menu_results['opentable'].raw_data
                if extraction_source == "yelp":
                    extraction_source = "combined"
                else:
                    extraction_source = "opentable"

        except Exception as e:
            print(f"[Extraction] scraping failed for {restaurant_name}: {e}")

    # if no scraped data and no geo data, return error
    if not scraped_data and not geo_data:
        return RestaurantInfo(
            restaurant_name=restaurant_name,
            cuisine=[],
            popular_dishes=[],
            common_allergens=[],
            price_range="",
            number_of_reviews=None,
            average_stars=None,
            hours=None,
            dietary_options=[],
            ambiance=None,
            reservations_required=None,
            extraction_source="none",
            extracted_at=datetime.now(UTC).isoformat(),
            status="failed",
            error="no data available for extraction"
        )

    # build extraction prompt
    prompt = build_extraction_prompt(restaurant_name, scraped_data, geo_data)

    # call claude haiku
    try:
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2048,
            temperature=0.0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # extract json from response
        content = response.content[0].text

        # find json in response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            raise ValueError("no json found in response")

        json_str = content[json_start:json_end]
        extracted_data = json.loads(json_str)

        # create RestaurantInfo object
        extracted_at = datetime.now(UTC).isoformat()

        restaurant_info = RestaurantInfo(
            restaurant_name=restaurant_name,
            cuisine=extracted_data.get('cuisine', []),
            popular_dishes=extracted_data.get('popular_dishes', []),
            common_allergens=extracted_data.get('common_allergens', []),
            price_range=extracted_data.get('price_range', ''),
            number_of_reviews=extracted_data.get('number_of_reviews'),
            average_stars=extracted_data.get('average_stars'),
            hours=extracted_data.get('hours'),
            dietary_options=extracted_data.get('dietary_options', []),
            ambiance=extracted_data.get('ambiance'),
            reservations_required=extracted_data.get('reservations_required'),
            extraction_source=extraction_source,
            extracted_at=extracted_at,
            status="success",
            error=None
        )

        # cache the result
        if use_cache:
            data_hash = hashlib.md5(
                json.dumps(restaurant_info.to_dict(), sort_keys=True).encode()
            ).hexdigest()
            cache.set(
                restaurant_name=restaurant_name,
                source="combined",
                extracted_at=extracted_at,
                data_hash=data_hash,
                extraction_data=restaurant_info.to_dict()
            )

        return restaurant_info

    except Exception as e:
        # return partial data on extraction failure
        return RestaurantInfo(
            restaurant_name=restaurant_name,
            cuisine=geo_data.get('cuisine', '').split(',') if geo_data and geo_data.get('cuisine') else [],
            popular_dishes=[],
            common_allergens=[],
            price_range="",
            number_of_reviews=None,
            average_stars=None,
            hours=None,
            dietary_options=[],
            ambiance=None,
            reservations_required=None,
            extraction_source=extraction_source,
            extracted_at=datetime.now(UTC).isoformat(),
            status="partial",
            error=f"extraction failed: {str(e)}"
        )


def batch_extract_restaurant_info(
    restaurants: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    use_cache: bool = True,
    scraper: Optional[MenuScraper] = None,
    cache: Optional[ExtractionCache] = None
) -> List[RestaurantInfo]:
    """extract information for multiple restaurants.

    args:
        restaurants: list of dicts with keys:
            - name: restaurant name (required)
            - identifier: RestaurantIdentifier (optional)
            - geo_data: dict from geo agent (optional)
        api_key: anthropic api key
        use_cache: whether to use extraction cache
        scraper: optional shared menu scraper instance
        cache: optional shared extraction cache instance

    returns:
        list of RestaurantInfo objects
    """
    # initialize shared resources
    if scraper is None:
        try:
            scraper = MenuScraper(use_cache=use_cache)
        except ValueError:
            # scraper initialization failed (likely missing BRIGHT_DATA_API_KEY)
            # continue without scraper, will use geo_data fallback
            scraper = None

    if cache is None:
        cache = ExtractionCache()

    results = []

    for i, restaurant in enumerate(restaurants, 1):
        print(f"[Extraction] processing {i}/{len(restaurants)}: {restaurant.get('name')}")

        try:
            info = extract_restaurant_info(
                restaurant_name=restaurant['name'],
                identifier=restaurant.get('identifier'),
                geo_data=restaurant.get('geo_data'),
                api_key=api_key,
                use_cache=use_cache,
                scraper=scraper,
                cache=cache
            )
            results.append(info)

        except Exception as e:
            print(f"[Extraction] error processing {restaurant.get('name')}: {e}")
            results.append(
                RestaurantInfo(
                    restaurant_name=restaurant.get('name', 'Unknown'),
                    cuisine=[],
                    popular_dishes=[],
                    common_allergens=[],
                    price_range="",
                    number_of_reviews=None,
                    average_stars=None,
                    hours=None,
                    dietary_options=[],
                    ambiance=None,
                    reservations_required=None,
                    extraction_source="none",
                    extracted_at=datetime.now(UTC).isoformat(),
                    status="failed",
                    error=str(e)
                )
            )

    return results


if __name__ == "__main__":
    # example usage
    test_identifier = RestaurantIdentifier(
        name="Tony's Pizza Napoletana",
        location="San Francisco",
        yelp_url="https://www.yelp.com/biz/tonys-pizza-napoletana-san-francisco"
    )

    result = extract_restaurant_info(
        restaurant_name="Tony's Pizza Napoletana",
        identifier=test_identifier
    )

    print(f"Status: {result.status}")
    print(f"Cuisine: {result.cuisine}")
    print(f"Price Range: {result.price_range}")
    print(f"Popular Dishes: {result.popular_dishes}")
    print(f"Average Stars: {result.average_stars}")
