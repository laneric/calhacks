# flask api documentation

rest api for restaurant discovery and research.

## overview

the flask api provides endpoints for finding restaurants geographically and researching them using ai-powered web search. it combines the geo agent (openstreetmap data) with the research agent (reka ai) to deliver comprehensive restaurant information.

## base url

```
http://localhost:5001
```

## endpoints

### `GET /`

home endpoint with api information.

**response**:
```json
{
  "message": "Restaurant Finder API",
  "endpoints": {
    "/restaurants": "GET - Find restaurants near a location",
    "/restaurants/research": "GET - Find and research restaurants",
    "/health": "GET - Health check"
  }
}
```

---

### `GET /health`

health check endpoint.

**response**:
```json
{
  "status": "healthy"
}
```

---

### `GET /restaurants`

find restaurants within a radius of given coordinates.

**query parameters**:
- `latitude` or `lat` (float, required): latitude of the location
- `longitude` or `lng` (float, required): longitude of the location
- `distance` (float, optional): radius in miles (default: 3.1)
- `radius` (float, optional): radius in meters (converted to miles internally)

**example request**:
```bash
curl "http://localhost:5001/restaurants?latitude=37.7749&longitude=-122.4194&distance=5"
```

**success response** (200):
```json
{
  "restaurants": [
    {
      "id": "uuid-string",
      "name": "Restaurant Name",
      "location": {
        "lat": 37.7749,
        "lng": -122.4194
      },
      "distanceMeters": 804,
      "cuisine": ["italian"],
      "address": "123 Main St",
      "amenity_type": "restaurant"
    }
  ],
  "query": {
    "lat": 37.7749,
    "lng": -122.4194,
    "radius": 8046
  },
  "total": 15
}
```

**error response** (400):
```json
{
  "status": "error",
  "error": "Missing required parameter: latitude or lat"
}
```

**notes**:
- restaurants are sorted by distance (nearest first)
- cuisine is returned as array (can be empty for unknown)
- distances are in meters for frontend compatibility

---

### `GET /restaurants/research`

find restaurants and research top N results using reka ai.

**query parameters**:
- `latitude` or `lat` (float, required): latitude of the location
- `longitude` or `lng` (float, required): longitude of the location
- `distance` (float, optional): radius in miles (default: 3.1)
- `radius` (float, optional): radius in meters (converted to miles internally)
- `limit` (int, optional): number of restaurants to research (default: 3, min: 1, max: 10)

**example request**:
```bash
curl "http://localhost:5001/restaurants/research?latitude=37.7749&longitude=-122.4194&distance=5&limit=3"
```

**success response** (200):
```json
{
  "restaurants_with_research": [
    {
      "id": "uuid-string",
      "name": "Restaurant Name",
      "location": {
        "lat": 37.7749,
        "lng": -122.4194
      },
      "distanceMeters": 804,
      "cuisine": ["italian"],
      "address": "123 Main St",
      "amenity_type": "restaurant",
      "research": {
        "status": "success",
        "content": "Detailed research content with menu analysis, reviews, pricing...",
        "citations": [
          {
            "title": "Source Title",
            "url": "https://example.com",
            "start_index": 0,
            "end_index": 50
          }
        ],
        "reasoning_steps": [
          "Step 1: Searched for restaurant reviews",
          "Step 2: Analyzed menu offerings"
        ],
        "timestamp": "2025-01-01T00:00:00+00:00",
        "error": null
      }
    }
  ],
  "restaurants_without_research": [
    {
      "id": "uuid-string",
      "name": "Another Restaurant",
      "location": {
        "lat": 37.7750,
        "lng": -122.4195
      },
      "distanceMeters": 1609,
      "cuisine": ["mexican"],
      "address": "456 Oak St",
      "amenity_type": "restaurant"
    }
  ],
  "query": {
    "lat": 37.7749,
    "lng": -122.4194,
    "radius": 8046,
    "research_limit": 3
  },
  "total_found": 15,
  "total_researched": 3
}
```

**research object structure**:
- `status`: 'success' or 'failed'
- `content`: main research findings (empty string if failed)
- `citations`: array of citation objects with sources
- `reasoning_steps`: array showing reka's research methodology
- `timestamp`: iso format timestamp of research
- `error`: error message if status is 'failed' (null otherwise)

**error response** (400):
```json
{
  "status": "error",
  "error": "Missing required parameter: latitude or lat"
}
```

**notes**:
- limit is clamped between 1 and 10 to control api costs
- researched restaurants appear in `restaurants_with_research`
- remaining restaurants appear in `restaurants_without_research`
- research failures are included in response (check `research.status`)
- requires `REKA_API_KEY` environment variable to be set

