"""cache system for tracking restaurant extraction metadata."""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from pathlib import Path


class ExtractionCacheEntry:
    """represents a cache entry for extracted restaurant information."""

    def __init__(
        self,
        restaurant_name: str,
        source: str,
        extracted_at: str,
        data_hash: str,
        ttl_days: int = 30,
        extraction_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """initialize extraction cache entry.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp', 'opentable', or 'combined')
            extracted_at: iso timestamp of extraction
            data_hash: hash of extraction data for change detection
            ttl_days: days until cache expires (default: 30)
            extraction_data: extracted restaurant information
        """
        self.restaurant_name = restaurant_name
        self.source = source
        self.extracted_at = extracted_at
        self.data_hash = data_hash
        self.ttl_days = ttl_days
        self.extraction_data = extraction_data

    def to_dict(self) -> Dict[str, Any]:
        """convert to dictionary.

        returns:
            dict representation of cache entry
        """
        return {
            "restaurant_name": self.restaurant_name,
            "source": self.source,
            "extracted_at": self.extracted_at,
            "data_hash": self.data_hash,
            "ttl_days": self.ttl_days,
            "extraction_data": self.extraction_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionCacheEntry":
        """create cache entry from dictionary.

        args:
            data: dictionary with cache entry data

        returns:
            ExtractionCacheEntry instance
        """
        return cls(
            restaurant_name=data["restaurant_name"],
            source=data["source"],
            extracted_at=data["extracted_at"],
            data_hash=data["data_hash"],
            ttl_days=data.get("ttl_days", 30),
            extraction_data=data.get("extraction_data")
        )

    def is_valid(self) -> bool:
        """check if cache entry is still valid based on ttl.

        returns:
            True if cache is valid, False if expired
        """
        extracted_time = datetime.fromisoformat(self.extracted_at.replace("Z", "+00:00"))
        expiry_time = extracted_time + timedelta(days=self.ttl_days)
        return datetime.now(UTC) < expiry_time


class ExtractionCache:
    """cache manager for restaurant extraction operations."""

    def __init__(self, cache_file: str = "data/cache/extraction_cache.json") -> None:
        """initialize extraction cache.

        args:
            cache_file: path to cache metadata file
        """
        self.cache_file = cache_file
        self.cache: Dict[str, ExtractionCacheEntry] = {}
        Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
        self.load()

    def _generate_key(self, restaurant_name: str, source: str) -> str:
        """generate cache key from restaurant name and source.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp', 'opentable', or 'combined')

        returns:
            cache key string
        """
        # normalize restaurant name for consistent keying
        normalized_name = restaurant_name.lower().strip()
        return f"{normalized_name}_{source}"

    def load(self) -> None:
        """load cache from file.

        returns:
            None
        """
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.cache = {
                    key: ExtractionCacheEntry.from_dict(entry)
                    for key, entry in data.items()
                }
            print(f"[ExtractionCache] loaded {len(self.cache)} entries from {self.cache_file}")
        except Exception as e:
            print(f"[ExtractionCache] error loading cache: {e}")
            self.cache = {}

    def save(self) -> None:
        """save cache to file.

        returns:
            None
        """
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                data = {
                    key: entry.to_dict()
                    for key, entry in self.cache.items()
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[ExtractionCache] saved {len(self.cache)} entries to {self.cache_file}")
        except Exception as e:
            print(f"[ExtractionCache] error saving cache: {e}")

    def get(
        self,
        restaurant_name: str,
        source: str
    ) -> Optional[ExtractionCacheEntry]:
        """get cache entry if valid.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp', 'opentable', or 'combined')

        returns:
            ExtractionCacheEntry if valid, None if not found or expired
        """
        key = self._generate_key(restaurant_name, source)
        entry = self.cache.get(key)

        if not entry:
            print(f"[ExtractionCache] MISS for {restaurant_name} ({source})")
            return None

        if not entry.is_valid():
            print(f"[ExtractionCache] EXPIRED for {restaurant_name} ({source})")
            self.remove(restaurant_name, source)
            return None

        print(f"[ExtractionCache] HIT for {restaurant_name} ({source})")
        return entry

    def set(
        self,
        restaurant_name: str,
        source: str,
        extracted_at: str,
        data_hash: str,
        ttl_days: int = 30,
        extraction_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """set cache entry.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp', 'opentable', or 'combined')
            extracted_at: iso timestamp of extraction
            data_hash: hash of extraction data
            ttl_days: days until cache expires (default: 30)
            extraction_data: extracted restaurant information

        returns:
            None
        """
        key = self._generate_key(restaurant_name, source)

        entry = ExtractionCacheEntry(
            restaurant_name=restaurant_name,
            source=source,
            extracted_at=extracted_at,
            data_hash=data_hash,
            ttl_days=ttl_days,
            extraction_data=extraction_data
        )

        self.cache[key] = entry
        self.save()
        print(f"[ExtractionCache] SET for {restaurant_name} ({source}), expires in {ttl_days} days")

    def remove(self, restaurant_name: str, source: str) -> None:
        """remove cache entry.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp', 'opentable', or 'combined')

        returns:
            None
        """
        key = self._generate_key(restaurant_name, source)
        if key in self.cache:
            del self.cache[key]
            self.save()
            print(f"[ExtractionCache] REMOVED {restaurant_name} ({source})")

    def is_cache_valid(self, restaurant_name: str, source: str) -> bool:
        """check if cache entry exists and is valid.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp', 'opentable', or 'combined')

        returns:
            True if cache hit and valid, False otherwise
        """
        entry = self.get(restaurant_name, source)
        return entry is not None

    def cleanup_expired(self) -> int:
        """remove all expired cache entries.

        returns:
            number of entries removed
        """
        keys_to_remove = []

        for key, entry in self.cache.items():
            if not entry.is_valid():
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

        if keys_to_remove:
            self.save()
            print(f"[ExtractionCache] CLEANUP removed {len(keys_to_remove)} expired entries")

        return len(keys_to_remove)

    def clear(self) -> None:
        """clear all cache entries.

        returns:
            None
        """
        self.cache.clear()
        self.save()
        print("[ExtractionCache] CLEARED all entries")

    def get_stats(self) -> Dict[str, Any]:
        """get cache statistics.

        returns:
            dict with cache statistics
        """
        total = len(self.cache)
        valid = sum(1 for entry in self.cache.values() if entry.is_valid())
        expired = total - valid

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": expired,
            "cache_file": self.cache_file
        }

    def list_cached_restaurants(self) -> List[Dict[str, Any]]:
        """list all cached restaurants with their sources.

        returns:
            list of dicts with restaurant names and sources
        """
        return [
            {
                "restaurant_name": entry.restaurant_name,
                "source": entry.source,
                "extracted_at": entry.extracted_at,
                "valid": entry.is_valid()
            }
            for entry in self.cache.values()
        ]
