#!/usr/bin/env python3
"""
tasbot_obs_autoswitcher

Automated video switcher for OBS based on external conditions.
Cody Wilson <cody@codywilson.co>
"""
import aiohttp
import asyncio
import datetime
import logging
import requests
import simpleobsws

from timer import Timer

### Tracker Constants
# GDQ_DONATION_TRACKER_API_BASE_URL = 'https://gamesdonequick.com/tracker/api/v2/'
GDQ_DONATION_TRACKER_API_BASE_URL = 'http://localhost:8000/tracker/api/v2/' # For testing
USE_MOCK_TRACKER: bool = False # Change to true to use the mock tracker. 
MOCK_TRACKER_ENDPOINTS: dict = {
    "save", "http://localhost:8000/save",
    "kill", "http://localhost:8000/kill",
}
### OBS Websocket Constants
OBS_WEBSOCKET_PARAMETERS = simpleobsws.IdentificationParameters()
OBS_WEBSOCKET_PARAMETERS.eventSubscriptions = (1 << 0) | (1 << 2) 

### Variable for holding the start time of the operation
run_started_at: datetime.datetime


CONFIG = {
    'obs': {
        'host': '127.0.0.1',
        'port': 4455,
        'password': 'txp7BwUDHuRcakur'
    },
    'sources': [
        'Tie',
        'Kill',
        'Save',
    ],
    'agdq2024': {
        'bids_to_track': [
            {
                'bid_id': 1,
                'friendly_name': 'Kill the Animals',
                'source': 'Kill',
            },
            {
                'bid_id': 2,
                'friendly_name': 'Save the Animals',
                'source': 'Save',
            },
            {
                'bid_id': null,
                'friendly_name': 'Tie',
                'source': 'Tie',
            }
        ],
        'bid_ttl_delta': datetime.timedelta(hours=0, minutes=1, seconds=0),
    }
}

ws = simpleobsws.WebSocketClient(
    url = f"ws://{CONFIG['obs']['host']}:{CONFIG['obs']['port']}",
    password = CONFIG['obs']['password'],
    identification_parameters = OBS_WEBSOCKET_PARAMETERS
)

async def on_switchedscenes(eventData):
    scene_name = eventData['sceneName']
    print(f"Switched to scene: {scene_name}")
    if(scene_name == "Metalive"): # TODO: Make this configurable
        print("Current scene is metalive - engaging auto switcher")
        await engage_auto_switcher()

async def engage_auto_switcher():
    # Add your implementation here
    global run_started_at
    run_started_at = datetime.datetime.now()

async def gdq_tracker_callback(timer_name, context, timer):
    bid: str = str(context['bid'])
    async with aiohttp.ClientSession() as session:
        if USE_MOCK_TRACKER:
            url = MOCK_TRACKER_ENDPOINTS[bid]
        else:
            url = GDQ_DONATION_TRACKER_API_BASE_URL + 'bids/?id=' + bid
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data['count'] > 0:
                    bid_data = data['results'][0]
                    if bid_data['state'] == 'OPENED':
                        global api_bid_data
                        api_bid_data[bid] = bid_data['total']
                        print(f"Updated {bid} to {api_bid_data[bid]}")

async def tasbot_obs_autoswitcher_callback(timer_name, context, timer):
    global api_bid_data
    if api_bid_data['kill'] > api_bid_data['save']:
        print("Kill > Save")
        await ws.call('SetCurrentScene', {'scene-name': 'Kill'})
    elif api_bid_data['kill'] < api_bid_data['save']:
        print("Kill < Save")
        await ws.call('SetCurrentScene', {'scene-name': 'Save'})
    else:
        print("Kill == Save")
        await ws.call('SetCurrentScene', {'scene-name': 'Tie'})

async def init():
    await ws.connect()
    await ws.wait_until_identified()


def main():
    should_we_poll_api_event: asyncio.event = asyncio.event()
    api_bid_data: dict = {
        "save": float(0),
        "kill": float(0),
    }
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(init())
        ws.register_event_callback(on_switchedscenes, 'CurrentProgramSceneChanged')
        loop.run_forever()
    except KeyboardInterrupt:
        print("Exiting...")
        loop.run_until_complete(ws.disconnect())
        loop.close()
        print("Exited.")

if __name__ == "__main__":
    main()