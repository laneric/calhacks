"""tests for the flask api endpoints."""

import pytest
from unittest.mock import patch, Mock
from main import app


@pytest.fixture
def client():
    """create a test client for the flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_home_endpoint(client):
    """test the home endpoint returns api information."""
    response = client.get('/')
    assert response.status_code == 200

    data = response.get_json()
    assert data['message'] == 'Restaurant Finder API'
    assert '/restaurants' in data['endpoints']
    assert '/restaurants/research' in data['endpoints']
    assert '/health' in data['endpoints']


def test_health_endpoint(client):
    """test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200

    data = response.get_json()
    assert data['status'] == 'healthy'


def test_get_restaurants_missing_latitude(client):
    """test /restaurants endpoint with missing latitude."""
    response = client.get('/restaurants?longitude=-122.4194')
    assert response.status_code == 400

    data = response.get_json()
    assert data['status'] == 'error'
    assert 'latitude' in data['error'].lower()


def test_get_restaurants_missing_longitude(client):
    """test /restaurants endpoint with missing longitude."""
    response = client.get('/restaurants?latitude=37.7749')
    assert response.status_code == 400

    data = response.get_json()
    assert data['status'] == 'error'
    assert 'longitude' in data['error'].lower()


@patch('main.find_restaurants')
def test_get_restaurants_success(mock_find_restaurants, client):
    """test /restaurants endpoint with successful response."""
    mock_find_restaurants.return_value = {
        'status': 'success',
        'count': 2,
        'restaurants': [
            {
                'name': 'Test Restaurant 1',
                'latitude': 37.7749,
                'longitude': -122.4194,
                'distance_miles': 0.5,
                'cuisine': 'italian',
                'address': '123 Main St',
                'city': 'San Francisco',
                'amenity_type': 'restaurant'
            },
            {
                'name': 'Test Restaurant 2',
                'latitude': 37.7750,
                'longitude': -122.4195,
                'distance_miles': 1.0,
                'cuisine': 'Unknown',
                'address': 'Address not available',
                'city': '',
                'amenity_type': 'fast_food'
            }
        ]
    }

    response = client.get('/restaurants?latitude=37.7749&longitude=-122.4194&distance=5')
    assert response.status_code == 200

    data = response.get_json()
    assert data['total'] == 2
    assert len(data['restaurants']) == 2
    assert data['restaurants'][0]['name'] == 'Test Restaurant 1'
    assert data['restaurants'][0]['cuisine'] == ['italian']
    assert data['restaurants'][1]['cuisine'] == []  # Unknown cuisine becomes empty list


@patch('main.find_restaurants')
def test_get_restaurants_geo_error(mock_find_restaurants, client):
    """test /restaurants endpoint when geo agent returns error."""
    mock_find_restaurants.return_value = {
        'status': 'error',
        'error': 'Invalid coordinates'
    }

    response = client.get('/restaurants?latitude=100&longitude=200')
    assert response.status_code == 400

    data = response.get_json()
    assert data['status'] == 'error'


def test_research_endpoint_missing_latitude(client):
    """test /restaurants/research endpoint with missing latitude."""
    response = client.get('/restaurants/research?longitude=-122.4194')
    assert response.status_code == 400

    data = response.get_json()
    assert data['status'] == 'error'
    assert 'latitude' in data['error'].lower()


def test_research_endpoint_missing_longitude(client):
    """test /restaurants/research endpoint with missing longitude."""
    response = client.get('/restaurants/research?latitude=37.7749')
    assert response.status_code == 400

    data = response.get_json()
    assert data['status'] == 'error'
    assert 'longitude' in data['error'].lower()


@patch('main.research_restaurant')
@patch('main.find_restaurants')
def test_research_endpoint_success(mock_find_restaurants, mock_research_restaurant, client):
    """test /restaurants/research endpoint with successful response."""
    mock_find_restaurants.return_value = {
        'status': 'success',
        'count': 5,
        'restaurants': [
            {
                'name': f'Restaurant {i}',
                'latitude': 37.7749 + i * 0.001,
                'longitude': -122.4194,
                'distance_miles': i * 0.5,
                'cuisine': 'italian',
                'address': f'{i} Main St',
                'city': 'San Francisco',
                'amenity_type': 'restaurant'
            }
            for i in range(5)
        ]
    }

    mock_research_restaurant.return_value = {
        'status': 'success',
        'research_content': 'Detailed research content about the restaurant.',
        'citations': [{'title': 'Source 1', 'url': 'http://example.com'}],
        'reasoning_steps': ['Step 1', 'Step 2'],
        'timestamp': '2025-01-01T00:00:00Z'
    }

    response = client.get('/restaurants/research?latitude=37.7749&longitude=-122.4194&distance=5&limit=3')
    assert response.status_code == 200

    data = response.get_json()
    assert data['total_found'] == 5
    assert data['total_researched'] == 3
    assert len(data['restaurants_with_research']) == 3
    assert len(data['restaurants_without_research']) == 2

    # check first researched restaurant
    first = data['restaurants_with_research'][0]
    assert first['name'] == 'Restaurant 0'
    assert first['research']['status'] == 'success'
    assert first['research']['content'] == 'Detailed research content about the restaurant.'
    assert len(first['research']['citations']) == 1


