'''
Created on 17 May 2020

@author: Carsten Schipmann
'''

from aiohttp import web;
import aiohttp
import aiohttp_session;
from aiohttp_session import get_session;
from aiohttp_session.cookie_storage import EncryptedCookieStorage;
import asyncio;
import util;
import json;
from entities import TwitchEntry;
from TwitchChecker import printEntry;
from entities.TwitchAPI.TwitchAPI import TwitchStream;
from util import logEx;
import traceback;
import sys;
import datetime;
import base64;
from cryptography import fernet;
from util import HELIX;
import ssl;
import logging;
import time;

log = logging.getLogger(__name__);
routes = web.RouteTableDef();
routes.static('/blubb', "./ressources", show_index=True);

web_srv_session = aiohttp.ClientSession(); 

bot_client = None;
httpsapp = None;
import os;

clientsession = aiohttp.ClientSession(); 


def setup(my_client, testing):
	global bot_client;
	global httpsapp;
	bot_client = my_client;
	app = web.Application();
	httpsapp = app;
	fernet_key = fernet.Fernet.generate_key()
	secret_key = base64.urlsafe_b64decode(fernet_key)
	storage = EncryptedCookieStorage(secret_key);
	#print(storage.cookie_params)
	#storage.cookie_params['samesite']='strict';
	#storage.save_cookie(response, cookie_data)
	aiohttp_session.setup(app, storage);
	
	
	app.add_routes(routes);
	sys.path.insert(0, 'jackboxLauncher')
	from jackbox_server import jackroutes;
	app.add_routes(jackroutes);
	sys.path.insert(0, 'beatsaber')
	from beatsaber_server import bsroutes
	app.add_routes(bsroutes)

	runner = web.AppRunner(app);
	root_folder = os.path.dirname(__file__)
	app.router.add_static('/images', root_folder+'/jackboxLauncher/images')

	app.router.add_static('/css', root_folder+'/jackboxLauncher/htdocs/css')

	asyncio.get_event_loop().run_until_complete(runner.setup())
	if not testing:
		ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
		ssl_context.load_cert_chain(util.cfgPath+'/fullchain.pem', util.cfgPath+'/privkey.pem');

		website = web.TCPSite(runner, util.serverHost, util.serverPort, ssl_context = ssl_context)
	else:
		website = web.TCPSite(runner, util.serverHost, util.serverPort)

	return website;

async def handle_http(request):
	u = str(request.url)
	if u.startswith('http:'):
		global httpsapp;
		x = await httpsapp.router.resolve(request); 
		if not isinstance(x,aiohttp.web_urldispatcher.MatchInfoError):
			log.info('redirecting')
			raise web.HTTPFound(location=('https:'+u[5:]));
		else:
			raise web.HTTPNotFound();
	else:
		raise web.HTTPNotFound();

def setuphttp():
	apphttp = web.Application();
	apphttp.router.add_route('GET', '/{tail:.*}', handle_http)
	
	runner = web.AppRunner(apphttp);
	   
	asyncio.get_event_loop().run_until_complete(runner.setup())
	
	website = web.TCPSite(runner, util.serverHost, 80);
	
	return website;

@routes.get('/u/{shorthand}')
async def urlredirector(request):
	shorthand = request.match_info['shorthand'];
	c = util.DB.cursor();
	for row in c.execute('select * from urlmap where short = ?',(shorthand,)):
		c.execute('update urlmap set used = used +1 where short = ?',(shorthand,));
		raise web.HTTPFound(location=row['long']);
	raise web.HTTPNotFound();

@routes.get('/d/{token}')
async def discorddisplay(request):
	token = request.match_info['token'];
	c = util.DB.cursor();
	for row in c.execute('select * from token where token=?',(token,)):
		nowish = datetime.datetime.now() - datetime.timedelta(seconds=60);
		nowish = nowish.strftime('%Y-%m-%d %H:%M:%S'); 
		result = []
		cc = util.DBLOG.cursor();
		for row in cc.execute('select * from log where datetime(time) > datetime(?) order by message_id desc',(nowish,)):
			result.append(row);
			#raise web.HTTPFound(location=row['long']);
		return web.Response(body=json.dumps(result),content_type='application/json');
	return web.HTTPForbidden();

@routes.get('/beatsaber/{shorthand}')
async def beatsaber(request):
	shorthand = request.match_info['shorthand'];
	async with aiohttp.ClientSession() as session:
		async with session.get("https://beatsaver.com/api/download/key/"+shorthand,headers={"user-agent":"curl/7.68.0"																							
																							}) as resp:
			if resp.status == 200:
				print(resp)
				result = await resp.read();
				return web.Response(body=result,content_type='application/zip',headers={'Content-Disposition': 'attachment; filename="'+shorthand+'.zip"'});
			else:
				return web.Response(text=(str(resp.status)+'\n'+str(resp)));
	
	raise web.HTTPNotFound();

