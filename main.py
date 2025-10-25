from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from agents.geo.geo import find_restaurants
from agents.research.research import research_restaurant
from dotenv import load_dotenv
import uuid
import json

# load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)


@app.route('/')
def home():
    """home endpoint with api information."""
    return jsonify({
        'message': 'Restaurant Finder API',
        'endpoints': {
            '/restaurants': 'GET - Find restaurants near a location',
            '/restaurants/research': 'GET - Find and research restaurants',
            '/restaurants/research/stream': 'GET - Stream restaurant research results (SSE)',
            '/health': 'GET - Health check'
        }
    })


@app.route('/health')
def health():
    """health check endpoint."""
    return jsonify({'status': 'healthy'})


@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    """get restaurants within a radius of given coordinates.

    query parameters:
        latitude (float): required - latitude of the location
        longitude (float): required - longitude of the location
        distance (float): optional - radius in miles (default: 3.1)
        max_num (int): optional - maximum number of restaurants to return (default: 50)

    returns:
        json response with restaurant data in frontend-compatible format
    """
    try:
        # Get query parameters (support both frontend and backend parameter names)
        latitude = request.args.get('latitude') or request.args.get('lat')
        longitude = request.args.get('longitude') or request.args.get('lng')

        # Convert to float
        latitude = float(latitude) if latitude else None
        longitude = float(longitude) if longitude else None

        # Get distance/radius - frontend sends meters, convert to miles
        radius_meters = request.args.get('radius', type=float)
        distance = request.args.get('distance', type=float)

        if radius_meters:
            distance = radius_meters / 1609.34  # Convert meters to miles
        elif not distance:
            distance = 3.1  # Default ~5km in miles

        # Get max_num parameter (maximum restaurants to return)
        max_num = request.args.get('max_num', type=int, default=50)
        if max_num < 1:
            max_num = 1

        # Validate required parameters
        if latitude is None:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: latitude or lat'
            }), 400

        if longitude is None:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: longitude or lng'
            }), 400

        # Call the restaurant finder
        result = find_restaurants(latitude, longitude, distance)

        # Return appropriate status code
        if result['status'] == 'error':
            return jsonify(result), 400

        # Transform data to match frontend types (limit to top max_num)
        transformed_restaurants = []
        for restaurant in result['restaurants'][:max_num]:
            transformed_restaurants.append({
                'id': str(uuid.uuid4()),  # Generate unique ID
                'name': restaurant['name'],
                'location': {
                    'lat': restaurant['latitude'],
                    'lng': restaurant['longitude']
                },
                'distanceMeters': int(restaurant['distance_miles'] * 1609.34),  # Convert miles to meters
                'cuisine': [restaurant['cuisine']] if restaurant['cuisine'] and restaurant['cuisine'] != 'Unknown' else [],
                'address': restaurant['address'],
                'amenity_type': restaurant['amenity_type']
            })

        # Return in frontend-compatible format
        response = {
            'restaurants': transformed_restaurants,
            'query': {
                'lat': latitude,
                'lng': longitude,
                'radius': int(distance * 1609.34),  # Convert back to meters for response
                'max_num': max_num
            },
            'total': len(transformed_restaurants),
            'total_found': result['count']
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Server error: {str(e)}'
        }), 500


@app.route('/restaurants/research', methods=['GET'])
def get_restaurants_with_research():
    """find restaurants and research top N results using reka api.

    query parameters:
        latitude (float): required - latitude of the location
        longitude (float): required - longitude of the location
        distance (float): optional - radius in miles (default: 3.1)
        limit (int): optional - number of restaurants to research (default: 3, max: 10)

    returns:
        json response with restaurant geo data and research reports
    """
    try:
        # get query parameters (support both frontend and backend parameter names)
        latitude = request.args.get('latitude') or request.args.get('lat')
        longitude = request.args.get('longitude') or request.args.get('lng')

        # convert to float
        latitude = float(latitude) if latitude else None
        longitude = float(longitude) if longitude else None

        # get distance/radius - frontend sends meters, convert to miles
        radius_meters = request.args.get('radius', type=float)
        distance = request.args.get('distance', type=float)

        if radius_meters:
            distance = radius_meters / 1609.34  # convert meters to miles
        elif not distance:
            distance = 3.1  # default ~5km in miles

        # get limit parameter (how many restaurants to research)
        limit = request.args.get('limit', type=int, default=3)
        if limit < 1:
            limit = 1
        if limit > 10:
            limit = 10

        # validate required parameters
        if latitude is None:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: latitude or lat'
            }), 400

        if longitude is None:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: longitude or lng'
            }), 400

        # call the restaurant finder
        geo_result = find_restaurants(latitude, longitude, distance)

        # return appropriate status code
        if geo_result['status'] == 'error':
            return jsonify(geo_result), 400

        # research top N restaurants
        researched_restaurants = []
        for i, restaurant in enumerate(geo_result['restaurants'][:limit]):
            # add id to restaurant for research tracking
            restaurant['id'] = str(uuid.uuid4())

            # call research agent
            research_result = research_restaurant(restaurant)

            # combine geo and research data
            combined = {
                'id': restaurant['id'],
                'name': restaurant['name'],
                'location': {
                    'lat': restaurant['latitude'],
                    'lng': restaurant['longitude']
                },
                'distanceMeters': int(restaurant['distance_miles'] * 1609.34),
                'cuisine': [restaurant['cuisine']] if restaurant['cuisine'] and restaurant['cuisine'] != 'Unknown' else [],
                'address': restaurant['address'],
                'amenity_type': restaurant['amenity_type'],
                'research': {
                    'status': research_result['status'],
                    'content': research_result.get('research_content', ''),
                    'citations': research_result.get('citations', []),
                    'reasoning_steps': research_result.get('reasoning_steps', []),
                    'timestamp': research_result.get('timestamp', ''),
                    'error': research_result.get('error')
                }
            }

            researched_restaurants.append(combined)

        # transform remaining restaurants without research
        remaining_restaurants = []
        for restaurant in geo_result['restaurants'][limit:]:
            remaining_restaurants.append({
                'id': str(uuid.uuid4()),
                'name': restaurant['name'],
                'location': {
                    'lat': restaurant['latitude'],
                    'lng': restaurant['longitude']
                },
                'distanceMeters': int(restaurant['distance_miles'] * 1609.34),
                'cuisine': [restaurant['cuisine']] if restaurant['cuisine'] and restaurant['cuisine'] != 'Unknown' else [],
                'address': restaurant['address'],
                'amenity_type': restaurant['amenity_type']
            })

        # return combined results
        response = {
            'restaurants_with_research': researched_restaurants,
            'restaurants_without_research': remaining_restaurants,
            'query': {
                'lat': latitude,
                'lng': longitude,
                'radius': int(distance * 1609.34),
                'research_limit': limit
            },
            'total_found': geo_result['count'],
            'total_researched': len(researched_restaurants)
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Server error: {str(e)}'
        }), 500


