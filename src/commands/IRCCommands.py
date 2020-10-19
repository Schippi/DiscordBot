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
import traceback;
import sys;

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
			util.DBcursor.execute('''insert into irc_channel(channel,joined,raid_auto,raid_time) 
										select ?,?,?,? from dual where not exists (select * from irc_channel where channel = ? and left is null)
										''',(name,mydate,0,10,name));
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
		
	@irc.command(name='raid')
	async def raid(self, context, name : str = None):
		"""turn raid on and off for channel <name>"""
		if(not isAdmin(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		name = name.lower();
		try:
			for row in util.DBcursor.execute('''select * from irc_channel 	
										where left is null
										and channel = ?
										''',(name,)):
				a = row['raid_auto'];
				if a and a > 0:
					a = 'OFF';
				else:
					a = 'ON'
				util.DBcursor.execute('''update irc_channel 
											set raid_auto = 1 - raid_auto
											where left is null
											and channel = ?
											''',(name,));
				util.DB.commit();							
				return await sayWords(context,'ok - status now '+a);
			return await sayWords(context,'not in channel, join it first');
		except:
			return await sayWords(context,'failed');
		
	@irc.command(name='raidtime')
	async def raidtime(self, context, name : str = None, mtime : int = None):
		"""change the amout of time for follower mode after a raid"""
		if(not isAdmin(context)):
			return;
		if not name or name == '':
			return await sayWords(context,'need arguments');
		if not mtime or (mtime == 0):
			return await sayWords(context,'need arguments');
		name = name.lower();
		try:
			for row in util.DBcursor.execute('''select * from irc_channel 	
										where left is null
										and channel = ?
										''',(name,)):
				a = row['raid_time'];
				util.DBcursor.execute('''update irc_channel 
											set raid_time = ?
											where left is null
											and channel = ?
											''',(mtime,name,));
				util.DB.commit();							
				return await sayWords(context,'ok - time now '+str(mtime)+", was "+str(a));
			return await sayWords(context,'not in channel, join it first');
		except Exception:
			traceback.print_exc(file=sys.stdout);
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