@routes.get('/nilesy/paintings')
async def paintings(request):
	raise web.HTTPFound(location='https://imgur.com/a/BZTW5gr');

@routes.get('/subs')
async def subs_main(request):
	if 'error' in request.rel_url.query.keys():
		log.info('error in /subs'+request.rel_url.query)
		return str(request.rel_url.query);
	
	session = await get_session(request);
	access_token = None;
	
	if 'code' in request.rel_url.query.keys():
		html = await util.posting(clientsession, 'https://id.twitch.tv/oauth2/token?'
																	+'client_id='+util.TwitchAPI
																	+'&client_secret='+util.TwitchSECRET
																	+'&code='+request.rel_url.query['code']
																	+'&grant_type=authorization_code'
																	+'&redirect_uri=https://'+util.serverFull+'/subs'
																	, None, None);
		log.info('code:'+html);
		myjson = json.loads(html);
		access_token = myjson['access_token'];
		refresh_token = myjson['refresh_token'];
	
	if access_token:
		html = await util.fetchUser(clientsession,HELIX+'users',{'client-id':util.TwitchAPI,
																				'Accept':'application/vnd.twitchtv.v5+json',
																				'Authorization':'Bearer '+access_token});
		log.info('access_token:' + html)
		
		myjson = json.loads(html);
		if('error' in myjson.keys()):
			if not 'last_page' in session.keys():
				raise web.HTTPNotAcceptable;
			util.DBcursor.execute('update twitch_person set subs_auth_token = null , refresh_token = null where login = ? or lower(display_name) = ?',(session['last_page'].lower(),session['last_page'].lower()));
			util.DB.commit();
			return authUserPage();
			
		mydata = myjson['data'][0]; 
		
		session['last_page'] = mydata['display_name'].lower();
		
		log.info('saved last page: '+session['last_page'])
		cnt = await pullSubCount(mydata['id'],access_token);
		
		util.DBcursor.execute('update twitch_person set subs_auth_token = ? , refresh_token = ? where id = ?',(access_token,refresh_token,mydata['id']));
		util.DB.commit();
	
	if not ('last_page' in session.keys()):
		session['last_page'] = 'Dalai_Lama'
		
	raise web.HTTPFound(location='/subs/'+session['last_page']);
	#return web.Response(text=str(request));
	
@routes.get('/pull/{idd}/{token}')
async def pull(request):
	idd = request.match_info['idd'].lower();
	token = request.match_info['token'].lower();
	await pullSubCount(idd, token);
	return web.HTTPAccepted();
	
async def pullSubCount(broadcaster_id,user_access_token):
	b = True;
	cursor = '';
	cnt = 0;
	data = [];
	
	while b: 
		html = await util.fetchUser(clientsession,HELIX+'subscriptions?broadcaster_id='+broadcaster_id+cursor,{'client-id':util.TwitchAPI,
																				'Accept':'application/vnd.twitchtv.v5+json',
																				'Authorization':'Bearer '+user_access_token});
		log.info(html)
		myjson = json.loads(html);
		for d in myjson['data']:
			data.append(d)
		cnt = cnt+ len(myjson['data']);
		if 'cursor' in myjson['pagination']:
			cursor = '&after='+myjson['pagination']['cursor'];
		else:
			b = False;
		b = b and (len(myjson['data']) > 0);
	log.info('fetched subs for '+broadcaster_id+', they have '+str(cnt)+' subs');
	try:
		util.DBcursor.execute('delete from twitch_sub where broadcaster_id = ?',(broadcaster_id,));
		for d in data:
			util.DBcursor.execute('''insert into twitch_sub(broadcaster_id,broadcaster_name,gifter_id,gifter_name,is_gift,plan_name,tier,user_id,user_name)
									values(?,?,?,?,?,?,?,?,?)''',(d['broadcaster_id'],d['broadcaster_name'],d['gifter_id'],d['gifter_name'],d['is_gift'],d['plan_name'],d['tier'],d['user_id'],d['user_name']));
	except Exception as e:
		traceback.print_exc(file=sys.stdout)
		print('sub except')
		pass;
	util.DBcursor.execute('update twitch_person set subs = ? where id = ?',(cnt,broadcaster_id));
	util.DB.commit();
	
	return cnt;

