'''
Created on 22.09.2017

@author: Carsten Schipmann
'''
from discord.ext import commands;
from util import sayWords;
import util;
from GuildSettings import isAllowed, isAdmin;
import ircStart;
import time;

class IRCCommand(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.group()
	async def irc(self, ctx):
		"""IRC Control"""
		if ctx.invoked_subcommand is None and isAllowed(ctx):
			await util.sayWords(ctx,'irc commands are join & part')
			
	@irc.command(name='join')
	async def join(self, context, name : str = None):
		"""joins twitch-chat of <name>"""
		if(not isAdmin(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		name = name.lower();
		try:
			await ircStart.ircBot.join_channels((name,));
			
			mydate = time.strftime('%Y-%m-%d %H:%M:%S');
			util.DBcursor.execute('''insert into irc_channel(channel,joined) 
										select ?,? from dual where not exists (select * from irc_channel where channel = ? and left is null)
										''',(name,mydate,name));
			util.DB.commit();
			return await sayWords(context,'ok');
		except:
			return await sayWords(context,'failed');
		
	@irc.command(name='part')
	async def part(self, context, name : str = None):
		"""parts twitch-chat of <name>"""
		if(not isAdmin(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		name = name.lower();
		try:
			await ircStart.ircBot.part_channels((name,));
			
			mydate = time.strftime('%Y-%m-%d %H:%M:%S');
			util.DBcursor.execute('''update irc_channel 
										set left = ?
										where left is null
										and channel = ?
										''',(mydate,name));
			util.DB.commit();							
			return await sayWords(context,'ok');
		except:
			return await sayWords(context,'failed');
		
	@irc.command(name='limmy')
	async def limmy(self, context):
		"""toggle limmy alert"""
		if(not isAdmin(context)):
			return;
		print(ircStart.ircBot.enableLimmy);
		ircStart.ircBot.enableLimmy = not ircStart.ircBot.enableLimmy;
		util.setControlVal("Limmy",str(ircStart.ircBot.enableLimmy));
		return await sayWords(context,'Limmy-Cake control now '+str(ircStart.ircBot.enableLimmy));












