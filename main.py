from flask import Flask, request, jsonify
from flask_cors import CORS
from agents.geo.geo import find_restaurants
import uuid

app = Flask(__name__)
CORS(app)


@app.route('/')
def home():
    """Home endpoint with API information."""
    return jsonify({
        'message': 'Restaurant Finder API',
        'endpoints': {
            '/restaurants': 'GET - Find restaurants near a location',
            '/health': 'GET - Health check'
        }
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    """
    Get restaurants within a radius of given coordinates.

    Query Parameters:
        latitude (float): Required - Latitude of the location
        longitude (float): Required - Longitude of the location
        distance (float): Optional - Radius in miles (default: 3.1)

    Returns:
        JSON response with restaurant data in frontend-compatible format
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

        # Transform data to match frontend types
        transformed_restaurants = []
        for restaurant in result['restaurants']:
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
                'radius': int(distance * 1609.34)  # Convert back to meters for response
            },
            'total': len(transformed_restaurants)
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Server error: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
