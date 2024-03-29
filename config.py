import argparse
import datetime
from environs import Env 

CONFIG = {
    "main": {
        "event": "agdq2024",
        "env": "prod",
        "ttl_persist_path": "./ttl_persist.json",
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
    "tasbot": {
        "aninja": "/path/to/aninja.py",
        "images": {
            "kill": "/path/to/kill.png",
            "save": "/path/to/save.png",
            "tie": "/path/to/tie.png",
        },
    },
    "events": {
        "agdq2024": {
            "bid_client": "gdq_donation_tracker",
            "bid_check_ttl": datetime.timedelta(hours=0, minutes=1, seconds=0),
            "prod": {
                "api_base_url": "https://gamesdonequick.com/tracker/api/v2/bids/?id=",
                "bids_to_track": [
                    {
                        "bid_id": 16115,
                        "friendly_name": "Kill the Animals",
                        "source": "Kill",
                    },
                    {
                        "bid_id": 16116,
                        "friendly_name": "Save the Animals",
                        "source": "Save",
                    },
                    {
                        "bid_id": None,
                        "friendly_name": "Tie",
                        "source": "Tie",
                    },
                ],
            },
            "dev": {
                "api_base_url": "http://localhost:8000/tracker/api/v2/bids/?id=",  # For testing
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
            },
            "mock": {
                "api_base_url": "http://localhost:5000/",  
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
            },
            "poll_interval_seconds": 1,
        },
    },
}
