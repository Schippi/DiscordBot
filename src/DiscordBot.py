import GuildSettings;
import sys;
import time;
import pytz;
import util;
import logging;
from datetime import datetime, timedelta;
import sqlite3;
import os;
import asyncio;
from asyncio import CancelledError;

import signal;

from GuildSettings import GuildSetting;
from GuildSettings import isAllowed;
from GuildSettings import getSetting;

from commands.TwitchCommands import TwitchCommand;
from commands.TimerCommands import TimerCommand;
from commands.AdminCommands import AdminCommand;
from commands.YoutubeCommands import YoutubeCommand;
from commands.GraphCommands import GraphCommand;
from commands.IRCCommands import IRCCommand;
from commands.JackCommands import TTSJack;
from RunnerGame import playgame;
import traceback;
import DBUpdate;

import discord;
from discord.ext import commands;
from discord.ext.commands.errors import CommandNotFound;

from TwitchChecker import startChecking;

from util import sayWords;
from util import quote;
from util import askYesNoReaction;
from util import sendMail;

CSARversion = '1.3.0'
logging.basicConfig(level=logging.INFO);
NOT_ALLOWED = 'You are not allowed to call this command!';
UTC = pytz.utc;
TIMEZONE = pytz.timezone('Europe/London');

utc_dat = datetime.utcnow();
loc_dt = TIMEZONE.localize(datetime.utcnow());

if len(sys.argv) < 2:
    print('please provide token')
    exit();
file = open(sys.argv[1], "r");
print(sys.argv[2]);
TOKEN = file.read().splitlines()[0];
file.close();

if len(sys.argv) >= 3:
    util.cfgPath = sys.argv[2];

if len(sys.argv) >= 4:
    util.serverHost = sys.argv[3];

if len(sys.argv) >= 5:
    util.serverPort = int(sys.argv[4]);

try:
    fil = open(util.cfgPath + '/testing.cfg', 'r');
    testing = True;
    fil.close();
except Exception:
    testing = False;
    pass;

util.serverFull = util.serverHost;
if util.serverPort != 80 and util.serverPort != 443:
    util.serverFull = util.serverFull + ':' + str(util.serverPort);

DBFile = util.cfgPath + '/bot.db';
DBJournal = util.cfgPath + '/bot.db-journal';
DBLOG = util.cfgPath + '/botlog.db';
DBLOGJournal = util.cfgPath + '/botlog.db-journal';

try:
    os.remove(DBJournal);
except OSError:
    pass;
try:
    os.remove(DBLOGJournal);
except OSError as e:
    pass;

util.DB = sqlite3.connect(DBFile);
util.DB.row_factory = util.dict_factory;
util.DBcursor = util.DB.cursor();

DBUpdate.update(util.DB, util.DBcursor)

LOGDB = sqlite3.connect(DBLOG);
LOGDB.row_factory = util.dict_factory;
LOGDBcursor = LOGDB.cursor();
LOGCNT = 0;
LOGDBCHANGES = 0;
LOGTIME = datetime.utcnow();
util.DBLOG = LOGDB;

LOGDBcursor.execute('''CREATE TABLE IF NOT EXISTS  `dual` (
		`DUMMY`	TEXT
	);''');

LOGDBcursor.execute('''insert into dual(dummy)
					select 'X' from sqlite_master 
					where not exists (select * from dual)
					limit 1''');


def checkPrefix(bot, disMessage):
    try:
        sett = getSetting(disMessage.guild.id);
    except Exception:
        sett = None;
    if sett is None:
        return '!';
    else:
        return sett.prefix;


try:
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=checkPrefix, intents=intents)
except Exception as e:
    print(e);
    print('INTENTS FAILED');
    client = commands.Bot(command_prefix=checkPrefix)


def needArgs(arg_msg):
    return 'needs more arguments:\n' + quote(arg_msg);


def printRoles(client, context):
    result = "The roles are:\n`"
    for role in context.message.guild.roles:
        result += role.name + ": " + role.id + ", \n"
    return client.say(result + '`')


