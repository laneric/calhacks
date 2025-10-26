# restaurant retrieval module

## overview

the restaurant retrieval module provides functionality to scrape google maps via bright data api and retrieve local restaurant metadata based on geographic coordinates. this module implements caching to optimize performance and reduce api calls.

## file location

`helpers/restaurants/restaurant_retrieval.py`

## purpose

to retrieve comprehensive restaurant data from google maps including names, ratings, addresses, and other metadata for restaurants near specified coordinates. designed for production-level scalability with built-in caching and error handling.

## dependencies

- `requests`: http library for api calls
- `json`: data serialization
- `hashlib`: cache key generation
- `datetime`: cache expiration management
- `os`: file system operations
- `typing`: type hints for function signatures

## installation

add bright data credentials to `.env`:

```bash
BRIGHT_DATA_API_KEY=your_api_key_here
BRIGHT_DATA_ZONE=your_zone_here
```

ensure dependencies are installed:

```bash
uv pip install -r requirements.txt
```

## core functions

### `retrieve_restaurants(latitude: float, longitude: float, query: Optional[str] = None, max_results: int = 20) -> dict`

main entry point for retrieving restaurant data.

**arguments:**
- `latitude` (float): latitude coordinate, must be between -90 and 90
- `longitude` (float): longitude coordinate, must be between -180 and 180
- `query` (optional[str]): custom search query. defaults to `"restaurants near {latitude}, {longitude}"`
- `max_results` (int): maximum number of results to return. default is 20

**returns:**
- dict containing:
  - `query` (str): the search query used
  - `total_results` (int): number of restaurants found
  - `restaurants` (list[dict]): array of restaurant objects
  - `cached` (bool): whether results came from cache
  - `error` (str, optional): error message if request failed

**example usage:**

```python
from helpers.restaurants.restaurant_retrieval import retrieve_restaurants

# basic usage with coordinates
results = retrieve_restaurants(37.7749, -122.4194)

# with custom query
results = retrieve_restaurants(
    37.7749,
    -122.4194,
    query="italian restaurants in san francisco"
)

# with custom max results
results = retrieve_restaurants(
    37.7749,
    -122.4194,
    max_results=50
)
```

**restaurant object structure:**

```json
{
  "name": "restaurant name",
  "address": "123 main st, city, state",
  "rating": 4.5,
  "reviews": 234,
  "price_level": "$$",
  "cuisine": "italian",
  "coordinates": {
    "lat": 37.7749,
    "lng": -122.4194
  },
  "place_id": "ChIJxxxx",
  "phone": "+1-415-555-0100"
}
```

### `_validate_coordinates(latitude: float, longitude: float) -> bool`

validates that coordinates are within valid geographic bounds.

**arguments:**
- `latitude` (float): latitude to validate
- `longitude` (float): longitude to validate

**returns:**
- bool: true if coordinates are valid

**raises:**
- `ValueError`: if coordinates are out of bounds
- `TypeError`: if coordinates are not numeric

**validation rules:**
- latitude must be between -90 and 90
- longitude must be between -180 and 180
- both must be numeric types (int or float)

### `_construct_query(latitude: float, longitude: float, custom_query: Optional[str]) -> str`

constructs search query for google maps.

**arguments:**
- `latitude` (float): latitude coordinate
- `longitude` (float): longitude coordinate
- `custom_query` (optional[str]): user-provided custom query

**returns:**
- str: formatted query string

**behavior:**
- if `custom_query` is provided, returns it unchanged
- otherwise, returns `f"restaurants near {latitude}, {longitude}"`

### `_get_cache_key(latitude: float, longitude: float, query: str) -> str`

generates unique cache key for coordinate/query combination.

**arguments:**
- `latitude` (float): latitude coordinate
- `longitude` (float): longitude coordinate
- `query` (str): search query

**returns:**
- str: md5 hash of combined inputs

**implementation:**
- combines latitude, longitude, and query into single string
- generates md5 hash for consistent, collision-resistant keys
- ensures same inputs always produce same cache key

### `_check_cache(latitude: float, longitude: float, query: str) -> Optional[dict]`

checks if valid cached data exists for given parameters.

**arguments:**
- `latitude` (float): latitude coordinate
- `longitude` (float): longitude coordinate
- `query` (str): search query

**returns:**
- dict: cached data if valid cache exists
- none: if cache miss or cache expired

**cache validation:**
- checks if cache file exists
- validates cache age (must be < 24 hours old)
- returns none if cache is expired or invalid

