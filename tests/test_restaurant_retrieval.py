"""
tests for restaurant retrieval module.

this test suite covers:
- coordinate validation
- query construction
- caching mechanism
- bright data api integration
- error handling
- data parsing and structure
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

# adjust import path based on project structure
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers.restaurants.restaurant_retrieval import (
    retrieve_restaurants,
    _validate_coordinates,
    _construct_query,
    _get_cache_key,
    _check_cache,
    _save_to_cache,
    _parse_restaurant_data
)


class TestCoordinateValidation:
    """test coordinate validation logic."""

    def test_valid_coordinates(self):
        """test that valid coordinates pass validation."""
        assert _validate_coordinates(37.7749, -122.4194) is True
        assert _validate_coordinates(0.0, 0.0) is True
        assert _validate_coordinates(90.0, 180.0) is True
        assert _validate_coordinates(-90.0, -180.0) is True

    def test_invalid_latitude(self):
        """test that invalid latitude raises error."""
        with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
            _validate_coordinates(91.0, 0.0)

        with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
            _validate_coordinates(-91.0, 0.0)

    def test_invalid_longitude(self):
        """test that invalid longitude raises error."""
        with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
            _validate_coordinates(0.0, 181.0)

        with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
            _validate_coordinates(0.0, -181.0)

    def test_non_numeric_coordinates(self):
        """test that non-numeric coordinates raise error."""
        with pytest.raises(TypeError):
            _validate_coordinates("37.7749", -122.4194)

        with pytest.raises(TypeError):
            _validate_coordinates(37.7749, "invalid")


class TestQueryConstruction:
    """test query construction logic."""

    def test_default_query(self):
        """test default query construction."""
        query = _construct_query(37.7749, -122.4194, None)
        assert query == "restaurants near 37.7749, -122.4194"

    def test_custom_query(self):
        """test custom query override."""
        custom = "italian restaurants in san francisco"
        query = _construct_query(37.7749, -122.4194, custom)
        assert query == custom

    def test_query_with_zero_coordinates(self):
        """test query construction with zero coordinates."""
        query = _construct_query(0.0, 0.0, None)
        assert query == "restaurants near 0.0, 0.0"


class TestCachingMechanism:
    """test caching functionality."""

    @pytest.fixture
    def cache_dir(self, tmp_path):
        """create temporary cache directory."""
        cache = tmp_path / ".cache"
        cache.mkdir()
        return cache

    def test_cache_key_generation(self):
        """test cache key generation is consistent."""
        key1 = _get_cache_key(37.7749, -122.4194, "test query")
        key2 = _get_cache_key(37.7749, -122.4194, "test query")
        assert key1 == key2

        key3 = _get_cache_key(37.7749, -122.4194, "different query")
        assert key1 != key3

    def test_cache_miss(self, cache_dir):
        """test cache miss returns none."""
        with patch('helpers.restaurants.restaurant_retrieval.CACHE_DIR', cache_dir):
            result = _check_cache(37.7749, -122.4194, "test query")
            assert result is None

    def test_cache_hit_valid(self, cache_dir):
        """test cache hit with valid (non-expired) data."""
        cache_key = _get_cache_key(37.7749, -122.4194, "test query")
        cache_file = cache_dir / f"{cache_key}.json"

        test_data = {
            "cached_at": datetime.now().isoformat(),
            "data": {"restaurants": [{"name": "test restaurant"}]}
        }

        cache_file.write_text(json.dumps(test_data))

        with patch('helpers.restaurants.restaurant_retrieval.CACHE_DIR', cache_dir):
            result = _check_cache(37.7749, -122.4194, "test query")
            assert result is not None
            assert result["data"]["restaurants"][0]["name"] == "test restaurant"

    def test_cache_hit_expired(self, cache_dir):
        """test cache hit with expired data returns none."""
        cache_key = _get_cache_key(37.7749, -122.4194, "test query")
        cache_file = cache_dir / f"{cache_key}.json"

        # create cache entry from 25 hours ago
        expired_time = datetime.now() - timedelta(hours=25)
        test_data = {
            "cached_at": expired_time.isoformat(),
            "data": {"restaurants": [{"name": "old restaurant"}]}
        }

        cache_file.write_text(json.dumps(test_data))

        with patch('helpers.restaurants.restaurant_retrieval.CACHE_DIR', cache_dir):
            result = _check_cache(37.7749, -122.4194, "test query")
            assert result is None

    def test_save_to_cache(self, cache_dir):
        """test saving data to cache."""
        test_data = {"restaurants": [{"name": "new restaurant"}]}

        with patch('helpers.restaurants.restaurant_retrieval.CACHE_DIR', cache_dir):
            _save_to_cache(37.7749, -122.4194, "test query", test_data)

            cache_key = _get_cache_key(37.7749, -122.4194, "test query")
            cache_file = cache_dir / f"{cache_key}.json"

            assert cache_file.exists()
            cached_data = json.loads(cache_file.read_text())
            assert "cached_at" in cached_data
            assert cached_data["data"] == test_data


class TestBrightDataIntegration:
    """test bright data api integration."""

    @pytest.fixture
    def mock_bright_data_response(self) -> Dict[str, Any]:
        """mock bright data api response."""
        return {
            "results": [
                {
                    "name": "test restaurant 1",
                    "address": "123 main st, san francisco, ca",
                    "rating": 4.5,
                    "reviews_count": 234,
                    "price_level": "$$",
                    "type": "italian",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "place_id": "ChIJtest123",
                    "phone": "+1-415-555-0100"
                },
                {
                    "name": "test restaurant 2",
                    "address": "456 oak ave, san francisco, ca",
                    "rating": 4.2,
                    "reviews_count": 156,
                    "price_level": "$$$",
                    "type": "japanese",
                    "latitude": 37.7750,
                    "longitude": -122.4195,
                    "place_id": "ChIJtest456",
                    "phone": "+1-415-555-0200"
                }
            ]
        }

    @patch('helpers.restaurants.restaurant_retrieval.requests.post')
    def test_successful_api_call(self, mock_post, mock_bright_data_response):
        """test successful bright data api call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_bright_data_response
        mock_post.return_value = mock_response

        result = retrieve_restaurants(37.7749, -122.4194)

        assert result["total_results"] == 2
        assert len(result["restaurants"]) == 2
        assert result["restaurants"][0]["name"] == "test restaurant 1"
        assert result["cached"] is False

    @patch('helpers.restaurants.restaurant_retrieval.requests.post')
    def test_api_failure_handling(self, mock_post):
        """test api failure is handled gracefully."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("api error")
        mock_post.return_value = mock_response

        result = retrieve_restaurants(37.7749, -122.4194)

        assert "error" in result
        assert result["total_results"] == 0
        assert result["restaurants"] == []

    @patch('helpers.restaurants.restaurant_retrieval.requests.post')
    def test_api_timeout_handling(self, mock_post):
        """test api timeout is handled gracefully."""
        mock_post.side_effect = Exception("timeout error")

        result = retrieve_restaurants(37.7749, -122.4194)

        assert "error" in result
        assert result["total_results"] == 0


class TestDataParsing:
    """test restaurant data parsing."""

    def test_parse_complete_data(self):
        """test parsing complete restaurant data."""
        raw_data = {
            "name": "test restaurant",
            "address": "123 main st",
            "rating": 4.5,
            "reviews_count": 234,
            "price_level": "$$",
            "type": "italian",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "place_id": "ChIJtest123",
            "phone": "+1-415-555-0100"
        }

        parsed = _parse_restaurant_data(raw_data)

        assert parsed["name"] == "test restaurant"
        assert parsed["rating"] == 4.5
        assert parsed["coordinates"]["lat"] == 37.7749
        assert parsed["coordinates"]["lng"] == -122.4194

    def test_parse_incomplete_data(self):
        """test parsing incomplete restaurant data with defaults."""
        raw_data = {
            "name": "minimal restaurant",
            "latitude": 37.7749,
            "longitude": -122.4194
        }

        parsed = _parse_restaurant_data(raw_data)

        assert parsed["name"] == "minimal restaurant"
        assert parsed["rating"] is None
        assert parsed["phone"] is None
        assert parsed["coordinates"]["lat"] == 37.7749


class TestEndToEnd:
    """end-to-end integration tests."""

    @patch('helpers.restaurants.restaurant_retrieval.requests.post')
    def test_retrieve_with_custom_query(self, mock_post):
        """test retrieval with custom query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        custom_query = "pizza places near me"
        result = retrieve_restaurants(
            37.7749,
            -122.4194,
            query=custom_query
        )

        assert result["query"] == custom_query

    @patch('helpers.restaurants.restaurant_retrieval.requests.post')
    def test_retrieve_with_max_results(self, mock_post):
        """test retrieval with max results limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        # create 30 mock results
        mock_results = [
            {"name": f"restaurant {i}", "latitude": 37.77, "longitude": -122.41}
            for i in range(30)
        ]
        mock_response.json.return_value = {"results": mock_results}
        mock_post.return_value = mock_response

        result = retrieve_restaurants(
            37.7749,
            -122.4194,
            max_results=10
        )

        # should be limited to max_results
        assert len(result["restaurants"]) <= 10

    def test_retrieve_with_cache(self, tmp_path):
        """test retrieval uses cache when available."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()

        # pre-populate cache
        cached_data = {
            "query": "test query",
            "total_results": 1,
            "restaurants": [{"name": "cached restaurant"}],
            "cached": True
        }

        with patch('helpers.restaurants.restaurant_retrieval.CACHE_DIR', cache_dir):
            _save_to_cache(37.7749, -122.4194, "test query", cached_data)

            # should return cached data without api call
            result = retrieve_restaurants(37.7749, -122.4194, query="test query")

            assert result["cached"] is True
            assert result["restaurants"][0]["name"] == "cached restaurant"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