@client.event
async def on_ready():
    for svr in client.guilds:
        GuildSetting(svr);
        print(svr.name + '\t' + str(svr.id));
    if not testing:
        allguilds = [];
        for svr in client.guilds:
            allguilds.append(svr.id);
        print(allguilds)
        guildcount = 0;
        for row in util.DBcursor.execute('SELECT count(distinct id_guild) as guildcount FROM twitch'):
            guildcount = int(row['guildcount']);

        placeholders = ', '.join(['?'] * len(allguilds));

        util.DBcursor.execute('delete FROM twitch where id_guild not in ({})'.format(placeholders), tuple(allguilds));

        util.DBcursor.execute('delete FROM guild where id not in ({})'.format(placeholders), tuple(allguilds));

        for row in util.DBcursor.execute('SELECT count(distinct id_guild) as guildcount FROM twitch'):
            guildcount = guildcount - int(row['guildcount']);
        if (guildcount != 0):
            print('deleted ' + str(guildcount) + ' entries');
        util.DB.commit();
    await client.change_presence(activity=discord.Activity(name='Feel Good (Gorillaz)', type=0));
    # TwitchChecker.client = client;

    print("Client logged in");

from chroma import *
import chromaconfig

@client.event
async def on_message(message):
    ok = True;
    if message.author.id != client.user.id:  # and not message.author.bot
        if message.author.id in [296707158047719425, '296707158047719425', 106087197588889600, '106087197588889600']:
            if util.getControlVal('chroma', 'false').lower() == 'true':
                print('trying chroma')
                if not client.running_chroma:
                    client.running_chroma = True;
                    try:
                        print(message.content)
                        print(chromaconfig.chroma_ip)
                        print(chromaconfig.chroma_port)
                        print('go on..')
                        keyboard = ChromaImpl(custom_url=chromaconfig.chroma_ip, custom_port=chromaconfig.chroma_port);
                        await keyboard.connect()
                        await keyboard.show_text(" "+message.content, 5, color=(255, 255, 0))
                        await keyboard.disconnect()
                    except:
                        print('chroma failed');
                    finally:
                        print('chroma done')
                        client.running_chroma = False;

        if message.guild:
            try:
                if util.pleaseLog:
                    global LOGCNT;
                    global LOGTIME;
                    LOGCNT = (LOGCNT + 1) % 10;
                    valdict = {};
                    valdict['GUILD_ID'] = message.guild.id;
                    valdict['AUTHOR_ID'] = message.author.id;
                    valdict['MESSAGE_ID'] = message.id;
                    membrname = message.author.display_name if message.author.display_name else message.author.name;
                    valdict['AUTHOR_NAME'] = membrname + '#' + message.author.discriminator;
                    valdict['TIME'] = time.strftime('%Y-%m-%d %H:%M:%S');
                    valdict['MESSAGE'] = message.content;
                    vallist = list(valdict.keys());
                    q1 = 'INSERT INTO LOG (' + ', '.join(vallist) + ' )';
                    q1 = q1 + ' values ( ' + ', '.join(['?' for s in vallist]) + ' )';
                    l1 = list(valdict.values());
                    try:
                        LOGDBcursor.execute(q1, l1);
                    except sqlite3.OperationalError as e:
                        await asyncio.sleep(0.5);
                        LOGDBcursor.execute(q1, l1);
                    if (LOGCNT <= 0 or (LOGTIME + timedelta(minutes=5) < datetime.utcnow())):
                        # print('commit')
                        LOGDB.commit();
                    LOGTIME = datetime.utcnow();
                else:
                    global LOGDBCHANGES;
                    if (LOGDBCHANGES < LOGDB.total_changes):
                        LOGDB.commit();
                        LOGDBCHANGES = LOGDB.total_changes;
            except Exception as e:
                traceback.print_exc(file=sys.stdout);
            # pass;
            sett = getSetting(message.guild.id);
            if sett is None:
                ok = False;
            for att in message.attachments:
                await att.save(util.cfgPath + "/qr/botcheck");
                from pyzbar.pyzbar import decode;
                from PIL import Image;
                from shutil import copyfile;
                x = decode(Image.open(util.cfgPath + "/qr/botcheck"));
                #copyfile(util.cfgPath + "/qr/botcheck", util.cfgPath + "/qr/" + str(att.id) + "_" + str(att.filename));
                if len(x) > 0:
                    try:
                        if x[0].data and "discord" in x[0].data.decode("utf-8", "ignore").lower():
                            ok = False;
                            try:
                                await message.delete();
                            except:
                                pass;
                        # with open(util.cfgPath+"/qr/"+str(att.id)+".data","w+") as the_file:
                        #	the_file.write(str(x[0])+"\n\n");
                        #	the_file.write(str(x[0].data)+"\n\n");
                        #	the_file.write(att.filename+"\n\n");
                        #	the_file.write(str(message)+"\n\n");
                    except:
                        if x[0].data:
                            print(x[0].data);
                        pass
            if ok and (message.author.id != GuildSettings.adminId) and (message.author.id in sett.timeouts.keys()):
                now = datetime.utcnow();
                untilDate = sett.timeouts[message.author.id];
                if untilDate < now:
                    sett.timeouts.pop(message.author.id)
                else:
                    d1_ts = time.mktime(now.timetuple())
                    d2_ts = time.mktime(untilDate.timetuple())
                    minu = int(round(d2_ts - d1_ts) / 60) + 1;
                    try:
                        print('timed out a message from ' + message.author.mention + ':');
                        print(message.content);
                    except:
                        pass;
                    try:
                        await message.delete();
                        if minu == 1:
                            await message.author.send(
                                'you are currently timed out.\ntake a deep breath and come back in ' + str(
                                    minu) + ' minute');
                        else:
                            await message.author.send(
                                'you are currently timed out.\ntake a deep breath and come back in ' + str(
                                    minu) + ' minutes');
                    except:
                        print('tried to delete but couldnt');
                        pass;
                    ok = False;
            if (ok):
                msg = message.content.split(' ', 1);
                if (len(msg) > 0 and msg[0].startswith('!help') and sett.prefix != '!'):
                    return await sayWords(sett=sett, chan=message.channel,
                                          message='prefix is "' + sett.prefix + '" - use ' + sett.prefix + 'help for more help')
                prefixlen = len(sett.prefix);
                if (len(msg) > 0) and (msg[0][:prefixlen] == checkPrefix(client, message)):
                    c = client.all_commands.get(msg[0][prefixlen:]);
                    if (c is None) and sett.isAllowed(userID=message.author.id, command=msg[0][prefixlen:]):
                        for cmd in sett.customCommands:
                            if cmd.command == msg[0][prefixlen:]:
                                ok = False;
                                await sayWords(sett=sett, message=cmd.response, chan=message.channel);
        if ok:
            try:
                await client.process_commands(message)
            except CommandNotFound:
                pass;


