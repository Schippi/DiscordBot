import time;
import pytz;
from datetime import datetime, timedelta;
import threading;
import asyncio;
import async_timeout;
import sys;
import base64;
import yagmail;
import json;
import traceback;

DBcursor = None;
DB = None;
cfgPath = None;
serverPort = 8081;
serverHost = 'localhost'
serverFull = 'localhost:8081';

HELIX = 'https://api.twitch.tv/helix/';

timeStr= '%Y-%m-%dT%H:%M:%S.%fZ';
backupStr = '%Y-%m-%dT%H:%M:%SZ'
lock = threading.Lock();
#your Client-ID - go to https://blog.twitch.tv/client-id-required-for-kraken-api-calls-afbb8e95f843 and follow the instructions
TwitchAPI = '';
TwitchSECRET = '';
YTAPI = '';
pleaseLog=True;

class AuthFailed(Exception):
	pass;

if len(sys.argv) >= 3:
	cfgPath = sys.argv[2];
	
file = open(cfgPath+"/../tokens/twitch.token","r");
try:
	contents =file.read().splitlines(); 
	TwitchAPI = contents[0];
	TwitchSECRET = contents[1];
except:
	TwitchAPI = '';
	TwitchSECRET = '';
	pass;
file.close();

file = open(cfgPath+"/../tokens/youtube.token","r");
try:
	contents =file.read().splitlines(); 
	YTAPI = contents[0];
except:
	pass;
file.close();

if len(sys.argv) >= 3:
	cfgPath = sys.argv[2];

def toDateTime(strr):
	if(strr == None or len(strr.strip()) == 0):
		return 1; 
	try:
		return datetime.strptime(strr, timeStr);
	except ValueError as ex:
		return datetime.strptime(strr, backupStr);
	
def dateToStr(dd):
	return dd.strftime(timeStr);

def getMarkupStr(args):
	if(len(args) > 1):
		text = '';
		myargs = [];
		for i in range(0,len(args)):
			if args[i] == ' ':
				myargs.append(text);
				text = ''
			else:
				text = text+args[i];
		if text != '':
			myargs.append(text);
		text = '```'+myargs[0]+'\n'
		for i in range(1,len(myargs)):
			text = text+myargs[i]+' '		
		text = text+'\n```'
		return text
	else:
		return ''
		
def repl(inputt,toreplace,replacewith):
	if(replacewith):
		return inputt.replace(toreplace,replacewith);
	else:
		return inputt;
		
def is_dst(zonename):
	tz = pytz.timezone(zonename)
	now = pytz.utc.localize(datetime.utcnow())
	return now.astimezone(tz).dst() != timedelta(0)		

def dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description):
		d[col[0].lower()] = row[idx];
	return d;
	
def singleQuote(stri):
	return "'"+str(stri)+"'";

def quote(msg):
	return '` '+msg+' `';

def updateOrInsert(table,pkdict,valdict, alwaysUsePK):
	#print(type(pkdict));	
	pklist = list(pkdict.keys());
	vallist = list(valdict.keys());
	q = 'UPDATE '+table+" set ";	
	q= q+ '= ? , '.join(vallist)+' = ?';
	q= q+' where '+pklist[0]+' = ?';
	
	
	q2 = 'INSERT INTO '+table+' ('
	if(alwaysUsePK):
		q2 = 'INSERT INTO '+table+' ('
		q2 = q2 + pklist[0]+', ';
		q2 = q2+', '.join(vallist)+') ';
		q2 = q2+' select ?, '+ ', '.join(['?' for s in vallist])
	else : 
		q2 = 'INSERT INTO '+table+' ('
		q2 = q2+', '.join(vallist)+') ';
		q2 = q2+' select '+ ', '.join(['?' for s in vallist])
	q2 = q2+" WHERE (Select Changes() = 0);";
	
	pkval = pkdict[pklist[0]];
	
	l1 = list(valdict.values());
	l1.append(pkval);
	l2 = list(valdict.values());
	
	DBcursor.execute(q,l1);
	if(alwaysUsePK):
		l2.insert(0,pkval);	
		DBcursor.execute(q2,l2);
	else:
		DBcursor.execute(q2,l2);	
	print(q);
	print(l1);
	#print(l2);	
	if pkval:
		return pkval;
	else:
		q = 'Select max('+pklist[0]+') as id from '+table;
		DBcursor.execute(q);
		row = DBcursor.fetchone();
		print(q);
		print(row);
		return row['id'];

def delete(table,pk, pkval):
		q = 'DELETE FROM '+table+ ' where '+pk+' = ' +str(pkval);
		DBcursor.execute(q);

def logEx(ex):
	try:
		if ex:
			if type(ex) == type(str()):
				err = time.strftime('%X %x %Z') + ': ' + ex;
			else:
				err = time.strftime('%X %x %Z') + ': ' + 'Exception : {0}: {1}\n\t{2}'.format(ex.errno, ex.strerror,str(ex))
		else:
			return;
		print(err)
		fil = open('TwitchChecker.log','a')
		fil.write(err+'\n')
		fil.close();
	except Exception:
		traceback.print_exc(file=sys.stdout);
		pass
	
