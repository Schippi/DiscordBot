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

async def start_site(app: web.Application, config: dict):
    host = config['host']
    port = config['port']
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
    return web.FileResponse('jackboxLauncher/htdocs/jackbox.html')


@jackroutes.get('/jackbox/')
async def jackbox_index_handler_2(request):
    return await jackbox_index_handler(request)


@jackroutes.get('/jackbox/all')
async def jackbox_list_index_handler(request):
    return await gallery_handler(request);


@jackroutes.post('/jackbox')
async def jackbox_post_handler(request):
    data = await request.post()
    steamid = None
    try:
        steamid = int(data['steamid'])
    except (ValueError, KeyError) as e:
        return web.Response(text='Invalid SteamId, did you use the Steam64 ID?', status=400)
    raise web.HTTPFound('/jackbox/'+str(steamid))


@jackroutes.get('/jackbox/{steamid}')
async def steam_play_handler(request):
    steamid = int(request.match_info['steamid'])
    return await user_gallery_handler(request, steamid)

@jackroutes.get('/jackbox/{steamid}/draw')
async def steam_play_handler(request):
    steamid = int(request.match_info['steamid'])
    return await user_gallery_handler(request, steamid, onlydraw=True)

@jackroutes.get('/jackbox/{steamid}/draw/{playerCount}')
async def steam_play_handler(request):
    steamid = int(request.match_info['steamid'])
    return await user_gallery_handler(request, steamid, onlydraw=True, playerCount=int(request.match_info['playerCount']))


async def user_gallery_handler(request, steamid: int, onlydraw: bool = False, playerCount: int = 0):
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
                return await gallery_handler(request, onlydraw=False, playerCount=playerCount, filter_games=app_list);
    except Exception as e:
        traceback.print_exc();
        return web.Response(text=str('Error while looking up your profile. is your profile set to public?'))


async def gallery_handler(request, onlydraw: bool = False, playerCount: int = 0, prefix: str = '/', filter_games: list = ALL_APP_IDS):
    result = ""
    with open('jackboxLauncher/htdocs/list.html.part01', 'r') as f:
        result = result + f.read()
    with open('jackboxLauncher/htdocs/list.html.part02', 'r') as f:
        loopy = f.read()
    item = None;
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
