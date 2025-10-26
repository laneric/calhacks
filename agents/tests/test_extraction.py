"""tests for extraction agent."""

import pytest
import os
import json
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, MagicMock

from agents.extraction.extraction_cache import ExtractionCache, ExtractionCacheEntry
from agents.extraction.extraction import (
    RestaurantInfo,
    build_extraction_prompt,
    extract_restaurant_info,
    batch_extract_restaurant_info
)
from agents.scraping.restaurant_discovery import RestaurantIdentifier


class TestExtractionCacheEntry:
    """tests for ExtractionCacheEntry class."""

    def test_cache_entry_creation(self):
        """test creating cache entry."""
        entry = ExtractionCacheEntry(
            restaurant_name="Test Restaurant",
            source="combined",
            extracted_at="2025-01-01T00:00:00+00:00",
            data_hash="abc123",
            ttl_days=30
        )

        assert entry.restaurant_name == "Test Restaurant"
        assert entry.source == "combined"
        assert entry.ttl_days == 30

    def test_cache_entry_to_dict(self):
        """test converting cache entry to dict."""
        entry = ExtractionCacheEntry(
            restaurant_name="Test Restaurant",
            source="combined",
            extracted_at="2025-01-01T00:00:00+00:00",
            data_hash="abc123"
        )

        data = entry.to_dict()
        assert data['restaurant_name'] == "Test Restaurant"
        assert data['source'] == "combined"
        assert data['data_hash'] == "abc123"

    def test_cache_entry_from_dict(self):
        """test creating cache entry from dict."""
        data = {
            "restaurant_name": "Test Restaurant",
            "source": "yelp",
            "extracted_at": "2025-01-01T00:00:00+00:00",
            "data_hash": "abc123",
            "ttl_days": 30
        }

        entry = ExtractionCacheEntry.from_dict(data)
        assert entry.restaurant_name == "Test Restaurant"
        assert entry.source == "yelp"

    def test_cache_entry_is_valid(self):
        """test cache entry validity check."""
        # create recent entry
        recent_time = datetime.now(UTC).isoformat()
        entry = ExtractionCacheEntry(
            restaurant_name="Test",
            source="combined",
            extracted_at=recent_time,
            data_hash="abc",
            ttl_days=30
        )

        assert entry.is_valid() is True

    def test_cache_entry_is_expired(self):
        """test expired cache entry."""
        # create old entry (40 days ago)
        old_time = (datetime.now(UTC) - timedelta(days=40)).isoformat()
        entry = ExtractionCacheEntry(
            restaurant_name="Test",
            source="combined",
            extracted_at=old_time,
            data_hash="abc",
            ttl_days=30
        )

        assert entry.is_valid() is False


class TestExtractionCache:
    """tests for ExtractionCache class."""

    @pytest.fixture
    def temp_cache_file(self, tmp_path):
        """create temporary cache file."""
        return str(tmp_path / "test_extraction_cache.json")

    def test_cache_initialization(self, temp_cache_file):
        """test cache initialization."""
        cache = ExtractionCache(cache_file=temp_cache_file)
        assert cache.cache_file == temp_cache_file
        assert isinstance(cache.cache, dict)

    def test_cache_set_and_get(self, temp_cache_file):
        """test setting and getting cache entries."""
        cache = ExtractionCache(cache_file=temp_cache_file)

        cache.set(
            restaurant_name="Test Restaurant",
            source="combined",
            extracted_at=datetime.now(UTC).isoformat(),
            data_hash="abc123",
            extraction_data={"cuisine": ["Italian"]}
        )

        entry = cache.get("Test Restaurant", "combined")
        assert entry is not None
        assert entry.restaurant_name == "Test Restaurant"
        assert entry.extraction_data['cuisine'] == ["Italian"]

    def test_cache_miss(self, temp_cache_file):
        """test cache miss."""
        cache = ExtractionCache(cache_file=temp_cache_file)
        entry = cache.get("Nonexistent Restaurant", "combined")
        assert entry is None

    def test_cache_remove(self, temp_cache_file):
        """test removing cache entry."""
        cache = ExtractionCache(cache_file=temp_cache_file)

        cache.set(
            restaurant_name="Test",
            source="combined",
            extracted_at=datetime.now(UTC).isoformat(),
            data_hash="abc"
        )

        cache.remove("Test", "combined")
        entry = cache.get("Test", "combined")
        assert entry is None

    def test_cache_cleanup_expired(self, temp_cache_file):
        """test cleaning up expired entries."""
        cache = ExtractionCache(cache_file=temp_cache_file)

        # add expired entry
        old_time = (datetime.now(UTC) - timedelta(days=40)).isoformat()
        cache.set(
            restaurant_name="Old Restaurant",
            source="combined",
            extracted_at=old_time,
            data_hash="old"
        )

        # add valid entry
        cache.set(
            restaurant_name="New Restaurant",
            source="combined",
            extracted_at=datetime.now(UTC).isoformat(),
            data_hash="new"
        )

        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("New Restaurant", "combined") is not None
        assert cache.get("Old Restaurant", "combined") is None

    def test_cache_get_stats(self, temp_cache_file):
        """test getting cache statistics."""
        cache = ExtractionCache(cache_file=temp_cache_file)

        cache.set(
            restaurant_name="Test1",
            source="combined",
            extracted_at=datetime.now(UTC).isoformat(),
            data_hash="abc"
        )

        cache.set(
            restaurant_name="Test2",
            source="yelp",
            extracted_at=datetime.now(UTC).isoformat(),
            data_hash="def"
        )

        stats = cache.get_stats()
        assert stats['total_entries'] == 2
        assert stats['valid_entries'] == 2


