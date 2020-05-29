'''
Created on 17 May 2020

@author: Carsten Schipmann
'''

from aiohttp import web;
import aiohttp;
import aiohttp_session;
from aiohttp_session import setup, get_session;
from aiohttp_session.cookie_storage import EncryptedCookieStorage;
import asyncio;
import util;
import json;
from entities import TwitchEntry;
from TwitchChecker import streamonline;
from TwitchChecker import printEntry;
from TwitchChecker import stuff_lock;
from entities.TwitchAPI.TwitchAPI import TwitchUser;
from entities.TwitchAPI.TwitchAPI import TwitchStream;
from util import logEx;
import traceback;
import sys;
import datetime;
import base64;
from cryptography import fernet;
from util import HELIX;
import ssl;

routes = web.RouteTableDef();
routes.static('/blubb', "./ressources", show_index=True);

web_srv_session = aiohttp.ClientSession(); 

bot_client = None;

clientsession = aiohttp.ClientSession(); 

def setup(my_client):
    global bot_client;
    bot_client = my_client;
    app = web.Application();
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    storage = EncryptedCookieStorage(secret_key);
    #print(storage.cookie_params)
    #storage.cookie_params['samesite']='strict';
    #storage.save_cookie(response, cookie_data)
    aiohttp_session.setup(app, storage);
    
    
    app.add_routes(routes);
    
    runner = web.AppRunner(app);
   
    
    asyncio.get_event_loop().run_until_complete(runner.setup())
    
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(util.cfgPath+'/domain_srv.crt', util.cfgPath+'/domain_srv.key');

    website = web.TCPSite(runner, util.serverHost, util.serverPort,ssl_context = ssl_context)
    return website;

@routes.get('/subs')
async def subs_main(request):
    if 'error' in request.rel_url.query.keys():
        return str(request.rel_url.query);
    
    print("subs  "+str(request.rel_url.query.keys()))
    session = await get_session(request);
    
    print(request.url);
    
    if 'code' in request.rel_url.query.keys():
        html = await util.posting(clientsession, 'https://id.twitch.tv/oauth2/token?'
                                                                    +'client_id='+util.TwitchAPI
                                                                    +'&client_secret='+util.TwitchSECRET
                                                                    +'&code='+request.rel_url.query['code']
                                                                    +'&grant_type=authorization_code'
                                                                    +'&redirect_uri=https://'+util.serverFull+'/subs'
                                                                    , None, None);
        print(html);
        myjson = json.loads(html);
        access_token = myjson['access_token'];
        refresh_token = myjson['refresh_token'];
    
    if access_token:
        html = await util.fetchUser(clientsession,HELIX+'users',{'client-id':util.TwitchAPI,
                                                                                'Accept':'application/vnd.twitchtv.v5+json',
                                                                                'Authorization':'Bearer '+access_token});
        print(html)       
        
        myjson = json.loads(html);
        mydata = myjson['data'][0]; 
        
        session['last_page'] = mydata['display_name'].lower();
        print('saved last page: '+session['last_page'])
        html = await util.fetchUser(clientsession,HELIX+'subscriptions',{'client-id':util.TwitchAPI,
                                                                                'Accept':'application/vnd.twitchtv.v5+json',
                                                                                'Authorization':'Bearer '+access_token});
        print(html)                                                                        
        
        
        util.DBcursor.execute('update twitch_person set subs_auth_token = ? , refresh_token = ? where id = ?',(access_token,refresh_token,mydata['id']));
        util.DB.commit();
    
    if not ('last_page' in session.keys()):
        session['last_page'] = 'Dalai_Lama'
    #raise web.HTTPFound(location='/subs/'+session['last_page']);
    return web.Response(text=str(request));
    

