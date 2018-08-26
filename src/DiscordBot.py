from commands.JackCommands import TTSJack
CSARversion = '0.3.0'

import ServerSettings;
import sys;
import time;
import pytz;
import util;
import logging;
from datetime import datetime, timedelta;
import sqlite3;
import os;
from RunnerGame import playgame;
import asyncio;
from asyncio import CancelledError;
import signal;

from ServerSettings import ServerSetting;
from ServerSettings import isAllowed;
from ServerSettings import getSetting;

from commands.TwitchCommands import TwitchCommand;
from commands.AdminCommands import AdminCommand;
from commands.YoutubeCommands import YoutubeCommand;
from commands.JackCommands import TTSJack;

import discord.ext.commands;

from discord.ext.commands import Bot;
from TwitchChecker import startChecking

from util import sayWords;
from util import quote;
from util import askYesNoReaction;
from util import sendMail;
from discord.ext.commands.errors import CommandNotFound;

logging.basicConfig(level=logging.INFO);
NOT_ALLOWED = 'You are not allowed to call this command!';
UTC = pytz.utc;
TIMEZONE = pytz.timezone('Europe/London');

utc_dat = datetime.utcnow();
loc_dt = TIMEZONE.localize(datetime.utcnow());

if len(sys.argv) < 2:
	print('please provide token')
	exit();
file = open(sys.argv[1],"r");
print(sys.argv[2]);
TOKEN = file.read().splitlines()[0];
file.close();

if len(sys.argv) >= 3:
	util.cfgPath = sys.argv[2];
	
try:
	fil = open(util.cfgPath+'/testing.cfg','r');
	testing = True;
	fil.close();
except Exception:
	testing = False;
	pass;
	
DBFile = util.cfgPath+'/bot.db';
DBJournal = util.cfgPath+'/bot.db-journal';


try:
	os.remove(DBJournal);
except OSError:
	pass;

util.DB = sqlite3.connect(DBFile);
util.DB.row_factory = util.dict_factory;
util.DBcursor = util.DB.cursor();

def checkPrefix(bot, disMessage):
	try:
		sett = getSetting(disMessage.server.id);
	except:
		sett = None;
	if sett is None:
		return '!';
	else:
		return sett.prefix;

client = Bot(command_prefix=checkPrefix)

def needArgs(msg):
	return 'needs more arguments:\n'+quote(msg);

def printRoles(client,context):
	result = "The roles are:\n`"
	for role in context.message.server.roles:
		result += role.name + ": " + role.id + ", \n"
	return client.say(result+'`')
	
@client.async_event
async def on_ready():
	
	for svr in client.servers:
		print(svr.name);
		ServerSetting(svr);
	if not testing:	
		sendMail('Bot Back Up','bot back online');
	else:
		sendMail('abc','bot back online');
		pass;
		#client.send_message()		
	await client.change_presence(game=discord.Game(name='Feel Good (Gorillaz)', type=0));
	#TwitchChecker.client = client;
	
	print("Client logged in");
	
@client.async_event
async def on_message(message):
	ok = True;
	if message.author.id != client.user.id: # and not message.author.bot
		if message.server:
			sett = getSetting(message.server.id);
			if sett is None:
				ok = False;
			if ok and (message.author.id != ServerSettings.adminId) and (message.author.id in sett.timeouts.keys()):
				now = datetime.utcnow();
				untilDate = sett.timeouts[message.author.id];
				if untilDate < now:
					sett.timeouts.pop(message.author.id)
				else:
					d1_ts = time.mktime(now.timetuple())
					d2_ts = time.mktime(untilDate.timetuple())
					minu = int(round(d2_ts-d1_ts) / 60);
					if minu == 1:
						await client.send_message(message.author,'you are currently timed out.\ntake a deep breath and come back in '+str(minu)+' minute');
					else:
						await client.send_message(message.author,'you are currently timed out.\ntake a deep breath and come back in '+str(minu)+' minutes');
					return await client.delete_message(message);
					ok = False;
			if(ok):
				msg = message.content.split(' ',1);
				if (len(msg) > 0) and (msg[0][:1] == checkPrefix(client,message)) and (not msg[0][1:] in client.commands.keys()):
					if sett.isAllowed(userID = message.author.id,command = msg[0]):
						for cmd in sett.customCommands:
							if(cmd.command == msg[0][1:]):
								ok = False;
								await sayWords(sett = sett, message = cmd.response, chan = message.channel);
		if(ok):
			try:
				await client.process_commands(message)
			except CommandNotFound:
				pass;
	