class TestRestaurantInfo:
    """tests for RestaurantInfo dataclass."""

    def test_restaurant_info_creation(self):
        """test creating RestaurantInfo object."""
        info = RestaurantInfo(
            restaurant_name="Test Restaurant",
            cuisine=["Italian", "Pizza"],
            popular_dishes=["Margherita Pizza"],
            common_allergens=["Gluten", "Dairy"],
            price_range="$$",
            number_of_reviews=100,
            average_stars=4.5,
            hours="11am-10pm",
            dietary_options=["Vegetarian"],
            ambiance="Casual",
            reservations_required=False,
            extraction_source="combined",
            extracted_at="2025-01-01T00:00:00+00:00",
            status="success"
        )

        assert info.restaurant_name == "Test Restaurant"
        assert info.cuisine == ["Italian", "Pizza"]
        assert info.price_range == "$$"
        assert info.status == "success"

    def test_restaurant_info_to_dict(self):
        """test converting RestaurantInfo to dict."""
        info = RestaurantInfo(
            restaurant_name="Test",
            cuisine=["Italian"],
            popular_dishes=[],
            common_allergens=[],
            price_range="$",
            number_of_reviews=None,
            average_stars=None,
            hours=None,
            dietary_options=[],
            ambiance=None,
            reservations_required=None,
            extraction_source="geo_only",
            extracted_at="2025-01-01T00:00:00+00:00",
            status="partial",
            error="test error"
        )

        data = info.to_dict()
        assert data['restaurant_name'] == "Test"
        assert data['status'] == "partial"
        assert data['error'] == "test error"


class TestBuildExtractionPrompt:
    """tests for build_extraction_prompt function."""

    def test_build_prompt_with_yelp_data(self):
        """test building prompt with yelp data."""
        scraped_data = {
            'yelp': {
                'name': 'Test Restaurant',
                'rating': 4.5,
                'review_count': 100
            }
        }

        prompt = build_extraction_prompt("Test Restaurant", scraped_data)
        assert "Test Restaurant" in prompt
        assert "YELP DATA" in prompt
        assert "extract the following fields" in prompt

    def test_build_prompt_with_combined_data(self):
        """test building prompt with yelp and opentable data."""
        scraped_data = {
            'yelp': {'name': 'Test', 'rating': 4.5},
            'opentable': {'name': 'Test', 'price_tier': 3}
        }

        prompt = build_extraction_prompt("Test", scraped_data)
        assert "YELP DATA" in prompt
        assert "OPENTABLE DATA" in prompt

    def test_build_prompt_with_geo_fallback(self):
        """test building prompt with geo data fallback."""
        scraped_data = {}
        geo_data = {'name': 'Test', 'cuisine': 'Italian'}

        prompt = build_extraction_prompt("Test", scraped_data, geo_data)
        assert "GEO DATA (FALLBACK)" in prompt
        assert "Italian" in prompt


