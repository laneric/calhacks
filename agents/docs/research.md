# research agent

comprehensive restaurant research and reporting system using reka's research sdk.

## overview

the research agent leverages reka's `reka-flash-research` model to generate detailed, citation-backed reports about restaurants. it performs real-time web searches to gather information about menus, pricing, reviews, health inspections, awards, and business details.

## architecture

### core components

1. **prompt builder**: constructs detailed research prompts for reka api
2. **research executor**: makes api calls and handles responses
3. **location context extractor**: formats restaurant location data for better search results

## functions

### `build_research_prompt(restaurant: Dict) -> str`

constructs a comprehensive research prompt for a single restaurant.

**parameters**:
- `restaurant` (dict): restaurant data containing:
  - `name` (str): restaurant name (required)
  - `address` (str, optional): street address
  - `city` (str, optional): city name
  - `cuisine` (str, optional): cuisine type
  - `latitude` (float, optional): location latitude
  - `longitude` (float, optional): location longitude

**returns**:
- `str`: formatted prompt string for reka api

**research areas covered**:
1. menu & cuisine (signature dishes, popular items, dietary options)
2. pricing (price range, value proposition, average meal cost)
3. customer experience (review sentiment, praise/complaints)
4. health & safety (inspection scores, violations, cleanliness)
5. recognition (awards, michelin stars, certifications)
6. business information (establishment date, ownership, hours, status)

**example**:
```python
restaurant = {
    'name': 'Tonys Pizza',
    'address': '1570 Stockton St',
    'city': 'San Francisco',
    'cuisine': 'Italian'
}
prompt = build_research_prompt(restaurant)
```

### `research_restaurant(restaurant: Dict, api_key: Optional[str] = None) -> Dict`

executes reka api call to research a single restaurant.

**parameters**:
- `restaurant` (dict): restaurant data (see `build_research_prompt` for structure)
- `api_key` (str, optional): reka api key (defaults to `REKA_API_KEY` env var)

**returns**:
- `dict`: research result containing:
  - `restaurant_id` (str): unique identifier
  - `restaurant_name` (str): restaurant name
  - `research_content` (str): main research findings
  - `reasoning_steps` (list): reka's reasoning steps
  - `citations` (list): citation objects with title, url, and indices
  - `timestamp` (str): iso format timestamp
  - `status` (str): 'success' or 'failed'
  - `error` (str, optional): error message if failed

**example**:
```python
restaurant = {
    'id': '1',
    'name': 'Tonys Pizza',
    'address': '1570 Stockton St',
    'city': 'San Francisco'
}
result = research_restaurant(restaurant)

if result['status'] == 'success':
    print(result['research_content'])
    print(f"Citations: {len(result['citations'])}")
```

**error handling**:
- returns failed status if api key is not set
- returns failed status if restaurant name is missing
- catches all api exceptions and returns error details

### `extract_location_context(restaurant: Dict) -> str`

builds a formatted location string for better search context.

**parameters**:
- `restaurant` (dict): restaurant data

**returns**:
- `str`: formatted location string (e.g., "tonys pizza, 1570 stockton st, san francisco (italian cuisine)")

**example**:
```python
restaurant = {
    'name': 'Pizza Place',
    'address': '123 Main St',
    'city': 'Berkeley',
    'cuisine': 'Italian'
}
context = extract_location_context(restaurant)
# returns: "Pizza Place, 123 Main St, Berkeley (Italian cuisine)"
```

## configuration

### environment variables

- `REKA_API_KEY`: reka api key (required)

set via `.env` file or environment:
```bash
export REKA_API_KEY="your-api-key-here"
```

### api configuration

- **model**: `reka-flash-research`
- **temperature**: 0.3 (for consistent, factual research)
- **max_tokens**: 4096 (for comprehensive reports)
- **base_url**: `https://api.reka.ai/v1`

## usage

### basic usage

```python
from agents.research.research import research_restaurant

restaurant = {
    'id': '123',
    'name': 'Example Restaurant',
    'address': '456 Oak St',
    'city': 'Oakland',
    'cuisine': 'Mexican'
}

result = research_restaurant(restaurant)

if result['status'] == 'success':
    print(f"Research for {result['restaurant_name']}")
    print(result['research_content'])
    print(f"\nSources: {len(result['citations'])} citations")
else:
    print(f"Error: {result['error']}")
```

### command line usage

```bash
cd /Users/gurnoor/Desktop/calhacks
export REKA_API_KEY="your-key"
python3 agents/research/research.py
```

## testing

tests are located in `/tests/test_research.py`.

run tests:
```bash
PYTHONPATH=/Users/gurnoor/Desktop/calhacks pytest tests/test_research.py -v
```

### test coverage

- prompt building (full data, minimal data, missing name)
- location context extraction (full data, minimal data, empty)
- research function (no api key, no name, missing id)

## integration

### with geo agent

the research agent is designed to consume restaurant data from the geo agent:

```python
from agents.geo.geo import find_restaurants
from agents.research.research import research_restaurant

# find restaurants
geo_result = find_restaurants(37.7749, -122.4194, distance=5)

# research first restaurant
if geo_result['status'] == 'success' and geo_result['restaurants']:
    restaurant = geo_result['restaurants'][0]
    research_result = research_restaurant(restaurant)
```

### with flask api

future integration point for main.py:

```python
@app.route('/research/restaurant', methods=['POST'])
def research_restaurant_endpoint():
    data = request.json
    restaurant = data.get('restaurant')
    result = research_restaurant(restaurant)
    return jsonify(result)
```

## future enhancements

### phase 2: report processing
- structured report parsing
- section categorization
- citation management
- quality validation

### phase 3: batch processing
- concurrent restaurant research
- rate limiting
- retry logic with exponential backoff
- progress tracking

### phase 4: export formats
- markdown reports
- pdf generation
- json api responses

### phase 5: caching
- report caching with ttl
- incremental updates
- cost optimization

## dependencies

```
openai>=1.0.0  # for reka api (openai-compatible)
python-dotenv>=1.0.0  # for environment variables
```

install:
```bash
uv pip install -r requirements.txt
```

## api costs

reka pricing applies. estimate:
- ~2000-4000 tokens per restaurant (prompt + response)
- citations and reasoning add minimal overhead
- costs depend on reka's current pricing model

## limitations

- requires valid reka api key
- depends on real-time web search availability
- quality depends on available online information about restaurant
- rate limits apply based on reka's api tier

## troubleshooting

### "REKA_API_KEY not set"
set the environment variable:
```bash
export REKA_API_KEY="your-key"
```

### "restaurant name is required"
ensure the restaurant dict has a 'name' field:
```python
restaurant = {'name': 'Restaurant Name', ...}
```

### module import errors
ensure pythonpath is set:
```bash
export PYTHONPATH=/Users/gurnoor/Desktop/calhacks
```

## version history

- **v1.0** (phase 1): core research function for single restaurant
  - prompt building
  - api integration
  - error handling
  - basic testing
