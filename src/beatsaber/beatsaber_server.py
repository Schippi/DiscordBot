import random

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
import aiofiles
import os
from beatMain import read_map
import io


bsroutes = web.RouteTableDef()
call_cnt = 0
sys.path.append('..')
import util

def current_milli_time():
    return round(time.time() * 1000)

async def start_site(app: web.Application, theConfig: dict):
    host = theConfig['host']
    port = theConfig['port']
    app.add_routes(bsroutes)
    runner = web.AppRunner(app)
    root_folder = os.path.dirname(sys.argv[0])

    app.router.add_route('*', '/', launcher_handler)

    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

async def launcher_handler(request):
    return await gallery_handler(request);

def strToBoolOrNone(draw: str):
    if draw and draw.lower() in ('true', 'false'):
        return draw.lower() == 'true'
    else:
        return None

async def download_all_loop(users):
    while True:
        await download_all(users, True)
        for i in range(30):
            #print(i)
            await asyncio.sleep(60)

def data_to_db(data,cur):
    doSong = True
    doDiff = True
    debug = 0
    song = data['leaderboard']['song']
    try:
        for row in cur.execute('SELECT id from bs_song where id = ?', (song['id'],)):
            doSong = False
        if doSong:
            cur.execute('insert into bs_song(id,hash,author,mapper,mapper_id,cover_image,duration,uploadtime, name, sub_name) '
                        'select ?,?,?,?,?,?,?,?,?,? from dual', (song['id'],song['hash'],song['author'],song['mapper'],song['mapperId'],song['coverImage'],song['duration'],song['uploadTime'],song['name'],song['subName']))
        debug = 1
        for d in song['difficulties']:
            for row in cur.execute('SELECT id from bs_song_diff where id = ?', (d['id'],)):
                doDiff = False
            if doDiff:
                cur.execute('insert into bs_song_diff(id,id_song,difficultyName,stars,notes,bombs,walls,rankedTime,nps) '
                        'select ?,?,?,?,?,?,?,?,? from dual', (d['id'],song['id'],d['difficultyName'],int(d['stars']*10) if d['stars'] else 0,d['notes'],d['bombs'],d['walls'],d['rankedTime'],str(d['nps'])))
        debug = 2
        d = data['leaderboard']['difficulty']
        doDiff = True
        for row in cur.execute('SELECT id from bs_song_diff where id = ?', (d['id'],)):
            doDiff = False
        if doDiff:
            cur.execute('insert into bs_song_diff(id,id_song,difficultyName,stars,notes,bombs,walls,rankedTime,nps) '
                        'select ?,?,?,?,?,?,?,?,? from dual', (d['id'],song['id'],d['difficultyName'],int(d['stars']*10),d['notes'],d['bombs'],d['walls'],d['rankedTime'],str(d['nps'])))
        debug = 3
        dic = {
            'id_diff':data['leaderboard']['difficulty']['id'],
            'id_user':int(data['playerId']),
            'badCuts':int(data['badCuts']),
            'missedNotes':int(data['missedNotes']),
            'bombCuts':int(data['bombCuts']),
            'wallsHit':int(data['wallsHit']),
            'pauses':int(data['pauses']),
            'fullCombo':int(data['fullCombo']),
            'score':int(data['baseScore']),
            'modifiers':data['modifiers'],
            'replay':data['replay']
        }
        util.updateOrInsert('bs_replay',{'id':data['id']},dic,True)
        util.DB.commit()
    except Exception as e:
        print(e)