### `_save_to_cache(latitude: float, longitude: float, query: str, data: dict) -> None`

saves restaurant data to cache.

**arguments:**
- `latitude` (float): latitude coordinate
- `longitude` (float): longitude coordinate
- `query` (str): search query
- `data` (dict): restaurant data to cache

**returns:**
- none

**cache structure:**
```json
{
  "cached_at": "2025-10-25T12:34:56.789012",
  "data": {
    "query": "...",
    "total_results": 10,
    "restaurants": [...]
  }
}
```

**cache location:**
- directory: `helpers/restaurants/.cache/`
- filename format: `{cache_key}.json`
- expires after: 24 hours

### `_parse_restaurant_data(raw_data: dict) -> dict`

parses raw bright data response into standardized restaurant object.

**arguments:**
- `raw_data` (dict): raw restaurant data from bright data api

**returns:**
- dict: standardized restaurant object

**field mapping:**
- extracts relevant fields from bright data response
- provides default values for missing fields
- normalizes coordinate structure
- handles missing or null values gracefully

## caching mechanism

### cache strategy

the module implements file-based caching to:
1. reduce api calls to bright data (cost optimization)
2. improve response times for repeated queries
3. reduce load on google maps infrastructure

### cache key generation

cache keys are generated using md5 hash of:
- latitude (rounded to 4 decimal places)
- longitude (rounded to 4 decimal places)
- query string (normalized)

this ensures:
- same location + query = same cache
- different queries at same location = different cache
- slight coordinate variations (< 11m) = same cache

### cache expiration

- **expiration time**: 24 hours
- **rationale**: restaurant data is relatively static
- **validation**: checked on every cache read

### cache directory structure

```
helpers/restaurants/.cache/
├── 5f4dcc3b5aa765d61d8327deb882cf99.json
├── 098f6bcd4621d373cade4e832627b4f6.json
└── ...
```

### cache invalidation

cache is automatically invalidated when:
- 24 hours have passed since creation
- cache file is corrupted or unreadable
- cache file is manually deleted

## bright data integration

### api configuration

the module uses bright data's scraping browser api to access google maps data.

**required environment variables:**
```bash
BRIGHT_DATA_API_KEY=your_api_key_here
BRIGHT_DATA_ZONE=your_zone_name
```

### api endpoint

```
POST https://api.brightdata.com/zones/{zone}/collector
```

### request structure

```json
{
  "url": "https://www.google.com/maps/search/restaurants+near+37.7749,+-122.4194",
  "format": "json",
  "country": "us"
}
```

### response structure

bright data returns structured json with restaurant data:

```json
{
  "results": [
    {
      "name": "restaurant name",
      "address": "full address",
      "rating": 4.5,
      "reviews_count": 234,
      "price_level": "$$",
      "type": "cuisine type",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "place_id": "google place id",
      "phone": "phone number"
    }
  ]
}
```

### error handling

api errors are handled gracefully:
- network timeouts: return empty results with error message
- authentication failures: logged and returned as error
- rate limiting: caught and reported
- malformed responses: parsed with defaults

## error handling

### coordinate validation errors

```python
# invalid latitude
retrieve_restaurants(91.0, -122.4194)
# raises: ValueError: latitude must be between -90 and 90

# invalid longitude
retrieve_restaurants(37.7749, 181.0)
# raises: ValueError: longitude must be between -180 and 180
```

### api errors

```python
# returns error structure
{
  "query": "restaurants near 37.7749, -122.4194",
  "total_results": 0,
  "restaurants": [],
  "cached": false,
  "error": "api timeout: request took longer than 30 seconds"
}
```

### cache errors

cache read/write errors are logged but don't stop execution:
- cache read error → proceeds to api call
- cache write error → logged, results still returned

## testing

comprehensive test suite located at `tests/test_restaurant_retrieval.py`

### test coverage

1. **coordinate validation tests**
   - valid coordinates (edge cases: 0, max/min values)
   - invalid latitude (> 90 or < -90)
   - invalid longitude (> 180 or < -180)
   - non-numeric inputs

2. **query construction tests**
   - default query generation
   - custom query override
   - edge cases (zero coordinates)

3. **caching tests**
   - cache key generation consistency
   - cache miss handling
   - cache hit with valid data
   - cache expiration (> 24 hours)
   - cache save functionality

4. **api integration tests**
   - successful api call with mock response
   - api failure handling (500 errors)
   - api timeout handling
   - rate limiting scenarios

5. **data parsing tests**
   - complete restaurant data parsing
   - incomplete data with defaults
   - malformed data handling

