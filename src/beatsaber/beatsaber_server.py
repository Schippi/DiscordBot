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


    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

def strToBoolOrNone(draw: str):
    if draw and draw.lower() in ('true', 'false'):
        return draw.lower() == 'true'
    else:
        return None

async def download_all_loop(users):
    await asyncio.sleep(20)
    while True:
        await download_all(users, False)
        #sleep 3 hours
        await asyncio.sleep(60*60*3)

async def data_to_db(data,cur):
    doSong = True
    doDiff = True
    debug = 0
    print(data['id'] if 'id' in data else 'no id')
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
        with util.OpenCursor(util.DB) as cur:
            rows = [row for row in cur.execute('SELECT id_user from bs_user where id_user = ?', (data['playerId'],))]
            if len(rows) == 0:
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://api.beatleader.xyz/player/%s' % (data['playerId'],)) as resp:
                        if resp.status == 200:
                            player_data =  await resp.json()
                            cur.execute('insert into bs_user(id_user, user_name) values(?,?)', (player_data['id'], player_data['name'],))
                return
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
            'pp':float(data['timeset']),
        }
        util.updateOrInsert('bs_replay',{'id':data['id']},dic,True,True)
        util.DB.commit()
    except Exception as e:
        print(e)


def stats_to_db(d):
    dic = {'id': d['id'],
           'timestamp': d['timestamp'],
           'id_user': d['playerId'],
           'rank': d['rank'],
           'country_rank': d['countryRank'],
           'pp': d['pp']
           }
    util.updateOrInsert('bs_user_stats', {'id': d['id']}, dic, True, True)
    util.DB.commit()


async def sync_stats(p, session):
    async with session.get('https://api.beatleader.xyz/player/%s/history?count=60' % (p,)) as resp:
        if resp.status == 200:
            data = await resp.json()
            for d in data:
                stats_to_db(d)


async def download_all(users, stopOnPgOne):
    with util.OpenCursor(util.DB) as cur:
        last_time = 0
        for row in cur.execute('SELECT * from control where key = ?',('bs_last_fetch',)):
            last_time = int(row['value'])
        save_time = last_time
        count = 0
        async with aiohttp.ClientSession() as session:
            for p in users:
                await sync_stats(p, session)
                os.makedirs('beatsaber/replays/%d' % p, exist_ok=True)
                i = 1
                while i > 0:
                    url = 'https://api.beatleader.xyz/player/%d/scores?time_from=%d&page=%d' % (p, last_time + 1, i)
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            print('load page failed user: %d page: %d ' % (p, i))
                            break
                        #print('loaded page user: %d page: %d ' % (p, i))

                        data = await resp.json()
                        dld = 0
                        if len(data['data']) == 0:
                            break
                        count = count + len(data['data'])
                        for x in data['data']:
                            save_time = max(save_time,int(x['timepost']))
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
                        i = i + 1 if data['metadata']['page'] < data['metadata']['total'] - i * data['metadata']['itemsPerPage'] else -1

        if save_time != last_time:
            cur.execute('update control set value = ? where key = ?',(str(save_time), 'bs_last_fetch',))
            util.DB.commit()

        print('dowloaded %d replays - %s' % (count,url))




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
        songs = [s for s in cur.execute('SELECT * from bs_song where id = ?',(song_id,))]
        if len(songs) == 0:
            raise web.HTTPNotFound()
        song = songs[0]
        with open('beatsaber/htdocs/song/song.html.part01.header', 'r') as f:
            result = result + f.read()
        with open('beatsaber/htdocs/song/song.html.part02.diff', 'r') as f:
            difftxt = f.read()
        with open('beatsaber/htdocs/song/song.html.part03.replay', 'r') as f:
            repltxt = f.read()
        with open('beatsaber/htdocs/song/song.html.part04.diffend', 'r') as f:
            diffendtxt = f.read()
        difs = [d for d in cur.execute('SELECT * from bs_song_diff where id_song = ? order by difficultyName', (song_id,))]
        for dif in difs:
            result = result + difftxt.replace('{mytxt}',dif['difficultyname'])
            replays = [rep for rep in cur.execute('''SELECT 
            id,ifnull(user_name,r.id_user) as user,badcuts,missednotes,bombcuts,wallshit,pauses,fullcombo,replay,modifiers,score, 
            datetime(timeset, 'unixepoch', 'localtime') as timeset 
            from bs_replay r  
            left join bs_user u on u.id_user = r.id_user  
            where r.id_diff = ?''',(dif['id'],))]
            #'<a href="/bs/replay/' || id || '">replay</a>' as replaylink
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
    post_fig_stats = []
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
        user_name = 'Unknown'
        with util.OpenCursor(util.DB) as cur:
            for row in cur.execute('select * from bs_replay br '
                                   'left join bs_song_diff bsf on br.id_diff = bsf.id '
                                   'left join bs_song bs on bsf.id_song = bs.id '
                                   'left join bs_user bu on bu.id_user = br.id_user '
                                   'where br.id = ?',(score_id,)):
                replay_url = row['replay']
                user_name = row['user_name']
                id_song= row['id_song']
        fig,map = read_map(local_file_name, fig=fig, suffix='(%s)' % user_name)
        fig.update_layout(
            title= '<a target="_self" href="/bs/song/%s">%s</a>' % (id_song, row['name']) if 'name' in row else 'Unknown',
        )
        max_in_a_row = 0
        in_a_row = 0
        stats = {}
        for n in map.notes:
            if n.score == 115:
                in_a_row += 1
            else:
                max_in_a_row = max(max_in_a_row, in_a_row)
                in_a_row = 0
        max_in_a_row = max(max_in_a_row, in_a_row)
        post_fig_stats.append({'stat':'115\'s in a row - %s' % user_name, 'value':max_in_a_row})
        if map.fc_acc[1] > 0:
            post_fig_stats.append({'stat':'fc acc left - %s' % user_name,'value':map.fc_acc[0]/map.fc_acc[1]})
        if map.fc_acc[3] > 0:
            post_fig_stats.append({'stat':'fc acc right - %s' % user_name,'value':map.fc_acc[2]/map.fc_acc[3]})
        if map.fc_acc[1] > 0 and map.fc_acc[3] > 0:
            post_fig_stats.append({'stat':'fc acc - %s' % user_name,'value':(map.fc_acc[0]+map.fc_acc[2])/(map.fc_acc[1]+map.fc_acc[3])})
        #post_fig_stats.append(stats)


    buf = io.StringIO()
    fig.update_layout(template='plotly_dark')
    fig.write_html(buf)
    with open('beatsaber/htdocs/headonly.html.head', 'r') as f:
        head_result = f.read()
    val = buf.getvalue().replace('<head>', head_result)
    val = buf.getvalue().replace('</html>', html_table(post_fig_stats) + '</html>')

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
