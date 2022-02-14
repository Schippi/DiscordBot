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

async def start_site(app: web.Application, theConfig: dict):
    host = theConfig['host']
    port = theConfig['port']
    app.add_routes(jackroutes)
    runner = web.AppRunner(app)
    root_folder = os.path.dirname(sys.argv[0])
    app.router.add_static('/images', root_folder+'/images')
    app.router.add_static('/css', root_folder+'/htdocs/css')
    app.router.add_route('*', '/', launcher_handler)

    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

async def launcher_handler(request):
    return await gallery_handler(request);

def strToBoolOrNone(draw: str):
    if draw and draw.lower() in ('true', 'false'):
        return bool(draw)
    else:
        return None

@jackroutes.get('/jackbox')
async def jackbox_index_handler(request):
    steamid = request.rel_url.query.get('steamid', None)
    if steamid:
        try:
            steamid = int(steamid)
        except ValueError:
            return web.Response(text='Invalid SteamId, did you use the Steam64 ID?', status=400)
    draw = request.rel_url.query.get('draw', None)
    draw = strToBoolOrNone(draw)
    try:
        playerCount = int(request.rel_url.query.get('playerCount', '0'))
    except ValueError:
        playerCount = 0
    localOnly = request.rel_url.query.get('localOnly', None)
    localOnly = strToBoolOrNone(localOnly)
    if not steamid and not draw and not localOnly and playerCount == 0:
        return web.FileResponse('jackboxLauncher/htdocs/jackbox.html')
    if steamid:
        return await user_gallery_handler(request, steamid, onlydraw=draw, playerCount=playerCount, localOnly=localOnly)
    else:
        return await gallery_handler(request, onlydraw=draw, playerCount=playerCount, localOnly=localOnly)


@jackroutes.get('/jackbox/')
async def jackbox_index_handler_2(request):
    return await jackbox_index_handler(request)


@jackroutes.get('/jackbox/all')
async def jackbox_list_index_handler(request):
    return await gallery_handler(request)


@jackroutes.post('/jackbox')
async def jackbox_post_handler(request):
    data = await request.post()
    steamid = None
    try:
        steamid = int(data['steamid'])
    except (ValueError, KeyError) as e:
        return web.Response(text='Invalid SteamId, did you use the Steam64 ID?', status=400)
    raise web.HTTPFound('/jackbox?steamid='+str(steamid))


async def user_gallery_handler(request, steamid: int, onlydraw: bool = None, playerCount: int = 0, localOnly: bool = None):
    from jackbox_secrets import STEAM_API_KEY;
    try:
        async with aiohttp.ClientSession() as session:
            my_dict = {
                'steamid': steamid,
                'appids_filter': list(ALL_APP_IDS)
            }
            my_url='https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key=%s&input_json=%s' % (STEAM_API_KEY, json.dumps(my_dict))
            #print(my_url)
            async with session.get(my_url) as resp:
                #print(await resp.text())
                data = await resp.json()
                app_list = list(g['appid'] for g in data['response']['games'] if g['appid'] in ALL_APP_IDS);
                return await gallery_handler(request, onlydraw=onlydraw, playerCount=playerCount, filter_games=app_list, localOnly=localOnly)
    except Exception as e:
        traceback.print_exc()
        return web.FileResponse('jackboxLauncher/htdocs/errorSteamAPI.html')


async def gallery_handler(request, onlydraw: bool = False, playerCount: int = 0, prefix: str = '/', filter_games: list = ALL_APP_IDS, localOnly: bool = None):
    result = ""
    with open('jackboxLauncher/htdocs/list.html.part01', 'r') as f:
        result = result + f.read()
    with open('jackboxLauncher/htdocs/list.html.part02', 'r') as f:
        loopy = f.read()
    item = None
    for game in (g for g in games if g.game.app_id in filter_games and (playerCount == 0 or g.players_min <= playerCount <= g.players_max) and (g.drawing == onlydraw or not onlydraw) and (g.local_recommended == localOnly or not localOnly)):
        item = loopy.replace('{app_id}', str(game.game.app_id))
        item = item.replace('{game_name}', game.name)
        if game.image:
            item = item.replace('{app_icon}', prefix+'images/'+game.game.name.replace(' ','')+'/'+game.image)
        else:
            item = item.replace('{app_icon}', prefix+'images/'+game.game.name.replace(' ','')+'/'+game.name.replace("'", '').replace(' ', '') + '.webp')

        item = item.replace('{tooltip_text}', '%s<br/>%s</br>%d - %d players<br/>' % (game.name,game.game.name,game.players_min, game.players_max))
        result = result + item
    if item is None:
        return web.FileResponse('jackboxLauncher/htdocs/nogames.html')
    with open('jackboxLauncher/htdocs/list.html.part03', 'r') as f:
        result = result + f.read()

    return web.Response(content_type='text/html', text=result)

if __name__ == '__main__':
    from jackbox_config import config;

    loop = asyncio.get_event_loop()
    # web.run_app(setuphttp(config)[0])
    loop.create_task(start_site(web.Application(), config))

    try:
        print("starting, config:")
        print(config)
        loop.run_forever()
    except Exception as e:
        pass
