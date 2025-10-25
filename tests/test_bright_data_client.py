"""tests for bright data client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents.scraping.bright_data_client import BrightDataClient


class TestBrightDataClient:
    """test suite for BrightDataClient."""

    def test_init_with_api_key(self):
        """test client initialization with provided API key.

        args:
            None

        returns:
            None
        """
        client = BrightDataClient(api_key="test_key_123")
        assert client.api_key == "test_key_123"
        assert client.rate_limit_delay == 0.5
        assert client.max_retries == 3

    def test_init_with_env_var(self):
        """test client initialization with environment variable.

        args:
            None

        returns:
            None
        """
        with patch.dict("os.environ", {"BRIGHT_DATA_API_KEY": "env_key_456"}):
            client = BrightDataClient()
            assert client.api_key == "env_key_456"

    def test_init_without_api_key_raises_error(self):
        """test client initialization fails without API key.

        args:
            None

        returns:
            None
        """
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="bright data API key required"):
                BrightDataClient()

    def test_rate_limiting(self):
        """test rate limiting mechanism.

        args:
            None

        returns:
            None
        """
        client = BrightDataClient(api_key="test_key", rate_limit_delay=0.1)

        with patch("time.time") as mock_time:
            mock_time.side_effect = [0.0, 0.05, 0.15]
            with patch("time.sleep") as mock_sleep:
                client._rate_limit()  # first call, no sleep
                client._rate_limit()  # second call, should sleep

                # should have slept to enforce rate limit
                mock_sleep.assert_called_once()

    @patch("requests.Session.request")
    def test_make_request_success(self, mock_request):
        """test successful API request.

        args:
            mock_request: mocked request method

        returns:
            None
        """
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success", "data": {}}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = BrightDataClient(api_key="test_key")
        result = client._make_request("POST", "/test", data={"foo": "bar"})

        assert result == {"status": "success", "data": {}}
        mock_request.assert_called_once()

    @patch("requests.Session.request")
    @patch("time.sleep")
    def test_make_request_retry_on_failure(self, mock_sleep, mock_request):
        """test request retry mechanism on failure.

        args:
            mock_sleep: mocked sleep function
            mock_request: mocked request method

        returns:
            None
        """
        import requests

        # fail twice, succeed on third attempt
        mock_request.side_effect = [
            requests.exceptions.RequestException("error 1"),
            requests.exceptions.RequestException("error 2"),
            Mock(json=lambda: {"status": "ok"}, raise_for_status=lambda: None)
        ]

        client = BrightDataClient(api_key="test_key", max_retries=3)
        result = client._make_request("GET", "/test")

        assert result == {"status": "ok"}
        assert mock_request.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("requests.Session.request")
    def test_scrape_yelp_business(self, mock_request):
        """test yelp business scraping.

        args:
            mock_request: mocked request method

        returns:
            None
        """
        mock_response = Mock()
        mock_response.json.return_value = {
            "business_id": "yelp123",
            "name": "Test Restaurant",
            "rating": 4.5
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = BrightDataClient(api_key="test_key")
        result = client.scrape_yelp_business(
            "https://yelp.com/biz/test",
            include_reviews=True
        )

        assert result["name"] == "Test Restaurant"
        assert result["rating"] == 4.5

    @patch("requests.Session.request")
    def test_scrape_opentable_restaurant(self, mock_request):
        """test opentable restaurant scraping.

        args:
            mock_request: mocked request method

        returns:
            None
        """
        mock_response = Mock()
        mock_response.json.return_value = {
            "restaurant_id": "ot456",
            "name": "Fancy Place",
            "price_range": 3
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = BrightDataClient(api_key="test_key")
        result = client.scrape_opentable_restaurant(
            "https://opentable.com/restaurant/test"
        )

        assert result["name"] == "Fancy Place"
        assert result["price_range"] == 3

    @patch.object(BrightDataClient, "scrape_yelp_business")
    def test_batch_scrape_yelp(self, mock_scrape):
        """test batch yelp scraping.

        args:
            mock_scrape: mocked scrape method

        returns:
            None
        """
        mock_scrape.side_effect = [
            {"name": "Restaurant 1"},
            {"name": "Restaurant 2"}
        ]

        client = BrightDataClient(api_key="test_key")
        urls = ["https://yelp.com/biz/r1", "https://yelp.com/biz/r2"]
        results = client.batch_scrape_yelp(urls)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is True
        assert results[0]["data"]["name"] == "Restaurant 1"

    @patch.object(BrightDataClient, "scrape_yelp_business")
    def test_batch_scrape_yelp_handles_errors(self, mock_scrape):
        """test batch scraping handles individual failures.

        args:
            mock_scrape: mocked scrape method

        returns:
            None
        """
        mock_scrape.side_effect = [
            {"name": "Restaurant 1"},
            Exception("API error")
        ]

        client = BrightDataClient(api_key="test_key")
        urls = ["https://yelp.com/biz/r1", "https://yelp.com/biz/r2"]
        results = client.batch_scrape_yelp(urls)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "API error" in results[1]["error"]
