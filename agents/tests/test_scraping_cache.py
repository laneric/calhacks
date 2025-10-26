"""tests for scraping cache system."""

import pytest
import json
import os
import tempfile
from datetime import datetime, timedelta, UTC
from agents.scraping.scraping_cache import ScrapingCache, ScrapingCacheEntry


class TestScrapingCacheEntry:
    """test suite for ScrapingCacheEntry."""

    def test_cache_entry_creation(self):
        """test cache entry initialization.

        args:
            None

        returns:
            None
        """
        entry = ScrapingCacheEntry(
            restaurant_name="Test Restaurant",
            source="yelp",
            menu_url="https://yelp.com/test",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="abc123",
            ttl_days=7
        )

        assert entry.restaurant_name == "Test Restaurant"
        assert entry.source == "yelp"
        assert entry.ttl_days == 7

    def test_cache_entry_to_dict(self):
        """test cache entry serialization.

        args:
            None

        returns:
            None
        """
        entry = ScrapingCacheEntry(
            restaurant_name="Test Restaurant",
            source="yelp",
            menu_url="https://yelp.com/test",
            scraped_at="2025-01-01T00:00:00Z",
            menu_hash="abc123"
        )

        data = entry.to_dict()
        assert data["restaurant_name"] == "Test Restaurant"
        assert data["source"] == "yelp"
        assert data["menu_hash"] == "abc123"

    def test_cache_entry_from_dict(self):
        """test cache entry deserialization.

        args:
            None

        returns:
            None
        """
        data = {
            "restaurant_name": "Test Restaurant",
            "source": "opentable",
            "menu_url": "https://opentable.com/test",
            "scraped_at": "2025-01-01T00:00:00Z",
            "menu_hash": "xyz789",
            "ttl_days": 14,
            "file_path": "/path/to/file.json"
        }

        entry = ScrapingCacheEntry.from_dict(data)
        assert entry.restaurant_name == "Test Restaurant"
        assert entry.source == "opentable"
        assert entry.ttl_days == 14

    def test_cache_entry_is_valid_fresh(self):
        """test cache entry validity when fresh.

        args:
            None

        returns:
            None
        """
        # entry from 1 day ago with 7 day TTL
        scraped_at = datetime.now(UTC) - timedelta(days=1)
        entry = ScrapingCacheEntry(
            restaurant_name="Test",
            source="yelp",
            menu_url="url",
            scraped_at=scraped_at.isoformat(),
            menu_hash="hash",
            ttl_days=7
        )

        assert entry.is_valid() is True

    def test_cache_entry_is_valid_expired(self):
        """test cache entry validity when expired.

        args:
            None

        returns:
            None
        """
        # entry from 10 days ago with 7 day TTL
        scraped_at = datetime.now(UTC) - timedelta(days=10)
        entry = ScrapingCacheEntry(
            restaurant_name="Test",
            source="yelp",
            menu_url="url",
            scraped_at=scraped_at.isoformat(),
            menu_hash="hash",
            ttl_days=7
        )

        assert entry.is_valid() is False