@client.event
async def on_guild_join(guild):
    GuildSetting(guild);
    print("new server!: " + guild.name);


@client.event
async def on_guild_remove(guild):
    if not testing:
        util.DBcursor.execute('delete FROM twitch where id_guild = ?', (guild.id,));
        util.DBcursor.execute('delete FROM guild where id = ?', (guild.id,));
        util.DB.commit();
        print('left guild ' + guild.name)


@client.command(hidden=True)
async def shitgame(context):
    if context.message.guild:
        m = await context.send('initializing...\n be in a voicechannel - deaf = down - mute = up')
        await asyncio.sleep(2);
        await playgame(m, context.message.author.id, client);
    else:
        await context.send('whisper-game not supported');


@client.command(hidden=True)
async def get(context):
    """!get <kind> <String> : display markup String"""
    if isAllowed(context):
        cnt = context.message.content.split(' ', 2);
        if len(cnt) > 2:
            result = '```' + cnt[1] + '\n' + cnt[2] + '```'
            await sayWords(context, result);
            await sayWords(context, quote(result));
        else:
            return await sayWords(context, needArgs('!get <kind> <String>'));


@client.command()
async def allow(context):
    """!allow <command>:<role> : allows rights to use the command"""
    if isAllowed(context):
        cnt = context.message.content.split(' ', 1);
        if len(cnt) < 2:
            return await sayWords(context, needArgs('!allow <Command>:<Role> '));
        cnt = cnt[1].split(':', 1);
        if len(cnt) > 1:
            rl = getRoleID(context, cnt[1].strip());
            if rl:
                getSetting(context=context).addPermission(rl, cnt[0]);
                return await sayWords(context, 'command ' + cnt[0] + ' now usable by Role ' + cnt[1]);
            else:
                return await sayWords(context, 'no such role:\n' + quote('!allow <Command>:<Role>'));
        else:
            return await sayWords(context, needArgs('!allow <Command>:<Role> '));
    else:
        return await sayWords(context, NOT_ALLOWED);