@client.async_event
async def on_server_join(server):
	ServerSetting(server);
	
@client.command(pass_context=True)
async def shitgame(context):
	if(context.message.server):
		await client.send_message(context.message.channel, 'initializing...\n be in a voicechannel - deaf = down - mute = up')
		await asyncio.sleep(2);
		for m in client.messages:
			if m.author.id == client.user.id:
				await playgame(m,context.message.author.id,client);
	else:
		await client.send_message(context.message.author,'whisper-game not supported');
		
@client.command(pass_context=True, hidden=True)
async def get(context):
	"""!get <kind> <String> : display markup String"""
	if isAllowed(context):
		cnt = context.message.content.split(' ',2);
		if(len(cnt) > 2):
			result = '```'+cnt[1]+'\n'+cnt[2]+'```'
			await sayWords(context,result);
			await sayWords(context,quote(result));
		else:
			return await sayWords(context,needArgs('!get <kind> <String>'));
		
@client.command(pass_context=True)
async def allow(context):
	"""!allow <command>:<role> : allows rights to use the command"""
	for svr in client.servers:
		ServerSetting(svr);
	if isAllowed(context):
		cnt = context.message.content.split(' ',1);
		if(len(cnt) < 2):
			return await sayWords(context,needArgs('!allow <Command> <Role> '));
		cnt = cnt[1].split(':',1);
		if(len(cnt) > 1):
			rl = getRoleID(context,cnt[1].strip());
			if rl:
				getSetting(context = context).addPermission(rl,cnt[0]);
				return await sayWords(context,'command '+cnt[0]+' now usable by Role '+cnt[1]);
			else:
				return await sayWords(context,'no such role:\n'+quote('!allow <Command>:<Role>'));
		else:
			return await sayWords(context,needArgs('!allow <Command>:<Role> '));
	else:
		return await sayWords(context,NOT_ALLOWED);
		
@client.command(pass_context=True)
async def deny(context):
	"""!deny <command> <role> : revokes rights to use the command"""
	if isAllowed(context):
		cnt = context.message.content.split(' ',1);
		cnt = cnt[1].split(':',1);
		if(len(cnt) > 1):
			rl = getRoleID(context,cnt[1].strip());
			if rl:
				getSetting(context = context).removePermission(rl,cnt[0]);
				return await sayWords(context,'command '+cnt[0]+' now usable by Role '+cnt[1]);
			else:
				return await sayWords(context,'no such role:\n'+quote('!allow <Command>:<Role>'));
		else:
			return await sayWords(context,needArgs('!allow <Command> <Role> '));
	else:
		return await sayWords(context,NOT_ALLOWED);
			
@client.event
async def on_member_join(member):
	sett = getSetting(member.server.id);
	if sett and (sett.getWelcomeMessage() != ''):
		return await client.send_message(member,sett.getWelcomeMessage());
		
@client.command(pass_context=True)
async def setWelcome(context):
	"""!setWelcome <message> : set messaged sent on joining the server"""
	if isAllowed(context):
		cnt = context.message.content.split(' ',1);
		if len(cnt) > 1:
			getSetting(context = context).setWelcomeMessage(cnt[1]);
			return await sayWords(context,'welcome message set to:\n\n'+quote(cnt[1]) );
		else:
			getSetting(context = context).setWelcomeMessage('');
			return await sayWords(context,'welcome message cleared');
	else:
		return await sayWords(context,NOT_ALLOWED);			
	