@routes.get('/deleteraids')
async def deleteraids(request):
	query = '''
	select * from twitch_person p
		where p.watching_raid_id is not null
		or p.watching_raid_id_from is not null
	''';
	oauthToken = await util.getOAuth();
	cnt = 0;
	for row in util.DB.cursor().execute(query):
		if row['watching_raid_id']:
			x = await util.deletehttp(clientsession, HELIX+'eventsub/subscriptions?id='+row['watching_raid_id'],headers = {'client-id':util.TwitchAPI,
																						'Accept':'application/vnd.twitchtv.v5+json',
																						'Authorization':'Bearer '+oauthToken,
																						'Content-Type': 'application/json'
																					})
			log.info(x)
			cnt+=1;
		if row['watching_raid_id_from']:
			x = await util.deletehttp(clientsession, HELIX+'eventsub/subscriptions?id='+row['watching_raid_id_from'], headers ={'client-id':util.TwitchAPI,
																						'Accept':'application/vnd.twitchtv.v5+json',
																						'Authorization':'Bearer '+oauthToken,
																						'Content-Type': 'application/json'
																					})
			log.info(x)
			cnt+=1;
	util.DB.cursor().execute('''
	update twitch_person set watching_raid_id = null,watching_raid_id_from = null 
	''');
	util.DB.commit();
	return web.Response(text='killed '+str(cnt));
	

@routes.get('/startupraid')
async def watchraids(request):
	query = '''
	select * from irc_channel irc
		inner join twitch_person p
		on lower(irc.channel) = lower(p.login)
		where irc.left is null
		and p.watching_raid_id is null
		and p.watching_raid_id_from is null
	''';
	cnt = 0;
	html = "";
	for row in util.DB.cursor().execute(query):
		html = await ask_for_raidwatch(row);
		cnt += 1
	return web.Response(text=str(cnt)+' new people\n\n\n'+str(html));
		
async def ask_for_raidwatch(row):
	res = "";
	html = "";
	for condition in ['to_broadcaster_user_id','from_broadcaster_user_id']:
		print('asking for raids events for '+row['login']+' '+condition);
		payload = {
				"type":"channel.raid",
				"version":"1",
				"condition": {
					condition : str(row['id'])
				},
				"transport": {
					"method": "webhook",
					"callback": 'https://'+util.serverFull+'/raidhook',
					"secret": '1ABC23X6Z420'+row['login']
				}
			
			}
		oauthToken = await util.getOAuth();
		try:
			html = await util.posting(clientsession, HELIX+'eventsub/subscriptions', str(payload).replace('\'','"'),headers = {'client-id':util.TwitchAPI,
																						'Accept':'application/vnd.twitchtv.v5+json',
																						'Authorization':'Bearer '+oauthToken,
																						'Content-Type': 'application/json'
			})
			if('error' in html.lower()):
				log.error('error in asking for raidwatch');
				log.error('row '+row);
				log.error('response '+html);
		except Exception:
			traceback.print_exc();
		res = res + '\n\n' + html
	return res;

@routes.get('/testingbaby')
async def testingbaby(request):
	for row in util.DBcursor.execute('''select * from connection where from_channel = ?
																		and to_channel = ?
																		and kind = ?
																		and viewers = ?
																		and date like ?
											
										''',('ravs_','hybridpanda','hookraid','258','2021-07-08 19:50%'
										)):
		return web.Response(text=str(row));
	
@routes.post('/raidhook')
async def handle_notif_raid(request):
	try:
		data = json.loads((await request.content.read()).decode("utf-8"));
		log.info('raidhook triggered')
		if('challenge' in data.keys()):
			asyncio.get_event_loop().create_task(handle_raid_confirmed(request,data));
			return web.Response(text=data['challenge']);
		else:
			asyncio.get_event_loop().create_task(handle_raid_data(request,data));
			return web.Response(text='ok');
	except:
		return web.HTTPInternalServerError();
	

async def handle_raid_confirmed(request,data):
	global bot_client;
	log.info('raid webhook confirmed');
	mydate = time.strftime('%Y-%m-%d %H:%M:%S'); 
	for conds in data['subscription']['condition'].keys():
		usr= data['subscription']['condition'][conds];
		if usr and usr != '':
			field = 'watching_raid_id' if conds == 'to_broadcaster_user_id' else 'watching_raid_id_from'
			util.DBcursor.execute('''
				update twitch_person set '''
				+field+
				''' = ?
				,watching_since = ? where id = ?
			''',(data['subscription']['id'],mydate,usr));
	util.DB.commit();
	