@client.command()
async def deny(context):
    """!deny <command>:<role> : revokes rights to use the command"""
    if isAllowed(context):
        cnt = context.message.content.split(' ', 1);
        if len(cnt) < 2:
            return await sayWords(context, needArgs('!deny <Command>:<Role> '));
        cnt = cnt[1].split(':', 1);
        if len(cnt) > 1:
            rl = getRoleID(context, cnt[1].strip());
            if rl:
                getSetting(context=context).removePermission(rl, cnt[0]);
                return await sayWords(context, 'command ' + cnt[0] + ' now usable by Role ' + cnt[1]);
            else:
                return await sayWords(context, 'no such role:\n' + quote('!deny <Command>:<Role>'));
        else:
            return await sayWords(context, needArgs('!deny <Command>:<Role> '));
    else:
        return await sayWords(context, NOT_ALLOWED);


@client.event
async def on_member_join(member):
    sett = getSetting(member.guild.id);
    if sett and (sett.getWelcomeMessage() != ''):
        print('welcomed: ' + member.mention + '(' + str(member.discriminator) + ')');
        return await member.send(sett.getWelcomeMessage());


@client.command()
async def setWelcome(context):
    """!setWelcome <message> : set messaged sent on joining the guild"""
    if isAllowed(context):
        cnt = context.message.content.split(' ', 1);
        if len(cnt) > 1:
            getSetting(context=context).setWelcomeMessage(cnt[1]);
            return await sayWords(context, 'welcome message set to:\n\n' + quote(cnt[1]));
        else:
            getSetting(context=context).setWelcomeMessage('');
            return await sayWords(context, 'welcome message cleared');
    else:
        return await sayWords(context, NOT_ALLOWED);


@client.command()
async def setLogLevel(context):
    """!setLogLevel whisper|mute|channel : how the bot responds"""
    if isAllowed(context):
        cnt = context.message.content.split(' ', 1);
        if len(cnt) > 1 and cnt[1].lower() in ('mute', 'whisper'):
            getSetting(context=context).setLogLevel(cnt[1].lower());
            return await sayWords(context, 'loglevel set to:\n\n' + quote(cnt[1]));
        else:
            getSetting(context=context).setLogLevel('channel');
            return await sayWords(context, 'loglevel set to channel');
    else:
        return await sayWords(context, NOT_ALLOWED);


