"""bright data API client for web scraping with rate limiting and error handling."""

import os
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC


class BrightDataClient:
    """client wrapper for bright data web scraper API.

    provides typed methods for scraping yelp and opentable data with automatic
    rate limiting, error handling, and retry logic.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 0.5,
        max_retries: int = 3
    ) -> None:
        """initialize bright data client.

        args:
            api_key: bright data API key (defaults to BRIGHT_DATA_API_KEY env var)
            rate_limit_delay: delay between requests in seconds
            max_retries: maximum number of retry attempts for failed requests

        raises:
            ValueError: if api_key is not provided and not in environment
        """
        self.api_key = api_key or os.getenv("BRIGHT_DATA_API_KEY")
        if not self.api_key:
            raise ValueError("bright data API key required")

        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.base_url = "https://api.brightdata.com"
        self.last_request_time = 0.0

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def _rate_limit(self) -> None:
        """enforce rate limiting between requests.

        returns:
            None
        """
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """make HTTP request with retry logic and error handling.

        args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: request body data
            params: URL query parameters

        returns:
            parsed json response

        raises:
            requests.exceptions.RequestException: if request fails after retries
        """
        self._rate_limit()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise

                # exponential backoff
                wait_time = 2 ** attempt
                time.sleep(wait_time)

        return {}

    def scrape_yelp_business(
        self,
        business_url: str,
        include_reviews: bool = False
    ) -> Dict[str, Any]:
        """scrape yelp business data by URL.

        args:
            business_url: full yelp business URL
            include_reviews: whether to include customer reviews

        returns:
            dict containing business data:
                - business_id: unique yelp id
                - name: business name
                - rating: average rating
                - review_count: number of reviews
                - categories: list of category strings
                - website: business website
                - phone: phone number
                - address: full address
                - hours: operating hours
                - menu_url: menu URL if available
                - reviews: list of reviews (if include_reviews=True)
        """
        endpoint = "datasets/gd_l7q7dkf244hwxrsmi/trigger"

        data = {
            "url": business_url,
            "include_reviews": include_reviews,
            "format": "json"
        }

        return self._make_request("POST", endpoint, data=data)

    def scrape_opentable_restaurant(
        self,
        restaurant_url: str
    ) -> Dict[str, Any]:
        """scrape opentable restaurant data by URL.

        args:
            restaurant_url: full opentable restaurant URL

        returns:
            dict containing restaurant data:
                - restaurant_id: unique opentable id
                - name: restaurant name
                - rating: average rating
                - review_count: number of reviews
                - cuisine: cuisine type
                - price_range: price tier (1-4)
                - address: full address
                - hours: operating hours
                - menu_url: menu URL if available
                - reservation_info: availability information
        """
        endpoint = "datasets/gd_opentable/trigger"

        data = {
            "url": restaurant_url,
            "format": "json"
        }

        return self._make_request("POST", endpoint, data=data)

    def scrape_generic_webpage(
        self,
        url: str,
        css_selectors: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """scrape generic webpage using web unlocker API.

        args:
            url: target webpage URL
            css_selectors: optional dict mapping field names to CSS selectors

        returns:
            dict containing scraped data with html content or parsed fields
        """
        endpoint = "web_unlocker/trigger"

        data: Dict[str, Any] = {
            "url": url,
            "format": "json"
        }

        if css_selectors:
            data["selectors"] = css_selectors

        return self._make_request("POST", endpoint, data=data)

    def batch_scrape_yelp(
        self,
        business_urls: List[str],
        include_reviews: bool = False
    ) -> List[Dict[str, Any]]:
        """scrape multiple yelp businesses in batch.

        args:
            business_urls: list of yelp business URLs
            include_reviews: whether to include customer reviews

        returns:
            list of dicts containing business data for each URL
        """
        results = []

        for url in business_urls:
            try:
                data = self.scrape_yelp_business(url, include_reviews)
                results.append({
                    "url": url,
                    "data": data,
                    "success": True,
                    "scraped_at": datetime.now(UTC).isoformat()
                })
            except Exception as e:
                results.append({
                    "url": url,
                    "data": None,
                    "success": False,
                    "error": str(e),
                    "scraped_at": datetime.now(UTC).isoformat()
                })

        return results

    def batch_scrape_opentable(
        self,
        restaurant_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """scrape multiple opentable restaurants in batch.

        args:
            restaurant_urls: list of opentable restaurant URLs

        returns:
            list of dicts containing restaurant data for each URL
        """
        results = []

        for url in restaurant_urls:
            try:
                data = self.scrape_opentable_restaurant(url)
                results.append({
                    "url": url,
                    "data": data,
                    "success": True,
                    "scraped_at": datetime.now(UTC).isoformat()
                })
            except Exception as e:
                results.append({
                    "url": url,
                    "data": None,
                    "success": False,
                    "error": str(e),
                    "scraped_at": datetime.now(UTC).isoformat()
                })

        return results
