import aiohttp

# GDQ_DONATION_TRACKER_API_BASE_URL = 'https://gamesdonequick.com/tracker/api/v2/'
GDQ_DONATION_TRACKER_API_BASE_URL = 'http://localhost:8000/tracker/api/v2/' # For testing

async def gdq_tracker_callback(timer_name, context, timer):
    bid: str = str(context['bid'])
    async with aiohttp.ClientSession() as session:
        async with session.get(GDQ_DONATION_TRACKER_API_BASE_URL + 'bids/?id=' + bid) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data['count'] > 0:
                    bid_data = data['results'][0]
                    if bid_data['state'] == 'OPENED':
                        pass
                        # TODO: Use a consumer 

