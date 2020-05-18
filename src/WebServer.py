'''
Created on 17 May 2020

@author: Carsten Schipmann
'''

from aiohttp import web;
import aiohttp;
import asyncio;
import util;
import json;
from entities import TwitchEntry;
from TwitchChecker import streamonline;
from TwitchChecker import printEntry;
from entities.TwitchAPI.TwitchAPI import TwitchUser;
from entities.TwitchAPI.TwitchAPI import TwitchStream;
from util import logEx;
import traceback;
import sys;
import datetime;

routes = web.RouteTableDef();

web_srv_session = aiohttp.ClientSession(); 

bot_client = None;

def setup(my_client):
    global bot_client;
    bot_client = my_client;
    app = web.Application();
    app.add_routes(routes);
    
    runner = web.AppRunner(app);
    
    asyncio.get_event_loop().run_until_complete(runner.setup())
    website = web.TCPSite(runner, util.serverHost, util.serverPort)
    return website;
        
@routes.get('/webhook')
async def handle_webhook(request):  
    print('webhook was accepted ('+str(request.rel_url.query)+')');
    if not 'hub.challenge' in request.rel_url.query.keys():
        return web.HTTPExpectationFailed();
    return web.Response(text=request.rel_url.query['hub.challenge'])

@routes.post('/webhook')
async def handle_notif(request):
    try:
        data = (await request.content.read()).decode("utf-8");
        asyncio.get_event_loop().create_task(handle_data(request,data));
    except:
        return web.HTTPInternalServerError();
    return web.Response(text='OK');

async def handle_data(request,data):
    global bot_client;
    myjson = json.loads(data)['data'];
    user_id = request.rel_url.query['user_id'];
    user_name = request.rel_url.query['user_name'].lower();
    
    global streamonline; 
    
    
    
    if len(myjson == 0):
        streamonline[user_name] = False;
        util.DBcursor.execute('update twitch_person set last_check_status = ? , last_check = ? where userid = ?',('offline',util.dateToStr(datetime.datetime.now()),user_id) );
        util.DB.commit();
    else:
        util.DBcursor.execute('update twitch_person set last_check_status = ? , last_check = ? where userid = ?',('online',util.dateToStr(datetime.datetime.now()),user_id) );
        util.DB.commit();
        streamonline[user_name] = True;
        gamesToFetch = set([k['game_id'] for k in myjson]);
        oauthToken = util.getControlVal('token_oauth','');
        games = await util.getGames(gamesToFetch,web_srv_session,oauthToken);
            
        for item in myjson:
            stream = TwitchStream(item);
            stream.game = games[stream.game_id];
            
            for row in util.DBcursor.execute('SELECT * FROM twitch where userid = ? and lower(username) = ?',(user_id,user_name,)):
                entr = TwitchEntry.TwitchEntry(row);
                try:                                       #print(streamprinted[entr]);
                    if (entr.shouldprint(stream.game)):
                        if user_name in streamonline:
                            #edit maybe
                            await printEntry(bot_client,entr,stream.isRerun(),stream.user_name,stream.game,stream.url,'WEBHOOK TEST EDIT:'+stream.title,stream.thumbnail_url);
                            pass;
                        else:
                            await printEntry(bot_client,entr,stream.isRerun(),stream.user_name,stream.game,stream.url,'WEBHOOK TEST:'+stream.title,stream.thumbnail_url);
                        #sayWords(None, entr.getYString(n,sGame,sURL,sLogo,sTitle), entr.guild, entr.channel);
                        logEx('WEB: sent Twitch message for '+stream.user_name);
                        #print(10);
                except Exception as e:
                    print(stream.user_name)
                    traceback.print_exc(file=sys.stdout);
                    logEx(e);      
    
    pass;



