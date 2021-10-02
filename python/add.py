from motor.motor_asyncio import AsyncIOMotorClient
from config import CONFIG
import asyncio

client = AsyncIOMotorClient(CONFIG.MONGO_ENDPOINT, connect=False)
db = client['production']
servers = db['servers']


async def addmembers():
    """Review total number of users."""
    total = 0
    async for serv in servers.find({'bot_in_server': True}):
        total += serv['members']
    print(f'Total Active Members: {total}')
    async for serv in servers.find({'bot_in_server': False}):
        total += serv['members']
    print(f'Total Active Members: {total}')


async def addservers():
    """Review total number of users."""
    res = await servers.count_documents({'bot_in_server': True})
    print(f'bot in server count: {res}')
    res = await servers.count_documents({'bot_in_server': False})
    print(f'lifetime count: {res}')


async def dash():
    """Provide a basic dashboard."""
    await addmembers()
    await addservers()


loop = asyncio.get_event_loop()
loop.run_until_complete(dash())