---

### `GET /restaurants/research/stream`

find restaurants and stream research results as they complete using server-sent events (sse).

**query parameters**:
- `latitude` or `lat` (float, required): latitude of the location
- `longitude` or `lng` (float, required): longitude of the location
- `distance` (float, optional): radius in miles (default: 3.1)
- `radius` (float, optional): radius in meters (converted to miles internally)
- `limit` (int, optional): number of restaurants to research (default: 3, min: 1, max: 10)

**example request**:
```bash
curl -N "http://localhost:5001/restaurants/research/stream?latitude=37.7749&longitude=-122.4194&distance=5&limit=3"
```

**response format**: server-sent events (text/event-stream)

**event types**:

1. **metadata** (first event):
```json
{
  "type": "metadata",
  "query": {
    "lat": 37.7749,
    "lng": -122.4194,
    "radius": 8046,
    "research_limit": 3
  },
  "total_found": 15,
  "total_to_research": 3
}
```

2. **restaurant_researched** (one per researched restaurant):
```json
{
  "type": "restaurant_researched",
  "index": 0,
  "data": {
    "id": "uuid-string",
    "name": "Restaurant Name",
    "location": {
      "lat": 37.7749,
      "lng": -122.4194
    },
    "distanceMeters": 804,
    "cuisine": ["italian"],
    "address": "123 Main St",
    "amenity_type": "restaurant",
    "research": {
      "status": "success",
      "content": "Detailed research content...",
      "citations": [...],
      "reasoning_steps": [...],
      "timestamp": "2025-01-01T00:00:00+00:00",
      "error": null
    }
  }
}
```

3. **restaurants_without_research** (batch of remaining restaurants):
```json
{
  "type": "restaurants_without_research",
  "data": [
    {
      "id": "uuid-string",
      "name": "Another Restaurant",
      "location": {
        "lat": 37.7750,
        "lng": -122.4195
      },
      "distanceMeters": 1609,
      "cuisine": ["mexican"],
      "address": "456 Oak St",
      "amenity_type": "restaurant"
    }
  ]
}
```

4. **complete** (final event):
```json
{
  "type": "complete"
}
```

5. **error** (if error occurs):
```json
{
  "type": "error",
  "error": "error message"
}
```

**javascript client example**:
```javascript
const eventSource = new EventSource(
  `http://localhost:5001/restaurants/research/stream?lat=${lat}&lng=${lng}&limit=3`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'metadata':
      console.log(`Found ${data.total_found} restaurants, researching ${data.total_to_research}`);
      break;
    case 'restaurant_researched':
      console.log(`Received research for: ${data.data.name}`);
      // update ui with new restaurant data
      break;
    case 'restaurants_without_research':
      console.log(`Received ${data.data.length} restaurants without research`);
      break;
    case 'complete':
      console.log('Stream complete');
      eventSource.close();
      break;
    case 'error':
      console.error('Error:', data.error);
      eventSource.close();
      break;
  }
};

eventSource.onerror = (error) => {
  console.error('EventSource failed:', error);
  eventSource.close();
};
```

**python client example**:
```python
import requests
import json

