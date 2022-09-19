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
import typing

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

async def data_to_db(data,cur):
    doSong = True
    doDiff = True
    debug = 0
    if not data['leaderboard'] and data['leaderboardId']:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.beatleader.xyz/leaderboard/%s' % (data['leaderboardId'],)) as resp:
                if resp.status == 200:
                    data['leaderboard'] = await resp.json()
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
            'replay':data['replay'],
            'timeset':int(data['timeset']),
        }
        util.updateOrInsert('bs_replay',{'id':data['id']},dic,True,False)
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
                                local_file_name = 'beatsaber/replays/%s/%s%s' % (p, x['id'], replay_file_name)
                                if not os.path.exists(local_file_name):
                                    id_less = 'beatsaber/replays/%s/%s' % (p, replay_file_name)
                                    if os.path.exists(id_less):
                                        os.rename(id_less, local_file_name)
                                        print('renamed')
                                        dld = dld + 1
                                        continue
                                    await data_to_db(x, cur)
                                    dld = dld + 1
                                    async with session.get(replay_url) as resp:
                                        if resp.status != 200:
                                            print(resp.status)
                                            break
                                        f = await aiofiles.open(local_file_name, mode='wb')
                                        await f.write(await resp.read())
                                        await f.close()
                                else:
                                    await data_to_db(x, cur)
                            else:
                                print('REPLAY MISSING !?!? ' + str(x['id']))
                        if dld == 0 and stopOnPgOne:
                            break

@bsroutes.get('/bs/songs')
async def replay_handler(request):
    with util.OpenCursor(util.DB) as cur:
        result = ''
        with open('beatsaber/htdocs/list.html.part01', 'r') as f:
            result = result + f.read()
        with open('beatsaber/htdocs/list.html.part02', 'r') as f:
            loopstr = f.read()
        for row in cur.execute('SELECT * from bs_song order by name'):
            a = loopstr.replace('{song_id}', row['id']).replace('{cover}', row['cover_image']).replace('{mytxt}',row['name'] + ' ' + row['sub_name'])
            result = result + a
        with open('beatsaber/htdocs/list.html.part03', 'r') as f:
            result = result + f.read()

        result = insert_bs_header(result)

        return web.Response(content_type='text/html', text=result)

@bsroutes.get('/bs/song/{song_id}')
async def urlredirector(request):
    song_id = request.match_info['song_id']
    result = ''
    with util.OpenCursor(util.DB) as cur:
        song = [s for s in cur.execute('SELECT * from bs_song where id = ?',(song_id,))][0]
        with open('beatsaber/htdocs/song/song.html.part01.header', 'r') as f:
            result = result + f.read()
        with open('beatsaber/htdocs/song/song.html.part02.diff', 'r') as f:
            difftxt = f.read()
        with open('beatsaber/htdocs/song/song.html.part03.replay', 'r') as f:
            repltxt = f.read()
        with open('beatsaber/htdocs/song/song.html.part04.diffend', 'r') as f:
            diffendtxt = f.read()
        for dif in cur.execute('SELECT * from bs_song_diff sd where sd.id_song = ?',(song_id,)):
            result = result + difftxt.replace('{mytxt}',dif['difficultyname'])
            replays = [rep for rep in cur.execute('SELECT * from bs_replay r where r.id_diff = ?',(dif['id'],))]
            result = result + html_table(replays)
            result = result + diffendtxt
        with open('beatsaber/htdocs/song/song.html.part05.end', 'r') as f:
            result = result + f.read()
        result = insert_bs_header(result)

    return web.Response(content_type='text/html', text=result)


def insert_bs_header(result):
    with open('beatsaber/htdocs/headonly.html.head', 'r') as f:
        result = result.replace('<bshead/>', f.read())
    return result


def html_table(stuff:typing.List[dict]):
    result = '<table>'
    if len(stuff) == 0:
        return ''
    result = result + '<tr>'
    for k in stuff[0].keys():
        result = result + '<th>' + k + '</th>'
    result = result + '</tr>'
    for d in stuff:
        result = result + '<tr>'
        for k,v in d.items():
            if k == 'replay':
                result = result + '<td><a href="/bs/replay/' + str(d['id']) + '">click</a></td>'
            else:
                result = result + '<td>' + str(v) + '</td>'
        result = result + '</tr>'
    result = result + '</table>'
    return result

@bsroutes.get('/bs/replay/{score_id}')
async def replay_handler(request):
    vgl_score = request.rel_url.query['vgl'] if 'vgl' in request.rel_url.query else None
    o_score = request.match_info['score_id']
    if not o_score:
        return web.Response(status=400, reason='no score id')
    try:
        o_score = int(o_score)
        if vgl_score:
            vgl_score = int(vgl_score)
    except:
        return web.Response(status=400, reason='score id invalid')
    fig=None
    for score_id in [o_score, vgl_score]:
        if not score_id:
            continue
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.beatleader.xyz/score/%d' % score_id) as resp:
                if resp.status != 200:
                    return web.Response(text=await resp.text(), status=resp.status, reason=resp.reason)
                data = await resp.json()
                with util.OpenCursor(util.DB) as cur:
                    if data['id'] != score_id:
                        for row in cur.execute('select * from bs_replay where id = ?',(score_id,)):
                            data['replay'] = row['replay']
                            data['id'] = score_id
                    for row in cur.execute('select * from dual where not exists (select * from bs_replay where id = ?)',(score_id,)):
                        await data_to_db(data, cur)
                replay_url = data['replay']
                replay_file_name = replay_url[replay_url.rindex('/')+1:]
                os.makedirs('beatsaber/replays/%s' % data['playerId'], exist_ok=True)
            local_file_name = 'beatsaber/replays/%s/%s%s' % (data['playerId'], data['id'], replay_file_name)
            if not os.path.exists(local_file_name):
                async with session.get(replay_url) as resp:
                    if resp.status != 200:
                        return web.Response(text=await resp.text(), status=resp.status, reason=resp.reason)
                    f = await aiofiles.open(local_file_name, mode='wb')
                    await f.write(await resp.read())
                    await f.close()
        fig = read_map(local_file_name, fig=fig)

    with util.OpenCursor(util.DB) as cur:
        for row in cur.execute('select * from bs_replay br '
                               'left join bs_song_diff bsf on br.id_diff = bsf.id '
                               'left join bs_song bs on bsf.id_song = bs.id '
                               'where br.id = ?',(o_score,)):
            replay_url = row['replay']
            fig.update_layout(
                title=row['name']
            )
    buf = io.StringIO()
    fig.update_layout(template='plotly_dark')
    fig.write_html(buf)
    with open('beatsaber/htdocs/headonly.html.head', 'r') as f:
        head_result = f.read()
    val = buf.getvalue().replace('<head>', head_result)
    return web.Response(text=val, content_type='text/html')

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