async def handle_raid_data(request,data):
	global bot_client;
	log.info('raid webhook data:');
	log.info(str(data));
	from_chnl_id = data['event']['from_broadcaster_user_id']
	from_chnl = data['event']['from_broadcaster_user_login']
	to_chnl_id = data['event']['to_broadcaster_user_id']
	to_chnl = data['event']['to_broadcaster_user_login']
	newconnection = int(util.getControlVal('hooknewconnection',1));
	hookspread = int(util.getControlVal('hookspread',1));
	raidminviews = int(util.getControlVal('raidminviews',10));
	session = clientsession
	raidingviewers = int(data['event']['viewers']);
	if raidingviewers > raidminviews:
		peeps = {
			from_chnl:from_chnl_id,
			to_chnl:to_chnl_id
			};
		newpeople = await util.fetch_new_people(session,peeps);
		oauthtoken = await util.getOAuth();
		myjson = await util.fetch(session,'https://api.twitch.tv/helix/streams?user_id='+'&user_id='.join(newpeople.values()),{'client-id':util.TwitchAPI,
																																	'Accept':'application/vnd.twitchtv.v5+json',
																																	'Authorization':'Bearer '+oauthtoken});
		myjson = json.loads(myjson);																															
		gamesToFetch = set([k['game_id'] for k in myjson['data']]);
		games = await util.getGames(gamesToFetch,session,(await util.getOAuth()));
		peopleGame = {};
		for streamjson in myjson['data']:
			peopleGame[streamjson['user_name'].lower()] = games[streamjson['game_id']];
		from_game = peopleGame.get(from_chnl, '');
		to_game = peopleGame.get(to_chnl, '');  
		myshortdate = time.strftime('%Y-%m-%d %H:%M')+'%';
		mydate = time.strftime('%Y-%m-%d %H:%M:%S');
		if newconnection > 0:																								
			util.DBcursor.execute('''insert into connection(date,from_channel,to_channel,kind,viewers,from_game,to_game) 
										select ?,?,?,?,?,?,? from dual 
										where not exists
											(select * from connection where from_channel = ?
																		and to_channel = ?
																		and kind = ?
																		and viewers = ?
																		and date like ?
											)
										''',(mydate,from_chnl,to_chnl,'hookraid',raidingviewers ,from_game,to_game,
											from_chnl,to_chnl,'hookraid',raidingviewers,myshortdate
										));
			util.DB.commit();
			log.info((from_chnl_id,to_chnl_id))
		if hookspread > 0:
			for row in util.DBcursor.execute('''
					select * from twitch_person 
						where watching_raid_id is null 
							and watching_raid_id_from is null
						and id in (?,?)
						order by login desc
				''',(from_chnl_id,to_chnl_id)):
				asyncio.get_event_loop().create_task(ask_for_raidwatch(row));


	

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
		topic = HELIX+'subscriptions/events?first=1&broadcaster_id='+str(user_id);
		
		if userAuth and (userAuth != ''):
			
			oauthToken = util.getControlVal('token_oauth','');
			#look if user is still authed..
			html = await util.fetchUser(clientsession,HELIX+'users',{'client-id':util.TwitchAPI,
																				'Accept':'application/vnd.twitchtv.v5+json',
																				'Authorization':'Bearer '+userAuth});
			myjson = json.loads(html);																	
			if not ('data' in myjson):
				return authUserPage(user_id);
			#look if webhook still valid
			goon = True;
			webcursor = '';
			log.info('looking for hook');
			while goon and not hookvalid:
				html = await util.fetch(clientsession,HELIX+'webhooks/subscriptions'+webcursor,{'client-id':util.TwitchAPI,
																								'Accept':'application/vnd.twitchtv.v5+json',
																								'Authorization':'Bearer '+oauthToken});
				log.info(html);
				myjson = json.loads(html);
				for d in myjson['data']:
					if d['topic'] == topic:
						hookvalid = True;
						#check time of hook maybe
				if('cursor' in myjson['pagination']):
					webcursor = '?after='+myjson['pagination']['cursor'];
				else:
					goon = False;
			
			
			#renew the hook anyway...
			payload = {'hub.callback':('https://'+util.serverFull+'/subhook?user_name='+name+'&user_id='+user_id),
							   "hub.mode":"subscribe",
							   "hub.topic":topic,
							   "hub.lease_seconds":864000 #864000 = 10 days = maximum
							   };
			log.info('renew hook:'+str(payload))
			html = await util.posting(clientsession, HELIX+'webhooks/hub', str(payload).replace('\'','"'),headers = {'client-id':util.TwitchAPI,
																							'Accept':'application/vnd.twitchtv.v5+json',
																							'Authorization':'Bearer '+userAuth,
																							'Content-Type': 'application/json'
																						})
		if not hookvalid:
			try:
				if (not userAuth) or (userAuth == ''):
					raise util.AuthFailed;
				
				#fetch current sub count
				cnt = await pullSubCount(user_id,userAuth);

			except util.AuthFailed as aex:
				return authUserPage(user_id);
				#raise web.HTTPFound(location=auth_url);
	
	with open("ressources/subs.html", "r") as f: 
		es = f.read().replace('{REPLACE_ME}',name);
	return web.Response(text=es,content_type = 'text/html');

