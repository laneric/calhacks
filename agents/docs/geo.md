# geo agent

geospatial restaurant discovery system using openstreetmap's overpass api.

## overview

the geo agent provides functionality to find restaurants within a specified radius of geographic coordinates. it uses the overpass api to query openstreetmap data for restaurants and fast food establishments, calculating precise distances and filtering results.

## architecture

### core components

1. **coordinate validation**: validates latitude and longitude ranges
2. **distance calculation**: haversine formula for precise earth surface distances
3. **unit conversion**: miles to meters conversion for api compatibility
4. **api integration**: overpass api queries for restaurant data
5. **result processing**: filtering, sorting, and formatting restaurant data

## functions

### `miles_to_meters(miles: float) -> float`

convert miles to meters for distance calculations.

**parameters**:
- `miles` (float): distance in miles

**returns**:
- `float`: distance in meters

**conversion factor**: 1 mile = 1609.34 meters

**example**:
```python
meters = miles_to_meters(5)
print(meters)  # 8046.7
```

### `haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float`

calculate the distance between two points on earth using the haversine formula.

**parameters**:
- `lat1` (float): latitude of first point in degrees
- `lon1` (float): longitude of first point in degrees
- `lat2` (float): latitude of second point in degrees
- `lon2` (float): longitude of second point in degrees

**returns**:
- `float`: distance in miles

**algorithm**:
- uses haversine formula for great-circle distance
- earth radius: 3959.0 miles
- accounts for earth's spherical shape

**example**:
```python
# distance from san francisco to berkeley
sf_lat, sf_lon = 37.7749, -122.4194
berkeley_lat, berkeley_lon = 37.8715, -122.2730

distance = haversine_distance(sf_lat, sf_lon, berkeley_lat, berkeley_lon)
print(f"Distance: {distance:.2f} miles")  # ~11 miles
```

### `validate_coordinates(latitude: float, longitude: float) -> bool`

validate that latitude and longitude are within valid ranges.

**parameters**:
- `latitude` (float): latitude value to validate
- `longitude` (float): longitude value to validate

**returns**:
- `bool`: true if coordinates are valid, false otherwise

**validation rules**:
- latitude: must be between -90 and 90 degrees
- longitude: must be between -180 and 180 degrees

**example**:
```python
is_valid = validate_coordinates(37.7749, -122.4194)
print(is_valid)  # True

is_valid = validate_coordinates(100, 200)
print(is_valid)  # False
```

### `query_overpass_api(latitude: float, longitude: float, radius_meters: float) -> List[Dict]`

query overpass api for restaurants within a radius.

**parameters**:
- `latitude` (float): center point latitude
- `longitude` (float): center point longitude
- `radius_meters` (float): search radius in meters

**returns**:
- `List[Dict]`: raw results from overpass api

**api details**:
- endpoint: `http://overpass-api.de/api/interpreter`
- queries for: `amenity=restaurant` and `amenity=fast_food`
- format: overpass ql (query language)
- output: json with node elements

**example**:
```python
results = query_overpass_api(37.7749, -122.4194, 5000)
print(f"Found {len(results)} restaurants")
```

### `find_restaurants(latitude: float, longitude: float, distance: float = 10) -> Dict`

find restaurants within a specified radius of a given location.

**parameters**:
- `latitude` (float): user's latitude
- `longitude` (float): user's longitude
- `distance` (float, optional): search radius in miles (default: 10)

**returns**:
- `Dict`: response containing:
  - `status` (str): 'success' or 'error'
  - `count` (int): number of restaurants found
  - `restaurants` (List[Dict]): list of restaurant objects
  - `query` (Dict): original query parameters
  - `error` (str, optional): error message if status is 'error'

**restaurant object structure**:
```python
{
    'name': str,                    # restaurant name or 'Unnamed Restaurant'
    'latitude': float,              # restaurant latitude
    'longitude': float,             # restaurant longitude
    'distance_miles': float,        # distance from query point (rounded to 2 decimals)
    'cuisine': str,                 # cuisine type or 'Unknown'
    'address': str,                 # street address or 'Address not available'
    'city': str,                    # city name
    'amenity_type': str             # 'restaurant' or 'fast_food'
}
```

**processing steps**:
1. validate input coordinates
2. validate distance is positive
3. convert distance to meters
4. query overpass api
5. filter results by exact distance
6. extract and format restaurant data
7. sort by distance (nearest first)

**example**:
```python
result = find_restaurants(37.7749, -122.4194, distance=5)

if result['status'] == 'success':
    print(f"Found {result['count']} restaurants")
    for restaurant in result['restaurants']:
        print(f"{restaurant['name']} - {restaurant['distance_miles']} miles")
else:
    print(f"Error: {result['error']}")
```

**error cases**:
- invalid coordinates: returns error with validation message
- invalid distance: returns error if distance <= 0
- api failures: returns error with exception details

## usage

### basic usage

