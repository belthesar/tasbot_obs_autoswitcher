async def consumer(event, data):
    while True:
        await event.wait()
        event.clear()
        if not data:
            break
        