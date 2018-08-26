'''
Created on 22.09.2017

@author: Carsten Schipmann
'''
from discord.ext import commands;
import discord;
from util import sayWords;
from util import quote;
from util import askYesNoReaction;
import entities.YTEntry;
import util;
from ServerSettings import isAllowed;
from ServerSettings import getSetting;
from util import fetch;
import aiohttp;
import json;
from TwitchChecker import YTAPI;
from util import sendMail;
import urllib;

class YoutubeCommand():
	def __init__(self, bot):
		self.bot = bot

	@commands.group(pass_context=True)
	async def youtube(self, ctx):
		"""Youtube Control"""
		if ctx.invoked_subcommand is None and isAllowed(ctx):
			await self.bot.say('youtube commands are add, edit and delete')
			
	@youtube.command(name='add', pass_context = True)
	async def add(self, context, name : str = None):
		"""adds a new alert for channel <name>"""
		if(not isAllowed(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		if not context.message.server:
			return await sayWords(context,'need server');
		tname = name.split(' ',1)[0];
		t = (context.message.server.id,tname);	
		entryDict = {'message':entities.YTEntry.defaultYTText};
		entryDict['id_server'] = context.message.server.id;
		entryDict['id_channel'] = context.message.channel.id;
		entryDict['id'] = None;				  
		entryDict['username'] = tname;
		entryDict['color'] = None;
		entryDict['image'] = None;
		entryDict['embedmessage'] = None;
		entryDict['wasprinted'] = None;
		for row in util.DBcursor.execute('SELECT * FROM youtube where ID_Server = ? and username = ?',t):
			return await sayWords(context,'There already exists an Alert for '+tname);
		
		urlsafename = urllib.parse.quote(tname, safe='');
		if tname != urlsafename:
			sendMail('Bot: somebody tried to fuck with the system', context.message.author.name +'\nid'+str(context.message.author.id)+'\n'+  tname +' entered as twitchname');
			return;
		try:
			async with aiohttp.ClientSession() as session:
				html = await fetch(session,'https://www.googleapis.com/youtube/v3/channels?part=id&key='+YTAPI+'&forUsername='+tname,{});
			html = json.loads(html);
			#print(html);
			if len(html['items']) == 0:
				async with aiohttp.ClientSession() as session:
					html = await fetch(session,'https://www.googleapis.com/youtube/v3/channels?part=id&key='+YTAPI+'&id='+tname,{});
				html = json.loads(html);	
				if len(html['items']) == 0:
					return await sayWords(context, 'could not find channel `'+tname+'`');
			if len(html['items']) > 1:
				await sayWords(context, 'username is not unique, please stand by while its being patched');
				sendMail('Bot: not unique username', tname +' is not unique');
				return;
		except:
			return await sayWords(context, 'could not find channel `'+tname+'`');
		
		return await self.edit_youtube(context,entryDict);
		
	@commands.command(name = 'latest', pass_context=True)
	async def latest(self, context, name : str = None):
		"""post latest video of <name>"""
		if(not isAllowed(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		if not context.message.server:
			return await sayWords(context,'need server');
		tname = context.message.content.split(' ',1)[1];
		t = (tname.lower(),tname.lower(),);
		for row in util.DBcursor.execute('SELECT * FROM YTUser where lower(username) = ? or lower(displayname) = ?',t):
			if(row['lastid']):
				return await sayWords(context, 'here is the latest video of `'+tname+'`\n'+
								'https://www.youtube.com/watch?v='+	row['lastid']
								);
			else:
				return await sayWords(context, 'there has not been a video from `'+tname+'` since setup, or setup was very recently');
		return await sayWords(context, tname+' is not being monitored.');	
	
	@youtube.command(name='list', pass_context = True)
	async def list(self, context):
		"""lists active monitors"""
		if(not isAllowed(context)):
			return;
		t = (context.message.server.id,);
		l = [];
		for row in util.DBcursor.execute('SELECT * FROM youtube where ID_Server = ?',t):
			l.append("`"+row['username']+"`");
		return await sayWords(context, 'here are the channels being monitored: '+", ".join(l));
		
	@youtube.command(name='edit', pass_context = True)
	async def edit(self, context, name : str = None):
		"""edits the alert for <name>"""
		if(not isAllowed(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		if not context.message.server:
			return await sayWords(context,'need server');
		tname = name.split(' ',1)[0];
		entryDict = {};
	
		t = (context.message.server.id,tname);
		for row in util.DBcursor.execute('SELECT * FROM youtube where ID_Server = ? and username = ?',t):
			for k in row.keys():
				entryDict[k.lower()] = row[k];
		if len(entryDict.keys()) > 0:		
			return await self.edit_youtube(context,entryDict);
		else:
			return await sayWords(context, 'no Alert found for '+tname);
		
	async def edit_youtube(self, context, entryDict):
		if('id' in entryDict.keys() and entryDict['id']):
			await sayWords(context,'Editing the YoutubeCheck for Channel '+entryDict['username'].upper()+'\nYou can customize the Alert. no command within 120 seconds will abort');
		else:
			await sayWords(context,'Setting up YoutubeCheck for Channel '+entryDict['username'].upper()+'\nYou can customize the Alert. no command within 120 seconds will abort');
		prefix = getSetting(context = context).prefix;	
		helpstring = ('```\n'
					'- Customizing Options:\n'
					+prefix+'ymessage <message> : set custom message, use %%name%%, %%game%%, %%title%% and %%url%% as placeholder\n'
					+prefix+'ycolor <color> : changes the color on the side for the embed. in HEX\n'
					+prefix+'ychannel <id / name> : change the channel - must be on this server\n'
					+prefix+'yembed <message> : changes the Embed - , use %%name%%, %%game%%, %%title%% and %%url%% as placeholder\n'
					+prefix+'yimage <url to image>: sets the imaeg for the embed\n'
					+prefix+'yshow : show current options\n'
					+prefix+'yabort : cancel the process\n'
					+prefix+'yfinish : complete the process\n'
					+prefix+'ytest : test it\n'
					+prefix+'yhelp : print help again'
					'```');
		await self.bot.say(helpstring);  
		while True:
			def check(msg):
				return (msg.content.startswith(prefix+'yshow') or 
						msg.content.startswith(prefix+'ychannel') or  
						msg.content.startswith(prefix+'yfinish') or 
						msg.content.startswith(prefix+'yabort') or 
						msg.content.startswith(prefix+'ymessage') or 
						msg.content.startswith(prefix+'yembed') or 
						msg.content.startswith(prefix+'ycolor') or 
						msg.content.startswith(prefix+'ytest') or 
						msg.content.startswith(prefix+'yimage') or 
						msg.content.startswith(prefix+'yhelp'));
			
			reply = await self.bot.wait_for_message(author = context.message.author, timeout= 120, check = check);
			if reply:
				if(reply.content.startswith(prefix+'yabort')):
					reply = None;
					break;
				if(reply.content.startswith(prefix+'yfinish')):
					break;
				if(reply.content.startswith(prefix+'yshow')):
					rep = 'current options:'
					for k in entryDict.keys():
						if( not (k == 'id' or k == 'id_server' or k == 'username' or k == 'wasprinted') and (not entryDict[k] is None)):
							rep = rep+'\n'+k+'\t: '+str(entryDict[k]);
					await sayWords(context,rep);
					
				if(reply.content.startswith(prefix+'ychannel')):
					try:
						ct = reply.content.split(' ',1);
						chan = reply.server.get_channel(ct[1]);
						if not chan:
							for c in reply.server.channels:
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
						
				if(reply.content.startswith(prefix+'ycolor')):
					ct = reply.content.split(' ');
					try:
						entryDict['color'] = int(ct[1],16);
						await sayWords(context,'color set');
					except:
						entryDict['color'] = None;
						await sayWords(context,'color reset');
					
				if(reply.content.startswith(prefix+'yimage')):
					ct = reply.content.split(' ');
					if len(ct) == 2:
						if ct[1].startswith('http') and (ct[1].endswith('png') or ct[1].endswith('jpg') or ct[1].endswith('jpeg')):
							entryDict['image'] = ct[1];
							await sayWords(context,'image set!');
						else:
							await sayWords(context,'only online images: png and jpg');
					else:
						entryDict['image'] = None;
						await sayWords(context,'image cleared');
				if(reply.content.startswith(prefix+'yhelp')):
					await self.bot.say(helpstring);
				if(reply.content.startswith(prefix+'ymessage')):
					ct = reply.content.split(' ',1);
					if len(ct) == 2:
						entryDict['message'] = ct[1];
						await sayWords(context,'Message set');
					else:
						entryDict['message'] = entities.YTEntry.defaultYTText;
						await sayWords(context,'wrong format!\n'+quote('!tmessage <message>'));
				if(reply.content.startswith(prefix+'yembed')):
					ct = reply.content.split(' ',1);
					if len(ct) == 2:
						entryDict['embedmessage'] = ct[1];
						await sayWords(context,'Embed set');
					else:
						entryDict['embedmessage'] = None;
						await sayWords(context,'Embed cleared');
				if(reply.content.startswith(prefix+'ygame')):
					ct = reply.content.split(' ',1);
					if len(ct) == 2:
						entryDict['game'] = ct[1];
						await sayWords(context,'Game set');
					else:
						entryDict['game'] = None;
						await sayWords(context,'Game cleared');
				if(reply.content.startswith(prefix+'ytest')):
					testx = entities.YTEntry.YTEntry(entryDict);
					embedx = testx.getEmbed('Super Channel','http://google.com','welcome to the internet','image');
					st = testx.getYString(testx.text,'[Super Channel]','http://google.com','[welcome to the internet]','[image]');
					await self.bot.send_message(context.message.channel,content = st,embed=embedx);
			else:
				break;
		if reply:
			entities.YTEntry.YTEntry(entryDict).save();
			await sayWords(context, 'Youtube Alerts updated!');
		else:
			await sayWords(context, 'Process Aborted!');

	@youtube.command(name='delete', pass_context = True)
	async def delete(self,context, name : str = None):
		"""deletes the alert for <name>"""
		if(not isAllowed(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		if not context.message.server:
			return await sayWords(context,'need server');
		tname = name.split(' ',1)[0];
		t = (context.message.server.id,tname);
		

		for row in util.DBcursor.execute('SELECT * FROM youtube where ID_Server = ? and username = ?',t):
			if await askYesNoReaction(context, 'Are you sure you want to delete the YoutubeCheck for'+tname.upper()+'?'):
				t = (row['id'],);
				util.DBcursor.execute('DELETE FROM youtube where ID = ?',t);
				util.DB.commit();
				return await sayWords(context, 'Alert deleted');
			return await sayWords(context, 'no Alert found for '+tname);
		return None;













