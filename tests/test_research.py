"""tests for the research agent functionality."""

import pytest
from agents.research.research import (
    build_research_prompt,
    extract_location_context,
    research_restaurant
)


def test_build_research_prompt_full_data():
    """test prompt building with complete restaurant data."""
    restaurant = {
        'name': 'Test Restaurant',
        'address': '123 Main St',
        'city': 'San Francisco',
        'cuisine': 'Italian'
    }

    prompt = build_research_prompt(restaurant)

    assert 'Test Restaurant' in prompt
    assert '123 Main St' in prompt
    assert 'San Francisco' in prompt
    assert 'Menu & Cuisine' in prompt
    assert 'Pricing' in prompt
    assert 'Customer Experience' in prompt


def test_build_research_prompt_minimal_data():
    """test prompt building with minimal restaurant data."""
    restaurant = {
        'name': 'Minimal Restaurant'
    }

    prompt = build_research_prompt(restaurant)

    assert 'Minimal Restaurant' in prompt
    assert 'Menu & Cuisine' in prompt


def test_build_research_prompt_no_name():
    """test prompt building when restaurant has no name."""
    restaurant = {
        'address': '456 Oak Ave'
    }

    prompt = build_research_prompt(restaurant)

    assert 'Unknown Restaurant' in prompt
    assert '456 Oak Ave' in prompt


def test_extract_location_context_full_data():
    """test location context extraction with complete data."""
    restaurant = {
        'name': 'Pizza Place',
        'address': '789 Elm St',
        'city': 'Berkeley',
        'cuisine': 'Italian'
    }

    context = extract_location_context(restaurant)

    assert 'Pizza Place' in context
    assert '789 Elm St' in context
    assert 'Berkeley' in context
    assert 'Italian cuisine' in context


def test_extract_location_context_minimal_data():
    """test location context extraction with minimal data."""
    restaurant = {
        'name': 'Simple Cafe'
    }

    context = extract_location_context(restaurant)

    assert context == 'Simple Cafe'


def test_extract_location_context_unknown_cuisine():
    """test location context with unknown cuisine (should be excluded)."""
    restaurant = {
        'name': 'Generic Restaurant',
        'cuisine': 'Unknown'
    }

    context = extract_location_context(restaurant)

    assert 'Unknown' not in context
    assert 'Generic Restaurant' in context


def test_extract_location_context_empty():
    """test location context with empty restaurant dict."""
    restaurant = {}

    context = extract_location_context(restaurant)

    assert context == 'Unknown Location'


def test_research_restaurant_no_api_key(monkeypatch):
    """test research function when api key is not set."""
    # ensure REKA_API_KEY is not set
    monkeypatch.delenv('REKA_API_KEY', raising=False)

    restaurant = {
        'id': '1',
        'name': 'Test Restaurant'
    }

    result = research_restaurant(restaurant, api_key=None)

    assert result['status'] == 'failed'
    assert 'REKA_API_KEY not set' in result['error']
    assert result['restaurant_id'] == '1'
    assert result['restaurant_name'] == 'Test Restaurant'


def test_research_restaurant_no_name():
    """test research function when restaurant has no name."""
    restaurant = {
        'id': '2',
        'address': '123 Test St'
    }

    result = research_restaurant(restaurant, api_key='fake_key')

    assert result['status'] == 'failed'
    assert 'restaurant name is required' in result['error']
    assert result['restaurant_id'] == '2'


def test_research_restaurant_missing_id():
    """test research function when restaurant has no id."""
    restaurant = {
        'name': 'No ID Restaurant'
    }

    result = research_restaurant(restaurant, api_key='fake_key')

    assert result['restaurant_id'] == 'unknown'
    assert result['restaurant_name'] == 'No ID Restaurant'
