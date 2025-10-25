"""menu scraper module for extracting restaurant menu data from yelp and opentable."""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from pathlib import Path

from agents.scraping.bright_data_client import BrightDataClient
from agents.scraping.restaurant_discovery import RestaurantIdentifier
from agents.scraping.scraping_cache import ScrapingCache


class MenuData:
    """represents scraped menu data for a restaurant."""

    def __init__(
        self,
        restaurant_name: str,
        source: str,
        url: str,
        raw_data: Dict[str, Any],
        scraped_at: str
    ) -> None:
        """initialize menu data.

        args:
            restaurant_name: name of the restaurant
            source: data source ('yelp' or 'opentable')
            url: source URL that was scraped
            raw_data: raw scraped data from bright data API
            scraped_at: ISO timestamp of scraping
        """
        self.restaurant_name = restaurant_name
        self.source = source
        self.url = url
        self.raw_data = raw_data
        self.scraped_at = scraped_at

    def to_dict(self) -> Dict[str, Any]:
        """convert to dictionary representation.

        returns:
            dict containing all menu data fields
        """
        return {
            "restaurant_name": self.restaurant_name,
            "source": self.source,
            "url": self.url,
            "raw_data": self.raw_data,
            "scraped_at": self.scraped_at
        }

    def save_to_file(self, output_dir: str) -> str:
        """save menu data to json file.

        args:
            output_dir: directory to save the file

        returns:
            path to saved file
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # create filename from restaurant name and source
        safe_name = "".join(
            c if c.isalnum() else "_" for c in self.restaurant_name
        ).lower()
        filename = f"{safe_name}_{self.source}_{self.scraped_at.split('T')[0]}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        return filepath


class MenuScraper:
    """scraper for restaurant menu data using bright data API."""

    def __init__(
        self,
        client: Optional[BrightDataClient] = None,
        raw_data_dir: str = "data/raw/menus",
        cache: Optional[ScrapingCache] = None,
        use_cache: bool = True
    ) -> None:
        """initialize menu scraper.

        args:
            client: bright data client instance (creates new if None)
            raw_data_dir: directory to store raw scraped data
            cache: scraping cache instance (creates new if None)
            use_cache: whether to use cache for deduplication
        """
        self.client = client or BrightDataClient()
        self.raw_data_dir = raw_data_dir
        self.cache = cache or ScrapingCache()
        self.use_cache = use_cache
        Path(raw_data_dir).mkdir(parents=True, exist_ok=True)

    def scrape_yelp_menu(
        self,
        restaurant_name: str,
        yelp_url: str,
        include_reviews: bool = True
    ) -> Optional[MenuData]:
        """scrape menu data from yelp.

        args:
            restaurant_name: name of the restaurant
            yelp_url: yelp business URL
            include_reviews: whether to include customer reviews

        returns:
            MenuData object or None if scraping failed
        """
        # check cache first
        if self.use_cache and self.cache.is_cache_valid(restaurant_name, "yelp"):
            cache_entry = self.cache.get(restaurant_name, "yelp")
            if cache_entry and cache_entry.file_path:
                print(f"using cached data for {restaurant_name} (yelp)")
                # load from cached file
                try:
                    with open(cache_entry.file_path, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                        return MenuData(
                            restaurant_name=cached_data["restaurant_name"],
                            source=cached_data["source"],
                            url=cached_data["url"],
                            raw_data=cached_data["raw_data"],
                            scraped_at=cached_data["scraped_at"]
                        )
                except Exception as e:
                    print(f"error loading cached data: {e}, re-scraping...")

        try:
            raw_data = self.client.scrape_yelp_business(
                business_url=yelp_url,
                include_reviews=include_reviews
            )

            menu_data = MenuData(
                restaurant_name=restaurant_name,
                source="yelp",
                url=yelp_url,
                raw_data=raw_data,
                scraped_at=datetime.now(UTC).isoformat()
            )

            # save raw data
            file_path = menu_data.save_to_file(self.raw_data_dir)

            # update cache
            if self.use_cache:
                import hashlib
                menu_hash = hashlib.md5(
                    json.dumps(raw_data, sort_keys=True).encode()
                ).hexdigest()
                self.cache.set(
                    restaurant_name=restaurant_name,
                    source="yelp",
                    menu_url=yelp_url,
                    scraped_at=menu_data.scraped_at,
                    menu_hash=menu_hash,
                    file_path=file_path
                )

            return menu_data

        except Exception as e:
            print(f"error scraping yelp for {restaurant_name}: {e}")
            return None

    def scrape_opentable_menu(
        self,
        restaurant_name: str,
        opentable_url: str
    ) -> Optional[MenuData]:
        """scrape menu data from opentable.

        args:
            restaurant_name: name of the restaurant
            opentable_url: opentable restaurant URL

        returns:
            MenuData object or None if scraping failed
        """
        # check cache first
        if self.use_cache and self.cache.is_cache_valid(restaurant_name, "opentable"):
            cache_entry = self.cache.get(restaurant_name, "opentable")
            if cache_entry and cache_entry.file_path:
                print(f"using cached data for {restaurant_name} (opentable)")
                # load from cached file
                try:
                    with open(cache_entry.file_path, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                        return MenuData(
                            restaurant_name=cached_data["restaurant_name"],
                            source=cached_data["source"],
                            url=cached_data["url"],
                            raw_data=cached_data["raw_data"],
                            scraped_at=cached_data["scraped_at"]
                        )
                except Exception as e:
                    print(f"error loading cached data: {e}, re-scraping...")

        try:
            raw_data = self.client.scrape_opentable_restaurant(
                restaurant_url=opentable_url
            )

            menu_data = MenuData(
                restaurant_name=restaurant_name,
                source="opentable",
                url=opentable_url,
                raw_data=raw_data,
                scraped_at=datetime.now(UTC).isoformat()
            )

            # save raw data
            file_path = menu_data.save_to_file(self.raw_data_dir)

            # update cache
            if self.use_cache:
                import hashlib
                menu_hash = hashlib.md5(
                    json.dumps(raw_data, sort_keys=True).encode()
                ).hexdigest()
                self.cache.set(
                    restaurant_name=restaurant_name,
                    source="opentable",
                    menu_url=opentable_url,
                    scraped_at=menu_data.scraped_at,
                    menu_hash=menu_hash,
                    file_path=file_path
                )

            return menu_data

        except Exception as e:
            print(f"error scraping opentable for {restaurant_name}: {e}")
            return None

    def scrape_restaurant(
        self,
        identifier: RestaurantIdentifier,
        scrape_yelp: bool = True,
        scrape_opentable: bool = True,
        include_reviews: bool = True
    ) -> Dict[str, Optional[MenuData]]:
        """scrape menu data from both yelp and opentable for a restaurant.

        args:
            identifier: restaurant identifier with URLs
            scrape_yelp: whether to scrape yelp data
            scrape_opentable: whether to scrape opentable data
            include_reviews: whether to include reviews in yelp data

        returns:
            dict with keys 'yelp' and 'opentable' mapping to MenuData or None
        """
        results: Dict[str, Optional[MenuData]] = {
            "yelp": None,
            "opentable": None
        }

        if scrape_yelp and identifier.yelp_url:
            results["yelp"] = self.scrape_yelp_menu(
                restaurant_name=identifier.name,
                yelp_url=identifier.yelp_url,
                include_reviews=include_reviews
            )

        if scrape_opentable and identifier.opentable_url:
            results["opentable"] = self.scrape_opentable_menu(
                restaurant_name=identifier.name,
                opentable_url=identifier.opentable_url
            )

        return results

    def batch_scrape_restaurants(
        self,
        identifiers: List[RestaurantIdentifier],
        scrape_yelp: bool = True,
        scrape_opentable: bool = True,
        include_reviews: bool = False
    ) -> List[Dict[str, Any]]:
        """scrape menu data for multiple restaurants in batch.

        args:
            identifiers: list of restaurant identifiers
            scrape_yelp: whether to scrape yelp data
            scrape_opentable: whether to scrape opentable data
            include_reviews: whether to include reviews

        returns:
            list of dicts containing scraping results for each restaurant
        """
        results = []

        for i, identifier in enumerate(identifiers, 1):
            print(f"scraping {i}/{len(identifiers)}: {identifier.name}")

            try:
                menu_data = self.scrape_restaurant(
                    identifier=identifier,
                    scrape_yelp=scrape_yelp,
                    scrape_opentable=scrape_opentable,
                    include_reviews=include_reviews
                )

                results.append({
                    "restaurant_name": identifier.name,
                    "location": identifier.location,
                    "yelp_success": menu_data["yelp"] is not None,
                    "opentable_success": menu_data["opentable"] is not None,
                    "yelp_data": menu_data["yelp"].to_dict() if menu_data["yelp"] else None,
                    "opentable_data": menu_data["opentable"].to_dict() if menu_data["opentable"] else None
                })

            except Exception as e:
                print(f"error scraping {identifier.name}: {e}")
                results.append({
                    "restaurant_name": identifier.name,
                    "location": identifier.location,
                    "yelp_success": False,
                    "opentable_success": False,
                    "error": str(e)
                })

        return results
