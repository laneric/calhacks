# extraction agent

structured restaurant information extraction using web scraping and claude haiku.

## overview

the extraction agent combines web scraping (yelp, opentable) with claude haiku's language understanding to extract structured restaurant information. it provides detailed fields including cuisine, popular dishes, allergens, pricing, reviews, hours, dietary options, ambiance, and reservation requirements.

## architecture

### data pipeline

```
restaurant identifier
  ↓
scraping agent (yelp + opentable)
  ↓
claude haiku (structured extraction)
  ↓
RestaurantInfo (structured output)
  ↓
extraction cache (30-day ttl)
```

### core components

1. **extraction orchestrator**: coordinates scraping and llm extraction
2. **prompt builder**: constructs detailed prompts for claude haiku
3. **cache manager**: caches extracted data to reduce api costs
4. **batch processor**: handles concurrent extraction for multiple restaurants

## data structures

### `RestaurantInfo` dataclass

complete structured information about a restaurant.

```python
@dataclass
class RestaurantInfo:
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
```

**field descriptions**:
- `cuisine`: list of cuisine types (e.g., ["Italian", "Pizza"])
- `popular_dishes`: signature or frequently mentioned dishes
- `common_allergens`: allergens found in menu items (dairy, nuts, shellfish, gluten, soy, eggs)
- `price_range`: price tier using $ symbols ($ = under $10, $$ = $10-25, $$$ = $25-50, $$$$ = over $50)
- `number_of_reviews`: total review count across sources
- `average_stars`: average rating (typically 1-5 scale)
- `hours`: operating hours string
- `dietary_options`: available dietary accommodations (vegetarian, vegan, gluten-free, etc.)
- `ambiance`: brief description (casual, fine dining, family-friendly, etc.)
- `reservations_required`: whether reservations are required/recommended
- `extraction_source`: indicates data source used
- `status`: extraction success status
- `error`: error message if extraction failed

## functions

### `extract_restaurant_info()`

extract structured information for a single restaurant.

```python
def extract_restaurant_info(
    restaurant_name: str,
    identifier: Optional[RestaurantIdentifier] = None,
    geo_data: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    use_cache: bool = True,
    scraper: Optional[MenuScraper] = None,
    cache: Optional[ExtractionCache] = None
) -> RestaurantInfo
```

**parameters**:
- `restaurant_name` (str): name of the restaurant (required)
- `identifier` (RestaurantIdentifier, optional): restaurant with yelp/opentable urls
- `geo_data` (dict, optional): basic data from geo agent (fallback)
- `api_key` (str, optional): anthropic api key (defaults to `ANTHROPIC_API_KEY` env var)
- `use_cache` (bool): whether to use extraction cache (default: True)
- `scraper` (MenuScraper, optional): shared scraper instance
- `cache` (ExtractionCache, optional): shared cache instance

**returns**: `RestaurantInfo` object

**example**:
```python
from agents.extraction import extract_restaurant_info
from agents.scraping.restaurant_discovery import RestaurantIdentifier

identifier = RestaurantIdentifier(
    name="Tony's Pizza",
    location="San Francisco",
    yelp_url="https://www.yelp.com/biz/tonys-pizza-napoletana-san-francisco"
)

result = extract_restaurant_info(
    restaurant_name="Tony's Pizza",
    identifier=identifier
)

if result.status == "success":
    print(f"Cuisine: {result.cuisine}")
    print(f"Price Range: {result.price_range}")
    print(f"Popular Dishes: {result.popular_dishes}")
    print(f"Rating: {result.average_stars}/5")
```

### `batch_extract_restaurant_info()`

extract information for multiple restaurants concurrently.

```python
def batch_extract_restaurant_info(
    restaurants: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    use_cache: bool = True,
    scraper: Optional[MenuScraper] = None,
    cache: Optional[ExtractionCache] = None
) -> List[RestaurantInfo]
```

**parameters**:
- `restaurants` (list): list of dicts with keys:
  - `name` (str, required): restaurant name
  - `identifier` (RestaurantIdentifier, optional): urls for scraping
  - `geo_data` (dict, optional): fallback geo agent data
- `api_key` (str, optional): anthropic api key
- `use_cache` (bool): whether to use cache (default: True)
- `scraper` (MenuScraper, optional): shared scraper instance
- `cache` (ExtractionCache, optional): shared cache instance

**returns**: list of `RestaurantInfo` objects

**example**:
```python
from agents.extraction import batch_extract_restaurant_info

restaurants = [
    {
        'name': 'Restaurant 1',
        'geo_data': {'cuisine': 'Italian', 'address': '123 Main St'}
    },
    {
        'name': 'Restaurant 2',
        'geo_data': {'cuisine': 'Mexican', 'address': '456 Oak Ave'}
    }
]

results = batch_extract_restaurant_info(restaurants)

for info in results:
    print(f"{info.restaurant_name}: {info.status}")
    if info.status == "success":
        print(f"  Cuisine: {', '.join(info.cuisine)}")
        print(f"  Price: {info.price_range}")
```

