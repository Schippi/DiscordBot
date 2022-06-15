import asyncio
from aiohttp import web
import aiohttp
import aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
import base64
import os
import os.path
import sys
import ssl

from chroma import ChromaImpl

routes = web.RouteTableDef()
runners = []
keyboard = None
myqueue = []
hb_counter = 30

async def start_site(app: web.Application, config: dict):
    host = config['host']
    port = config['port']
    root_folder = os.path.dirname(sys.argv[0])
    app.add_routes(routes)
    runner = web.AppRunner(app)
    app.router.add_route('*', '/razer/chromasdk', gallery_handler)
    app.router.add_route('*', '/chromasdk', gallery_handler)
    app.router.add_route('*', '/chromasdk/heartbeat', gallery_handler)
    app.router.add_route('*', '/chromasdk/keyboard', gallery_handler)
    app.router.add_route('*', '/chromasdk/effect', gallery_handler)

    #app.router.add_route('POST', '/razer/chromasdk', gallery_handler)
    #app.router.add_route('GET', '/chroma', gallery_handler)
    runners.append(runner)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

@routes.post('/chroma/text')
async def post_handler(request):
    data = await request.json()
    myqueue.append(data)


async def heartbeat():
    global hb_counter, keyboard
    while True:
        if hb_counter > 0:
            if keyboard is not None and keyboard.uri is not None:
                hb_counter -= 1
                await keyboard.heartbeat()
            else:
                hb_counter = 0
        else:
            if keyboard is not None and keyboard.uri is not None:
                print("disconnecting")
                await keyboard.disconnect()
                keyboard = None
        await asyncio.sleep(1.0)
    pass

async def handle_queue():
    global keyboard, myqueue, hb_counter
    while True:
        if len(myqueue) > 0:
            if keyboard is None:
                keyboard = ChromaImpl()
                await keyboard.connect()
            hb_counter = 15
            data = myqueue.pop(0)
            await keyboard.show_text(" "+data['text'], data['speed'], color=(255, 255, 0))
            if len(myqueue) > 0:
                await keyboard.flash(color=(255, 255, 0))
        elif keyboard is not None and hb_counter == 15:
            print('disconnection')
            await keyboard.disconnect()
            keyboard = None
        await asyncio.sleep(1.0)

async def gallery_handler(request):
    met = request.method.upper()
    rel_url = str(request.rel_url).split('?')[0]
    port = request.rel_url.query.get('port', 54235)
    local_url = 'http://localhost:%d%s' % (int(port), rel_url)
    print(local_url)
    async with aiohttp.ClientSession() as session:
        if met == 'GET':
            async with session.get(local_url) as resp:
                return await handle_response(resp)
        elif met == 'POST':
            data = await request.json()
            async with session.post(local_url, json=data) as resp:
                return await handle_response(resp)
        elif met == 'PUT':
            try:
                data = await request.json()
                async with session.put(local_url, json=data) as resp:
                    return await handle_response(resp)
            except:
                async with session.put(local_url) as resp:
                    return await handle_response(resp)
        elif met == 'DELETE':
            #local_url = 'http://localhost:%d%s' % (int(port), '/chromasdk')

            async with session.delete(local_url) as resp:
                return await handle_response(resp)
    return web.json_response({'error': 'not found'})

async def handle_response(response):
    try:
        d = await response.json()
        print(d)
        return web.json_response(d)
    except Exception as e:
        import traceback
        traceback.print_exc()

    return web.json_response({'error': 'kaputt'})




if __name__ == '__main__':
    from chromaconfig import config

    # web.run_app(setuphttp(config)[0])
    # print("something")
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    # loop.create_task(consumer(queue),name='consumer')
    # loop.create_task(consumer(queue),name='consumer')
    # web.run_app(setuphttp(config)[0])
    loop.create_task(start_site(web.Application(), config))
    loop.create_task(handle_queue())
    # loop.create_task(heartbeat())

    print("starting, config:")
    print(config)
    loop.run_forever()