class TestScrapingCache:
    """test suite for ScrapingCache."""

    @pytest.fixture
    def temp_cache_file(self):
        """create temporary cache file for testing.

        args:
            None

        returns:
            path to temporary file
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".json"
        ) as f:
            filepath = f.name
        yield filepath
        if os.path.exists(filepath):
            os.remove(filepath)

    def test_cache_initialization(self, temp_cache_file):
        """test cache initialization.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        cache = ScrapingCache(cache_file=temp_cache_file)
        assert cache.cache_file == temp_cache_file
        assert len(cache.cache) == 0

    def test_cache_set_and_get(self, temp_cache_file):
        """test setting and getting cache entries.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        cache = ScrapingCache(cache_file=temp_cache_file)

        cache.set(
            restaurant_name="Test Restaurant",
            source="yelp",
            menu_url="https://yelp.com/test",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="abc123",
            ttl_days=7
        )

        entry = cache.get("Test Restaurant", "yelp")
        assert entry is not None
        assert entry.restaurant_name == "Test Restaurant"
        assert entry.menu_hash == "abc123"

    def test_cache_get_miss(self, temp_cache_file):
        """test cache miss.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        cache = ScrapingCache(cache_file=temp_cache_file)
        entry = cache.get("Nonexistent Restaurant", "yelp")
        assert entry is None

    def test_cache_is_valid(self, temp_cache_file):
        """test cache validity check.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        cache = ScrapingCache(cache_file=temp_cache_file)

        cache.set(
            restaurant_name="Test Restaurant",
            source="yelp",
            menu_url="url",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="hash",
            ttl_days=7
        )

        assert cache.is_cache_valid("Test Restaurant", "yelp") is True
        assert cache.is_cache_valid("Other Restaurant", "yelp") is False

    def test_cache_remove(self, temp_cache_file):
        """test cache entry removal.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        cache = ScrapingCache(cache_file=temp_cache_file)

        cache.set(
            restaurant_name="Test Restaurant",
            source="yelp",
            menu_url="url",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="hash"
        )

        assert cache.get("Test Restaurant", "yelp") is not None

        cache.remove("Test Restaurant", "yelp")
        assert cache.get("Test Restaurant", "yelp") is None

    def test_cache_cleanup_expired(self, temp_cache_file):
        """test cleanup of expired entries.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        cache = ScrapingCache(cache_file=temp_cache_file)

        # add valid entry
        cache.set(
            restaurant_name="Valid Restaurant",
            source="yelp",
            menu_url="url",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="hash1",
            ttl_days=7
        )

        # add expired entry
        expired_time = datetime.now(UTC) - timedelta(days=10)
        cache.set(
            restaurant_name="Expired Restaurant",
            source="yelp",
            menu_url="url",
            scraped_at=expired_time.isoformat(),
            menu_hash="hash2",
            ttl_days=7
        )

        # cleanup should remove 1 entry
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("Valid Restaurant", "yelp") is not None
        assert cache.get("Expired Restaurant", "yelp") is None

    def test_cache_clear(self, temp_cache_file):
        """test clearing all cache entries.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        cache = ScrapingCache(cache_file=temp_cache_file)

        cache.set(
            restaurant_name="Restaurant 1",
            source="yelp",
            menu_url="url1",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="hash1"
        )

        cache.set(
            restaurant_name="Restaurant 2",
            source="opentable",
            menu_url="url2",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="hash2"
        )

        assert len(cache.cache) == 2

        cache.clear()
        assert len(cache.cache) == 0

    def test_cache_persistence(self, temp_cache_file):
        """test cache persistence across instances.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        # create cache and add entry
        cache1 = ScrapingCache(cache_file=temp_cache_file)
        cache1.set(
            restaurant_name="Persistent Restaurant",
            source="yelp",
            menu_url="url",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="hash"
        )

        # create new cache instance
        cache2 = ScrapingCache(cache_file=temp_cache_file)

        # should load entry from file
        entry = cache2.get("Persistent Restaurant", "yelp")
        assert entry is not None
        assert entry.restaurant_name == "Persistent Restaurant"

    def test_cache_get_stats(self, temp_cache_file):
        """test cache statistics.

        args:
            temp_cache_file: temporary cache file path

        returns:
            None
        """
        cache = ScrapingCache(cache_file=temp_cache_file)

        # add valid entry
        cache.set(
            restaurant_name="Restaurant 1",
            source="yelp",
            menu_url="url",
            scraped_at=datetime.now(UTC).isoformat(),
            menu_hash="hash1"
        )

        # add expired entry
        expired_time = datetime.now(UTC) - timedelta(days=10)
        cache.set(
            restaurant_name="Restaurant 2",
            source="yelp",
            menu_url="url",
            scraped_at=expired_time.isoformat(),
            menu_hash="hash2",
            ttl_days=7
        )

        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 1
        assert stats["expired_entries"] == 1