@patch('main.research_restaurant')
@patch('main.find_restaurants')
def test_research_endpoint_default_limit(mock_find_restaurants, mock_research_restaurant, client):
    """test /restaurants/research endpoint uses default limit of 3."""
    mock_find_restaurants.return_value = {
        'status': 'success',
        'count': 10,
        'restaurants': [
            {
                'name': f'Restaurant {i}',
                'latitude': 37.7749,
                'longitude': -122.4194,
                'distance_miles': i * 0.5,
                'cuisine': 'italian',
                'address': f'{i} Main St',
                'city': 'San Francisco',
                'amenity_type': 'restaurant'
            }
            for i in range(10)
        ]
    }

    mock_research_restaurant.return_value = {
        'status': 'success',
        'research_content': 'Research content',
        'citations': [],
        'reasoning_steps': [],
        'timestamp': '2025-01-01T00:00:00Z'
    }

    response = client.get('/restaurants/research?latitude=37.7749&longitude=-122.4194')
    assert response.status_code == 200

    data = response.get_json()
    assert data['total_researched'] == 3  # default limit
    assert data['query']['research_limit'] == 3


@patch('main.research_restaurant')
@patch('main.find_restaurants')
def test_research_endpoint_limit_clamping(mock_find_restaurants, mock_research_restaurant, client):
    """test /restaurants/research endpoint clamps limit between 1 and 10."""
    mock_find_restaurants.return_value = {
        'status': 'success',
        'count': 15,
        'restaurants': [
            {
                'name': f'Restaurant {i}',
                'latitude': 37.7749,
                'longitude': -122.4194,
                'distance_miles': i * 0.5,
                'cuisine': 'italian',
                'address': f'{i} Main St',
                'city': 'San Francisco',
                'amenity_type': 'restaurant'
            }
            for i in range(15)
        ]
    }

    mock_research_restaurant.return_value = {
        'status': 'success',
        'research_content': 'Research content',
        'citations': [],
        'reasoning_steps': [],
        'timestamp': '2025-01-01T00:00:00Z'
    }

    # test limit too high
    response = client.get('/restaurants/research?latitude=37.7749&longitude=-122.4194&limit=20')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total_researched'] == 10  # clamped to max

    # test limit too low
    response = client.get('/restaurants/research?latitude=37.7749&longitude=-122.4194&limit=0')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total_researched'] == 1  # clamped to min


@patch('main.research_restaurant')
@patch('main.find_restaurants')
def test_research_endpoint_handles_research_failure(mock_find_restaurants, mock_research_restaurant, client):
    """test /restaurants/research endpoint when research fails."""
    mock_find_restaurants.return_value = {
        'status': 'success',
        'count': 2,
        'restaurants': [
            {
                'name': 'Restaurant 1',
                'latitude': 37.7749,
                'longitude': -122.4194,
                'distance_miles': 0.5,
                'cuisine': 'italian',
                'address': '123 Main St',
                'city': 'San Francisco',
                'amenity_type': 'restaurant'
            }
        ]
    }

    mock_research_restaurant.return_value = {
        'status': 'failed',
        'error': 'REKA_API_KEY not set',
        'timestamp': '2025-01-01T00:00:00Z'
    }

    response = client.get('/restaurants/research?latitude=37.7749&longitude=-122.4194&limit=1')
    assert response.status_code == 200

    data = response.get_json()
    assert data['total_researched'] == 1
    assert data['restaurants_with_research'][0]['research']['status'] == 'failed'
    assert data['restaurants_with_research'][0]['research']['error'] == 'REKA_API_KEY not set'


@patch('main.find_restaurants')
def test_research_endpoint_geo_error(mock_find_restaurants, client):
    """test /restaurants/research endpoint when geo agent returns error."""
    mock_find_restaurants.return_value = {
        'status': 'error',
        'error': 'Invalid coordinates'
    }

    response = client.get('/restaurants/research?latitude=100&longitude=200')
    assert response.status_code == 400

    data = response.get_json()
    assert data['status'] == 'error'