### `build_extraction_prompt()`

build claude haiku prompt for structured extraction.

```python
def build_extraction_prompt(
    restaurant_name: str,
    scraped_data: Dict[str, Any],
    geo_data: Optional[Dict[str, Any]] = None
) -> str
```

**parameters**:
- `restaurant_name` (str): name of restaurant
- `scraped_data` (dict): combined yelp/opentable data
- `geo_data` (dict, optional): fallback geo data

**returns**: formatted prompt string

## caching

### `ExtractionCache`

caches extracted restaurant information with 30-day ttl.

```python
from agents.extraction import ExtractionCache

cache = ExtractionCache()

# check cache
entry = cache.get("Tony's Pizza", "combined")
if entry:
    print(f"Cached data: {entry.extraction_data}")

# set cache
cache.set(
    restaurant_name="Tony's Pizza",
    source="combined",
    extracted_at=datetime.now(UTC).isoformat(),
    data_hash="abc123",
    extraction_data=restaurant_info.to_dict()
)

# cleanup expired entries
removed = cache.cleanup_expired()
print(f"Removed {removed} expired entries")

# cache statistics
stats = cache.get_stats()
print(f"Total: {stats['total_entries']}, Valid: {stats['valid_entries']}")
```

**cache operations**:
- `get(restaurant_name, source)`: retrieve cached data
- `set(...)`: store extraction result
- `remove(restaurant_name, source)`: delete cache entry
- `is_cache_valid(restaurant_name, source)`: check if valid cache exists
- `cleanup_expired()`: remove expired entries
- `clear()`: remove all entries
- `get_stats()`: get cache statistics
- `list_cached_restaurants()`: list all cached restaurants

**cache ttl**: 30 days (configurable via `ttl_days` parameter)

**cache location**: `data/cache/extraction_cache.json`

## usage

### basic usage

```python
from agents.extraction import extract_restaurant_info

# with geo data only (fallback)
result = extract_restaurant_info(
    restaurant_name="Local Cafe",
    geo_data={'cuisine': 'American', 'address': '789 Pine St'}
)

print(f"Status: {result.status}")
print(f"Cuisine: {result.cuisine}")
```

### with scraping

```python
from agents.extraction import extract_restaurant_info
from agents.scraping.restaurant_discovery import RestaurantIdentifier

identifier = RestaurantIdentifier(
    name="Fine Dining Restaurant",
    location="New York",
    yelp_url="https://www.yelp.com/biz/restaurant-name",
    opentable_url="https://www.opentable.com/restaurant-name"
)

result = extract_restaurant_info(
    restaurant_name="Fine Dining Restaurant",
    identifier=identifier
)

if result.status == "success":
    print(f"Cuisine: {', '.join(result.cuisine)}")
    print(f"Price Range: {result.price_range}")
    print(f"Popular Dishes: {', '.join(result.popular_dishes)}")
    print(f"Dietary Options: {', '.join(result.dietary_options)}")
    print(f"Ambiance: {result.ambiance}")
    print(f"Reservations: {result.reservations_required}")
```

### batch processing

```python
from agents.extraction import batch_extract_restaurant_info
from agents.geo.geo import find_restaurants

# get restaurants from geo agent
geo_result = find_restaurants(37.7749, -122.4194, distance=5)

# prepare for batch extraction
restaurants = [
    {
        'name': r['name'],
        'geo_data': r
    }
    for r in geo_result['restaurants'][:10]
]

# extract information for all
results = batch_extract_restaurant_info(restaurants)

# display results
for info in results:
    if info.status == "success":
        print(f"{info.restaurant_name} - {info.price_range}")
        print(f"  Popular: {', '.join(info.popular_dishes[:3])}")
```

### integration with geo agent

```python
from agents.geo.geo import find_restaurants
from agents.extraction import extract_restaurant_info

# find restaurants
geo_result = find_restaurants(37.7749, -122.4194, distance=3)

# extract detailed info for top restaurant
if geo_result['status'] == 'success' and geo_result['restaurants']:
    top_restaurant = geo_result['restaurants'][0]

    detailed_info = extract_restaurant_info(
        restaurant_name=top_restaurant['name'],
        geo_data=top_restaurant
    )

    print(f"Name: {detailed_info.restaurant_name}")
    print(f"Cuisine: {', '.join(detailed_info.cuisine)}")
    print(f"Price: {detailed_info.price_range}")
```

## error handling

### status levels

- `success`: extraction completed successfully
- `partial`: extraction failed but some data available from geo agent
- `failed`: extraction failed completely