@client.command(pass_context=True)
async def setLogLevel(context):
	"""!setLogLevel whisper|mute|channel : how the bot responds"""
	if isAllowed(context):
		cnt = context.message.content.split(' ',1);
		if len(cnt) > 1:
			getSetting(context = context).setLogLevel(cnt[1]);
			return await sayWords(context,'loglevel set to:\n\n'+quote(cnt[1]));
		else:
			getSetting(context = context).setLogLevel('channel');
			return await sayWords(context,'loglevel set to channel');
	else:
		return await sayWords(context,NOT_ALLOWED);	
		
@client.command(pass_context=True)
async def timeout(context):
	"""!timeout [serverID if whispering] <person> <time in seconds>"""
	allowed = False;
	i = 0;
	if not context.message.server:
		cnt = context.message.content.split(' ',3);
		if len(cnt) == 3:
			cnt.append('600');
		if len(cnt) > 3:
			sett = getSetting(cnt[1]);
			i = 1;
			allowed = isAllowed(userid =context.message.author.id, serverid=cnt[1], command=cnt[0]);
	else:
		allowed = isAllowed(context);
		sett = getSetting(context = context);
		cnt = context.message.content.split(' ',2);
		if len(cnt) == 2:
			cnt.append('600');
	if allowed:
		if len(cnt) > 2+i:
			usr = cnt[1+i]
			amount = int(cnt[2+i]);			
			sett.timeoutPerson(usr,amount)
			if(amount > 1):
				return await client.send_message(context.message.author,usr + ' has been timed out for '+str(amount)+'seconds');	
		else:
			return await client.send_message(context.message.author,needArgs('!timeout [serverid] <user> [time in seconds = 600]'));
		
@client.command(pass_context=True)
async def setschedule(context):
	"""!setschedule <message> : sets message for !schedule"""
	if not context.message.server:
		return await sayWords(context, 'you need to set the message in a channel of the server its for');
	else:
		if isAllowed(context):
			if(len(context.message.content.split(' ',1)) <= 1):
				msg = ''
			else:
				msg = context.message.content.split(' ',1)[1];
			sett = getSetting(context=context);
			sett.scheduleMessage = msg;
			sett.saveSettings();
			return await sayWords(context, 'schedule set');
		
@client.command(pass_context=True)
async def schedule(context):
	"""!schedule : displays a message + current time"""
	if isAllowed(context):
		sett = getSetting(context=context);
		if sett.scheduleMessage != '':
			if util.is_dst('Europe/London'):
				return await sayWords(context, sett.scheduleMessage+'\ncurrently it is '+TIMEZONE.localize(datetime.utcnow()+timedelta(hours = 1)).strftime('%a %I:%M %p')+' BST');
			else:
				return await sayWords(context, sett.scheduleMessage+'\ncurrently it is '+TIMEZONE.localize(datetime.utcnow()).strftime('%a %I:%M %p')+' GMT');
		
@client.command(pass_context=True)
async def setcom(context):
	"""!setcom <command> <response> : sets a custom command"""
	await xsetcom(context, context.message.content);
	
async def xsetcom(context, message):	
	if isAllowed(context):
		if type(message) is str:
			msg = message.split(' ',2);
		else:
			msg = [''] + message;
		if len(msg) < 3:
			return await sayWords(context, needArgs('!setcom <command> <response>'));
		else:
			if msg[1][:1] == '!':
				cmd = msg[1];
			else:
				cmd = '!'+msg[1];
			cmd = cmd.lower();
			if cmd[1:] in client.commands.keys():
				return await sayWords(context, 'denied: command is predefined');
			else:
				sett = getSetting(context=context);
				sett.setCom(cmd,msg[2]);
				return await sayWords(context, 'command set');
		
@client.command(pass_context=True)
async def addcom(context):
	"""!addcom <command> <response> : add a custom command"""
	await xaddcom(context, context.message.content);
	
