'''
Created on 22.09.2017

@author: Carsten Schipmann
'''
from discord.ext import commands;
import discord;
from util import sayWords;
import util;
from GuildSettings import isAllowed;
import numpy as np 
from matplotlib import pyplot as plt 
from datetime import datetime;
from datetime import timedelta;
from datetime import timezone;
from matplotlib.dates import DateFormatter;
import os;

class GraphCommand(commands.Cog):
	def __init__(self, bot):
		self.bot = bot;
		
	@commands.group()
	async def graph(self, ctx):
		"""TTSJack Control"""
		if ctx.invoked_subcommand is None and isAllowed(ctx):
			await sayWords(ctx,'graph help')
			
	@graph.command(name='do')
	async def do(self, context, message : str, t : str = None):
		"""do a graph: !graph do <channel> <days to look back> <game>"""
		if(not isAllowed(context)):
			return;
		if not context.message.guild:
			return await sayWords(context,'need guild');
		if len(message) == 0:
			return await sayWords(context,'need argument');
		
		
		today = datetime.now();
		#start = datetime(today.year, today.month, today.day);
		
		end = datetime(2020,8, 1);
		cnt = 1;
		
		argsx = context.message.content.split(' ', 4);
		gamez = [];
		print(argsx)
		offset = 0;
		try:
			offset = int(argsx[3]);
		except:
			if(len(argsx) > 3):
				return await sayWords(context,'argument error: !graph do <channel> <days to look back> <game>');
		
		start = today - timedelta(days=offset);
		
		if(len(argsx) == 3):
			return await sayWords(context,'argument error: !graph do <channel> <days to look back> <game>');
		if(len(argsx) > 4):
			gamez.append(argsx[4]);
		else:
			for overrow in util.DB.cursor().execute('select game,c from (SELECT game, count(*) as c FROM twitchstats where channel = ? group by game) order by c desc limit 3',(message,)):
				gamez.append(overrow['game']);
				print(overrow['game']+': '+str(overrow['c']))	
		x = {};
		progress= 0;
		y = {};
		print(gamez)
		print(offset)
		print(start)
		fig_size = plt.gcf().get_size_inches() #Get current size
		sizefactor = 4 #Set a zoom factor
		# Modify the current size by the factor
		plt.gcf().set_size_inches(sizefactor * fig_size);
		plt.ylim(top=1000);
		ax = plt.gca();
		formatter = DateFormatter("%H:%M")
		ax.xaxis.set_major_formatter(formatter)
		#for overrow in util.DB.cursor().execute('SELECT distinct game FROM twitchstats where channel = ?',(message,)):
			#gamez.append(overrow['game']);
		ymax = 0;
		try:
			for game in gamez:
				x[game] = [];
				y[game] = [];
				for row in util.DB.cursor().execute('SELECT * FROM twitchstats t where channel = ? and game = ? order by id asc',(message,game,)):
					rowdate = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S');
					
					#if(progress % 1000 == 0):
					#	print(progress)
					if rowdate < start:
						continue;
					progress = progress + 1;
					rowdate = rowdate.replace(year=2020, month=1,day=1)
					#while (cnt > 1) and (start < rowdate):
					#	x.append(start);
					#	y.append(0);
					#	cnt = cnt +1;
					#	start = start + timedelta(minutes = 1);
					x[game].append(rowdate);
					cnt = cnt+1;
					#x[game].append(cnt);
					ymax = max(int(row['viewcount']),ymax);
					y[game].append(int(row['viewcount']));
					#start = start + timedelta(minutes = 1);
		except Exception as e:
			print(e);
		ymax = ymax +10;
		plt.ylim(top=ymax);
		if progress > 0:
			cnt = 1;	
			for k in x.keys():
				mc = 'C'+str(cnt);
				cnt = cnt + 1;
				if(len(x[k]) > 0):
					plt.scatter(x[k], y[k], c=mc,label = k);
			plt.legend();
			#plt.axis([0, 6, 0, 20]);
			fname = util.cfgPath+'/graph_'+str(context.message.id)+'.png';
			plt.savefig(fname, bbox_inches='tight');
			plt.close()
			plt.clf()
			plt.cla()
			f = discord.File(fname)
			await sayWords(context,'displaying '+str(progress)+' datapoints',file=f);
			try:
				os.remove(fname);
			except OSError:
				pass;
			return;
		else:
			return await sayWords(context,'no data in designated time');






