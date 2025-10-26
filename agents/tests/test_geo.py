"""tests for the geo agent functionality."""

import pytest
from unittest.mock import patch, Mock
from agents.geo.geo import (
    miles_to_meters,
    haversine_distance,
    validate_coordinates,
    query_overpass_api,
    find_restaurants
)


def test_miles_to_meters():
    """test miles to meters conversion."""
    assert miles_to_meters(1) == 1609.34
    assert miles_to_meters(5) == 8046.7
    assert miles_to_meters(0) == 0
    assert miles_to_meters(10) == 16093.4


def test_haversine_distance_same_point():
    """test haversine distance for same coordinates."""
    distance = haversine_distance(37.7749, -122.4194, 37.7749, -122.4194)
    assert distance == 0


def test_haversine_distance_known_distance():
    """test haversine distance with known coordinates."""
    # san francisco to berkeley (approx 11 miles)
    sf_lat, sf_lon = 37.7749, -122.4194
    berkeley_lat, berkeley_lon = 37.8715, -122.2730

    distance = haversine_distance(sf_lat, sf_lon, berkeley_lat, berkeley_lon)

    # should be around 11 miles (with some tolerance)
    assert 10 < distance < 12


def test_haversine_distance_cross_equator():
    """test haversine distance across equator."""
    # test north and south of equator
    distance = haversine_distance(10, 0, -10, 0)
    assert distance > 0


def test_validate_coordinates_valid():
    """test coordinate validation with valid coordinates."""
    assert validate_coordinates(0, 0) is True
    assert validate_coordinates(37.7749, -122.4194) is True
    assert validate_coordinates(90, 180) is True
    assert validate_coordinates(-90, -180) is True
    assert validate_coordinates(45.5, 123.4) is True


def test_validate_coordinates_invalid_latitude():
    """test coordinate validation with invalid latitude."""
    assert validate_coordinates(91, 0) is False
    assert validate_coordinates(-91, 0) is False
    assert validate_coordinates(100, 50) is False


def test_validate_coordinates_invalid_longitude():
    """test coordinate validation with invalid longitude."""
    assert validate_coordinates(0, 181) is False
    assert validate_coordinates(0, -181) is False
    assert validate_coordinates(50, 200) is False


def test_validate_coordinates_both_invalid():
    """test coordinate validation with both invalid."""
    assert validate_coordinates(100, 200) is False
    assert validate_coordinates(-100, -200) is False


