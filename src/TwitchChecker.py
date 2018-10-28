####################################################################
###########  user variables - change to your liking  ###############
####################################################################


#your Client-ID - go to https://blog.twitch.tv/client-id-required-for-kraken-api-calls-afbb8e95f843 and follow the instructions
TwitchAPI = '';
YTAPI = '';
#in what interval do you want to check the Status
MinuteInterval = 1

####################################################################
###########  don't change anything below this line  ################
####################################################################

import json
import time
import util;
from util import logEx;
import entities.TwitchEntry;
import entities.YTEntry;
import entities.YTUser;
import asyncio;
from asyncio import CancelledError;
import aiohttp
import traceback;
import sys
import fileinput
from datetime import datetime;
from util import toDateTime;
from util import fetch;

file = open(util.cfgPath+"/../tokens/twitch.token","r");
try:
	contents =file.read().splitlines(); 
	TwitchAPI = contents[0];
except:
	pass;
file.close();

file = open(util.cfgPath+"/../tokens/youtube.token","r");
try:
	contents =file.read().splitlines(); 
	YTAPI = contents[0];
except:
	pass;
file.close();

checkStatusOnStart = False;
EnableTwitch = True;
EnableYT = True;
stuff_lock = asyncio.Lock();

class SvrChan:
	def __init__(self,s,c,m):
		self.guildid = s;
		self.channelid = c;
		self.messages = m;
		self.time = datetime.utcnow();
		