@client.command()
async def timeout(context):
    """!timeout [guildID if whispering] <person> <time in seconds>"""
    allowed = False;
    i = 0;
    cnt = context.message.content.split(' ', 1)[1];
    if not context.message.guild:
        cnt = cnt.rsplit(' ');
        if not cnt[len(cnt) - 1].isdigit() or len(cnt) < 3:
            cnt = ' '.join(cnt).split(' ', 1);
            cnt.append('600');
        else:
            cnt = ' '.join(cnt).rsplit(' ', 2);
            tmp = cnt[len(cnt) - 1];
            cnt = ' '.join(cnt).split(' ', 1);
            tmp2 = cnt[len(cnt) - 1].rsplit(' ', 1)[0];
            cnt[len(cnt) - 1] = tmp2;
            cnt.append(tmp);
        if len(cnt) > 2:
            sett = getSetting(int(cnt[0]));
            i = 1;
            allowed = isAllowed(userid=context.message.author.id, guildid=int(cnt[0]), command='timeout');
    else:
        allowed = isAllowed(context);
        sett = getSetting(context=context);
        cnt = cnt.rsplit(' ', 1);
        if not cnt[len(cnt) - 1].isdigit():
            cnt.append('600');
    if allowed and sett:
        if len(cnt) > 1 + i:
            usr = cnt[0 + i];
            amount = int(cnt[1 + i]);
            if sett.timeoutPerson(usr, amount):
                if amount > 1:
                    return await context.send(usr + ' has been timed out for ' + str(amount) + 'seconds');
            else:
                return await context.send('cannot find user, enter with # or use the user-id')
        else:
            return await context.send(needArgs('!timeout [guildid] <user> [time in seconds = 600]'));


@client.command()
async def setschedule(context):
    """!setschedule <message> : sets message for !schedule"""
    if not context.message.guild:
        return await sayWords(context, 'you need to set the message in a channel of the guild its for');
    else:
        if isAllowed(context):
            if len(context.message.content.split(' ', 1)) <= 1:
                msg = ''
            else:
                msg = context.message.content.split(' ', 1)[1];
            sett = getSetting(context=context);
            sett.scheduleMessage = msg;
            sett.saveSettings();
            return await sayWords(context, 'schedule set');


@client.command()
async def schedule(context):
    """!schedule : displays a message + current time"""
    if isAllowed(context):
        sett = getSetting(context=context);
        if sett.scheduleMessage != '':
            if util.is_dst('Europe/London'):
                return await sayWords(context, sett.scheduleMessage + '\ncurrently it is ' + TIMEZONE.localize(
                    datetime.utcnow() + timedelta(hours=1)).strftime('%a %I:%M %p') + ' BST');
            else:
                return await sayWords(context, sett.scheduleMessage + '\ncurrently it is ' + TIMEZONE.localize(
                    datetime.utcnow()).strftime('%a %I:%M %p') + ' GMT');


@client.command(pass_context=True)
async def setcom(context):
    """!setcom <command> <response> : sets a custom command"""
    await xsetcom(context, context.message.content);


async def xsetcom(context, message):
    if isAllowed(context):
        if type(message) is str:
            msg = message.split(' ', 2);
        else:
            msg = [''] + message;
        if len(msg) < 3:
            return await sayWords(context, needArgs('!setcom <command> <response>'));
        else:
            sett = GuildSettings.getSetting(context=context);
            if msg[1][:1] == sett.prefix:
                cmd = msg[1][1:];
            else:
                cmd = msg[1];
            cmd = cmd.lower();
            if cmd[1:] in (c.name for c in client.commands):
                return await sayWords(context, 'denied: command is predefined');
            else:
                sett = getSetting(context=context);
                sett.setCom(cmd, msg[2]);
                return await sayWords(context, 'command set');


@client.command()
async def addcom(context):
    """!addcom <command> <response> : add a custom command"""
    await xaddcom(context, context.message.content);


async def xaddcom(context, message):
    if isAllowed(context):
        if type(message) is str:
            msg = message.split(' ', 2);
        else:
            msg = [''] + message;
        if len(msg) < 3:
            return await sayWords(context, needArgs('!addcom <command> <response>'));
        else:
            sett = GuildSettings.getSetting(context=context);
            if msg[1][:1] == sett.prefix:
                cmd = msg[1][1:];
            else:
                cmd = msg[1];
            cmd = cmd.lower();

            if not client.all_commands.get(cmd[1:]) is None:
                return await sayWords(context, 'denied: command is predefined');
            else:
                sett = getSetting(context=context);
                if sett.addCom(cmd, msg[2]):
                    return await sayWords(context, 'command added');
                else:
                    return await sayWords(context, 'command already exists');


@client.command()
async def editcom(context):
    """!editcom <command> <response> : edits a custom command"""
    await xeditcom(context, context.message.content);