@patch('agents.geo.geo.requests.post')
def test_query_overpass_api_success(mock_post):
    """test overpass api query with successful response."""
    mock_response = Mock()
    mock_response.json.return_value = {
        'elements': [
            {
                'lat': 37.7749,
                'lon': -122.4194,
                'tags': {
                    'name': 'Test Restaurant',
                    'amenity': 'restaurant',
                    'cuisine': 'italian'
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    results = query_overpass_api(37.7749, -122.4194, 1000)

    assert len(results) == 1
    assert results[0]['tags']['name'] == 'Test Restaurant'
    mock_post.assert_called_once()


@patch('agents.geo.geo.requests.post')
def test_query_overpass_api_empty_results(mock_post):
    """test overpass api query with no results."""
    mock_response = Mock()
    mock_response.json.return_value = {'elements': []}
    mock_post.return_value = mock_response

    results = query_overpass_api(37.7749, -122.4194, 1000)

    assert results == []


@patch('agents.geo.geo.requests.post')
def test_query_overpass_api_missing_elements(mock_post):
    """test overpass api query with missing elements key."""
    mock_response = Mock()
    mock_response.json.return_value = {}
    mock_post.return_value = mock_response

    results = query_overpass_api(37.7749, -122.4194, 1000)

    assert results == []


def test_find_restaurants_invalid_latitude():
    """test find_restaurants with invalid latitude."""
    result = find_restaurants(91, -122.4194)

    assert result['status'] == 'error'
    assert 'Invalid coordinates' in result['error']


def test_find_restaurants_invalid_longitude():
    """test find_restaurants with invalid longitude."""
    result = find_restaurants(37.7749, 200)

    assert result['status'] == 'error'
    assert 'Invalid coordinates' in result['error']


def test_find_restaurants_invalid_distance():
    """test find_restaurants with invalid distance."""
    result = find_restaurants(37.7749, -122.4194, distance=0)

    assert result['status'] == 'error'
    assert 'Distance must be greater than 0' in result['error']


def test_find_restaurants_negative_distance():
    """test find_restaurants with negative distance."""
    result = find_restaurants(37.7749, -122.4194, distance=-5)

    assert result['status'] == 'error'
    assert 'Distance must be greater than 0' in result['error']


@patch('agents.geo.geo.query_overpass_api')
def test_find_restaurants_success(mock_query):
    """test find_restaurants with successful api response."""
    mock_query.return_value = [
        {
            'lat': 37.7749,
            'lon': -122.4194,
            'tags': {
                'name': 'Restaurant 1',
                'amenity': 'restaurant',
                'cuisine': 'italian',
                'addr:street': 'Main St',
                'addr:city': 'San Francisco'
            }
        },
        {
            'lat': 37.7750,
            'lon': -122.4195,
            'tags': {
                'name': 'Restaurant 2',
                'amenity': 'fast_food',
                'cuisine': 'mexican',
                'addr:street': 'Oak St',
                'addr:city': 'San Francisco'
            }
        }
    ]

    result = find_restaurants(37.7749, -122.4194, distance=5)

    assert result['status'] == 'success'
    assert result['count'] == 2
    assert len(result['restaurants']) == 2
    assert result['restaurants'][0]['name'] == 'Restaurant 1'
    assert result['restaurants'][1]['name'] == 'Restaurant 2'
    assert result['query']['latitude'] == 37.7749
    assert result['query']['longitude'] == -122.4194


@patch('agents.geo.geo.query_overpass_api')
def test_find_restaurants_filters_out_of_range(mock_query):
    """test that restaurants beyond exact radius are filtered out."""
    mock_query.return_value = [
        {
            'lat': 37.7749,
            'lon': -122.4194,
            'tags': {'name': 'Nearby Restaurant', 'amenity': 'restaurant'}
        },
        {
            # very far away
            'lat': 40.7128,
            'lon': -74.0060,
            'tags': {'name': 'Far Restaurant', 'amenity': 'restaurant'}
        }
    ]

    result = find_restaurants(37.7749, -122.4194, distance=5)

    assert result['status'] == 'success'
    assert result['count'] == 1
    assert result['restaurants'][0]['name'] == 'Nearby Restaurant'


@patch('agents.geo.geo.query_overpass_api')
def test_find_restaurants_missing_coordinates(mock_query):
    """test restaurants with missing coordinates are skipped."""
    mock_query.return_value = [
        {
            'lat': 37.7749,
            'lon': -122.4194,
            'tags': {'name': 'Valid Restaurant', 'amenity': 'restaurant'}
        },
        {
            'tags': {'name': 'Missing Coords', 'amenity': 'restaurant'}
        },
        {
            'lat': 37.7750,
            'tags': {'name': 'Missing Lon', 'amenity': 'restaurant'}
        }
    ]

    result = find_restaurants(37.7749, -122.4194, distance=5)

    assert result['status'] == 'success'
    assert result['count'] == 1
    assert result['restaurants'][0]['name'] == 'Valid Restaurant'


@patch('agents.geo.geo.query_overpass_api')
def test_find_restaurants_unnamed_restaurant(mock_query):
    """test restaurants without names get default name."""
    mock_query.return_value = [
        {
            'lat': 37.7749,
            'lon': -122.4194,
            'tags': {'amenity': 'restaurant'}
        }
    ]

    result = find_restaurants(37.7749, -122.4194, distance=5)

    assert result['status'] == 'success'
    assert result['restaurants'][0]['name'] == 'Unnamed Restaurant'


@patch('agents.geo.geo.query_overpass_api')
def test_find_restaurants_unknown_cuisine(mock_query):
    """test restaurants without cuisine get 'Unknown'."""
    mock_query.return_value = [
        {
            'lat': 37.7749,
            'lon': -122.4194,
            'tags': {'name': 'Mystery Food', 'amenity': 'restaurant'}
        }
    ]

    result = find_restaurants(37.7749, -122.4194, distance=5)

    assert result['status'] == 'success'
    assert result['restaurants'][0]['cuisine'] == 'Unknown'


@patch('agents.geo.geo.query_overpass_api')
def test_find_restaurants_sorted_by_distance(mock_query):
    """test that restaurants are sorted by distance."""
    mock_query.return_value = [
        {
            'lat': 37.7800,
            'lon': -122.4194,
            'tags': {'name': 'Far Restaurant', 'amenity': 'restaurant'}
        },
        {
            'lat': 37.7749,
            'lon': -122.4194,
            'tags': {'name': 'Near Restaurant', 'amenity': 'restaurant'}
        },
        {
            'lat': 37.7760,
            'lon': -122.4194,
            'tags': {'name': 'Mid Restaurant', 'amenity': 'restaurant'}
        }
    ]

    result = find_restaurants(37.7749, -122.4194, distance=10)

    assert result['status'] == 'success'
    assert result['restaurants'][0]['name'] == 'Near Restaurant'
    assert result['restaurants'][0]['distance_miles'] == 0
    assert result['restaurants'][1]['distance_miles'] < result['restaurants'][2]['distance_miles']


@patch('agents.geo.geo.query_overpass_api')
def test_find_restaurants_api_error(mock_query):
    """test find_restaurants when api raises exception."""
    mock_query.side_effect = Exception('API connection failed')

    result = find_restaurants(37.7749, -122.4194, distance=5)

    assert result['status'] == 'error'
    assert 'Unexpected error' in result['error']