@routes.get('/subs/{name}')
async def subs(request):
    
    name = request.match_info['name'].lower();
    print("subs/"+name+"   "+str(request.rel_url.query.keys()))
    session = await get_session(request);
    session['last_page'] = name;
    
    for row in util.DBcursor.execute('select id,subs_auth_token,subs from twitch_person where lower(display_name) = ?',(name,)):
        hookvalid = False;
        userAuth = row['subs_auth_token'];
        user_id = row['id'];
        if userAuth and (userAuth != ''):
            
            oauthToken = util.getControlVal('token_oauth','');
            #look if webhook still valid
            html = await util.fetch(clientsession,HELIX+'webhooks/subscriptions',{'client-id':util.TwitchAPI,
                                                                                                'Accept':'application/vnd.twitchtv.v5+json',
                                                                                                'Authorization':'Bearer '+oauthToken});
            #check time of hook
            
        if not hookvalid:
            try:
                if not userAuth:
                    raise util.AuthFailed;
                payload = {'hub.callback':('https://'+util.serverFull+'/subhook?user_name='+name+'&user_id='+user_id),
                           "hub.mode":"subscribe",
                           "hub.topic":HELIX+'subscriptions/events?first=1&broadcaster_id='+str(user_id),
                           "hub.lease_seconds":120
                           };
                print(str(payload))
                html = await util.posting(clientsession, HELIX+'webhooks/hub', str(payload).replace('\'','"'),headers = {'client-id':util.TwitchAPI,
                                                                                                'Accept':'application/vnd.twitchtv.v5+json',
                                                                                                'Authorization':'Bearer '+userAuth,
                                                                                                'Content-Type': 'application/json'
                                                                                            })
                #create webhook
                print(html);
                #html = await util.fetchUser(clientsession,HELIX+'subscriptions/events?first=1&broadcaster_id='+str(user_id),{'client-id':util.TwitchAPI,
                #                                                                                'Accept':'application/vnd.twitchtv.v5+json',
                #                                                                                'Authorization':'Bearer '+userAuth});
                print(html);
            except util.AuthFailed as aex:
                auth_url = 'https://id.twitch.tv/oauth2/authorize?client_id='+util.TwitchAPI+'&redirect_uri=https://'+util.serverFull+'/subs&response_type=code&scope=channel:read:subscriptions';
                raise web.HTTPFound(location=auth_url);
                pass;
            #subscribe to webhook
    
    with open("ressources/subs.html", "r") as f: 
        es = f.read().replace('{REPLACE_ME}',name);
    return web.Response(text=es,content_type = 'text/html');

@routes.get('/subcounter/{name}')
async def subcount(request):
    su = util.getSubs(request.match_info['name'].lower())
    return web.Response(text=str(su));

@routes.get('/robots.txt')
async def robots(_):  
    return web.Response(text='''User-agent: *\n\rDisallow: /''');



        
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
    global stuff_lock
    with (await stuff_lock):
        if (len(myjson) == 0):
            streamonline[user_name] = False;
            util.DBcursor.execute('update twitch_person set last_check_status = ? , last_check = ? where id = ?',('offline',util.dateToStr(datetime.datetime.now()),user_id) );
            util.DB.commit();
        else:
            util.DBcursor.execute('update twitch_person set last_check_status = ? , last_check = ? where id = ?',('online',util.dateToStr(datetime.datetime.now()),user_id) );
            util.DB.commit();
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
                            if (user_name in streamonline.keys()) and streamonline[user_name]:
                                #edit maybe
                                await printEntry(bot_client,entr,stream.isRerun(),stream.user_name,stream.game,stream.url,''+stream.title,stream.thumbnail_url,True);
                                logEx('WEB EDIT: sent Twitch message for '+stream.user_name);
                            else:
                                await printEntry(bot_client,entr,stream.isRerun(),stream.user_name,stream.game,stream.url,''+stream.title,stream.thumbnail_url);
                                logEx('WEB: sent Twitch message for '+stream.user_name);
                            #sayWords(None, entr.getYString(n,sGame,sURL,sLogo,sTitle), entr.guild, entr.channel);
                            #print(10);
                    except Exception as e:
                        print(stream.user_name)
                        traceback.print_exc(file=sys.stdout);
                        logEx(e);      
            streamonline[user_name] = True;