async def xaddcom(context, message):
	if isAllowed(context):
		if type(message) is str:
			msg = message.split(' ',2);
		else:
			msg = [''] + message;
		if len(msg) < 3:
			return await sayWords(context, needArgs('!addcom <command> <response>'));
		else:
			sett = ServerSettings.getSetting(context = context);
			if msg[1][:1] == sett.prefix:
				cmd = msg[1][1:];
			else:
				cmd = msg[1];
			cmd = cmd.lower();
			if cmd[1:] in client.commands.keys():
				return await sayWords(context, 'denied: command is predefined');
			else:
				sett = getSetting(context=context);
				if sett.addCom(cmd,msg[2]):
					return await sayWords(context, 'command added');
				else:
					return await sayWords(context, 'command already exists');
			
@client.command(pass_context=True)
async def editcom(context):
	"""!editcom <command> <response> : edits a custom command"""
	await xeditcom(context, context.message.content);
	
async def xeditcom(context, message):
	if isAllowed(context):
		if type(message) is str:
			msg = message.split(' ',2);
		else:
			msg = [''] + message;
		if len(msg) < 3:
			return await sayWords(context, needArgs('!editcom <command> <response>'));
		else:
			if msg[1][:1] == '!':
				cmd = msg[1];
			else:
				cmd = '!'+msg[1];
			cmd = cmd.lower();
			if cmd[1:] in client.commands.keys():
				return await sayWords(context, 'denied: command is predefined');
			else:
				sett = getSetting(context=context);
				if sett.editCom(cmd,msg[2]):
					return await sayWords(context, 'command updated');
				else:
					return await sayWords(context, 'command doesn''t exist');
				
@client.command(pass_context=True)
async def delcom(context):
	"""!delcom <command> : deletes a custom command"""
	await xdelcom(context, context.message.content.split(' ',2)[1]);
		
@client.group(pass_context=True, aliases=['list'])
async def commands(context):
	"""!commands : displays serverID & !help"""
	if context.invoked_subcommand is None and isAllowed(context): 
		msg = '';
		if context.message.server:
			svr = context.message.server.id;
			for mm in client.formatter.format_help_for(context, client):
				msg = msg+mm;
			sett = ServerSettings.getSetting(context = context);
			
			if len(sett.customCommands) > 0:
				custommsg = '\n```Custom Server Commands:';
				for cmd in sett.customCommands:
					custommsg = custommsg+'\n'+cmd.command+' : '+cmd.response;
				msg = msg + custommsg + '```';
			#for k in client.commands.keys():
			#	if not client.commands[k].hidden:
			#		print(k);
			#		msg = msg+k+':\t'+str(client.commands[k].help)+'\n';
		else:
			svr = 'None'
		
		return await sayWords(context,'server ID is: '+str(svr)+'\n'+
						msg);
	
@commands.command(pass_context=True)
async def add(context : discord.ext.commands.Context, *msg):
	"""adds a command, doesnt do anything if command already exists"""
	x = context.message.content.split(' ',3)[2:];
	await xaddcom(context, x);
	
@commands.command(pass_context=True)
async def edit(context : discord.ext.commands.Context, *msg):
	"""edits a command, doesnt do anything if command doesnt exist"""
	await xeditcom(context, context.message.content.split(' ',3)[2:]);

@commands.command(pass_context=True)
async def set(context : discord.ext.commands.Context, *msg):
	"""sets a command, overrides if already existing"""
	await xsetcom(context, context.message.content.split(' ',3)[2:]);				
	
@commands.command(pass_context=True)
async def delete(context : discord.ext.commands.Context, msg : str):
	"""deltes a command"""
	await xdelcom(context,msg);
	
async def xdelcom(context : discord.ext.commands.Context, msg : str):
	if isAllowed(contxt = context):
		if msg == '':
			await sayWords(context, "need arguments");
		sett = ServerSettings.getSetting(context = context);
		if msg[:1] == '!':
			cmd = msg;
		else:
			cmd = '!'+msg;
		cmd = cmd.lower();				
		if sett.delCom(cmd):
			await sayWords(context, "command deleted")
		else:
			await sayWords(context, "no such command")
			
