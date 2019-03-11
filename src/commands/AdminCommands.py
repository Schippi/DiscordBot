'''
Created on 23.09.2017

@author: Carsten Schipmann
'''

from discord.ext import commands;
from GuildSettings import isAdmin;
import discord;
from util import quote;
from util import sayWords;
from util import logEx;
import util;
import GuildSettings;
import TwitchChecker;
from builtins import str;
import math;
import fileinput;


class AdminCommand(commands.Cog):
	
	client = None;
	
	def __init__(self, client):
		self.client = client

	@commands.command(hidden=True)
	async def play(self, context):
		"""ADMIN COMMAND : !play <game>"""
		if isAdmin(context):
			cnt = context.message.content.split(' ',1);
			if len(cnt) > 1:
				await self.client.change_presence(game=discord.Game(name=cnt[1], type=0));
			else:
				return await sayWords(context,'need argument');
			
	@commands.command( hidden=True)
	async def showlog(self, context):
		"""ADMIN COMMAND : !play <game>"""
		if isAdmin(context):
			cnt = context.message.content.split(' ',1);
			if len(cnt) > 1:
				try:
					#filename = 'H:/Code/LiClipse Workspace/DiscordBot/TwitchChecker.log';
					filename = '~/err.log';
					for counter, line in enumerate(fileinput.input(filename, mode='r')):
						pass;
					stri = '';
					fileinput.close();
					for j, line in enumerate(fileinput.input(filename, mode='r')):
						if counter - j <= int(cnt[1]):
							if len(stri+line) > 3000:
								await sayWords(context,quote(stri));
								stri = '';
							stri = stri + line;
					if len(stri) > 0:
						await sayWords(context,quote(stri));
					else:
						await sayWords(context,'_empty_');
					fileinput.close();		
				except Exception as e:
					fileinput.close();
					await sayWords(context,'_error_: '+str(e));
					logEx(e);
			else:
				return await sayWords(context,'need argument');		
			
	@commands.command( hidden=True)
	async def strip(self, context):
		"""ADMIN COMMAND : !strip <something>"""
		if isAdmin(context):
			cnt = context.message.content.split(' ',1);
			if len(cnt) > 1:
				txt = cnt[1].replace('\'\'','"').replace('\'','').replace('#','--').replace('"','\'');
				return await sayWords(context,quote(txt));
			else:
				return await sayWords(context,'need argument');
			
	@commands.command(hidden=True)
	async def broadcast(self, context):
		"""ADMIN COMMAND : !broadcast <message>"""
		if isAdmin(context):
			cnt = context.message.content.split(' ',1);
			if len(cnt) > 1:
				for s in GuildSettings.settings.values():
					await s.guild.get_channel(s.id).send(cnt[1]);
			else:
				return await sayWords(context,'need argument');

	@commands.command( hidden=True, aliases=['insert', 'update', 'delete'])
	async def select(self,context):
		if isAdmin(context):
			msg = context.message.content[1:];
			if len(msg) == 0:
				return await sayWords(context,'need argument');
			sss = [];
			maxlinelength = 18*9;
			cellwidth = 10;
			try:
				mystr = "";
				for row in util.DBcursor.execute(msg):
					cellwidth = math.trunc(maxlinelength / len(row.keys()))-1;
					fmtstr = '{0: <'+str(cellwidth)+'}';
					if len(sss) == 0:
						for k in row:
							sss.append(fmtstr.format(str(k)[:cellwidth]));
						mystr = "|".join(sss)[:maxlinelength];
						mystr = mystr+('\n{0:-<'+str(len(mystr))+'}\n').format('');
					sss = [];
					for key,value in row.items():
						sss.append(fmtstr.format(str(value).replace('\n','\\n')[:cellwidth]));
					mystr = mystr + "|".join(sss)[:maxlinelength]+"\n";
					if len(mystr) + maxlinelength > 2000:
						await sayWords(context, '`'+mystr+'`');
						mystr = '';
				if mystr == '':
					util.DB.commit();  
					mystr = 'success';	  
				return await sayWords(context, '`'+mystr+'`')
			except Exception as ex:
				template = "An exception of type {0} occurred. Arguments:\n{1!r}"
				message = template.format(type(ex).__name__, ex.args)   
				return await sayWords(context, '`'+message+'`')

	@commands.command( hidden=True)
	async def sendMail(self,context):
		if isAdmin(context):
			import yagmail;
			import base64;
			yag = yagmail.SMTP('theschippi@gmail.com',base64.b64decode('dnp6bGxxeWtybnJwaXNsZg==').decode());
			contents = [context.message.content.split(' ',1)[1]];
			yag.send('theschippi@gmail.com', 'CSAR Reminder Mail', contents);
			return await sayWords(context,'done');

	@commands.group( name = 'turn', hidden = True)
	async def switchfeature(self, context):
		"""ADMIN COMMAND : !turn [youtube|twitch] [on|off]"""
		if context.invoked_subcommand is None and GuildSettings.isAllowed(context):
			return await sayWords(context,'need arguments: `!turn [youtube|twitch] [on|off]`');
			 
	@switchfeature.group(name='twitch')
	async def switchtwitch(self, context):
		if str(context.invoked_subcommand) == 'turn twitch' and GuildSettings.isAllowed(context):
			return await sayWords(context,'Twitch status is: '+str(TwitchChecker.EnableTwitch));
	
	@switchtwitch.command(name='off')
	async def switchtwitchoff(self, context):
		if context.invoked_subcommand is None and GuildSettings.isAllowed(context):
			TwitchChecker.EnableTwitch = False;
			return await sayWords(context,'Twitch status is: '+str(TwitchChecker.EnableTwitch));
	
	@switchtwitch.command(name='on')
	async def switchtwitchon(self, context):
		if context.invoked_subcommand is None and GuildSettings.isAllowed(context):
			TwitchChecker.EnableTwitch = True;
			return await sayWords(context,'Twitch status is: '+str(TwitchChecker.EnableTwitch));
			
	@switchfeature.group(name='youtube')
	async def switchyoutube(self, context):
		if str(context.invoked_subcommand) == 'turn youtube' and GuildSettings.isAllowed(context):
			return await sayWords(context,'Youtube status is: '+str(TwitchChecker.EnableYT));
	
	@switchyoutube.command(name='off')
	async def switchyoutubeoff(self, context):
		if context.invoked_subcommand is None and GuildSettings.isAllowed(context):
			TwitchChecker.EnableYT = False;
			return await sayWords(context,'Youtube status is: '+str(TwitchChecker.EnableYT));
	
	@switchyoutube.command(name='on')
	async def switchyoutubeon(self, context):
		if context.invoked_subcommand is None and GuildSettings.isAllowed(context):
			TwitchChecker.EnableYT = True;
			return await sayWords(context,'Youtube status is: '+str(TwitchChecker.EnableYT));
				
			
	@commands.command( hidden=True)
	async def debug(self, context):
		if isAdmin(context):	  
			import datetime;	  
			embed = discord.Embed(title="title ~~(did you know you can have markdown here too?)~~", colour=discord.Colour(0x354751), url="https://discordapp.com", description="this supports [named links](https://discordapp.com) on top of the previously shown subset of markdown. ```\nyes, even code blocks```", timestamp=datetime.datetime.utcfromtimestamp(1506189183))
			embed.set_image(url="https://cdn.discordapp.com/embed/avatars/0.png")
			embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
			embed.set_author(name="author name", url="https://discordapp.com", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")
			embed.set_footer(text="footer text", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")
			await self.client.say(content="this `supports` __a__ **subset** *of* ~~markdown~~ ```js\nfunction foo(bar) {\n  console.log(bar);\n}\n\nfoo(1);```", embed=embed)		
			
			
