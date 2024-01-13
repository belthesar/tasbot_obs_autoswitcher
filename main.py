#!/usr/bin/env python3
"""
tasbot_obs_autoswitcher

Automated video switcher for OBS based on external conditions.
Cody Wilson <cody@codywilson.co>
"""
import aiohttp
import asyncio
import datetime
import json
import logging
import os
import simpleobsws

from enum import Enum
from pathlib import Path
from websockets import exceptions as websocket_exceptions

from config import CONFIG
from timer import Timer

logging.basicConfig(
    level=logging.INFO,
    style="{",
    format="{asctime} {levelname} {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
)

### OBS Websocket Constants
OBS_WEBSOCKET_PARAMETERS = simpleobsws.IdentificationParameters()
OBS_WEBSOCKET_PARAMETERS.eventSubscriptions = (1 << 0) | (1 << 2)

### Global Variables
run_started: bool = False
run_started_at: datetime.datetime = None
run_ttl_expired: bool = False
api_bid_data: dict = {"Save": 0.0, "Kill": 0.0}
last_api_bid_data: dict = {"Save": 0.0, "Kill": 0.0}

### OBS Websocket
ws = simpleobsws.WebSocketClient(
    url=f"ws://{CONFIG['obs']['host']}:{CONFIG['obs']['port']}",
    password=CONFIG["obs"]["password"],
    identification_parameters=OBS_WEBSOCKET_PARAMETERS,
)


### Persistence
class PersistenceAction(Enum):
    READ = 1
    WRITE = 2
    DELETE = 3

async def on_switchedscenes(eventData):
    scene_name = eventData["sceneName"]
    if scene_name == "Metalive":  # TODO: Make this configurable
        await engage_auto_switcher()

async def load_persistence_file(persistence_file_path: Path):
    with open(persistence_file_path, "r") as f:
        data = json.load(f)
        run_started = data["run_started"]
        run_started_at = datetime.datetime.strptime(
            data["run_started_at"], "%Y-%m-%d %H:%M:%S"
        )
        return run_started, run_started_at
    