response = requests.get(
    'http://localhost:5001/restaurants/research/stream',
    params={
        'latitude': 37.7749,
        'longitude': -122.4194,
        'distance': 5,
        'limit': 3
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        decoded_line = line.decode('utf-8')
        if decoded_line.startswith('data: '):
            data = json.loads(decoded_line[6:])
            print(f"Event: {data.get('type')}")

            if data.get('type') == 'complete':
                break
```

**notes**:
- streaming allows ui to update progressively as research completes
- reduces perceived latency compared to waiting for all research to finish
- client should handle connection errors and reconnection logic
- use `-N` flag with curl to disable buffering
- compatible with browser eventsource api
- same research quality as non-streaming endpoint

---

## error codes

- `200`: success
- `400`: bad request (missing parameters, invalid coordinates, geo agent errors)
- `500`: server error (unexpected exceptions)

## data types

### restaurant object (basic)

```typescript
{
  id: string;                    // uuid v4
  name: string;                  // restaurant name or "Unnamed Restaurant"
  location: {
    lat: number;                 // latitude
    lng: number;                 // longitude
  };
  distanceMeters: number;        // distance from query point in meters
  cuisine: string[];             // array of cuisine types (empty if unknown)
  address: string;               // street address or "Address not available"
  amenity_type: string;          // "restaurant" or "fast_food"
}
```

### restaurant object (with research)

extends basic restaurant object with:

```typescript
{
  research: {
    status: "success" | "failed";
    content: string;             // research findings
    citations: Array<{
      title: string;
      url: string;
      start_index?: number;
      end_index?: number;
    }>;
    reasoning_steps: string[];   // reka's research steps
    timestamp: string;           // iso format
    error: string | null;        // error message if failed
  }
}
```

## usage examples

### basic restaurant search

```javascript
// frontend example
const response = await fetch(
  `http://localhost:5001/restaurants?lat=${lat}&lng=${lng}&radius=5000`
);
const data = await response.json();

data.restaurants.forEach(restaurant => {
  console.log(`${restaurant.name} - ${restaurant.distanceMeters}m away`);
});
```

### restaurant search with research

```javascript
// frontend example with research
const response = await fetch(
  `http://localhost:5001/restaurants/research?lat=${lat}&lng=${lng}&limit=3`
);
const data = await response.json();

// display researched restaurants
data.restaurants_with_research.forEach(restaurant => {
  console.log(`${restaurant.name}`);
  console.log(`Research: ${restaurant.research.content.substring(0, 200)}...`);
  console.log(`Sources: ${restaurant.research.citations.length}`);
});

// display remaining restaurants without research
data.restaurants_without_research.forEach(restaurant => {
  console.log(`${restaurant.name} (no research)`);
});
```

### python client example

```python
import requests

# basic search
response = requests.get(
    'http://localhost:5001/restaurants',
    params={
        'latitude': 37.7749,
        'longitude': -122.4194,
        'distance': 5
    }
)
data = response.json()
print(f"Found {data['total']} restaurants")

# search with research
response = requests.get(
    'http://localhost:5001/restaurants/research',
    params={
        'latitude': 37.7749,
        'longitude': -122.4194,
        'distance': 5,
        'limit': 3
    }
)
data = response.json()
print(f"Researched {data['total_researched']} out of {data['total_found']} restaurants")
```

## configuration

### environment variables

- `REKA_API_KEY`: required for `/restaurants/research` endpoint
- `FLASK_ENV`: set to 'development' for debug mode

### running the server

```bash
# set environment variables
export REKA_API_KEY="your-reka-api-key"

# run the server
python3 main.py
```

server runs on `http://localhost:5001` by default.

## integration with frontend

the api is designed to work with the existing frontend map interface:

1. **map interaction**: user clicks on map or enters location
2. **fetch restaurants**: call `/restaurants` to get nearby restaurants
3. **display markers**: show restaurants on map
4. **optional research**: call `/restaurants/research` for detailed info on selected restaurants
5. **display details**: show research findings in sidebar or modal

## performance considerations

### `/restaurants` endpoint
- fast response times (1-3 seconds typical)
- depends on overpass api availability
- results cached by openstreetmap

### `/restaurants/research` endpoint
- slower response times (3-15 seconds per restaurant)
- depends on reka api availability
- costs apply based on reka pricing
- use `limit` parameter to control costs
- consider showing loading states in ui

### `/restaurants/research/stream` endpoint
- progressive response times (first result in 3-15 seconds, subsequent results stream)
- better perceived performance compared to non-streaming endpoint
- same api dependencies and costs as `/restaurants/research`
- ideal for ui that can update incrementally
- connection stays open until all research completes

## rate limiting

- no rate limiting implemented in this api
- subject to upstream api limits (overpass, reka)
- recommend implementing client-side debouncing for user interactions

## cors

cors is enabled for all origins via `flask_cors`.

## testing

run api tests:
```bash
PYTHONPATH=/Users/gurnoor/Desktop/calhacks pytest tests/test_main.py -v
```

## error handling

all endpoints return consistent error format:
```json
{
  "status": "error",
  "error": "descriptive error message"
}
```

common errors:
- missing required parameters
- invalid coordinates (out of range)
- geo agent failures (overpass api issues)
- research agent failures (missing api key, reka api errors)

## future enhancements

### caching
- implement redis caching for geo results
- cache research results with ttl
- reduce api costs and improve response times

### pagination
- add pagination for large result sets
- limit parameter for `/restaurants` endpoint

### filtering
- cuisine type filtering
- price range filtering
- rating filtering

### webhooks
- webhook support for async research processing
- background job queue for large batches

### authentication
- api key authentication
- rate limiting per user
- usage tracking

## dependencies

```
Flask==3.0.0
Flask-CORS==4.0.0
requests==2.31.0
openai>=1.0.0
python-dotenv>=1.0.0
```

## version history

- **v1.0**: initial api release
  - `/restaurants` endpoint (geo search)
  - `/health` endpoint
- **v1.1**: research integration
  - `/restaurants/research` endpoint
  - combined geo + ai research
- **v1.2**: streaming support
  - `/restaurants/research/stream` endpoint
  - server-sent events for progressive research results
