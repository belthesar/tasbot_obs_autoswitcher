import argparse
import datetime
from environs import Env


CONFIG = {
    "main": {
        "event": "agdq2024",
        "env": "mock",
    },
    "obs": {
        "host": "127.0.0.1",
        "port": 4455,
        "password": "txp7BwUDHuRcakur",
        "ws_update_interval_seconds": 1,
        "sources": [
            "Tie",
            "Kill",
            "Save",
        ],
        "scene_switching_interval_seconds": 1,  # TODO: Remove this
    },
    # TODO: Remove this
    "events": {
        "agdq2024": {
            "bid_client": "gdq_donation_tracker",
            "bid_check_ttl": datetime.timedelta(hours=0, minutes=1, seconds=0),
            "prod": {
                "bids_to_track": [
                    {
                        "bid_id": 5142,
                        "friendly_name": "Kill the Animals",
                        "source": "Kill",
                    },
                    {
                        "bid_id": 5141,
                        "friendly_name": "Save the Animals",
                        "source": "Save",
                    },
                    {
                        "bid_id": None,
                        "friendly_name": "Tie",
                        "source": "Tie",
                    },
                ],
                "api_base_url": "https://gamesdonequick.com/tracker/api/v2/bids/?id=",
                "poll_interval_seconds": 1,
            },
            "dev": {
                "bids_to_track": [
                    {
                        "bid_id": 1,
                        "friendly_name": "Kill the Animals",
                        "source": "Kill",
                    },
                    {
                        "bid_id": 2,
                        "friendly_name": "Save the Animals",
                        "source": "Save",
                    },
                    {
                        "bid_id": None,
                        "friendly_name": "Tie",
                        "source": "Tie",
                    },
                ],
                "api_base_url": "http://localhost:8000/tracker/api/v2/bids/?id=",  # For testing
                "poll_interval_seconds": 1,
            },
            "mock": {
                "bids_to_track": [
                    {
                        "bid_id": "save",
                        "friendly_name": "Save the Animals",
                        "source": "Save",
                    },
                    {
                        "bid_id": "kill",
                        "friendly_name": "Kill the Animals",
                        "source": "Kill",
                    },
                    {
                        "bid_id": None,
                        "friendly_name": "Tie",
                        "source": "Tie",
                    },
                ],
                "api_base_url": "http://localhost:8080/",  # see README.md
                "poll_interval_seconds": 1,
            },
            "bid_ttl_delta": datetime.timedelta(hours=0, minutes=1, seconds=0),
            "poll_interval_seconds": 1,
        },
    },
}