@app.route('/restaurants/research/stream', methods=['GET'])
def get_restaurants_with_research_stream():
    """stream restaurants with research results as they complete using server-sent events.

    query parameters:
        latitude (float): required - latitude of the location
        longitude (float): required - longitude of the location
        distance (float): optional - radius in miles (default: 3.1)
        limit (int): optional - number of restaurants to research (default: 3, max: 10)

    returns:
        server-sent event stream with restaurant geo data and research reports
    """
    def generate():
        try:
            # get query parameters (support both frontend and backend parameter names)
            latitude = request.args.get('latitude') or request.args.get('lat')
            longitude = request.args.get('longitude') or request.args.get('lng')

            # convert to float
            latitude = float(latitude) if latitude else None
            longitude = float(longitude) if longitude else None

            # get distance/radius - frontend sends meters, convert to miles
            radius_meters = request.args.get('radius', type=float)
            distance = request.args.get('distance', type=float)

            if radius_meters:
                distance = radius_meters / 1609.34  # convert meters to miles
            elif not distance:
                distance = 3.1  # default ~5km in miles

            # get limit parameter (how many restaurants to research)
            limit = request.args.get('limit', type=int, default=3)
            if limit < 1:
                limit = 1
            if limit > 10:
                limit = 10

            # validate required parameters
            if latitude is None:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Missing required parameter: latitude or lat'})}\n\n"
                return

            if longitude is None:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Missing required parameter: longitude or lng'})}\n\n"
                return

            # call the restaurant finder
            geo_result = find_restaurants(latitude, longitude, distance)

            # return appropriate status code
            if geo_result['status'] == 'error':
                yield f"data: {json.dumps({'type': 'error', 'error': geo_result.get('error', 'Unknown error')})}\n\n"
                return

            # send initial metadata
            metadata = {
                'type': 'metadata',
                'query': {
                    'lat': latitude,
                    'lng': longitude,
                    'radius': int(distance * 1609.34),
                    'research_limit': limit
                },
                'total_found': geo_result['count'],
                'total_to_research': min(limit, len(geo_result['restaurants']))
            }
            yield f"data: {json.dumps(metadata)}\n\n"

            # stream researched restaurants as they complete
            for i, restaurant in enumerate(geo_result['restaurants'][:limit]):
                # add id to restaurant for research tracking
                restaurant['id'] = str(uuid.uuid4())

                # call research agent
                research_result = research_restaurant(restaurant)

                # combine geo and research data
                combined = {
                    'type': 'restaurant_researched',
                    'index': i,
                    'data': {
                        'id': restaurant['id'],
                        'name': restaurant['name'],
                        'location': {
                            'lat': restaurant['latitude'],
                            'lng': restaurant['longitude']
                        },
                        'distanceMeters': int(restaurant['distance_miles'] * 1609.34),
                        'cuisine': [restaurant['cuisine']] if restaurant['cuisine'] and restaurant['cuisine'] != 'Unknown' else [],
                        'address': restaurant['address'],
                        'amenity_type': restaurant['amenity_type'],
                        'research': {
                            'status': research_result['status'],
                            'content': research_result.get('research_content', ''),
                            'citations': research_result.get('citations', []),
                            'reasoning_steps': research_result.get('reasoning_steps', []),
                            'timestamp': research_result.get('timestamp', ''),
                            'error': research_result.get('error')
                        }
                    }
                }

                yield f"data: {json.dumps(combined)}\n\n"

            # stream remaining restaurants without research
            remaining = []
            for restaurant in geo_result['restaurants'][limit:]:
                remaining.append({
                    'id': str(uuid.uuid4()),
                    'name': restaurant['name'],
                    'location': {
                        'lat': restaurant['latitude'],
                        'lng': restaurant['longitude']
                    },
                    'distanceMeters': int(restaurant['distance_miles'] * 1609.34),
                    'cuisine': [restaurant['cuisine']] if restaurant['cuisine'] and restaurant['cuisine'] != 'Unknown' else [],
                    'address': restaurant['address'],
                    'amenity_type': restaurant['amenity_type']
                })

            if remaining:
                yield f"data: {json.dumps({'type': 'restaurants_without_research', 'data': remaining})}\n\n"

            # send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': f'Server error: {str(e)}'})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