### error scenarios

**missing api key**:
```python
result = extract_restaurant_info(restaurant_name="Test")
# result.status == "failed"
# result.error == "ANTHROPIC_API_KEY not set"
```

**no data available**:
```python
result = extract_restaurant_info(
    restaurant_name="Test",
    identifier=None,
    geo_data=None
)
# result.status == "failed"
# result.error == "no data available for extraction"
```

**extraction failure with fallback**:
```python
result = extract_restaurant_info(
    restaurant_name="Test",
    geo_data={'cuisine': 'Italian'}
)
# if claude api fails:
# result.status == "partial"
# result.cuisine == ["Italian"]  # from geo data
# result.error == "extraction failed: <error message>"
```

## configuration

### environment variables

- `ANTHROPIC_API_KEY`: anthropic api key (required)

set via `.env` file or environment:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### api configuration

- **model**: `claude-3-5-haiku-20241022`
- **max_tokens**: 2048
- **temperature**: 0.0 (deterministic extraction)

## testing

tests are located in `/tests/test_extraction.py`.

run tests:
```bash
PYTHONPATH=/Users/gurnoor/Desktop/calhacks pytest agents/tests/test_extraction.py -v
```

### test coverage (22 tests)

**cache entry tests**:
- creation, serialization, validity checks
- expiration handling

**cache manager tests**:
- initialization, get/set operations
- cache miss, removal, cleanup
- statistics

**dataclass tests**:
- RestaurantInfo creation and serialization

**prompt building tests**:
- yelp data, opentable data, combined data
- geo fallback

**extraction tests**:
- missing api key handling
- no data scenario
- cached data usage
- successful extraction with mocked claude
- batch processing
- error handling

## integration

### with geo agent

the extraction agent can automatically enhance geo agent results:

```python
# see geo/geo.py for integration example
```

### with flask api

future integration point for main.py:

```python
@app.route('/restaurants/extract', methods=['POST'])
def extract_restaurant_endpoint():
    data = request.json
    restaurant_name = data.get('name')
    identifier = data.get('identifier')

    result = extract_restaurant_info(
        restaurant_name=restaurant_name,
        identifier=identifier
    )

    return jsonify(result.to_dict())
```

## performance considerations

### api costs

- uses claude-3-5-haiku-20241022 (cost-effective model)
- ~500-1000 tokens per extraction
- caching reduces repeat costs (30-day ttl)

### optimization tips

1. **use caching**: enables 30-day cache to avoid repeat extractions
2. **batch processing**: process multiple restaurants in single session
3. **shared resources**: reuse scraper and cache instances for batch operations
4. **fallback to geo**: uses lightweight geo data when scraping unavailable

### typical extraction times

- with cache hit: < 0.1 seconds
- with scraping + extraction: 5-10 seconds
- batch (10 restaurants): 30-60 seconds

## limitations

1. **api dependency**: requires anthropic api access
2. **scraping dependency**: quality depends on yelp/opentable data availability
3. **extraction accuracy**: depends on claude's interpretation of source data
4. **rate limits**: subject to anthropic api rate limits
5. **data freshness**: cached data may be outdated (30-day ttl)

## troubleshooting

### "ANTHROPIC_API_KEY not set"

set the environment variable:
```bash
export ANTHROPIC_API_KEY="your-key"
```

### "no data available for extraction"

ensure either `identifier` or `geo_data` is provided:
```python
# with identifier
result = extract_restaurant_info(
    restaurant_name="Test",
    identifier=identifier  # must have urls
)

# or with geo_data
result = extract_restaurant_info(
    restaurant_name="Test",
    geo_data={'cuisine': 'Italian'}
)
```

### extraction returns partial status

check the error message:
```python
if result.status == "partial":
    print(f"Partial extraction: {result.error}")
    print(f"Available data: {result.cuisine}")
```

### cache not working

verify cache directory exists and is writable:
```bash
mkdir -p data/cache
chmod 755 data/cache
```

## dependencies

```
anthropic>=0.18.0  # for claude haiku api
requests==2.31.0  # for web scraping
python-dotenv>=1.0.0  # for environment variables
```

install:
```bash
uv pip install -r requirements.txt
```

## future enhancements

### additional fields
- parking availability
- wifi availability
- outdoor seating
- delivery/takeout options
- payment methods

### improved extraction
- multi-language support
- confidence scores for extracted fields
- source attribution per field

### advanced caching
- partial cache updates
- cache invalidation triggers
- distributed cache support

### integration
- direct flask api endpoints
- real-time updates via websockets
- graphql api support

## version history

- **v1.0**: initial implementation
  - core extraction functionality
  - yelp + opentable scraping integration
  - claude haiku extraction
  - 30-day caching
  - batch processing support
  - comprehensive testing