async def xeditcom(context, message):
    if isAllowed(context):
        if type(message) is str:
            msg = message.split(' ', 2);
        else:
            msg = [''] + message;
        if len(msg) < 3:
            return await sayWords(context, needArgs('!editcom <command> <response>'));
        else:
            sett = GuildSettings.getSetting(context=context);
            if msg[1][:1] == sett.prefix:
                cmd = msg[1][1:];
            else:
                cmd = msg[1];
            cmd = cmd.lower();
            for x in client.commands:
                if x.name == cmd:
                    return await sayWords(context, 'denied: command is predefined');

            sett = getSetting(context=context);
            if sett.editCom(cmd, msg[2]):
                return await sayWords(context, 'command updated');
            else:
                return await sayWords(context, 'command doesn''t exist');


@client.command()
async def delcom(context):
    """!delcom <command> : deletes a custom command"""
    await xdelcom(context, context.message.content.split(' ', 2)[1]);


@client.group(aliases=['list'])
async def commands(context):
    """!commands : displays guildID & !help"""
    if context.invoked_subcommand is None and isAllowed(context):
        msg = '';
        if context.message.guild:
            svr = context.message.guild.id;
            for mm in client.formatter.format_help_for(context, client):
                msg = msg + mm;
            sett = GuildSettings.getSetting(context=context);

            if len(sett.customCommands) > 0:
                custommsg = '\n```Custom Guild Commands:';
                for cmd in sett.customCommands:
                    custommsg = custommsg + '\n' + cmd.command + ' : ' + cmd.response;
                msg = msg + custommsg + '```';
        # for k in client.commands.keys():
        #	if not client.commands[k].hidden:
        #		print(k);
        #		msg = msg+k+':\t'+str(client.commands[k].help)+'\n';
        else:
            svr = 'None'

        return await sayWords(context, 'guild ID is: ' + str(svr) + '\n' +
                              msg);


@commands.command()
async def add(context: discord.ext.commands.Context, *msg):
    """adds a command, doesnt do anything if command already exists"""
    x = context.message.content.split(' ', 3)[2:];
    await xaddcom(context, x);


@commands.command()
async def edit(context: discord.ext.commands.Context, *msg):
    """edits a command, doesnt do anything if command doesnt exist"""
    await xeditcom(context, context.message.content.split(' ', 3)[2:]);


@commands.command()
async def set(context: discord.ext.commands.Context, *msg):
    """sets a command, overrides if already existing"""
    await xsetcom(context, context.message.content.split(' ', 3)[2:]);


@commands.command()
async def delete(context: discord.ext.commands.Context, msg: str):
    """deltes a command"""
    await xdelcom(context, msg);


async def xdelcom(context: discord.ext.commands.Context, msg: str):
    if isAllowed(contxt=context):
        if msg == '':
            await sayWords(context, "need arguments");
        sett = GuildSettings.getSetting(context=context);
        if msg[:1] == sett.prefix:
            cmd = msg[1:];
        else:
            cmd = msg;
        cmd = cmd.lower();
        if sett.delCom(cmd):
            await sayWords(context, "command deleted")
        else:
            await sayWords(context, "no such command")


@client.command(aliases=['setprefix'])
async def setPrefix(context: discord.ext.commands.Context):
    """!setPrefix <prefix> sets the prefix for this guild"""
    if isAllowed(contxt=context):
        msg = context.message.content;
        ct = msg.split(' ');
        if len(ct) < 2:
            return await sayWords(context, needArgs('!setPrefix <prefix>'))
        if await askYesNoReaction(context, 'Change Prefix to "' + ct[1] + '" ?'):
            sett = GuildSettings.getSetting(context=context);
            sett.prefix = ct[1];
            sett.saveSettings();
            await sayWords(context, 'prefix changed!');
        else:
            await sayWords(context, 'Aborted change of prefix');


@client.command(
    aliases=['sayinchannel', 'sayInchannel', 'sayinChannel', 'sendtochannel', 'sendTochannel', 'sendToChannel', ])
