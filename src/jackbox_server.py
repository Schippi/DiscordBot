from aiohttp import web
import aiohttp
import aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import asyncio
import json
from cryptography import fernet
import traceback
import sys
import base64
import ssl
import time
import os.path
from jackbox_config import ALL_APP_IDS
from jackbox_config import games

jackroutes = web.RouteTableDef()


def current_milli_time():
    return round(time.time() * 1000)


def setup(config_dict: dict):
    app = web.Application()
    httpsapp = app
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    storage = EncryptedCookieStorage(secret_key)
    # print(storage.cookie_params)
    # storage.cookie_params['samesite']='strict'
    # storage.save_cookie(response, cookie_data)
    aiohttp_session.setup(app, storage)

    app.add_routes(jackroutes)

    runner = web.AppRunner(app)

    asyncio.get_event_loop().run_until_complete(runner.setup())

    host = config_dict['host']
    port = config_dict['port']

    if 'certificate' in config_dict.keys() and 'private_key' in config_dict.keys():
        certificate = config_dict['certificate']  # = util.cfgPath+'/fullchain.pem'
        private_key = config_dict['private_key']  # = util.cfgPath+'/privkey.pem'
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certificate, private_key)
        website = web.TCPSite(runner, host, port, ssl_context=ssl_context)
    else:
        website = web.TCPSite(runner, host, port)

    return website


async def start_site(app: web.Application, config: dict):
    host = config['host']
    port = config['port']
    root_folder = os.path.dirname(sys.argv[0])
    app.add_routes(jackroutes)
    runner = web.AppRunner(app)
    app.router.add_static('/images', root_folder+'/images')
    app.router.add_route('*', '/', launcher_handler)

    runners.append(runner)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()


async def root_handler(request, *args, **kwargs):
    tasklist.clear()
    return web.FileResponse('htdocs/index.html')


def loopdirectory(s):
    for f in os.listdir(s):
        yield f


async def launcher_handler(request):
    return await gallery_handler(request);


@jackroutes.get('/jackbox/draw')
async def draw_handler(request):
    return await gallery_handler(request, onlydraw=True, playerCount=0);


@jackroutes.get('/jackbox/draw/{playerCount}')
async def draw_play_handler(request):
    try:
        playerCount = int(request.match_info['playerCount'])
        return await gallery_handler(request, onlydraw=True, playerCount=playerCount);
    except (ValueError, KeyError) as e:
        return web.Response(text='Invalid playerCount', status=400)


@jackroutes.get('/jackbox/players/{playerCount}')
async def draw_play_handler(request):
    try:
        playerCount = int(request.match_info['playerCount'])
        return await gallery_handler(request, onlydraw=False, playerCount=playerCount);
    except (ValueError, KeyError) as e:
        return web.Response(text='Invalid playerCount', status=400)


@jackroutes.get('/jackbox')
async def jackbox_index_handler(request):
    return web.FileResponse('htdocs/jackbox.html')


@jackroutes.get('/jackbox/all')
async def jackbox_index_handler(request):
    return await gallery_handler(request);


@jackroutes.post('/jackbox')
async def jackbox_post_handler(request):
    data = await request.post()
    steamid = None
    try:
        steamid = int(data['steamid'])
    except (ValueError, KeyError) as e:
        return web.Response(text='Invalid SteamId, did you use the Steam64 ID?', status=400)
    return await user_gallery_handler(request, steamid=steamid)


@jackroutes.get('/jackbox/{steamid}')
async def steam_play_handler(request):
    steamid = int(request.match_info['steamid'])
    return await user_gallery_handler(request, steamid)


async def user_gallery_handler(request, steamid: int, onlydraw: bool = False, playerCount: int = 0):
    from jackbox_secrets import STEAM_API_KEY;
    try:
        async with aiohttp.ClientSession() as session:
            my_dict = {
                'steamid': steamid,
                'appids_filter':ALL_APP_IDS
            }
            my_url='https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key=%s&input_json=%s' % (STEAM_API_KEY, json.dumps(my_dict))
            #print(my_url)
            async with session.get(my_url) as resp:
                #print(await resp.text())
                data = await resp.json()
                app_list = list(g['appid'] for g in data['response']['games'] if g['appid'] in ALL_APP_IDS);
                return await gallery_handler(request, onlydraw=False, playerCount=playerCount, filter_games=app_list);
    except Exception as e:
        traceback.print_exc();
        return web.Response(text=str('Error while looking up your profile. is your profile set to public?'))


async def gallery_handler(request, onlydraw: bool = False, playerCount: int = 0, prefix: str = '/', filter_games: list = ALL_APP_IDS):
    result = ""
    with open('htdocs/list.html.part01', 'r') as f:
        result = result + f.read()
    with open('htdocs/list.html.part02', 'r') as f:
        loopy = f.read()
    item = None;
    print(ALL_APP_IDS)
    for game in (g for g in games if g.game.app_id in filter_games and (playerCount == 0 or g.players_min <= playerCount <= g.players_max) and (g.drawing or not onlydraw)):
        item = loopy.replace('{app_id}', str(game.game.app_id))
        item = item.replace('{game_name}', game.name)
        if game.image:
            item = item.replace('{app_icon}', prefix+'images/'+game.game.name.replace(' ','')+'/'+game.image)
        else:
            item = item.replace('{app_icon}', prefix+'images/'+game.game.name.replace(' ','')+'/'+game.name.replace("'",'').replace(' ','') + '.webp')

        item = item.replace('{tooltip_text}', '%s<br/>%s</br>%d - %d players<br/>' % (game.name,game.game.name,game.players_min, game.players_max))
        result = result + item
    if item is None:
        result = '<h1>No games found :(</h1>'
    with open('htdocs/list.html.part03', 'r') as f:
        result = result + f.read()

    return web.Response(content_type='text/html', text=result)


async def cancel_tasks():
    for t in tasklist:
        t.cancel()
        tasklist.remove(t)
        await t


from threading import  Lock

runners = []
tasklist = []
last_static_action = (None, None)
mutex = Lock()

if __name__ == '__main__':
    from jackbox_config import config;

    # web.run_app(setuphttp(config)[0])
    # print("something")
    loop = asyncio.get_event_loop()
    # web.run_app(setuphttp(config)[0])
    loop.create_task(start_site(web.Application(), config))

    try:
        print("starting, config:")
        print(config)
        loop.run_forever()
    except:
        pass
    finally:
        for runner in runners:
            loop.run_until_complete(runner.cleanup())