class TestExtractRestaurantInfo:
    """tests for extract_restaurant_info function."""

    def test_extract_no_api_key(self, tmp_path):
        """test extraction without api key."""
        cache_file = str(tmp_path / "test_cache.json")

        with patch.dict(os.environ, {}, clear=True):
            result = extract_restaurant_info(
                restaurant_name="Test",
                cache=ExtractionCache(cache_file=cache_file)
            )

            assert result.status == "failed"
            assert "ANTHROPIC_API_KEY" in result.error

    def test_extract_no_data(self, tmp_path):
        """test extraction with no data available."""
        cache_file = str(tmp_path / "test_cache.json")

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            result = extract_restaurant_info(
                restaurant_name="Test",
                identifier=None,
                geo_data=None,
                cache=ExtractionCache(cache_file=cache_file)
            )

            assert result.status == "failed"
            assert "no data available" in result.error

    def test_extract_with_cached_data(self, tmp_path):
        """test extraction using cached data."""
        cache_file = str(tmp_path / "test_cache.json")
        cache = ExtractionCache(cache_file=cache_file)

        # set cache entry
        cached_info = {
            "restaurant_name": "Test",
            "cuisine": ["Italian"],
            "popular_dishes": [],
            "common_allergens": [],
            "price_range": "$$",
            "number_of_reviews": 100,
            "average_stars": 4.5,
            "hours": None,
            "dietary_options": [],
            "ambiance": None,
            "reservations_required": None,
            "extraction_source": "combined",
            "extracted_at": datetime.now(UTC).isoformat(),
            "status": "success",
            "error": None
        }

        cache.set(
            restaurant_name="Test",
            source="combined",
            extracted_at=datetime.now(UTC).isoformat(),
            data_hash="abc123",
            extraction_data=cached_info
        )

        result = extract_restaurant_info(
            restaurant_name="Test",
            cache=cache,
            use_cache=True
        )

        assert result.status == "success"
        assert result.restaurant_name == "Test"
        assert result.cuisine == ["Italian"]

    @patch('agents.extraction.extraction.Anthropic')
    def test_extract_with_mock_claude(self, mock_anthropic, tmp_path):
        """test extraction with mocked claude api."""
        cache_file = str(tmp_path / "test_cache.json")

        # mock claude response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = """{
            "cuisine": ["Italian", "Pizza"],
            "popular_dishes": ["Margherita Pizza", "Pepperoni"],
            "common_allergens": ["Gluten", "Dairy"],
            "price_range": "$$",
            "number_of_reviews": 150,
            "average_stars": 4.5,
            "hours": "11am-10pm",
            "dietary_options": ["Vegetarian", "Vegan"],
            "ambiance": "Casual",
            "reservations_required": false
        }"""

        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        geo_data = {'name': 'Test Pizza', 'cuisine': 'Italian'}

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            result = extract_restaurant_info(
                restaurant_name="Test Pizza",
                geo_data=geo_data,
                cache=ExtractionCache(cache_file=cache_file),
                use_cache=False
            )

            assert result.status == "success"
            assert result.cuisine == ["Italian", "Pizza"]
            assert result.price_range == "$$"
            assert result.average_stars == 4.5
            assert result.popular_dishes == ["Margherita Pizza", "Pepperoni"]


class TestBatchExtractRestaurantInfo:
    """tests for batch_extract_restaurant_info function."""

    @patch('agents.extraction.extraction.Anthropic')
    def test_batch_extract_multiple_restaurants(self, mock_anthropic, tmp_path):
        """test batch extraction for multiple restaurants."""
        cache_file = str(tmp_path / "test_cache.json")

        # mock claude response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = """{
            "cuisine": ["Italian"],
            "popular_dishes": ["Pizza"],
            "common_allergens": ["Gluten"],
            "price_range": "$",
            "number_of_reviews": 50,
            "average_stars": 4.0,
            "hours": null,
            "dietary_options": [],
            "ambiance": null,
            "reservations_required": null
        }"""

        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        restaurants = [
            {
                'name': 'Restaurant 1',
                'geo_data': {'cuisine': 'Italian'}
            },
            {
                'name': 'Restaurant 2',
                'geo_data': {'cuisine': 'Mexican'}
            }
        ]

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            results = batch_extract_restaurant_info(
                restaurants=restaurants,
                cache=ExtractionCache(cache_file=cache_file),
                use_cache=False
            )

            assert len(results) == 2
            assert results[0].restaurant_name == 'Restaurant 1'
            assert results[1].restaurant_name == 'Restaurant 2'

    def test_batch_extract_handles_errors(self, tmp_path):
        """test batch extraction handles individual errors."""
        cache_file = str(tmp_path / "test_cache.json")

        restaurants = [
            {'name': 'Restaurant 1'},
            {'name': 'Restaurant 2'}
        ]

        with patch.dict(os.environ, {}, clear=True):
            results = batch_extract_restaurant_info(
                restaurants=restaurants,
                cache=ExtractionCache(cache_file=cache_file)
            )

            assert len(results) == 2
            assert results[0].status == "failed"
            assert results[1].status == "failed"