@client.command(pass_context=True, aliases=['setprefix'])			
async def setPrefix(context : discord.ext.commands.Context):
	"""!setPrefix <prefix> sets the prefix for this server"""
	if isAllowed(contxt = context):
		msg = context.message.content;
		ct = msg.split(' ');
		if(len(ct) < 2):
			return await sayWords(context,needArgs('!setPrefix <prefix>'))
		if await askYesNoReaction(context, 'Change Prefix to "'+ct[1]+'" ?'):
			sett = ServerSettings.getSetting(context = context);
			sett.prefix = ct[1];
			sett.saveSettings();
			await sayWords(context, 'prefix changed!');
		else:
			await sayWords(context, 'Aborted change of prefix');
		
@client.command(pass_context=True, aliases = ['sayinchannel','sayInchannel','sayinChannel','sendtochannel','sendTochannel','sendToChannel',])
async def sayInChannel(context : discord.ext.commands.Context):
	"""!sayInChannel <id or name>:<msg> sends a message to a different channel on the server"""
	if isAllowed(contxt = context):
		msg = context.message.content
		ct = msg.split(' ',1);
		if msg == '' or len(ct) != 2:
			return await sayWords(context, "need arguments" + str(len(ct)) + " " +str(ct));
		ct = ct[1].split(':',1);
		if msg == '' or len(ct) != 2:
			return await sayWords(context, "need arguments, missing : " + str(len(ct)) + str(ct));
		ch = context.message.server.get_channel(ct[0]);
		if not ch:
			for c in context.message.server.channels:
				if(c.type == discord.ChannelType.text and c.name.lower() == ct[0].strip().lower()):
					ch = c;
					break;
		if ch:
			return await client.send_message(destination=ch,content= ct[1].strip());
		else:
			return await sayWords(context, "channel "+ct[0]+" not found on this server");
		
@client.command()
async def version(*msg):
	"""displays the running version """
	return await client.say('CSAR v.'+CSARversion+'\nApi: '+ discord.__version__);
		
# HELP FUNCTIONS		
		
def getRoleID(context,rolename):
	for role in context.message.server.roles:
		if role.name.lower() == rolename.lower():
			return role.id;
	return None;

@asyncio.coroutine                                       
def exit():                                              
	loop = asyncio.get_event_loop()                      
	loop.stop()
	
def ask_exit():
	print('recieved Keyboard interrupt, exiting..');
	for task in asyncio.Task.all_tasks():
		task.cancel();                    
	asyncio.ensure_future(exit());  
	
util.client = client;
#client.remove_command('help');
checkingTask = client.loop.create_task(startChecking(client));

client.add_cog(TwitchCommand(client));
client.add_cog(YoutubeCommand(client));
client.add_cog(AdminCommand(client));
client.add_cog(TTSJack(client));

try:
	for sig in (signal.SIGINT, signal.SIGTERM):          
		client.loop.add_signal_handler(sig, ask_exit);
except NotImplementedError:
	print("no signals supported");
print("discord.py version: " + discord.__version__);

msg = "";

try:
	client.run(TOKEN); 
	print("client stopped for some reason");
	msg = msg + '\n'+time.strftime('%X %x %Z') +' Crash: no Exception :-('
except (KeyboardInterrupt,CancelledError):
	print("interrupt");
	pass;
except Exception as ex:
	template = "An exception of type {0} occurred. Arguments:\n{1!r}"
	message = template.format(type(ex).__name__, ex.args)
	print(message)
	err = str(ex);
	msg = msg + '\n'+ time.strftime('%X %x %Z') + ': ' + 'Exception: '+message+'\n'+err;
	if not testing:
		sendMail('Server Crash Report',msg);
try:
	checkingTask.cancel();
	asyncio.ensure_future(exit())
except:
	pass;
print("Ende");



#sendMail('!!!!!!Server crashed for good',time.strftime('%X %x %Z') + ': ' + 'please log back in');





