async def download_all(users, stopOnPgOne):
    with util.OpenCursor(util.DB) as cur:
        async with aiohttp.ClientSession() as session:
            for p in users:
                os.makedirs('beatsaber/replays/%d' % p, exist_ok=True)
                i = 1
                while i > 0:
                    async with session.get('https://api.beatleader.xyz/player/%d/scores?page=%d' % (p, i)) as resp:
                        if resp.status != 200:
                            print('load page failed user: %d page: %d ' % (p, i))
                            break
                        print('loaded page user: %d page: %d ' % (p, i))
                        i = i + 1
                        data = await resp.json()
                        dld = 0
                        if len(data['data']) == 0:
                            break
                        for x in data['data']:
                            replay_url = x['replay']
                            if replay_url:
                                replay_file_name = replay_url[replay_url.rindex('/')+1:]
                                local_file_name = 'beatsaber/replays/%s/%s' % (p, replay_file_name)
                                if not os.path.exists(local_file_name):
                                    data_to_db(x, cur)
                                    dld = dld + 1
                                    async with session.get(replay_url) as resp:
                                        if resp.status != 200:
                                            print(resp.status)
                                            break
                                        f = await aiofiles.open(local_file_name, mode='wb')
                                        await f.write(await resp.read())
                                        await f.close()
                            else:
                                print('REPLAY MISSING !?!? ' + str(x['id']))
                        if dld == 0 and stopOnPgOne:
                            break

@bsroutes.get('/bs/songs')
async def replay_handler(request):
    with util.OpenCursor(util.DB) as cur:
        result = ''
        with open('beatsaber/htdocs/list.html.part01', 'r') as f:
            result = result + f.read();
        with open('beatsaber/htdocs/list.html.part02', 'r') as f:
            loopstr = f.read();
        for row in cur.execute('SELECT * from bs_song '):
            a = loopstr.replace('{song_id}', row['id']).replace('{cover}', row['cover_image']).replace('{mytxt}',row['name'] + ' ' + row['subname'])
            result = result + a
        with open('beatsaber/htdocs/list.html.part03', 'r') as f:
            result = result + f.read();

        return web.Response(content_type='text/html', text=result)

@bsroutes.get('/bs/song/{song_id}')
async def urlredirector(request):
    song_id = request.match_info['song_id']

@bsroutes.get('/bs/replay/{score_id}')
async def replay_handler(request):
    score_id = request.rel_url.query['score']
    if not score_id:
        return web.Response(status=400, reason='no score id')
    try:
        score_id = int(score_id)
    except:
        return web.Response(status=400, reason='score id invalid')





    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.beatleader.xyz/score/%d' % score_id) as resp:
            if resp.status != 200:
                return web.Response(text=await resp.text(), status=resp.status, reason=resp.reason)
            data = await resp.json()
            replay_url = data['replay']
            replay_file_name = replay_url[replay_url.rindex('/')+1:]
            os.makedirs('beatsaber/replays/%s' % data['playerId'], exist_ok=True)
        local_file_name = 'beatsaber/replays/%s/%s' % (data['playerId'], replay_file_name)
        if not os.path.exists(local_file_name):
            async with session.get(replay_url) as resp:
                if resp.status != 200:
                    return web.Response(text=await resp.text(), status=resp.status, reason=resp.reason)
                f = await aiofiles.open(local_file_name, mode='wb')
                await f.write(await resp.read())
                await f.close()
    fig = read_map(local_file_name)

    with util.OpenCursor(util.DB) as cur:
        for row in cur.execute('select * from bs_replay br '
                               'left join bs_song_diff bsf on br.id_diff = bsf.id '
                               'left join bs_song bs on bsf.id_song = bs.id '
                               'where br.id = ?',(score_id,)):
            replay_url = row['replay']
            fig.update_layout(
                title=row['name']
            )
    buf = io.StringIO()
    fig.write_html(buf)

    return web.Response(text=buf.getvalue(), content_type='text/html')

if __name__ == '__main__':
    config = {
        'host': '::',
        'port': 8080
    }

    loop = asyncio.get_event_loop()
    loop.create_task(start_site(web.Application(), config))
    loop.create_task(download_all_loop([4476, 4478]))
    try:
        print("starting, config:")
        print(config)
        loop.run_forever()
    except Exception as e:
        pass
