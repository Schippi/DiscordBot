####################################################################
###########  user variables - change to your liking  ###############
####################################################################



#in what interval do you want to check the Status
MinuteInterval = 1

####################################################################
###########  don't change anything below this line  ################
####################################################################

import json
import time
import util;
from util import logEx, AuthFailed;
from entities import TwitchEntry;

#import entities.TwitchEntry;
import entities.YTEntry;
import entities.YTUser;
import asyncio;
from asyncio import CancelledError;
import aiohttp
import traceback;
import sys
import fileinput
from datetime import datetime;
from datetime import timedelta;
from dateutil import tz
from util import toDateTime;
from util import dateToStr;
from util import fetch;
from util import posting;
from util import getControlVal;
from util import setControlVal;


checkStatusOnStart = False;
EnableTwitch = True;
EnableYT = True;
frequencyYT = 2;
itemCountYT = 10;
frequencyTW = 1;
stuff_lock = asyncio.Lock();

		
async def startChecking(client):
	global EnableTwitch;
	global EnableYT;
	global stuff_lock;
	global checkStatusOnStart;
	global frequencyYT;
	global itemCountYT;
	global frequencyTW;
	
	if not EnableTwitch and not EnableYT:
		raise;
	
	if not util.TwitchAPI or not util.TwitchSECRET:
		EnableTwitch = False;
		print('WARNING: Twitch TOKENs not set');
	if not util.YTAPI:
		EnableYT = False;
		print('WARNING: Youtube TOKEN not set');	
		
	try:
		fil = open(util.cfgPath+'/testing.cfg','r');
		testing = True;
		fil.close();
	except Exception:
		testing = False;
		pass;
	
	try:
		await client.wait_until_ready();
		session = aiohttp.ClientSession(); 
		cnt = 0;
		streamonline = {};
		streamprinted = {};
		streams = {};
		
		util.DBcursor.execute('''CREATE TABLE IF NOT EXISTS twitchstats (
			'ID'	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
			'DATE'	TEXT,
			'viewcount'	INTEGER,
			'game'	TEXT,
			'channel'	TEXT
		);''');
		util.DB.commit();
		
		
		util.DBcursor.execute('''CREATE TABLE IF NOT EXISTS  `control` (
				`Key`	TEXT,
				`value`	TEXT
			);''');
		util.DB.commit();
		
		#util.DBcursor.execute('''DROP TABLE  `game`;''');
		
		util.DBcursor.execute('''CREATE TABLE IF NOT EXISTS  `game` (
				`id`	INTEGER,
				`name`	TEXT,
				`boxart`	TEXT
			);''');
		util.DB.commit();
		
		
		for row in util.DBcursor.execute('SELECT * FROM twitch'):
			streamonline[row['username'].lower()] = not checkStatusOnStart;
		while not client.is_closed():
			try:
				try:
					newpeople ={};
					frequencyYT = int(getControlVal('frequencyYT',frequencyYT));
					itemCountYT = int(getControlVal('itemCountYT',itemCountYT));
					frequencyTW = int(getControlVal('frequencyTW',frequencyTW));
					
					oauthToken = getControlVal('token_oauth','');
					
					if(oauthToken == ''):
						print('Authorization for the first time');
						await util.AuthMe(session);
						
					for row in util.DBcursor.execute('SELECT distinct lower(username) as username FROM twitch where userid is null'):
						newpeople[row['username']] = [];
					if len(newpeople.keys()) > 0:
						lookURL = 'https://api.twitch.tv/helix/users?login='+'&login='.join(newpeople.keys())
						myjson = await fetch(session,lookURL,{'client-id':util.TwitchAPI,
																'Accept':'application/vnd.twitchtv.v5+json',
																'Authorization':'Bearer '+oauthToken});
						
								
						myjson = json.loads(myjson);
						#print(myjson);
						myArray = myjson["users"];
						if myArray:
							for myEnt in myArray:
								newpeople[myEnt["name"].lower()] = myEnt["_id"]; 
						for p in newpeople:
							util.DBcursor.execute('update twitch set userid = ? where username = ?',[newpeople[p],p]);
						util.DB.commit();
				except:
					pass;	
				streams = {};
				ids = {};
				for row in util.DBcursor.execute('SELECT * FROM twitch'):
					if not row['username'] in streams:
						streams[row['username'].lower()] = [];
					ent = entities.TwitchEntry.TwitchEntry(row);
					streams[row['username'].lower()].append(ent);
					ids[row['username'].lower()] = row['userid'];
					streamprinted[ent] = False;
				for strm in streams.keys():
					if not strm in streamonline:
						streamonline[strm] = not checkStatusOnStart;
				if checkStatusOnStart and not testing:
					try:
						for i, line in enumerate(fileinput.input('TwitchChecker.py', inplace=1)):
							selfChanger = line.replace('checkStatusOnStart = True', 'checkStatusOnStart = False');
							sys.stdout.write(selfChanger)  # replace 'sit' and write
					except Exception as e:
						traceback.print_exc(file=sys.stdout);
						logEx(e);
				llist = [];
				cnt = cnt + 1;
				onlin = 0;
				streamArray = None;
				with (await stuff_lock):
					try:
						if EnableTwitch and (len(streams.keys()) > 0) and (cnt % frequencyTW == 0) :
							html = await fetch(session,'https://api.twitch.tv/helix/streams?user_id='+'&user_id='.join(ids.values()),{'client-id':util.TwitchAPI,
																															'Accept':'application/vnd.twitchtv.v5+json',
																															'Authorization':'Bearer '+oauthToken});
							html = json.loads(html);
							print(html);
							streamArray = html['data'];
						else:
							streamArray = None;
					except aiohttp.ClientConnectionError as ex:
						traceback.print_exc(file=sys.stdout);
						logEx(ex);
					except asyncio.TimeoutError as ex:
						traceback.print_exc(file=sys.stdout);
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
										await client.get_guild(entr.guild).get_channel(entr.channel).send(content = entr.getYString(entr.text,n,g,u,t,l),embed=embed);
										print('timer {0} triggered entry: {1}:{2} - {3}'.format(entr.id, entr.fromtimeH, entr.fromtimeM, entr.days));
									except:
										print('timer broken');
										pass;
								else:
									try:
										await client.get_guild(196211645289201665).get_channel(196211645289201665).send(content = entr.getYString(entr.text,n,g,u,t,l),embed=embed);
									except Exception as e:
										print(e);
					if streamArray:
						try:
							#fetch metadata in first loop
							display_names = {};
							gamesToFetch = set([k['game_id'] for k in streamArray]);
							games = await util.getGames(gamesToFetch,session,oauthToken);
							print(games);
							
							for streamjson in streamArray:
								if streamjson:
									isRerun = False;
									try:
										stype = streamjson['type'].lower();
										if(stype == "rerun"):
											isRerun = True;
									except:
										pass;
									streamername = streamjson['user_name'].lower();
									n = streamjson['user_name'];
									
									g = games[streamjson['game_id']];
									
									u = 'https://www.twitch.tv/'+streamername;
									t = streamjson['title'];
									l = streamjson['thumbnail_url'].replace('{width}','300').replace('{height}','300');
									
									if((streamername in ['nilesy','hybridpanda', 'ravs_'] ) and cnt%2 == 0):
										try:
											viewcount = int(streamjson['viewer_count']);
											mydate = time.strftime('%Y-%m-%d %H:%M:%S');
											util.DBcursor.execute('insert into twitchstats(channel,date,viewcount,game) values(?,?,?,?)',(streamername,mydate,viewcount,g));
										except Exception as e:
											print(e);
									
									llist.append(streamername);
									if not streamonline[streamername]:
										for entr in streams[streamername]:
											#print(time.strftime('%X %x %Z ')+n+' print: '+str(entr.shouldprint(g)));
											try:
												#print(streamprinted[entr]);
												if (entr.shouldprint(g) and not streamprinted[entr]):
													embed = entr.getEmbed(n,g,u,t,l);
													if not testing:
														ttext = entr.text;
														if isRerun:
															ttext = entr.text.replace("@here","Rerun!").replace("@everyone","Rerun!");
														messages = await client.get_guild(entr.guild).get_channel(entr.channel).history(limit=5).flatten();
														today = datetime.utcnow().date() - timedelta(hours = 3);
														start = datetime(today.year, today.month, today.day);
														doit = True;
														for mymsg in messages:
																if mymsg.author == client.user:
																	if mymsg.created_at > today:
																		alle = False;
																		for tee in entr.text.split():
																			if not (tee in mymsg.content) and not (tee in '%%game%% %%name%% %%url%% %%img%% %%title%% %%time%%'):
																				alle = True;
																				print(tee)
																				break;
																		doit = doit and alle;
																		print("wanted but didnt: "+str(doit));
														if doit:	
															await client.get_guild(entr.guild).get_channel(entr.channel).send(content = entr.getYString(ttext,n,g,u,t,l),embed=embed);
													else:
														try:
															ttext = entr.text;
															if isRerun:
																ttext = entr.text.replace("@here","Rerun!").replace("@everyone","Rerun!");
															messages = await client.get_guild(196211645289201665).get_channel(196211645289201665).history(limit=5).flatten();
															today = datetime.utcnow().date();
															start = datetime(today.year, today.month, today.day);
															doit = True;
															for mymsg in messages:
																if mymsg.author == client.user:
																	if mymsg.created_at > start:
																		alle = False;
																		for tee in entr.text.split():
																			if not (tee in mymsg.content) and not (tee in '%%game%% %%name%% %%url%% %%img%% %%title%% %%time%%'):
																				alle = True;
																				print(tee)
																				break;
																		doit = doit and alle;
																		print("wanted but didnt: "+str(doit));
															if doit:
																await client.get_guild(196211645289201665).get_channel(196211645289201665).send(content = entr.getYString(ttext,n,g,u,t,l),embed=embed);
															break;
														except Exception as e:
															print(e);
													#sayWords(None, entr.getYString(n,g,u,l,t), entr.guild, entr.channel);
													streamprinted[entr] = True;
													logEx('sent Twitch message for '+n);
													#print(10);
											except Exception as e:
												print(streamername)
												traceback.print_exc(file=sys.stdout);
												logEx(e); 
									#print(11);			
									onlin = onlin + 1;
									#print(12);
							try:                
								util.DB.commit();
							except Exception as e:
								traceback.print_exc(file=sys.stdout);
								logEx(e);
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
						for removed in (set(streamonline.keys()) - set(streamprinted.keys())):
							streamprinted[entr] = False;
						for removed in (set(streamprinted.keys()) - set(streams.keys())):
							streamprinted.pop(removed,None);
					else:
						onlin = 0;
						
				twitMessage = str(cnt)+' | '+time.strftime('%X %x %Z')+' online: '+str(onlin)+' | '+str(llist);
				ytMessage = 'no youtube ('+str(frequencyYT)+')';
				llist = [];
				if EnableYT and (cnt % frequencyYT == 0):
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
								#print(yt)
								usrused = True;
								html = await fetch(session,'https://www.googleapis.com/youtube/v3/channels?part=id,contentDetails&key='+util.YTAPI+'&forUsername='+yt,{});
								html = json.loads(html);
								if len(html['items']) == 0:
									html = await fetch(session,'https://www.googleapis.com/youtube/v3/channels?part=id,snippet,contentDetails&key='+util.YTAPI+'&id='+ytCaseSensitive[yt],{});
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
							except KeyError as ex:
								ytMessage = 'Youtube Daily Limit Exceeded';
								if('Daily Limit Exceeded' in str(html)):
									ytWorks = False;
									break;
						if ytWorks and ytUsrs[yt].uploadID:
							try:
								html = await fetch(session,'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults='+str(itemCountYT)+'&key='+util.YTAPI+'&playlistId='+ytUsrs[yt].uploadID,{});
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
								#print(newestItem);
								#print("");
								#print('>>'+str(len(html['items'])));
								bestDate = toDateTime(html['items'][0].get('snippet').get('publishedAt'));
								for itm in html['items']:
									itemDate = itm.get('snippet').get('publishedAt');
									dd = toDateTime(itemDate)
									if(not bestDate or bestDate <= dd):
										newestItem = itm;
										bestDate = dd;
										#print(itemDate+" "+itm['snippet']['resourceId']['videoId']);
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
								#print("");
								newid = newestItem['snippet']['resourceId']['videoId'];
								oldid = ytUsrs[yt].lastID;
								oldTime = toDateTime(ytUsrs[yt].lastprinted);
								
								if(newid != ytUsrs[yt].lastID and (oldTime == 1 or oldTime < newestTime or ytUsrs[yt].changed == True)):
									ytUsrs[yt].lastID = newid;
									ytUsrs[yt].lastprinted = newestTimeAsString;
									ytUsrs[yt].save();
								u = 'https://www.youtube.com/watch?v='+	newid;
								if(newid != oldid):
									if oldid:
										print(oldid + '  -->  '+newid);
									for entr in ytentries[yt]:
										try:
											if (entr.shouldprint(newestTime)):
												embed = entr.getEmbed(ytUsrs[yt].displayname,u,t,thumb);
												print(entr.getYString(entr.text,ytUsrs[yt].displayname,u,t,thumb))
												if not testing:
													await client.get_guild(entr.guild).get_channel(entr.channel).send(content = entr.getYString(entr.text,ytUsrs[yt].displayname,u,t,thumb),embed=embed);
												else:
													try:
														await client.get_guild(196211645289201665).get_channel(196211645289201665).send(content = entr.getYString(entr.text,ytUsrs[yt].displayname,u,t,thumb),embed=embed);
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
							except ValueError as ex:
								logEx(ex);
								print(str(newestItem['snippet']));
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
				#for st in streamonline.keys():
				#	streamonline[st] = False;
				await asyncio.sleep(4 * 15)
			else:
				for i in range(12):
					await asyncio.sleep(1 * 5)
	except BaseException as ex:
		err = str(ex);
		logEx(ex);
		if testing:
			print(err);
		if(not testing) and (err != ''):
			util.sendMail('TwitchCheckerloop crashed',time.strftime('%X %x %Z') + ': ' + 'Exception:\n\t '+err);
		else:
			pass;
	except CancelledError:
		pass;

















