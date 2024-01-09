import asyncio


class Timer:
    def __init__(self, interval, first_immediately, timer_name, context, callback):
        self._interval = interval
        self._first_immediately = first_immediately
        self._name = timer_name
        self._context = context
        self._callback = callback
        self._is_first_call = True
        self._ok = True
        self._task = asyncio.ensure_future(self._job())
        print(timer_name + " init done")

    async def _job(self):
        try:
            while self._ok:
                if not self._is_first_call or not self._first_immediately:
                    await asyncio.sleep(self._interval)
                await self._callback(self._name, self._context, self)
                self._is_first_call = False
        except Exception as ex:
            print(ex)

    def cancel(self):
        self._ok = False
        self._task.cancel()
