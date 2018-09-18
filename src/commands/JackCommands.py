'''
Created on 22.09.2017

@author: Carsten Schipmann
'''
from discord.ext import commands;
import discord;
from util import sayWords;
from GuildSettings import isAllowed;
import asyncio;
import random;

class TTSJack():
	def __init__(self, bot):
		self.bot = bot;
		self.gamesRunning = [];
		self.emotes = {	1:'1\u20e3',
						2:'2\u20e3',
						3:'3\u20e3',
						4:'4\u20e3',
						5:'5\u20e3',
						6:'6\u20e3',
						7:'7\u20e3',
						8:'8\u20e3',
						9:'9\u20e3',
						10:'\u0001f51f'};
						
		self.inlineemotes = {	1:':one:',
						2:':two:',
						3:':three:',
						4:':four:',
						5:':five:',
						6:':six:',
						7:':seven:',
						8:':eight:',
						9:':nine:',
						10:':ten:'}

	@commands.group()
	async def ttsjack(self, ctx):
		"""TTSJack Control"""
		if ctx.invoked_subcommand is None and isAllowed(ctx):
			await self.bot.say('ttsjack help')
			
	@ttsjack.command(name='play')
	async def play(self, context):
		"""join the game"""
		if(not isAllowed(context)):
			return;
		if not context.message.guild:
			return await sayWords(context,'need guild');
		if context.message.guild in self.gamesRunning:
			return await sayWords(context,'game in progress');
		svr = context.message.guild;
		usr = context.message.author;
		role = discord.utils.find(lambda r: r.name == 'ttsjack', svr.roles);
		if not role:
			#todo make role
			return await sayWords(context,'need role "ttsjack"');
		
		cnl =  discord.utils.find(lambda r: r.name == 'ttsjack', svr.channels);
		
		if cnl:
			#create channel
			await self.bot.edit_channel(channel=cnl, name='ttsjack'); # sinnlos
			#None;
		else:
			await self.bot.create_channel(svr, 'ttsjack', type=discord.ChannelType.text)
			#return await sayWords(context,'need text-channel "ttsjack"');
		
		#perm = cnl.permissions_for(self.bot.user);
		#usr = svr.get_member(usr.id);
		if not role in usr.roles:
			newroles = [role.id];
			for r in usr.roles:
				newroles.append(r.id);
			
			await self.bot.http.edit_member(svr.id, usr.id, roles = newroles);	
		
		
		
		return await sayWords(context,'success so far');
	
	async def get_answer(self, m, question):
		msg = await m.send(question); 
		# ^^ sollte m sein 
		def check(message):
			return message.author == m;
		res = await self.bot.wait_for(event = 'message', check = check, timeout = 20);
		return res;
	
	
	async def slow(self,msg):
		await asyncio.sleep(5);
		await msg.add_reaction('\N{NEGATIVE SQUARED CROSS MARK}');
		
	
	
	async def get_number_answer(self, m, question:str, yourNumber:int, peoplePlaying:int):
		if not m:
			return m,0;
		if m.id == self.bot.user.id:
			return m,0;
		
		msg = await m.send(question);
		
		for i in range(peoplePlaying):
			if(i != yourNumber):
				print(i)
				await msg.add_reaction(self.emotes[i+1]);
				
		#priv_channel = self.bot.connection._get_private_channel_by_user(m.id)
		
		def intcheck(msg):
			if not msg.author == m:
				return False;
			try:
				if msg.content in self.inlineemotes:
					return True;
				int(msg.content,10);
				return True;
			except:
				return False;
		
		def emojiCheck(reaction,user):
			return user == m.id and reaction.message.id == msg.id and reaction.emoji in self.emotes; 
	
		taskMsg = asyncio.ensure_future(self.bot.wait_for(event='message', timeout = 20, check = intcheck));
		taskEmote = asyncio.ensure_future(self.bot.wait_for(event='reaction_add',check = emojiCheck,  timeout = 20));

		tasks = [taskMsg,
				taskEmote];
			
		await msg.edit(content= question+'\n + vote now!');
		
		doneTasks,pendingTasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED);
		for x in pendingTasks:
			x.cancel();
		#try:
		for x in doneTasks:
			res = x.result();
			if isinstance(res, discord.message.Message):
				return m,int(res.content);
			elif isinstance(res, discord.client.WaitedReaction):
				#print(res.reaction.emoji.encode("ascii"));
				for k, v in self.emotes.items():
					if v == res.reaction.emoji:
						return m,k;
			else:
				return m,0;	
		#except:
		#	pass;	
		return m,0;
	
	@ttsjack.command(name='start', pass_context = True)
	async def start(self, context):
		if(not isAllowed(context)):
			return;
		role = discord.utils.find(lambda r: r.name == 'ttsjack', context.message.guild.roles);
		
		msg = await sayWords(context, role.mention+ '\n game is about to start, you have 30 seconds to press ready');
		await asyncio.sleep(0.1);
		await msg.add_reaction('\N{WHITE HEAVY CHECK MARK}');
		await asyncio.sleep(0.25);
		await msg.add_reaction('\N{NEGATIVE SQUARED CROSS MARK}'); 
		alreadyVoted = {};
		def check(reaction, user):
			if reaction.message.id == msg.id and not user in alreadyVoted and not user.id == self.bot.user.id:
				e = str(reaction.emoji)
				if not e in ['\N{WHITE HEAVY CHECK MARK}', '\N{NEGATIVE SQUARED CROSS MARK}']:
					return False;
				alreadyVoted[user] = e;
				return True;
				#if e.startswith(('\N{WHITE HEAVY CHECK MARK}', '\N{NEGATIVE SQUARED CROSS MARK}')):
			return False;
		
		svr = context.message.guild;
		relevantMembers = [];
		for mem in svr.members:
			if(role in mem.roles and self.bot.user.id != mem.id):
				relevantMembers.append(mem);
				print(mem.name);
		for m in relevantMembers:
			res = None;
			try:
				reaction,user = await self.bot.wait_for(event='reaction_add', 
												check=check, timeout = 30);
				res = 1;
			except asyncio.TimeoutError:
				res = None;
			if not res or ( '\N{NEGATIVE SQUARED CROSS MARK}' == reaction.emoji):
				return await sayWords(context, 'aborted');
				
		await sayWords(context, 'game starting, buckle in');
		failed = False;
		
		for m in relevantMembers:
			try:
				#await m.send("lets play");
				None;
			except discord.errors.Forbidden as e:
				await sayWords(context, m.mention +': you have to allow me to send PM''s');
				#def check(msg):
				#	return msg.context.guild is None;
				#res = await self.bot.wait_for_message(author = m, timeout = 20, check=check);
				#if not res:
				#	return await sayWords(context, m.mention +': didn''t message me in time - aborting game..');
				failed = True;
		if failed:
			return await sayWords(context, 'aborted');
		
		tasks = [self.get_answer(m,"question?") for m in relevantMembers];
		a = await asyncio.gather(*tasks);
		
		answers = {self.bot.user:'truth'};
		for f in a:
			answers[f.author] = f.content;
		
		keys =  list(answers.keys());
		random.shuffle(keys);
		answerstring = "";
		i = 1;		
		for key in keys:
			answerstring += self.inlineemotes[i]+": "+answers[key]+"\n";
			i+=1;

		answerstring= answerstring+"";
		
		await context.send(answerstring,tts=True);
		tasks = [self.get_number_answer(keys[i],answerstring,i,len(answers)) for i in range(len(answers))];
		a = await asyncio.gather(*tasks);
		print(a)
		for m,v in a:
			print(v);








