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

# from contextvars import ContextVar
from config import CONFIG

from timer import Timer

logging.basicConfig(
    level=logging.DEBUG,
    style="{",
    format="{asctime} {levelname} {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
)

### OBS Websocket Constants
OBS_WEBSOCKET_PARAMETERS = simpleobsws.IdentificationParameters()
OBS_WEBSOCKET_PARAMETERS.eventSubscriptions = (1 << 0) | (1 << 2)

### Context Variables
run_started: bool(False) = False
run_started_at: datetime.datetime = None
api_bid_data: dict = {"Save": 0.0, "Kill": 0.0}

ws = simpleobsws.WebSocketClient(
    url=f"ws://{CONFIG['obs']['host']}:{CONFIG['obs']['port']}",
    password=CONFIG["obs"]["password"],
    identification_parameters=OBS_WEBSOCKET_PARAMETERS,
)


async def on_switchedscenes(eventData):
    scene_name = eventData["sceneName"]
    if scene_name == "Metalive":  # TODO: Make this configurable
        await engage_auto_switcher()


async def engage_auto_switcher():
    global run_started
    global run_started_at
    if run_started is True:
        return
    logging.info("[META] Engaging auto switcher")
    run_started = True
    run_started_at = datetime.datetime.now()
    logging.debug(f"[META] engage_auto_switcher - run_started: {run_started}")


async def reorder_inputs(to_the_top: str, logger=logging.getLogger()):
    logging.info(f"[SWITCHER] Moving {to_the_top} to the top of the scene")
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
            logging.info(f"Found {to_the_top} at index {scene_item['sceneItemIndex']}")

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
    await ws.call(set_scene_item_index_request)


async def tasbot_obs_autoswitcher_callback_v2(timer_name, context, timer):
    global run_started
    global run_started_at
    if not run_started:
        get_current_scene_request = simpleobsws.Request("GetCurrentProgramScene")
        response = await ws.call(get_current_scene_request)
        current_scene_name = response.responseData["currentProgramSceneName"]
        if current_scene_name == "Metalive":  # TODO: Make this configurable
            await engage_auto_switcher()
    bids_to_track: list[dict] = context["bids_to_track"]
    base_url: str = context["base_url"]
    logger = context["logger"]
    global api_bid_data
    if run_started is True:
        run_started_time = run_started_at
        logging.info(f"Run started at: {run_started_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if datetime.datetime.now() > run_started_time + context["bid_check_ttl"]:
            logger.info("Run has been going on for too long, stopping auto switcher")
            run_started = False
            return
        async with aiohttp.ClientSession() as session:
            for bid_type in bids_to_track:
                if bid_type["bid_id"] is not None:
                    logger.debug(f"Looking up bid_id: {bid_type['bid_id']}")
                    async with session.get(base_url + str(bid_type["bid_id"])) as resp:
                        if resp.status == 200:
                            logger.info("Found bid_id, parsing response")
                            data = await resp.json(content_type='application/octet-stream')

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
        for key, value in api_bid_data.items():
            logger.info(f"[BID DATA] {key}: {value}")
        if api_bid_data["Kill"] > api_bid_data["Save"]:
            logger.info("[BID DATA] Kill > Save")
            await reorder_inputs("Kill")
        elif api_bid_data["Kill"] < api_bid_data["Save"]:
            logger.info("[BID DATA] Save > Kill")
            await reorder_inputs("Save")
        else:
            logger.info("[BID DATA] Kill == Save")
            await reorder_inputs("Tie")
    return

async def init():
    await ws.connect()
    await ws.wait_until_identified()

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
        polling_interval: int = CONFIG['events'][event]["poll_interval_seconds"]
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
            timer["timer"].cancel()
        loop.close()
        logger.warning("Exited.")


if __name__ == "__main__":
    main()
