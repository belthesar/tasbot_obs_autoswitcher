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
import simpleobsws

from timer import Timer

logger = logging.basicConfig(level=logging.WARNING)

### Tracker Constants
# GDQ_DONATION_TRACKER_API_BASE_URL = 'https://gamesdonequick.com/tracker/api/v2/'
GDQ_DONATION_TRACKER_API_BASE_URL = (
    "http://localhost:8000/tracker/api/v2/"  # For testing
)
USE_MOCK_TRACKER: bool = True  # Change to true to use the mock tracker.
MOCK_TRACKER_ENDPOINTS: dict = {
    "save",
    "http://localhost:8000/save",
    "kill",
    "http://localhost:8000/kill",
}
### OBS Websocket Constants
OBS_WEBSOCKET_PARAMETERS = simpleobsws.IdentificationParameters()
OBS_WEBSOCKET_PARAMETERS.eventSubscriptions = (1 << 0) | (1 << 2)

### Variable for holding the start time of the operation
run_started_at: datetime.datetime


CONFIG = {
    "obs": {
        "host": "127.0.0.1",
        "port": 4455,
        "password": "txp7BwUDHuRcakur",
        "ws_update_interval_seconds": 1,
    },
    "sources": [
        "Tie",
        "Kill",
        "Save",
    ],
    "scene_switching_interval_seconds": 1,
    "agdq2024": {
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
        "bid_ttl_delta": datetime.timedelta(hours=0, minutes=1, seconds=0),
        "poll_interval_seconds": 1,
    },
}

ws = simpleobsws.WebSocketClient(
    url=f"ws://{CONFIG['obs']['host']}:{CONFIG['obs']['port']}",
    password=CONFIG["obs"]["password"],
    identification_parameters=OBS_WEBSOCKET_PARAMETERS,
)


async def on_switchedscenes(eventData):
    scene_name = eventData["sceneName"]
    print(f"Switched to scene: {scene_name}")
    if scene_name == "Metalive":  # TODO: Make this configurable
        print("Current scene is metalive - engaging auto switcher")
        await engage_auto_switcher()


async def engage_auto_switcher():
    # Add your implementation here
    global run_started_at
    run_started_at = datetime.datetime.now()


async def gdq_tracker_callback(timer_name, context, timer):
    bid: str = str(context["bid"])
    async with aiohttp.ClientSession() as session:
        if USE_MOCK_TRACKER:
            url = MOCK_TRACKER_ENDPOINTS[bid]
        else:
            url = GDQ_DONATION_TRACKER_API_BASE_URL + "bids/?id=" + bid
        global run_started_at
        if (
            run_started_at + CONFIG["agdq2024"]["bid_ttl_delta"]
            < datetime.datetime.now()
        ):
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["count"] > 0:
                        bid_data = data["results"][0]
                        if bid_data["state"] == "OPENED":
                            global api_bid_data
                            api_bid_data[bid] = bid_data["total"]
                            print(f"Updated {bid} to {api_bid_data[bid]}")


async def reorder_inputs(to_the_top):
    get_scene_item_list_request = simpleobsws.Request(
        "GetSceneItemList", {"sceneName": "Metalive"}
    )
    response = await ws.call(get_scene_item_list_request)
    scene_items_list: list[dict] = response.responseData["sceneItems"]
    # search each scene item for the one we want to move (sceneItemName == to_the_top)
    id_scene_item_to_move: int = None
    top_scene_item_index: int = max(
        tuple(map(lambda x: x["sceneItemIndex"], scene_items_list))
    )
    for scene_item in scene_items_list:
        if scene_item["name"] == to_the_top:
            id_scene_item_to_move = scene_item["itemId"]
            break

    if id_scene_item_to_move is None:
        print(f"Could not find sceneItemIndex with name {to_the_top}")
        return
    set_scene_item_index_request = simpleobsws.Request(
        "SetSceneItemIndex",
        {
            "sceneName": "Metalive",
            "sceneItemId": id_scene_item_to_move,
            "sceneItemIndex": top_scene_item_index,
        },
    )
    response = await ws.call(set_scene_item_index_request)


async def tasbot_obs_autoswitcher_callback(timer_name, context, timer):
    api_bid_data: dict = context["api_bid_data"]
    print(f"Kill: {api_bid_data['kill']}")
    print(f"Save: {api_bid_data['save']}")
    if api_bid_data["kill"] > api_bid_data["save"]:
        print("Kill > Save")

    elif api_bid_data["kill"] < api_bid_data["save"]:
        print("Kill < Save")
        # await ws.call('SetCurrentScene', {'sceneName': 'Save'})
    else:
        print("Kill == Save")
        # await ws.call('SetCurrentScene', {'sceneName': 'Tie'})


async def init():
    await ws.connect()
    await ws.wait_until_identified()


def main():
    api_bid_data: dict = {
        "save": float(0),
        "kill": float(0),
    }
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(init())
        ws.register_event_callback(on_switchedscenes, "CurrentProgramSceneChanged")
        timers: list = []
        polling_interval: int = CONFIG["agdq2024"]["poll_interval_seconds"]
        obsws_update_interval: int = (
            CONFIG["obs"]["ws_update_interval_seconds"]
            if CONFIG["obs"]["ws_update_interval_seconds"]
            else None
        )
        global USE_MOCK_TRACKER
        if USE_MOCK_TRACKER:
            timers.append(
                {
                    "timer_name": "save",
                    "timer": Timer(
                        polling_interval,
                        True,
                        f"GDQ Tracker Poller - save",
                        {"bid": "save"},
                        gdq_tracker_callback,
                    ),
                }
            )
            timers.append(
                {
                    "timer_name": "kill",
                    "timer": Timer(
                        polling_interval,
                        True,
                        f"GDQ Tracker Poller - kill",
                        {"bid": "kill"},
                        gdq_tracker_callback,
                    ),
                }
            )
        else:
            for bid in CONFIG["agdq2024"]["bids_to_track"]:
                if bid["bid_id"] is not None:
                    timers.append(
                        {
                            "timer_name": "tracker_poller",
                            "timer": Timer(
                                polling_interval,
                                True,
                                f"GDQ Tracker Poller - {bid['friendly_name']}",
                                {"bid": bid["bid_id"]},
                                gdq_tracker_callback,
                            ),
                        }
                    )
        timers.append(
            {
                "timer_name": "obsws_poller",
                "timer": Timer(
                    obsws_update_interval
                    if obsws_update_interval
                    else polling_interval,
                    True,
                    "TASBot OBS Autoswitcher",
                    {"api_bid_data": api_bid_data},
                    tasbot_obs_autoswitcher_callback,
                ),
            }
        )
        loop.run_forever()
    except KeyboardInterrupt:
        print("Exiting...")
        loop.run_until_complete(ws.disconnect())
        for timer in timers:
            timer["timer"].cancel()
        loop.close()
        print("Exited.")


if __name__ == "__main__":
    main()