async def write_persistence_file(persistence_file_path: Path):
    with open(persistence_file_path, "rw+") as f:
        global run_started
        global run_started_at
        data = {
            "run_started": run_started,
            "run_started_at": run_started_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if json.load(f.read()) != data:
            json.dump(data, f)
            return True
        else:
            return False

async def engage_auto_switcher():
    global run_started
    global run_started_at
    if run_started is True:
        return
    logging.info("[SWITCHER] Engaging auto switcher")
    run_started = True
    run_started_at = datetime.datetime.now()
    logging.info(
        f"[SWITCHER] Run started at: {run_started_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )


async def switch_active_media(to_the_top: str, logger=logging.getLogger()):
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
    logging.debug(f"top_scene_item_index: {top_scene_item_index}")
    for scene_item in scene_items_list:
        if scene_item["sourceName"] == to_the_top:
            id_scene_item_to_move = scene_item["sceneItemId"]
            logging.debug(f"Found {to_the_top} at index {scene_item['sceneItemIndex']}")
            if scene_item["sceneItemIndex"] == top_scene_item_index:
                logging.debug(f"{to_the_top} is already at the top of the scene")
                return

    if id_scene_item_to_move is None:
        logger.error(f"Could not find sceneItemIndex with name {to_the_top}")
        return
    set_scene_item_index_request = simpleobsws.Request(
        "SetSceneItemIndex",
        {
            "sceneName": "Metalive",
            "sceneItemId": id_scene_item_to_move,
            "sceneItemIndex": top_scene_item_index,
        },
    )
    logging.info(f"[SWITCHER] Setting {to_the_top} as the top scene item")
    await ws.call(set_scene_item_index_request)


async def tasbot_obs_autoswitcher_callback_v2(timer_name, context, timer):
    global api_bid_data
    global last_api_bid_data
    global run_started
    global run_started_at
    global run_ttl_expired

    if not run_started:
        get_current_scene_request = simpleobsws.Request("GetCurrentProgramScene")
        response = await ws.call(get_current_scene_request)
        current_scene_name = response.responseData["currentProgramSceneName"]
        if current_scene_name == "Metalive":  # TODO: Make this configurable
            await engage_auto_switcher()
    bids_to_track: list[dict] = context["bids_to_track"]
    base_url: str = context["base_url"]
    logger = context["logger"]
    if run_started and not run_ttl_expired:
        logger.info("--------------------")
        if datetime.datetime.now() > run_started_at + context["bid_check_ttl"]:
            logger.info(
                "[SWITCHER] Run has exceeded the TTL, disabling the auto switcher!"
            )
            run_ttl_expired = True
            return
        async with aiohttp.ClientSession() as session:
            for bid_type in bids_to_track:
                if bid_type["bid_id"] is not None:
                    logger.debug(f"Looking up bid_id: {bid_type['bid_id']}")
                    try:
                        async with session.get(
                            base_url + str(bid_type["bid_id"])
                        ) as resp:
                            if resp.status == 200:
                                logger.debug("Found bid_id, parsing response")
                                data = (
                                    await resp.json(
                                        content_type="application/octet-stream"
                                    )
                                    if resp.content_type == "application/octet-stream"
                                    else await resp.json()
                                )
                                if (
                                    data["count"] == 1
                                ):  # we're looking up a bid by it's absolute ID, so we should only ever get one result
                                    tracker_bid_data = data["results"][0]
                                    if tracker_bid_data["state"] == "OPENED":
                                        api_bid_data[
                                            tracker_bid_data["shortdescription"]
                                        ] = float(tracker_bid_data["total"])
                                    else:
                                        logger.error(
                                            f"Got bid state {tracker_bid_data['state']} for bid_id {bid_type['bid_id']}, make sure that you have the correct bid ID in your config."
                                        )
                                        return
                                else:
                                    logger.error(
                                        f"Got {data['count']} results for bid_id {bid_type['bid_id']}, make sure that you have the correct bid ID in your config."
                                    )
                                    return
                    except aiohttp.ClientConnectorError as e:
                        logger.error(
                            f"[HTTP] We encountered an error while trying to connect to the API: {e}"
                        )
                        pass
        for key, value in api_bid_data.items():
            logger.debug(f"[BID DATA] {key}: {value}")
        if api_bid_data["Kill"] > api_bid_data["Save"]:
            logger.debug("[BID DATA] Kill > Save")
            await switch_active_media("Kill")
        elif api_bid_data["Kill"] < api_bid_data["Save"]:
            logger.debug("[BID DATA] Save > Kill")
            await switch_active_media("Save")
        else:
            logger.debug("[BID DATA] Kill == Save")
            await switch_active_media("Tie")
    return


async def init():
    global run_started
    global run_started_at
    try:
        await ws.connect()
    except websocket_exceptions.InvalidStatusCode as e:
        logging.error(
            f"Could not connect to OBS Websocket, please check your configuration: {e}"
        )
        exit(1)
    except ConnectionRefusedError as e:
        logging.error(
            f"Could not connect to OBS Websocket. Is OBS running and, is the websocket plugin activated? If so, please check your configuration: {e}"
        )
        exit(1)
    logging.info("Connected to OBS Websocket, identifying...")
    await ws.wait_until_identified(timeout=10)
    try:
        assert ws.identified
    except AssertionError:
        logging.error(
            "We were unable to identify with the OBS Websocket, please check your configuration to make sure your password matches the one the OBS Websocket plugin configuration."
        )
        exit(1)
    logging.info("Identified with OBS Websocket, checking for an active run...")
    # if (os.path.isfile(CONFIG["main"]["ttl_persist_path"])):
    #     logging.info("Found TTL persistence file, loading...")
    #     run_started, run started_at = await load_persistence_file(CONFIG["main"]["ttl_persist_path"])
    logging.info("TASBot OBS Autoswitcher initialized successfully!")


def main():
    logger = logging.getLogger()
    try:
        event: str = CONFIG["main"]["event"]
        event_env: str = CONFIG["main"]["env"]
        loop = asyncio.get_event_loop()
        loop.set_debug(enabled=True)
        loop.run_until_complete(init())
        ws.register_event_callback(on_switchedscenes, "CurrentProgramSceneChanged")
        timers: list = []
        polling_interval: int = CONFIG["events"][event]["poll_interval_seconds"]
        obsws_update_interval: int = (
            CONFIG["obs"]["ws_update_interval_seconds"]
            if CONFIG["obs"]["ws_update_interval_seconds"]
            else None
        )
        logger = logging.getLogger()
        timers.append(
            {
                "timer": Timer(
                    interval=1,
                    first_immediately=True,
                    timer_name="tasbot_obs_autoswitcher",
                    context={
                        "logger": logger,
                        "bids_to_track": CONFIG["events"][event][event_env][
                            "bids_to_track"
                        ],
                        "base_url": CONFIG["events"][event][event_env]["api_base_url"],
                        "bid_check_ttl": CONFIG["events"][event]["bid_check_ttl"],
                    },
                    callback=tasbot_obs_autoswitcher_callback_v2,
                ),
                "interval": 1,
            }
        )
        loop.run_forever()
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received, cleaning up...")
        loop.run_until_complete(ws.disconnect())
        for timer in timers:
            try:
                timer["timer"].cancel()
            except Exception as e:
                pass
        loop.close()
        logger.warning("Exited.")


if __name__ == "__main__":
    main()