async def sayInChannel(context: discord.ext.commands.Context):
    """!sayInChannel <id or name>:<msg> sends a message to a different channel on the guild"""
    if isAllowed(contxt=context):
        msg = context.message.content
        ct = msg.split(' ', 1);
        ch = None
        if msg == '' or len(ct) != 2:
            return await sayWords(context, "need arguments" + str(len(ct)) + " " + str(ct));
        ct = ct[1].split(':', 1);
        if msg == '' or len(ct) != 2:
            return await sayWords(context, "need arguments, missing : " + str(len(ct)) + str(ct));
        try:
            ch = context.message.guild.get_channel(int(ct[0]));
        except ValueError:
            for channel in context.message.guild.channels:
                if channel.name == ct[0]:
                    ch = channel;
                    break;

        if not ch:
            for c in context.message.guild.channels:
                if c.type == discord.ChannelType.text and c.name.lower() == ct[0].strip().lower():
                    ch = c;
                    break;
        if ch:
            return await ch.send(content=ct[1].strip());
        else:
            return await sayWords(context, "channel " + ct[0] + " not found on this guild");


@client.command()
async def version(context):
    """displays the running version """
    return await sayWords(context, 'CSAR v.' + CSARversion + '\nApi: ' + discord.__version__);


@client.command(aliases=['utc', 'time'])
async def servertime(context):
    """displays the current time"""
    return await sayWords(context, 'Servertime: ' + time.strftime('%Y-%m-%d %H:%M:%S'));


# HELP FUNCTIONS		

def getRoleID(context, rolename):
    for role in context.message.guild.roles:
        if role.name.lower() == rolename.lower():
            return role.id;
    return None;


async def exitx():
    loop = asyncio.get_event_loop()
    loop.stop()


def ask_exit():
    print('recieved Keyboard interrupt, exiting..');
    for task in asyncio.Task.all_tasks():
        task.cancel();
    asyncio.ensure_future(exitx());


util.client = client;
client.running_chroma = False;
# client.remove_command('help');
# startChecking(None);
checkingTask = client.loop.create_task(startChecking(client));

client.add_cog(TwitchCommand(client));
client.add_cog(YoutubeCommand(client));
client.add_cog(GraphCommand(client));
# client.add_cog(TimerCommand(client));
client.add_cog(AdminCommand(client));
client.add_cog(TTSJack(client));
client.add_cog(IRCCommand(client));
import ircStart;

ircTask = client.loop.create_task(ircStart.main(client, testing).start());

from WebServer import setup, setuphttp;

client.loop.run_until_complete(setup(client, testing).start())
client.loop.run_until_complete(setuphttp().start())

from beatsaber.beatsaber_server import download_all_loop

BS_DB = util.DB
client.loop.create_task(download_all_loop(util.beatsaber_people))
if not testing:

    pass

for sig in (signal.SIGINT, signal.SIGTERM):
    try:
        client.loop.add_signal_handler(sig, ask_exit);
    except NotImplementedError:
        print("no signals supported");

print("discord.py version: " + discord.__version__);

msg = "";

try:
    if not testing:
        sendMail('Bot is restarting', 'bot probably back online');
    client.run(TOKEN);
    print("client stopped for some reason");
    msg = msg + '\n' + time.strftime('%X %x %Z') + ' Crash: no Exception :-('
except (KeyboardInterrupt, CancelledError):
    print("interrupt");
    pass;
except Exception as ex:
    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
    message = template.format(type(ex).__name__, ex.args)
    print(message)
    err = str(ex);
    msg = msg + '\n' + time.strftime('%X %x %Z') + ': ' + 'Exception: ' + message + '\n' + err;
    if not testing:
        sendMail('Guild Crash Report', msg);
try:
    checkingTask.cancel();
    ircTask.cancel();
    asyncio.ensure_future(exit())
except:
    pass;
print("Ende");

# sendMail('!!!!!!Guild crashed for good',time.strftime('%X %x %Z') + ': ' + 'please log back in');