client = '';
from GuildSettings import getSetting;	
async def sayWords(context = None,message = None,sett = None, chan = None):
	#message.encode('utf-8')
	for m in message.split('\n'):
		print(m);
	if not message:
		return;
	if not sett:
		sett = getSetting(context = context);
		chan = context.message.channel;
	if not sett:
		if context.message:
			return await context.author.send(message);
	else:
		if (sett.logLevel == 'mute'):
			return None;
		if (sett.logLevel == 'whisper' and context.message):
			return await context.author.send(message);
		return await chan.send(message);

async def askYesNoReaction(context, question):
	msg = await sayWords(context, question);
	await asyncio.sleep(0.1);
	await msg.add_reaction('\N{WHITE HEAVY CHECK MARK}');
	await asyncio.sleep(0.1);
	await msg.add_reaction('\N{NEGATIVE SQUARED CROSS MARK}');
	def check(reaction,user):
		#print(reaction.message.id == msg.id);
		#print(user == context.message.author);
		#print(reaction.emoji in ['\N{WHITE HEAVY CHECK MARK}', '\N{NEGATIVE SQUARED CROSS MARK}']);
		if reaction.message.id == msg.id and user == context.message.author and reaction.emoji in ['\N{WHITE HEAVY CHECK MARK}', '\N{NEGATIVE SQUARED CROSS MARK}']:
			return True;
		return False;
	try:
		reaction,user = await client.wait_for(event='reaction_add',check = check, timeout = 20);
	except:
		return False;
	return not reaction is None and not user is None and ('\N{WHITE HEAVY CHECK MARK}' == reaction.emoji);

async def fetch(session, url, headers,secondTime=False):
	with async_timeout.timeout(10):
		async with session.get(url, headers = headers) as response:
			try:
				if (response.status == 401):
					print(await response.text())
					print(url)
					print(headers)
					if (('twitch' in url) and ('WWW-Authenticate' in response.headers.keys())):
						if secondTime:
							raise AuthFailed;
						else:
							headers['Authorization'] = 'Bearer '+(await AuthMe(session));
							return await fetch(session,url,headers,True);
				else:
					return await response.text()
			except asyncio.TimeoutError:
				return '';
			
async def fetchUser(session, url, headers):
	return await fetch(session,url,headers,True);

			
async def posting(session, url, payload, headers = None):
	with async_timeout.timeout(10):
		async with session.post(url, data = payload,headers = headers) as response:
			try:
				return await response.text()
			except asyncio.TimeoutError:
				return '';
			
def getControlVal(mystring,dflt):
	valset = False;
	for row in DBcursor.execute('SELECT * FROM control where key = ?',(mystring,)):
		valset = True;
		return row['value'];
	if not valset:
		DBcursor.execute('insert into control(key,value) values(?,?)',(mystring,dflt));
		DB.commit();
		return dflt;
	return None;

async def getGames(ids,session,oauthToken):
	placeholders= ', '.join(['?']*len(ids));
	retdict = {'':'Something'};
	if(len(ids)== 0):
		return retdict;
	
	for row in DBcursor.execute('SELECT * FROM game where id in ({})'.format(placeholders),tuple(ids)):
		retdict[str(row['id'])] = row['name'];
																	
	if (len(retdict.keys()) < len(ids)):
		lookURL = 'https://api.twitch.tv/helix/games?id='+('&id='.join(ids));
		
		myjson = await fetch(session,lookURL,{'client-id':TwitchAPI,
								'Accept':'application/vnd.twitchtv.v5+json',
								'Authorization':'Bearer '+oauthToken});
		myjson = json.loads(myjson);
		for d in myjson['data']:
			if not d['id'] in retdict.keys():
				DBcursor.execute('insert into game(id,name,boxart) values(?,?,?)',(d['id'],d['name'],d['box_art_url']));
			retdict[d['id']] = d['name'];
		DB.commit();
	return retdict;

def getGamesUrlbyName(name):
	for row in DBcursor.execute('SELECT * FROM game where name = ?',(name,)):
		return row['boxart'].replace('{width}','110').replace('{height}','150');
	return None;

async def AuthMe(session):
	authURL = 'https://id.twitch.tv/oauth2/token';
	
	myjson = await posting(session,authURL,{'client_id':TwitchAPI,'client_secret':TwitchSECRET, 'grant_type':'client_credentials'});
	myjson = json.loads(myjson);		
	return setControlVal('token_oauth',myjson['access_token']);

def setControlVal(mystring,val):
	DBcursor.execute('update control set value = ? where key = ?',(val,mystring));
	DB.commit();
	return val;

def getSubs(name):
	for row in DBcursor.execute('select subs from twitch_person where lower(display_name) = ?',(name,)):
		return 2; #row['subs']
	return 'not tracking';
			
def sendMail(title,inhalt):
	try:
		file = open(cfgPath+"/../tokens/mail.token","r");
		contents =file.read().splitlines(); 
		NAME = contents[0];
		TOKEN = contents[1];
	except:
		print("mailing not setup");
		if not file is None:
			file.close();
		return;
	file.close();
	yag = yagmail.SMTP(NAME,base64.b64decode(TOKEN).decode());
	contents = [inhalt];
	yag.send(NAME, title, contents);
	
def changeLog():
	return '''0.3.0: introduction of changelog\n
timer doesn't print all the time while creating a new one\n
if a timer should have triggered when the bot was offline, it doesn't trigger a week later at 12AM 
	'''