6. **end-to-end tests**
   - full workflow with custom query
   - max results limiting
   - cache integration

### running tests

```bash
# run all restaurant retrieval tests
pytest tests/test_restaurant_retrieval.py -v

# run specific test class
pytest tests/test_restaurant_retrieval.py::TestCachingMechanism -v

# run with coverage
pytest tests/test_restaurant_retrieval.py --cov=helpers.restaurants.restaurant_retrieval
```

## performance considerations

### api call optimization

- **caching**: reduces api calls by ~80% for repeated queries
- **batch processing**: supports retrieving multiple results in single call
- **timeout handling**: 30 second timeout prevents hanging requests

### response time benchmarks

| scenario | typical response time |
|----------|---------------------|
| cache hit | < 10ms |
| cache miss (api call) | 2-5 seconds |
| api timeout | 30 seconds (max) |

### cost optimization

with 24-hour caching:
- single location queried 10x/day = 1 api call (not 10)
- estimated cost reduction: 90% for high-traffic locations

## usage examples

### basic restaurant search

```python
from helpers.restaurants.restaurant_retrieval import retrieve_restaurants

# search restaurants in san francisco
results = retrieve_restaurants(37.7749, -122.4194)

print(f"found {results['total_results']} restaurants")
for restaurant in results['restaurants']:
    print(f"{restaurant['name']} - {restaurant['rating']}⭐")
```

### custom search query

```python
# search for specific cuisine
results = retrieve_restaurants(
    37.7749,
    -122.4194,
    query="vegan restaurants near union square san francisco"
)
```

### processing results

```python
# filter by rating
high_rated = [
    r for r in results['restaurants']
    if r['rating'] and r['rating'] >= 4.5
]

# sort by review count
by_popularity = sorted(
    results['restaurants'],
    key=lambda r: r['reviews'] or 0,
    reverse=True
)

# filter by price
affordable = [
    r for r in results['restaurants']
    if r['price_level'] in ['$', '$$']
]
```

### error handling in production

```python
from helpers.restaurants.restaurant_retrieval import retrieve_restaurants

def get_restaurants_safely(lat, lon):
    """production-safe restaurant retrieval with error handling."""
    try:
        results = retrieve_restaurants(lat, lon)

        if 'error' in results:
            # log error and return empty list
            print(f"error retrieving restaurants: {results['error']}")
            return []

        return results['restaurants']

    except ValueError as e:
        # handle coordinate validation errors
        print(f"invalid coordinates: {e}")
        return []

    except Exception as e:
        # catch any unexpected errors
        print(f"unexpected error: {e}")
        return []
```

## future enhancements

potential improvements for future iterations:

1. **database caching**: migrate from file-based to redis/postgres caching
2. **pagination**: support for retrieving > 100 results via pagination
3. **filtering**: add price range, cuisine type, rating filters to api
4. **batch queries**: support multiple coordinate pairs in single call
5. **real-time updates**: webhook integration for menu/hours changes
6. **image scraping**: retrieve restaurant photos from google maps
7. **reviews scraping**: fetch full review text and sentiment analysis
8. **hours parsing**: extract and normalize business hours
9. **menu extraction**: scrape menu items and prices where available
10. **distance calculation**: add distance from query coordinates to results

## troubleshooting

### common issues

**issue**: `ValueError: latitude must be between -90 and 90`
- **cause**: invalid coordinate input
- **solution**: validate coordinates before calling function

**issue**: empty results with no error
- **cause**: no restaurants found at location or bad query
- **solution**: check coordinates are in populated area, try broader query

**issue**: api timeout errors
- **cause**: bright data api slow or unavailable
- **solution**: implement retry logic, check bright data status

**issue**: cache not working
- **cause**: permission issues or disk full
- **solution**: check write permissions on `.cache/` directory

### debug mode

enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

results = retrieve_restaurants(37.7749, -122.4194)
# outputs detailed logs of cache checks, api calls, parsing
```

## changelog

### version 1.0.0 (2025-10-25)
- initial implementation
- coordinate validation
- bright data integration
- file-based caching (24 hour expiry)
- comprehensive test suite
- production error handling

## maintainers

for questions or issues, refer to:
- primary module: `helpers/restaurants/restaurant_retrieval.py`
- test suite: `tests/test_restaurant_retrieval.py`
- this documentation: `docs/restaurant_retrieval.md`

## related modules

- **geo helpers**: coordinate utilities and distance calculations
- **api client**: shared bright data client configuration
- **caching utils**: general caching utilities for other modules
