"""cache system for tracking restaurant menu scraping metadata."""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from pathlib import Path


class ScrapingCacheEntry:
    """represents a cache entry for scraped restaurant menu data."""

    def __init__(
        self,
        restaurant_name: str,
        source: str,
        menu_url: str,
        scraped_at: str,
        menu_hash: str,
        ttl_days: int = 7,
        file_path: Optional[str] = None
    ) -> None:
        """initialize scraping cache entry.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp' or 'opentable')
            menu_url: URL that was scraped
            scraped_at: ISO timestamp of scraping
            menu_hash: hash of menu content for change detection
            ttl_days: days until cache expires
            file_path: path to saved menu data file
        """
        self.restaurant_name = restaurant_name
        self.source = source
        self.menu_url = menu_url
        self.scraped_at = scraped_at
        self.menu_hash = menu_hash
        self.ttl_days = ttl_days
        self.file_path = file_path

    def to_dict(self) -> Dict[str, Any]:
        """convert to dictionary.

        returns:
            dict representation of cache entry
        """
        return {
            "restaurant_name": self.restaurant_name,
            "source": self.source,
            "menu_url": self.menu_url,
            "scraped_at": self.scraped_at,
            "menu_hash": self.menu_hash,
            "ttl_days": self.ttl_days,
            "file_path": self.file_path
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScrapingCacheEntry":
        """create cache entry from dictionary.

        args:
            data: dictionary with cache entry data

        returns:
            ScrapingCacheEntry instance
        """
        return cls(
            restaurant_name=data["restaurant_name"],
            source=data["source"],
            menu_url=data["menu_url"],
            scraped_at=data["scraped_at"],
            menu_hash=data["menu_hash"],
            ttl_days=data.get("ttl_days", 7),
            file_path=data.get("file_path")
        )

    def is_valid(self) -> bool:
        """check if cache entry is still valid based on TTL.

        returns:
            True if cache is valid, False if expired
        """
        scraped_time = datetime.fromisoformat(self.scraped_at.replace("Z", "+00:00"))
        expiry_time = scraped_time + timedelta(days=self.ttl_days)
        return datetime.now(UTC) < expiry_time


class ScrapingCache:
    """cache manager for restaurant menu scraping operations."""

    def __init__(self, cache_file: str = "data/cache/scraping_cache.json") -> None:
        """initialize scraping cache.

        args:
            cache_file: path to cache metadata file
        """
        self.cache_file = cache_file
        self.cache: Dict[str, ScrapingCacheEntry] = {}
        Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
        self.load()

    def _generate_key(self, restaurant_name: str, source: str) -> str:
        """generate cache key from restaurant name and source.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp' or 'opentable')

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
                    key: ScrapingCacheEntry.from_dict(entry)
                    for key, entry in data.items()
                }
            print(f"[Cache] loaded {len(self.cache)} entries from {self.cache_file}")
        except Exception as e:
            print(f"[Cache] error loading cache: {e}")
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
            print(f"[Cache] saved {len(self.cache)} entries to {self.cache_file}")
        except Exception as e:
            print(f"[Cache] error saving cache: {e}")

    def get(
        self,
        restaurant_name: str,
        source: str
    ) -> Optional[ScrapingCacheEntry]:
        """get cache entry if valid.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp' or 'opentable')

        returns:
            ScrapingCacheEntry if valid, None if not found or expired
        """
        key = self._generate_key(restaurant_name, source)
        entry = self.cache.get(key)

        if not entry:
            print(f"[Cache] MISS for {restaurant_name} ({source})")
            return None

        if not entry.is_valid():
            print(f"[Cache] EXPIRED for {restaurant_name} ({source})")
            self.remove(restaurant_name, source)
            return None

        print(f"[Cache] HIT for {restaurant_name} ({source})")
        return entry

    def set(
        self,
        restaurant_name: str,
        source: str,
        menu_url: str,
        scraped_at: str,
        menu_hash: str,
        ttl_days: int = 7,
        file_path: Optional[str] = None
    ) -> None:
        """set cache entry.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp' or 'opentable')
            menu_url: URL that was scraped
            scraped_at: ISO timestamp of scraping
            menu_hash: hash of menu content
            ttl_days: days until cache expires
            file_path: path to saved menu data file

        returns:
            None
        """
        key = self._generate_key(restaurant_name, source)

        entry = ScrapingCacheEntry(
            restaurant_name=restaurant_name,
            source=source,
            menu_url=menu_url,
            scraped_at=scraped_at,
            menu_hash=menu_hash,
            ttl_days=ttl_days,
            file_path=file_path
        )

        self.cache[key] = entry
        self.save()
        print(f"[Cache] SET for {restaurant_name} ({source}), expires in {ttl_days} days")

    def remove(self, restaurant_name: str, source: str) -> None:
        """remove cache entry.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp' or 'opentable')

        returns:
            None
        """
        key = self._generate_key(restaurant_name, source)
        if key in self.cache:
            del self.cache[key]
            self.save()
            print(f"[Cache] REMOVED {restaurant_name} ({source})")

    def is_cache_valid(self, restaurant_name: str, source: str) -> bool:
        """check if cache entry exists and is valid.

        args:
            restaurant_name: name of restaurant
            source: data source ('yelp' or 'opentable')

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
            print(f"[Cache] CLEANUP removed {len(keys_to_remove)} expired entries")

        return len(keys_to_remove)

    def clear(self) -> None:
        """clear all cache entries.

        returns:
            None
        """
        self.cache.clear()
        self.save()
        print("[Cache] CLEARED all entries")

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
                "scraped_at": entry.scraped_at,
                "valid": entry.is_valid()
            }
            for entry in self.cache.values()
        ]
