"""test streaming research endpoint functionality."""

import requests
import json


def test_stream_endpoint() -> None:
    """test the streaming research endpoint returns server-sent events.

    returns:
        None
    """
    url = "http://localhost:5001/restaurants/research/stream"
    params = {
        "lat": 37.7749,
        "lng": -122.4194,
        "radius": 5000,
        "limit": 2
    }

    response = requests.get(url, params=params, stream=True, timeout=60)

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/event-stream'

    events = []
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('data: '):
                data = json.loads(decoded_line[6:])
                events.append(data)
                print(f"Received event: {data.get('type')}")

                # stop after receiving complete event
                if data.get('type') == 'complete':
                    break

    # verify we received expected event types
    event_types = [e.get('type') for e in events]
    assert 'metadata' in event_types, "Should receive metadata event"
    assert 'complete' in event_types, "Should receive complete event"
    assert any('restaurant_researched' in t for t in event_types), "Should receive at least one restaurant_researched event"

    print(f"✓ Received {len(events)} events: {event_types}")


if __name__ == "__main__":
    test_stream_endpoint()
