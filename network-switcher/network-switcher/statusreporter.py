import asyncio
from aiohttp import web
import utils

logs = {}
states = {}
httpserver = None

async def handle_logs(request):
    utils.log("Request from %s:%d" % request.transport.get_extra_info('peername'))
    return web.json_response(logs)

async def handle_states(request):
    utils.log("Request from %s:%d" % request.transport.get_extra_info('peername'))
    return web.json_response(states)

app = web.Application()
app.add_routes([
    web.get('/logs', handle_logs),
    web.get('/states', handle_states)
])

def update_logs(new_logs):
    global logs
    logs = new_logs

def update_states(new_states):
    global states
    states = new_states

runner = None

async def start_server(address, port):
    global runner
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, address, port)
    utils.log("Listening on %s:%d" % (address, port))
    asyncio.create_task(site.start())

async def stop_server():
    await runner.cleanup()
