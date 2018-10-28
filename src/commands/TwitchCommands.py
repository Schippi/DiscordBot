'''
Created on 22.09.2017

@author: Carsten Schipmann
'''
from discord.ext import commands;
import discord;
from util import sayWords;
from util import quote;
from util import askYesNoReaction;
import util;
import entities.TwitchEntry;
import datetime;
from GuildSettings import isAllowed;
from GuildSettings import getSetting;
from util import fetch;
import aiohttp;
import json;
from util import TwitchAPI;
from util import sendMail;
import urllib;


class TwitchCommand():
	def __init__(self, bot):
		self.bot = bot

	@commands.group()
	async def twitch(self, ctx):
		"""TwitchAlert Control"""
		if ctx.invoked_subcommand is None and isAllowed(ctx):
			await self.bot.say('twitch commands are add, edit and delete')
			
	@twitch.command(name='add')
	async def add(self, context, name : str = None):
		"""adds a new alert for <name>"""
		if(not isAllowed(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		if not context.message.guild:
			return await sayWords(context,'need guild');
		tname = name.split(' ',1)[0];
		t = (context.message.guild.id,tname);	
		entryDict = {'message':entities.TwitchEntry.defaultStreamText};
		entryDict['id_guild'] = context.message.guild.id;
		entryDict['id_channel'] = context.message.channel.id;
		entryDict['id'] = None;				  
		entryDict['username'] = tname;
		entryDict['avatar'] = None;
		entryDict['color'] = None;
		entryDict['game'] = None;
		entryDict['embedmessage'] = None;
		if(tname.lower() == 'timer'):
			entr = entities.TwitchEntry.TwitchEntry(entryDict);
			entryDict['fromm'] = 23;
			entryDict['fromh'] = 59;
			entryDict['game'] = datetime.datetime.now().strftime("%d-%m-%Y");
			entryDict['days'] = '9';
			entr.save();
			entryDict['id'] = entr.id;
			entryDict['newtimer'] = True;
			return await self.edit_twitch(context,entryDict);
		else:
			for row in util.DBcursor.execute('SELECT * FROM twitch where ID_Guild = ? and username = ?',t):
				return await sayWords(context,'There already exists an Alert for '+tname);
		
		urlsafename = urllib.parse.quote(tname, safe='');
		if tname != urlsafename:
			sendMail('Bot: somebody tried to fuck with the system', context.message.author.name +'\nid'+str(context.message.author.id)+'\n'+  tname +' entered as twitchname');
			return;
		try:
			async with aiohttp.ClientSession() as session:
				html = await fetch(session,'https://api.twitch.tv/kraken/channels/'+tname,{'client-id':TwitchAPI});
			html = json.loads(html);
			if html['_id'] <= 0:
				return await sayWords(context, 'could not find channel `'+tname+'`');
		except:
			return await sayWords(context, 'could not find channel `'+tname+'`');
		
		await self.edit_twitch(context,entryDict);
		
	@twitch.command(name='list')
	async def list(self, context):
		"""lists active monitors"""
		if(not isAllowed(context)):
			return;
		t = (context.message.guild.id,'timer');
		l = [];
		for row in util.DBcursor.execute('SELECT * FROM twitch where ID_Guild = ? and not username = ?',t):
			l.append("`"+row['username']+"`");
		return await sayWords(context, 'here are the channels being monitored: '+", ".join(l));
		
	@twitch.command(name='edit')
	async def edit(self, context, name : str = None):
		"""edits the alert for <name>"""
		if(not isAllowed(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		if not context.message.guild:
			return await sayWords(context,'need guild');
		tname = name.split(' ',1)[0].lower();
		entryDict = {};
		if(tname == 'timer'):
			t = (context.message.guild.id,tname);	
			ids = '';
			for row in util.DBcursor.execute('SELECT * FROM twitch where ID_Guild = ? and username = ?',t):
				ids = ids+str(row['id'])+', '
			if not ids == '':
				return await sayWords(context,'for timer editing use one of these id\'s: '+ids);
		if(tname.isnumeric()):
			t = (context.message.guild.id,tname);
			for row in util.DBcursor.execute('SELECT * FROM twitch where ID_Guild = ? and id = ?',t):
				for k in row.keys():
					entryDict[k.lower()] = row[k];
		else:
			t = (context.message.guild.id,tname);
			for row in util.DBcursor.execute('SELECT * FROM twitch where ID_Guild = ? and lower(username) = ?',t):
				for k in row.keys():
					entryDict[k.lower()] = row[k];
		if len(entryDict.keys()) > 0:		
			return await self.edit_twitch(context,entryDict);
		else:
			return await sayWords(context, 'no Alert found for '+tname);
		
	async def edit_twitch(self, context, entryDict):
		if('id' in entryDict.keys() and entryDict['id']):
			if(entryDict['username'].lower() == 'timer'):
				await sayWords(context,'Editing the Timer '+str(entryDict['id']).upper()+'\nYou can customize the Alert. no command within 120 seconds will abort, though some options arent available for timers');
			else:
				await sayWords(context,'Editing the TwitchAlert for Channel '+entryDict['username'].upper()+'\nYou can customize the Alert. no command within 120 seconds will abort');
		else:
			if entryDict['username'] == 'timer':
				now = datetime.datetime.now();
				entryDict['game'] = now.strftime("%d-%m-%Y");
			await sayWords(context,'Setting up TwitchChecker for Channel '+entryDict['username'].upper()+'\nYou can customize the Alert. no command within 120 seconds will abort');
		prefix = getSetting(context = context).prefix;	
		helpstring = ('```\n'
					'- Customizing Options:\n'
					+prefix+'tmessage <message> : set custom message, use %%name%%, %%game%%, %%title%% and %%url%% as placeholder\n'
					+prefix+'timage <url> : the displayed picture\n'
					+prefix+'tcolor <color> : changes the color on the side of the embed. in HEX\n'
					+prefix+'tgame <message> : only trigger when specific game is played\n'
					+prefix+'ttime hh:mm-hh:mm-a,b,c : only trigger within timewindow UTC timezone, a,b,c = days on which to check 0= monday, 5 = saturday\n'
					+prefix+'tchannel <id / name> : change the channel - must be on this guild\n'
					+prefix+'tembed <message> : changes the Embed - , use %%name%%, %%game%%, %%title%% and %%url%% as placeholder\n'
					+prefix+'tshow : show current options\n'
					+prefix+'tabort : cancel the process\n'
					+prefix+'tfinish : complete the process\n'
					+prefix+'ttest : test it in this channel\n'
					+prefix+'thelp : print help again\n'
					+'current time is: '+datetime.datetime.now().strftime('%H:%M:%S')
					+'```');
		await self.bot.say(helpstring);  
		while True:
			def check(msg):
				return (msg.content.startswith(prefix+'tshow') or 
						msg.content.startswith(prefix+'tchannel') or  
						msg.content.startswith(prefix+'tfinish') or 
						msg.content.startswith(prefix+'tabort') or 
						msg.content.startswith(prefix+'tmessage') or 
						msg.content.startswith(prefix+'ttime') or 
						msg.content.startswith(prefix+'tgame') or 
						msg.content.startswith(prefix+'timage') or 
						msg.content.startswith(prefix+'tembed') or 
						msg.content.startswith(prefix+'tcolor') or 
						msg.content.startswith(prefix+'ttest') or 
						msg.content.startswith(prefix+'thelp'));
			try:
				reply = await self.bot.wait_for(event= 'message', author = context.message.author, timeout= 120, check = check);
			except:
				reply = None;
			if reply:
				if(reply.content.startswith(prefix+'tabort')):
					if (('newtimer' in entryDict) and (entryDict['newtimer'] == True)):
						t = (entryDict['id'],);
						util.DBcursor.execute('DELETE FROM twitch where ID = ?',t);
						util.DB.commit();
					reply = None;
					break;
				if(reply.content.startswith(prefix+'tfinish')):
					break;
				if(reply.content.startswith(prefix+'tshow')):
					rep = 'current options:'
					for k in entryDict.keys():
						if( not (k == 'id' or k == 'id_guild' or k == 'username') and (not entryDict[k] is None)):
							rep = rep+'\n'+k+'\t: `'+str(entryDict[k])+'`';
					await sayWords(context,rep);
					
				if(reply.content.startswith(prefix+'tchannel')):
					try:
						ct = reply.content.split(' ',1);
						chan = reply.guild.get_channel(ct[1]);
						if not chan:
							for c in reply.guild.channels:
								if (c.type == discord.ChannelType.text and c.name.lower() == ct[1].strip().lower()):
									chan = c;
									break;
						if chan:
							entryDict['id_channel'] = chan.id;
							await sayWords(context,'channel set');
						else:
							await sayWords(context,'channel not found!\n'+quote('!tchannel <id or name>'));
					except:
						await sayWords(context,'wrong format!\n'+quote('!tchannel <id or name>'));
						
				if(reply.content.startswith(prefix+'tcolor')):
					ct = reply.content.split(' ');
					try:
						entryDict['color'] = int(ct[1],16);
						await sayWords(context,'color set');
					except:
						entryDict['color'] = None;
						await sayWords(context,'color reset');
					
				if(reply.content.startswith(prefix+'timage')):
					ct = reply.content.split(' ');
					if len(ct) == 2:
						if ct[1].startswith('http') and (ct[1].endswith('png') or ct[1].endswith('jpg') or ct[1].endswith('jpeg')):
							entryDict['avatar'] = ct[1];
							await sayWords(context,'image set!');
						else:
							await sayWords(context,'only online images: png and jpg');
					else:
						entryDict['avatar'] = None;
						await sayWords(context,'avatar cleared');
				if(reply.content.startswith(prefix+'thelp')):
					await self.bot.say(helpstring);
				if(reply.content.startswith(prefix+'tmessage')):
					ct = reply.content.split(' ',1);
					if len(ct) == 2:
						entryDict['message'] = ct[1];
						await sayWords(context,'Message set');
					else:
						entryDict['message'] = None;
						await sayWords(context,'wrong format!\n'+quote('!tmessage <message>'));
				if(reply.content.startswith(prefix+'tembed')):
					ct = reply.content.split(' ',1);
					if len(ct) == 2:
						entryDict['embedmessage'] = ct[1];
						await sayWords(context,'Embed set');
					else:
						entryDict['embedmessage'] = None;
						await sayWords(context,'Embed cleared');
				if(reply.content.startswith(prefix+'tgame')):
					if(entryDict['username'].lower() == 'timer'):
						await sayWords(context,'option unavailable for timer');
					else:
						ct = reply.content.split(' ',1);
						if len(ct) == 2:
							entryDict['game'] = ct[1];
							await sayWords(context,'Game set');
						else:
							entryDict['game'] = None;
							await sayWords(context,'Game cleared');
				if(reply.content.startswith(prefix+'ttime')):
					try:
						if(entryDict['username'].lower() == 'timer'):
							ct = reply.content.split(' ',1)[1].split('-',2);
							zeit1 = ct[0].split(':',1);	
							entryDict['fromh'] = int(zeit1[0]);
							entryDict['fromm'] = int(zeit1[1]);  
							if len(ct) == 3:
								zeit2 = ct[1].split(':',1);
								entryDict['untilh'] = int(zeit2[0]);
								entryDict['untilm'] = int(zeit2[1]);  
								days = ct[2].split(',')
								p = [int(s) for s in days];
								entryDict['days'] = ct[2];
							else:
								entryDict['untilh'] = 0;
								entryDict['untilm'] = 0;
								days = ct[1].split(',');
								p = [int(s) for s in days];
								entryDict['days'] = ct[2];
							await sayWords(context,'time set!');
						else:
							ct = reply.content.split(' ',1);
							ct =ct[1].split('-',2);
							zeit1 = ct[0].split(':',1);
							entryDict['fromh'] = int(zeit1[0]);
							entryDict['fromm'] = int(zeit1[1]);  
							zeit2 = ct[1].split(':',1);
							entryDict['untilh'] = int(zeit2[0]);
							entryDict['untilm'] = int(zeit2[1]);  
							days = ct[2].split(',')
							p = [int(s) for s in days];
							entryDict['days'] = ct[2];
							await sayWords(context,'time set!');
					except:
						entryDict['fromh'] = None;
						entryDict['fromm'] = None;
						entryDict['untilh'] = None;
						entryDict['untilm'] = None;  
						entryDict['days'] = None;
						await sayWords(context,'time reset');
				if(reply.content.startswith(prefix+'ttest')):
					testx = entities.TwitchEntry.TwitchEntry(entryDict);
					embedx = testx.getEmbed('Super Channel','Pong','http://google.com','welcome to the internet','image');
					st = testx.getYString(testx.text,'[Super Channel]','[Pong]','http://google.com','[welcome to the internet]','[image]');
					await context.message.channel.send(content = st,embed=embedx);
			else:
				break;
		if reply:
			entities.TwitchEntry.TwitchEntry(entryDict).save();
			await sayWords(context, 'Twitch Alerts updated!');
		else:
			await sayWords(context, 'Process Aborted!');

	@twitch.command(name='delete', pass_context = True)
	async def delete(self,context, name : str = None):
		"""deletes the alert for <name>"""
		if(not isAllowed(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		if not context.message.guild:
			return await sayWords(context,'need guild');
		tname = name.split(' ',1)[0];
		t = (context.message.guild.id,tname);
		
		if(tname.lower() == 'timer'):
			t = (context.message.guild.id,tname);	
			ids = '';
			for row in util.DBcursor.execute('SELECT * FROM twitch where ID_Guild = ? and username = ?',t):
				ids = ids+str(row['id'])+', '
			if not ids == '':
				return await sayWords(context,'for timer editing use one of these id\'s: '+ids);
		if(tname.isnumeric()):
			t = (context.message.guild.id,tname);
			for row in util.DBcursor.execute('SELECT * FROM twitch where ID_Guild = ? and id = ?',t):
				if await askYesNoReaction(context, 'Are you sure you want to delete the Timer '+str(row['id']).upper()+'?'):
					t = (row['id'],);
					util.DBcursor.execute('DELETE FROM twitch where ID = ?',t);
					util.DB.commit();
					return await sayWords(context, 'Alert deleted');
		else:
			for row in util.DBcursor.execute('SELECT * FROM twitch where ID_Guild = ? and username = ?',t):
				if await askYesNoReaction(context, 'Are you sure you want to delete the TwichChecker for '+tname.upper()+'?'):
					t = (row['id'],);
					util.DBcursor.execute('DELETE FROM twitch where ID = ?',t);
					util.DB.commit();
					return await sayWords(context, 'Alert deleted');
					
				return None;
		return await sayWords(context, 'no Alert found for '+tname);