async def startChecking(client):
	if not EnableTwitch and not EnableYT:
		raise;
	try:
		fil = open(util.cfgPath+'/testing.cfg','r');
		testing = True;
		fil.close();
	except Exception:
		testing = False;
		pass;
	
	try:
		await client.wait_until_ready();
		cnt = 0;
		streamonline = {};
		streamprinted = {};
		streams = {};
		for row in util.DBcursor.execute('SELECT * FROM twitch'):
			streamonline[row['username'].lower()] = not checkStatusOnStart;
		while not client.is_closed():
			try:
				streams = {};
				for row in util.DBcursor.execute('SELECT * FROM twitch'):
					if not row['username'] in streams:
						streams[row['username'].lower()] = [];
					ent = entities.TwitchEntry.TwitchEntry(row);
					streams[row['username'].lower()].append(ent);
					streamprinted[ent] = False;
				for strm in streams.keys():
					if not strm in streamonline:
						streamonline[strm] = not checkStatusOnStart;
				if checkStatusOnStart:
					try:
						for i, line in enumerate(fileinput.input('TwitchChecker.py', inplace=1)):
							selfChanger = line.replace('checkStatusOnStart = True', 'checkStatusOnStart = False');
							sys.stdout.write(selfChanger)  # replace 'sit' and write
					except Exception as e:
						logEx(e);
				llist = [];
				cnt = cnt + 1;
				onlin = 0;
				streamArray = None;
				with (await stuff_lock):
					try:
						if EnableTwitch and len(streams.keys()) > 0:
							async with aiohttp.ClientSession() as session:
								html = await fetch(session,'https://api.twitch.tv/kraken/streams?channel='+','.join(streams.keys()),{'client-id':TwitchAPI});
							html = json.loads(html);
							streamArray = html['streams'];
					except aiohttp.ClientConnectionError as ex:
						logEx(ex);
					except asyncio.TimeoutError as ex:
						logEx(ex);
					if 'timer' in streams.keys():	
						for entr in streams['timer']:
							if entr.shouldprint(entr.game):
								n = '[timer]';
								g = '[Ding Dong!]';
								u = 'https://www.youtube.com/watch?v=oHg5SJYRHA0';
								t = 'it has happened!';
								l = None;
								embed = entr.getEmbed(n,g,u,t,l);
								if not testing:
									try:
										await client.get_guild(str(entr.guild)).get_channel(str(entr.channel)).send(content = entr.getYString(entr.text,n,g,u,t,l),embed=embed);
										print('timer {0} triggered entry: {1}:{2} - {3}'.format(entr.id, entr.fromtimeH, entr.fromtimeM, entr.days));
									except:
										print('timer broken');
										pass;
									
								else:
									try:
										await client.get_guild('196211645289201665').get_channel('196211645289201665').send(content = entr.getYString(entr.text,n,g,u,t,l),embed=embed);
									except Exception as e:
										print(e);
					if streamArray:
						try:
							for streamjson in streamArray:
								if streamjson:
									streamername = streamjson['channel']['name'].lower();
									llist.append(streamername);
									if not streamonline[streamername]:
										for entr in streams[streamername]:
											n = streamjson['channel']['display_name'];
											g = streamjson['game'];
											u = streamjson['channel']['url'];
											t = streamjson['channel']['status'];
											l = streamjson['channel']['logo'];
											#print(time.strftime('%X %x %Z ')+n+' print: '+str(entr.shouldprint(g)));
											try:
												#print(streamprinted[entr]);
												if (entr.shouldprint(g) and not streamprinted[entr]):
													embed = entr.getEmbed(n,g,u,t,l);
													if not testing:
														await client.get_guild(str(entr.guild)).get_channel(str(entr.channel)).send(content = entr.getYString(entr.text,n,g,u,t,l),embed=embed);
													else:
														try:
															await client.get_guild('196211645289201665').get_channel('196211645289201665').send(content = entr.getYString(entr.text,n,g,u,t,l),embed=embed);
														except Exception as e:
															print(e);
													#sayWords(None, entr.getYString(n,g,u,l,t), entr.guild, entr.channel);
													streamprinted[entr] = True;
													logEx('sent Twitch message for '+n);
													#print(10);
											except Exception as e:
												logEx(e); 
									#print(11);			
									onlin = onlin + 1;
									#print(12);
						finally:
							#print(14);
							onlin = onlin + 1 - 1;
						for people in streams.keys():
							streamonline[people] = people in llist;
							if not people in llist:
								for entr in streams[people]:
									streamprinted[entr] = False;						
						for removed in (set(streamonline.keys()) - set(streams.keys())):
							streamonline.pop(removed,None);
						for removed in (set(streamprinted.keys()) - set(streams.keys())):
							streamprinted.pop(removed,None);
					else:
						onlin = 0;
				twitMessage = str(cnt)+' | '+time.strftime('%X %x %Z')+' online: '+str(onlin)+' | '+str(llist);
				ytMessage = 'no youtube';
				llist = [];
				if EnableYT:
					ytentries = {}
					ytCaseSensitive = {};
					ytUsrs = {};
					for row in util.DBcursor.execute('SELECT y.*, yt.YTID, yt.lastprinted, yt.lastid, yt.id as idytid, yt.uploadid, yt.displayname FROM youtube y left join YTUser yt on y.username = yt.username'):
						if not row['username'] in ytentries:
							ytentries[row['username'].lower()] = [];
						ent = entities.YTEntry.YTEntry(row);
						usr = entities.YTUser.YTUser(row);
						ytentries[row['username'].lower()].append(ent);
						ytUsrs[row['username'].lower()] = usr;
						ytCaseSensitive[row['username'].lower()] = row['username'];
					ytMessage = str(ytentries.keys());
					for yt in ytentries:
						if not ytUsrs[yt] or not ytUsrs[yt].uploadID or not ytUsrs[yt].id or not ytUsrs[yt].displayname:
							try:
								usrused = True;
								async with aiohttp.ClientSession() as session:
									html = await fetch(session,'https://www.googleapis.com/youtube/v3/channels?part=id,contentDetails&key='+YTAPI+'&forUsername='+yt,{});
								html = json.loads(html);
								if len(html['items']) == 0:
									async with aiohttp.ClientSession() as session:
										html = await fetch(session,'https://www.googleapis.com/youtube/v3/channels?part=id,snippet,contentDetails&key='+YTAPI+'&id='+ytCaseSensitive[yt],{});
									html = json.loads(html);
									usrused = False;
								ytUsrs[yt].YTID = html['items'][0]['id'];
								ytUsrs[yt].uploadID = html['items'][0].get('contentDetails').get('relatedPlaylists').get('uploads',None);
								ytUsrs[yt].changed = True;
								if usrused:
									ytUsrs[yt].displayname = yt;
								else:
									ytUsrs[yt].displayname = html['items'][0]['snippet']['title'];
								#ytUpdateId[yt] = updateOrInsert('YTUser',{'id':None},{'username':yt,'YTID':ytChannelId[yt]},False);
								#print(uploadID);
								#util.DB.commit();
							except aiohttp.ClientConnectionError as ex:
								logEx(ex);
							except asyncio.TimeoutError as ex:
								logEx(ex);
						try:
							async with aiohttp.ClientSession() as session:
								#html = await fetch(session,'https://www.googleapis.com/youtube/v3/search?part=snippet&key='+YTAPI+'&channelId='+ytChannelId[yt]+'&order=date&type=video&safeSearch=none',{});
								html = await fetch(session,'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=25&key='+YTAPI+'&playlistId='+ytUsrs[yt].uploadID,{});
							html = json.loads(html);
							newestItem = None;
							
							#
							#total = html['pageInfo']['totalResults']
							#if total == old + 1
							#	then if not found and nextPageToken != null: 
							#		fetch http:// &pageToken= html['nextPageToken']
							#
							
							#timeStr ohne millisec
							if len(html['items']) == 0:
								continue;
							#bestDate = toDateTime(ytUsrs[yt].lastprinted);
							newestItem = html['items'][0];
							#print('>>'+str(len(html['items'])));
							bestDate = toDateTime(html['items'][0].get('snippet').get('publishedAt'));
							for itm in html['items']:
								itemDate = itm.get('snippet').get('publishedAt');
								dd = toDateTime(itemDate)
								if(not bestDate or bestDate <= dd):
									newestItem = itm;
									bestDate = dd;
							#newestItem = html['items'][0];
							newestTimeAsString = newestItem['snippet']['publishedAt'];
							newestTime = toDateTime(newestTimeAsString);
							thumb = newestItem['snippet']['thumbnails'];
							if 'maxres' in thumb:
								thumb = thumb['maxres'];
							elif 'standard' in thumb:
								thumb = thumb['standard'];	
							elif 'high' in thumb:
								thumb = thumb['high'];
							elif 'medium' in thumb:
								thumb = thumb['medium'];
							else:
								thumb = thumb['default'];
							thumb = thumb['url'];	
							t = newestItem['snippet']['title'];
							newid = newestItem['snippet']['resourceId']['videoId'];
							if(newid != ytUsrs[yt].lastID or ytUsrs[yt].changed == True):
								ytUsrs[yt].lastID = newid;
								ytUsrs[yt].lastprinted = newestTimeAsString;
								ytUsrs[yt].save();
							u = 'https://www.youtube.com/watch?v='+	newid;
							for entr in ytentries[yt]:
								try:
									if (entr.shouldprint(newestTime)):
										embed = entr.getEmbed(ytUsrs[yt].displayname,u,t,thumb);
										print(entr.getYString(entr.text,ytUsrs[yt].displayname,u,t,thumb))
										if not testing:
											await client.get_guild(str(entr.guild)).get_channel(str(entr.channel)).send(content = entr.getYString(entr.text,ytUsrs[yt].displayname,u,t,thumb),embed=embed);
										else:
											try:
												await client.get_guild('196211645289201665').get_channel('196211645289201665').send(content = entr.getYString(entr.text,ytUsrs[yt].displayname,u,t,thumb),embed=embed);
											except Exception as e:
												print(e);
										logEx('sent Youtube message for '+yt);
								except Exception as e:
									logEx(e);
						except aiohttp.ClientConnectionError as ex:
							logEx(ex);
						except asyncio.TimeoutError as ex:
							logEx(ex);
						except KeyError as ex:
							logEx(ex);
				print(twitMessage+'; '+ytMessage);			
			#	if onlin == len(streams):
			#		time.sleep(1800)
			#	else:
			except Exception:
				try:
					traceback.print_exc();
				except:
					pass;
			if testing:
				await asyncio.sleep(1 * 15)
			else:
				for i in range(12):
					await asyncio.sleep(1 * 5)
	except BaseException as ex:
		err = str(ex);
		if(not testing) and (err != ''):
			import yagmail;
			import base64;
			#yagmail.register('theschippi@gmail.com',base64.b64decode('dnp6bGxxeWtybnJwaXNsZg=='))
			yag = yagmail.SMTP('theschippi@gmail.com',base64.b64decode('dnp6bGxxeWtybnJwaXNsZg=='));
			contents = [time.strftime('%X %x %Z') + ': ' + 'Exception:\n\t '+err];
			yag.send('theschippi@gmail.com', 'Guild crashed', contents);
		else:
			pass;
	except CancelledError:
		pass;

















