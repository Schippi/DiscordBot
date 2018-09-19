import time;
import pytz;
from datetime import datetime, timedelta;
import threading;
import asyncio;
import async_timeout;
import sys;

DBcursor = None;
DB = None;
cfgPath = None;
timeStr= '%Y-%m-%dT%H:%M:%S.%fZ';
lock = threading.Lock();
#your Client-ID - go to https://blog.twitch.tv/client-id-required-for-kraken-api-calls-afbb8e95f843 and follow the instructions
TwitchAPI = '';
YTAPI = '';

if len(sys.argv) >= 3:
	cfgPath = sys.argv[2];
	
print(cfgPath+"/../tokens/twitch.token","r");
file = open(cfgPath+"/../tokens/twitch.token","r");
try:
	contents =file.read().splitlines(); 
	TwitchAPI = contents[0];
except:
	pass;
file.close();

file = open(cfgPath+"/../tokens/youtube.token","r");
try:
	contents =file.read().splitlines(); 
	YTAPI = contents[0];
except:
	pass;
file.close();

def toDateTime(strr):
	if(strr == None):
		return 1; 
	return datetime.strptime(strr, timeStr);

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
	res = None;
	try:
		reaction,user = await client.wait_for(event='reaction_add',check = check, timeout = 20);
	except:
		pass;
	return res and ('\N{WHITE HEAVY CHECK MARK}' == reaction.emoji);

async def fetch(session, url, headers):
	with async_timeout.timeout(10):
		async with session.get(url, headers = headers) as response:
			try:
				return await response.text()
			except asyncio.TimeoutError:
				return '';
			
def sendMail(a,b):
	import yagmail;
	import base64;
	file = open(cfgPath+"/../tokens/mail.token","r");
	try:
		contents =file.read().splitlines(); 
		NAME = contents[0];
		TOKEN = contents[1];
	except:
		pass;
	file.close();
	yag = yagmail.SMTP(NAME,base64.b64decode(TOKEN).decode());
	#yag = yagmail.SMTP('theschippi@gmail.com','vzzllqykrnrpislf');
	contents = [b];
	yag.send('theschippi@gmail.com', a, contents);
	
def changeLog():
	return '''0.3.0: introduction of changelog\n
timer doesn't print all the time while creating a new one\n
if a timer should have triggered when the bot was offline, it doesn't trigger a week later at 12AM 
	'''