```python
from agents.geo.geo import find_restaurants

# find restaurants within 5 miles of san francisco
result = find_restaurants(37.7749, -122.4194, distance=5)

if result['status'] == 'success':
    for restaurant in result['restaurants']:
        print(f"{restaurant['name']}")
        print(f"  Cuisine: {restaurant['cuisine']}")
        print(f"  Distance: {restaurant['distance_miles']} miles")
        print(f"  Address: {restaurant['address']}")
        print()
```

### command line usage

```bash
cd /Users/gurnoor/Desktop/calhacks
python3 agents/geo/geo.py
```

the main block includes an example that searches for restaurants in san francisco.

### integration with flask api

the geo agent is already integrated into main.py:

```python
# endpoint: GET /restaurants
# parameters: latitude, longitude, distance (or radius in meters)

curl "http://localhost:5001/restaurants?latitude=37.7749&longitude=-122.4194&distance=5"
```

## data source

### openstreetmap

- data source: openstreetmap contributors
- api: overpass api
- update frequency: typically daily
- coverage: worldwide

### amenity types

the api queries for two amenity types:
1. `amenity=restaurant`: sit-down restaurants
2. `amenity=fast_food`: fast food establishments

### available tags

common openstreetmap tags extracted:
- `name`: restaurant name
- `cuisine`: type of cuisine
- `addr:street`: street address
- `addr:city`: city name
- `amenity`: establishment type

## testing

tests are located in `/tests/test_geo.py`.

run tests:
```bash
PYTHONPATH=/Users/gurnoor/Desktop/calhacks pytest tests/test_geo.py -v
```

### test coverage (22 tests)

**unit conversions**:
- miles to meters conversion

**distance calculations**:
- same point (zero distance)
- known distances
- cross-equator calculations

**coordinate validation**:
- valid coordinates
- invalid latitude
- invalid longitude
- both invalid

**api integration**:
- successful responses
- empty results
- missing data handling

**restaurant finding**:
- invalid inputs (coordinates, distance)
- successful queries
- distance filtering
- missing data handling
- sorting by distance
- error handling

## integration

### with research agent

the geo agent provides restaurant data that can be enriched by the research agent:

```python
from agents.geo.geo import find_restaurants
from agents.research.research import research_restaurant

# find restaurants
geo_result = find_restaurants(37.7749, -122.4194, distance=5)

# research top 3 restaurants
if geo_result['status'] == 'success':
    for restaurant in geo_result['restaurants'][:3]:
        research = research_restaurant(restaurant)
        print(f"Research for {restaurant['name']}: {research['status']}")
```

### with frontend

the flask api transforms geo data for frontend consumption:

```javascript
// frontend map integration
const response = await fetch(
  `/restaurants?lat=${lat}&lng=${lng}&radius=${radiusMeters}`
);
const data = await response.json();

// data.restaurants contains transformed format:
// { id, name, location: {lat, lng}, distanceMeters, cuisine, address }
```

## performance considerations

### api limits

- overpass api has rate limits (typically generous for normal use)
- large radius queries take longer
- dense urban areas return more results

### optimization tips

1. **use appropriate radius**: smaller radius = faster queries
2. **cache results**: avoid repeated queries for same location
3. **filter on client**: reduce api calls by filtering client-side

### typical response times

- small radius (1-5 miles): 1-2 seconds
- medium radius (5-10 miles): 2-4 seconds
- large radius (10+ miles): 3-6 seconds

## limitations

1. **data completeness**: depends on openstreetmap coverage
2. **data accuracy**: community-maintained, may have outdated info
3. **api availability**: depends on overpass api uptime
4. **network dependency**: requires internet connection
5. **rate limits**: subject to overpass api rate limiting

## troubleshooting

### "invalid coordinates" error

ensure latitude is between -90 and 90, longitude between -180 and 180:
```python
# correct
find_restaurants(37.7749, -122.4194)

# incorrect
find_restaurants(100, 200)  # out of range
```

### "distance must be greater than 0" error

use positive distance value:
```python
# correct
find_restaurants(37.7749, -122.4194, distance=5)

# incorrect
find_restaurants(37.7749, -122.4194, distance=0)
find_restaurants(37.7749, -122.4194, distance=-5)
```

### no restaurants found

possible causes:
- sparse area with few restaurants
- radius too small
- openstreetmap data incomplete for area

solution: increase search radius or try different location

### api timeout errors

if overpass api is slow or unavailable:
- retry after a few seconds
- check overpass api status
- reduce search radius

## future enhancements

### additional filters
- cuisine type filtering
- price range filtering
- rating filters
- operating hours filtering

### enhanced data
- phone numbers
- websites
- operating hours
- wheelchair accessibility

### performance
- result caching with ttl
- pagination for large result sets
- geospatial indexing

### alternative apis
- google places api integration
- yelp api integration
- foursquare api integration

## dependencies

```
requests==2.31.0  # for http requests to overpass api
```

## version history

- **v1.0**: initial implementation
  - haversine distance calculation
  - overpass api integration
  - coordinate validation
  - restaurant finding and filtering
  - flask api integration
