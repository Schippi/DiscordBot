from twitchio.ext import commands;
import sqlite3;
import traceback;
import time;
import asyncio;
from datetime import datetime;
from datetime import timedelta;
import sys;
from util import TwitchAPI;
from util import TwitchIRCAUTH;
from util import TwitchIRCNICK;
import util;
import os;

starttime = {};
polls = {};
myprefix = '~'
lastmsgtime = None;
raidauto = True;
ircBot = None;
initialized = False;


class MyBot(commands.Bot):
	async def event_command_error(self, ctx, error):
		if ( isinstance(error,commands.CommandNotFound)):
			print('command {0} '.format(error), file=sys.stderr)
			pass;
		else:
			traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

def main(client,testing):
	DBLOG = util.cfgPath+'/irc.db';
	DBLOGJournal = util.cfgPath+'/irc.db-journal';
	try:
		os.remove(DBLOGJournal);
	except OSError:
		pass;
	
	global ircBot;
	
	ircBot = MyBot(
		irc_token=TwitchIRCAUTH,
		api_token=TwitchAPI,
		nick=TwitchIRCNICK,
		prefix=myprefix
		#,initial_channels=['nilesy','ravs_','theschippi','hybridpanda']
	);
	ircBot.enableLimmy = (util.getControlVal("Limmy", "True") == "True");
	ircBot.msgcnt = 0;
	ircBot.offset = 0;

	conn = sqlite3.connect(DBLOG);
	cur = conn.cursor();

	@ircBot.event
	async def event_ready():
		global initialized;
		initialized = False;
		print('IRC Ready | {}'.format(TwitchIRCNICK));
		for row in util.DBcursor.execute('''select * from irc_channel where left is null'''):
			await ircBot.join_channels((row['channel'],));
			print('joined irc: '+row['channel']);
		print(ircBot.prefixes);
		
		client.loop.create_task(waitForInit(testing));
		
		
	async def waitForInit(testing):
		await asyncio.sleep(5)
		global initialized;
		initialized = True;
		print("irc waiting over")
			
	@ircBot.event
	async def event_message( message):
		#print(message.content);
		if(ircBot.nick == message.author.name):
			return;
		try:
			await ircBot.handle_commands(message);
		except Exception:
			print(datetime.now().strftime("%d.%m.%Y, %H:%M:%S"));
			traceback.print_exc();
		
		
		channel = message.channel;
		#print(message.content);
				
		if( channel.name in polls):
			mypoll = polls[channel.name];
			if(time.time() < mypoll['time']):
				if 'VoteYea' in message.content:
					if not message.author.name in mypoll['users']:
						mypoll['users'].append(message.author.name);
						mypoll['yea']= mypoll['yea']+1;
				elif 'VoteNay' in message.content:
					if not message.author.name in mypoll['users']:
						mypoll['users'].append(message.author.name);
						mypoll['nay']= mypoll['nay']+1;
			elif not mypoll['done']:
				mypoll['done'] = True;
				if not message.content.startswith(myprefix+'poll'):
					await channel.send('the poll has closed! For results MODS can do '+myprefix+'poll (without asking a new question)')
						
		try:
			st = time.strftime('%Y-%m-%d %H:%M:%S');
			mlist = [st,message.channel.name,message.author.name,message.content];
			cur.execute("INSERT INTO words(date,channel,usr,msg) VALUES (?,?,?,?)",mlist);
			ircBot.msgcnt = ircBot.msgcnt + 1;
			currenttime = datetime.now();
			global lastmsgtime;
			lastmsgtime = currenttime;
			if(ircBot.msgcnt % 50 == ircBot.offset):
				print('>commited '+str(ircBot.msgcnt));
				conn.commit();
			else:
				await asyncio.sleep(60);
				if(currenttime == lastmsgtime):
					print('>>commited '+str(ircBot.msgcnt));
					ircBot.offset = ircBot.msgcnt % 50;
					conn.commit();
		except Exception:
			print(datetime.now().strftime("%d.%m.%Y, %H:%M:%S"));
			traceback.print_exc();
			
		

	@ircBot.event
	async def event_raw_usernotice( channel, tags: dict):
		global raidauto;
		if tags:
			shoulddo = False;
			#print('usernotice tags'+str(tags));
			if tags['msg-id'] == 'raid' and raidauto and shoulddo:
				
				for row in util.DBcursor.execute('''select * from irc_channel where left is null and channel = ?''',(channel.name,)):
					if row['raid_auto'] and row['raid_auto'] > 0:
						shoulddo = True;
				if shoulddo:	
					#global starttime;
					
					starttime[channel.name] = time.time() + 900;
					chnl= tags['msg-param-displayName'];
					
					#await channel.send("@nilesy i'd disable followers-only mode, but im not a mod");
					#await asyncio.sleep(2);
					await channel.send('.followersoff');
					await asyncio.sleep(30);
					if chnl:
						await channel.send('Hello Raiders of '+chnl+'! This channel is usually in followers only mode, but i''ve disabled it for now. Be sure to follow to continue to be able to chat when we turn it back on!');
					else:
						await channel.send('Hello Raiders! This channel is usually in followers only mode, but i''ve disabled it for now. Be sure to follow to continue to be able to chat when we turn it back on!');
					await asyncio.sleep(900);
					endtime = time.time();
					if starttime[channel.name] < endtime and raidauto:
						await channel.send('.followers 10m');
						#await asyncio.sleep(2);
						#await channel.send("@nilesy i'd turn on followers-only mode on again but im not a mod");
		pass;
	
	@ircBot.event
	async def event_join(user = None):
		global initialized;
		if initialized:
			if(user.channel.name.lower() == 'katercakes' and user.name.lower() == 'limmy'):
				print('joined cakes '+user.name);
				if(ircBot.enableLimmy and not testing):
					user.channel.send('Hey '+user.name)
	
	@ircBot.event
	async def event_part(user = None):
		global initialized;
		if initialized:
			if(user.channel.name.lower() == 'katercakes' and user.name.lower() == 'limmy'):
				print('parted cakes '+user.name);
				if(ircBot.enableLimmy and not testing):
					user.channel.send('Bye '+user.name)
		
	@ircBot.event	
	async def event_raw_data(data):
		try:
			st = time.strftime('%Y-%m-%d %H:%M:%S: ');
			fil = open('traffic.log','a', encoding="utf-8")
			fil.write((st+data.strip()+'\n'))
			fil.close();
		except Exception:
			traceback.print_exc();
		msg = data.strip().lower();
		#@msg-id=host_on :tmi.twitch.tv NOTICE #theschippi :Now hosting Nilesy.
		if '@msg-id=host_on' in msg and '#theschippi' in msg and 'hosting nilesy' in msg:
			if ircBot.get_channel('theschippi'):
				await ircBot.get_channel('theschippi').send('detecting host');
	
	@ircBot.command(name='raid')
	async def raidauto_command(ctx):
		if ctx.message.author.is_mod:
			channel = ctx.message.channel;
			channelname = channel.name.lower();
			for row in util.DBcursor.execute('''select * from irc_channel 	
										where left is null
										and channel = ?
										''',(channelname,)):
				a = row['raid_auto'];
				if a and a > 0:
					a = 'OFF';
				else:
					a = 'ON'
				util.DBcursor.execute('''update irc_channel 
											set raid_auto = 1 - raid_auto
											where left is null
											and channel = ?
											''',(channelname,));
				util.DB.commit();							
				return await channel.send('ok - status now '+a);
	
	# Commands use a different decorator
	@ircBot.command(name='test')
	async def test_command(ctx):
		print('mod'+str(ircBot._ws._mod_token))
		#print(ctx.message.author.name + str(ctx.message.tags));
		#print(ctx.message.author.name + str(ctx.message.author.badges));
		if ctx.message.author.is_mod:
		#	await ctx.message.channel.send(ctx.message.content[6:])
		#	await ctx.send(ctx.message.content[6:])
			channel = ctx.message.channel;
			#global starttime;!test 1
			starttime[channel.name] = time.time() + 10;
			await channel.send('Cheer100 i luv u');
			await asyncio.sleep(10);
			endtime = time.time();
			#await channel.send('test: times up+'+str(starttime[channel.name])+'  '+str(endtime));
			if starttime[channel.name] < endtime:
				await asyncio.sleep(1);
				#await channel.send('right time');
	
	@ircBot.command(name='poll')
	async def poll_command(ctx):
		if ctx.message.author.is_mod:
			channel = ctx.message.channel;
			if len(ctx.message.content.split(' ')) == 1:
				if( channel.name in polls):
					mypoll = polls[channel.name];
					yea = mypoll['yea'];
					nay = mypoll['nay'];
					sum = yea+nay;
					pyea = 100* yea / (sum * 1.0);
					pnay = 100* nay / (sum * 1.0);
					await channel.send(mypoll['question']+': '+format(pyea, '.2f')+'% voted VoteYea, '+format(pnay, '.2f')+'% voted VoteNay '+str(sum)+' people voted!');
					await asyncio.sleep(0.2);
					if(mypoll['done']):
						await channel.send('polls are closed, so no need to spam');
					else:
						await channel.send('polls are still open, you still can get your vote in!');
				else:
					await channel.send('no poll ever asked');
			elif len(ctx.message.content.split(' ')) < 3:
				await channel.send('you need to ask a question pal... '+myprefix+'poll [time in seconds] [question]');
			else:
				try:
					question= ctx.message.content.split(' ',2)[2];
					offset = int(ctx.message.content.split(' ',2)[1]);
					polls[channel.name] = {'time':(time.time()+offset), 'question':question, 'yea':0, 'nay':0, 'users':[], 'done':False};
					await channel.send('A new poll has been started! - '+question+' - vote with VoteYea or VoteNay! - You have '+str(offset)+ ' seconds!');
				except:
					await channel.send('Something went wrong, please try again. '+myprefix+'poll [time in seconds] [question]');
	return ircBot;
	#bot.run();
	#conn.close();
	
if __name__ == '__main__':
	main();