import aiofiles
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
from util import getControlVal;
import util;
import logging;
import os;
import aiohttp;
import json;

starttime = {};
polls = {};
myprefix = '~'
lastmsgtime = None;
raidauto = True;
ircBot = None;
initialized = False;


class MyIRCBot(commands.Bot):

	#def __init__(self,testing,irc_token,api_token,nick,prefix):
	#	super().__init(self,irc_token=irc_token,api_token=api_token,nick=nick,prefix=prefix);
	#	self.testing = testing;		
		
	
	async def event_command_error(self, ctx, error):
		if ( isinstance(error,commands.CommandNotFound)):
			print('command {0} '.format(error), file=sys.stderr)
			pass;
		else:
			traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)





def main(client,testing, loop = None):
	DBLOG = util.cfgPath+'/irc.db';
	DBLOGJournal = util.cfgPath+'/irc.db-journal';
	try:
		os.remove(DBLOGJournal);
	except OSError:
		pass;
	
	global ircBot;
	
	ircBot = MyIRCBot(
		TwitchIRCAUTH,
		api_token=TwitchAPI,
		nick=TwitchIRCNICK,
		prefix=myprefix
		#,initial_channels=['nilesy','ravs_','theschippi','hybridpanda']
	);
	ircBot.testing = testing;
	ircBot.enableLimmy = (util.getControlVal("Limmy", "True") == "True");
	ircBot.msgcnt = 0;
	ircBot.offset = 0;
	ircBot.session = aiohttp.ClientSession(); 

	conn = sqlite3.connect(DBLOG);
	cur = conn.cursor();
	
	cur.execute('''CREATE TABLE IF NOT EXISTS  `dual` (
			`DUMMY`	TEXT
		);''');
		
	cur.execute('''insert into dual(dummy)
						select 'X' from sqlite_master 
						where not exists (select * from dual)
						limit 1''');
	conn.commit();

	@ircBot.event
	async def event_ready():
		global initialized;
		initialized = False;
		global ghost_channels;
		ghost_channels = [];
		for row in util.DBcursor.execute('''select * from irc_channel where left is null and ghost = 1'''):
			ghost_channels.append(row['channel']);
		print('IRC Ready | {}'.format(TwitchIRCNICK));
		i = 1;
		if not ircBot.testing:
			for row in util.DBcursor.execute('''select * from irc_channel where left is null order by channel'''):
				i = i+1;
				#print('trying: '+row['channel']);
				#await ircBot.join_channels((row['channel'],));
				#await asyncio.sleep(1)
				#print('joined irc: '+row['channel']);
				loop.create_task(joinLater(i,row['channel']));
		else:
			await ircBot.join_channels(('theschippi',));
			for row in util.DBcursor.execute('''select * from irc_channel where left is null and ghost = 1'''):
				i = i+1;
				loop.create_task(joinLater(i,row['channel']));
				#print('trying: '+row['channel']);
				#await ircBot.join_channels((row['channel'],));
				#await asyncio.sleep(1)
				#print('joined irc: '+row['channel']);
		print(ircBot.prefixes);
		
		loop.create_task(waitForInit(i,testing));
	
	async def joinLater(time,chn):
		print('irc: '+chn);
		await asyncio.sleep(time*0.5)
		try:
			await ircBot.join_channels((chn,));
			print('joined irc: '+chn);
		except Exception as e:
			mydate = time.strftime('%Y-%m-%d %H:%M:%S');
			util.DBcursor.execute('''update irc_channel set left = ? where channel = ? and left is null''',(mydate,chn));
			print('CANNOT JOIN irc: '+chn);
		
		
	async def waitForInit(i,testing):
		await asyncio.sleep(i*0.5+1)
		global initialized;
		initialized = True;
		print("irc waiting over")
			
	@ircBot.event
	async def event_message( message):
		#print(message.content);
		
		try:
			if(ircBot.nick != message.author.name):
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
			global ghost_channels;
			if message.channel.name in ghost_channels:
				return;
			st = time.strftime('%Y-%m-%d %H:%M:%S');
			mlist = [st,message.channel.name,message.author.name,message.content];
			cur.execute('''INSERT INTO words(date,channel,usr,msg) 
						select ?,?,?,? from `dual` 
						''',mlist);
						#where not exists(select * from irc_channel where ghost=1 and channel=?)
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
			if tags['msg-id'] == 'raid' and raidauto:
				print('raid incomming in '+channel.name);
				mtime = 10;
				for row in util.DBcursor.execute('''select * from irc_channel where left is null and channel = ?''',(channel.name,)):
					if row['raid_auto'] and row['raid_auto'] > 0:
						shoulddo = True;
					if row['raid_time'] and int(row['raid_time']) > 0:
						mtime = int(row['raid_time']);
				#print('raid shoulddo '+str(shoulddo)+ "time: "+str(mtime));		
				if shoulddo:	
					#global starttime;
					
					starttime[channel.name] = time.time() + (90*mtime);
					chnl= tags['msg-param-displayName'];
					
					#await channel.send("@nilesy i'd disable followers-only mode, but im not a mod");
					#await asyncio.sleep(2);
					await channel.send('.followersoff');
					await asyncio.sleep(30);
					if chnl:
						await channel.send('Hello Raiders of '+chnl+'! This channel is usually in followers only mode, but i''ve disabled it for now. Be sure to follow to continue to be able to chat when we turn it back on!');
					else:
						await channel.send('Hello Raiders! This channel is usually in followers only mode, but i''ve disabled it for now. Be sure to follow to continue to be able to chat when we turn it back on!');
					await asyncio.sleep(mtime * 90);
					endtime = time.time();
					if starttime[channel.name] < endtime and raidauto:
						await channel.send('.followers '+str(mtime)+'m');
						#await asyncio.sleep(2);
						#await channel.send("@nilesy i'd turn on followers-only mode on again but im not a mod");
			if tags['msg-id'] == 'raid':
				newraid = int(getControlVal('newraid',1));
				if newraid > 0:
					raidminviews = int(getControlVal('raidminviews',20));
					try:
						to_chnl = channel.name;
						from_chnl= tags['msg-param-displayName'];
						viewcount = int(tags['msg-param-viewerCount']);
						if raidminviews < viewcount:
							await raid_channel('raid',from_chnl,to_chnl,viewcount);
						
						
					except Exception as e:
						traceback.print_exc();
				
				
		pass;
	

	
	async def raid_channel(kind,from_chnl,to_chnl,viewers=0):
		global initialized;
		if not initialized and kind != 'host':
			#dont do hosts when starting up
			print('nope')
			return;
		try:
			newconnection = int(getControlVal('newconnection',1));
			newirc = int(getControlVal('newirc',1));
			if newconnection > 0:
				from_chnl = from_chnl.lower();
				to_chnl = to_chnl.lower();
				print('raidorhost: '+kind + ' '+from_chnl+' '+to_chnl +' '+str(viewers));
				
				mydate = time.strftime('%Y-%m-%d %H:%M:%S');
				people = {from_chnl,to_chnl};
				peopleGame = {};
				try:
					if int(getControlVal('raidgames',1)) > 0:
						oauthToken = getControlVal('token_oauth','');
						if(oauthToken == ''):
							oauthToken = await util.AuthMe(ircBot.session);
						lookURL = 'https://api.twitch.tv/helix/users?login='+'&login='.join(people)
						print(lookURL)
						myjson = await util.fetch(ircBot.session,lookURL,{'client-id':util.TwitchAPI,
																'Accept':'application/vnd.twitchtv.v5+json',
																'Authorization':'Bearer '+oauthToken});	
						myjson = json.loads(myjson);
						newpeople = {};
						myArray = myjson["data"];
						for myEnt in myArray:
							newpeople[myEnt["display_name"].lower()] = myEnt["id"];										
							
						myjson = await util.fetch(ircBot.session,'https://api.twitch.tv/helix/streams?user_id='+'&user_id='.join(newpeople.values()),{'client-id':util.TwitchAPI,
																																'Accept':'application/vnd.twitchtv.v5+json',
																																'Authorization':'Bearer '+oauthToken});
						myjson = json.loads(myjson);
						print(myjson)
						gamesToFetch = set([k['game_id'] for k in myjson['data']]);
						games = await util.getGames(gamesToFetch,ircBot.session,oauthToken);
						for streamjson in myjson['data']:
							peopleGame[streamjson['user_name'].lower()] = games[streamjson['game_id']];																										
																															
				except Exception:
					traceback.print_exc();		
				from_game = peopleGame.get(from_chnl, '');
				to_game = peopleGame.get(to_chnl, ''); 																									
				util.DBcursor.execute('''insert into connection(date,from_channel,to_channel,kind,viewers,from_game,to_game) 
											select ?,?,?,?,?,?,? from dual ''',(mydate,from_chnl,to_chnl,kind,viewers,from_game,to_game));
				util.DB.commit();
			if newirc > 0:
			#only join if not kicked before
				for person in people:
					exists = False;
					for row in util.DBcursor.execute('''select * from irc_channel where channel = ?''',(person,)):
						exists = True;
						break;
					if not exists:
						await ircBot.join_channels((person,));
						mydate = time.strftime('%Y-%m-%d %H:%M:%S');
						util.DBcursor.execute('''insert into irc_channel(channel,joined,raid_auto,raid_time,ghost) 
													select ?,?,?,?,? from dual where not exists (select * from irc_channel where channel = ?)
													''',(person,mydate,0,None,1,person));
						util.DB.commit();
				
				#refresh ghost channels
				global ghost_channels;
				ghost_channels = [];
				for row in util.DBcursor.execute('''select * from irc_channel where left is null and ghost = 1'''):
					ghost_channels.append(row['channel']);
		except Exception:
			traceback.print_exc();
	
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

	async def log_data_in_file(data):
		try:
			st = time.strftime('%Y-%m-%d')
			filename = 'traffic%s.log' % st
			st = time.strftime('%Y-%m-%d %H:%M:%S: ')
			async with aiofiles.open(filename, mode='a', encoding='UTF-8') as f:
				await f.write((st+data.strip()+'\n'))
		except Exception:
			traceback.print_exc()

	@ircBot.event	
	async def event_raw_data(data):
		#await log_data_in_file(data);
		msg = data.strip().lower();
		#@msg-id=host_on :tmi.twitch.tv NOTICE #theschippi :Now hosting Nilesy.
		if '@msg-id=host_on' in msg and '#theschippi' in msg and 'hosting nilesy' in msg:
			if ircBot.get_channel('theschippi'):
				await ircBot.get_channel('theschippi').send('detecting host');
		mymsg = data.strip().lower();	
		#print(mymsg);	
		if (('@msg-id=host_on' in mymsg) and ('now hosting' in mymsg)):
			newhost = int(getControlVal('newhost',1));
			#print('-_1>msg host\n', file=sys.stderr)
			#print('-_2>'+mymsg+"----end\n\n\n", file=sys.stderr)
			#print('-_3>'+data.strip().lower()+"----end\n\n\n", file=sys.stderr)
			#print('-_4>'+mymsg.split(' ')[-1]+"----end\n\n\n", file=sys.stderr)
			if newhost > 0:
				for msg in [x.strip() for x in mymsg.split('\n')]:
					if "now hosting" in msg:
						to_channel = msg.split(' ')[-1][:-1]; 
						print('')
						print(msg.replace('\n','\\n'));
						print('')
						print(to_channel)
						#print("--->"+mymsg+"<---")
						for m in msg.split(' '):
							if m[0] == '#':
								from_channel = m[1:];
								await raid_channel('host',from_channel,to_channel);
								return;
			
	
	@ircBot.command(name='raid')
	async def raidauto_command(ctx):
		if ctx.message.author.is_mod:
			channel = ctx.message.channel;
			channelname = channel.name.lower();
			for row in util.DBcursor.execute('''select * from irc_channel 	
										where left is null
										and channel = ?
										and ghost is null
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
			
	@ircBot.command(name='raidtime')
	async def raidtime(ctx, mtime : int = None):
		"""change the amout of time for follower mode after a raid"""
		if ctx.message.author.is_mod:
			channel = ctx.message.channel;
			channelname = channel.name.lower();
			
			for row in util.DBcursor.execute('''select * from irc_channel 	
										where left is null
										and channel = ?
										and ghost is null
										''',(channelname,)):
				try:
					if not mtime or (mtime == 0):
						return await channel.send('time missing or 0');
					a = row['raid_time'];
					util.DBcursor.execute('''update irc_channel 
												set raid_time = ?
												where left is null
												and channel = ?
												''',(mtime,channelname,));
					util.DB.commit();							
					return await channel.send('ok - time now '+str(mtime)+", was "+str(a));
				except:
					return await channel.send('failed :(')
				return;
			
	
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
			channelname = channel.name.lower();
			for row in util.DBcursor.execute('''select * from irc_channel 	
										where left is null
										and channel = ?
										and ghost is null
										''',(channelname,)):
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
				return;
	return ircBot;
	#bot.run();
	#conn.close();
	
if __name__ == '__main__':
	main();