@routes.get('/subhook')
async def handle_webhook_sub(request):  
	log.info('webhook (sub) was accepted ('+str(request.rel_url.query)+')');
	if not 'hub.challenge' in request.rel_url.query.keys():
		return web.HTTPExpectationFailed();
	return web.Response(text=request.rel_url.query['hub.challenge'])

@routes.post('/subhook')
async def handle_notif_sub(request):
	try:
		data = (await request.content.read()).decode("utf-8");
		asyncio.get_event_loop().create_task(handle_data_sub(request,data));
	except:
		return web.HTTPInternalServerError();
	return web.Response(text='OK');

async def handle_data_sub(request,data):
	global bot_client;
	log.info('sub webhook data:');
	log.info(str(data));
	myjson = json.loads(data)['data'];
	user_id = request.rel_url.query['user_id'];
	user_name = request.rel_url.query['user_name'].lower();
	plusminus = {};
	for d in myjson:
		broadcaster = d['event_data']['broadcaster_id'];
		sub_user = d['event_data']['user_id'];
		if not broadcaster in plusminus:
			plusminus[broadcaster] = 0;
		if d['event_type'] == 'subscriptions.subscribe':
			f = d['event_data'];
			plusminus[broadcaster] = plusminus[broadcaster] + 1;
			util.DBcursor.execute('''insert into twitch_sub(broadcaster_id,broadcaster_name,gifter_id,gifter_name,is_gift,plan_name,tier,user_id,user_name)
									values(?,?,?,?,?,?,?,?,?)''',(f['broadcaster_id'],f['broadcaster_name'],f['gifter_id'],f['gifter_name'],f['is_gift'],f['plan_name'],f['tier'],f['user_id'],f['user_name']));
			print("inserted sub")
									
		elif d['event_type'] == 'subscriptions.unsubscribe':
			plusminus[broadcaster] = plusminus[broadcaster] - 1;
			util.DBcursor.execute('''delete from twitch_sub where broadcaster_id = ? and user_id = ?''',(broadcaster,sub_user));
			print("deleted sub")
	for k,v in plusminus.items():
		if v > 0:
			util.DBcursor.execute('update twitch_person set subs = subs + ? where id = ?',(v,k));
		elif v < 0:
			v = -v;
			util.DBcursor.execute('update twitch_person set subs = subs - ? where id = ?',(v,k));
	util.DB.commit();
		
@routes.get('/subcounter/{name}')
async def subcount(request):
	su = util.getSubs(request.match_info['name'].lower())
	try:
		int(su)
	except:
		raise web.HTTPError();
	return web.Response(text=str(su));

@routes.get('/robots.txt')
async def robots(_):  
	return web.Response(text='''User-agent: *\n\rDisallow: /''');

def authUserPage(user_id):
	with open("ressources/authuser.html", "r") as f:
		auth_url = 'https://id.twitch.tv/oauth2/authorize?client_id='+util.TwitchAPI+'&redirect_uri=https://'+util.serverFull+'/subs&response_type=code&scope=channel:read:subscriptions'; 
		es = f.read().replace('{REPLACE_URL}',auth_url);
	return web.Response(text=es,content_type = 'text/html');
		
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
			util.DBcursor.execute('update twitch_person set last_check_status = ? , last_check = ? where id = ?',('offline',util.dateToStr(datetime.datetime.utcnow()),user_id) );
			util.DB.commit();
		else:
			util.DBcursor.execute('update twitch_person set last_check_status = ? , last_check = ? where id = ?',('online',util.dateToStr(datetime.datetime.utcnow()),user_id) );
			util.DB.commit();
			gamesToFetch = set([k['game_id'] for k in myjson]);
			oauthToken = util.getControlVal('token_oauth','');
			games = await util.getGames(gamesToFetch,web_srv_session,oauthToken);
				
			for item in myjson:
				stream = TwitchStream(item);
				stream.game = games[stream.game_id];
				
				for row in util.DBcursor.execute('SELECT * FROM twitch where userid = ? and lower(username) = ?',(user_id,user_name,)):
					entr = TwitchEntry.TwitchEntry(row);
					try:									   #print(streamprinted[entr]);
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


