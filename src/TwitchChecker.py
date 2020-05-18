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
from entities.TwitchAPI.TwitchAPI import TwitchUser;



checkStatusOnStart = False;
EnableTwitch = True;
EnableYT = True;
frequencyYT = 2;
itemCountYT = 10;
frequencyTW = 1;
stuff_lock = asyncio.Lock();
streamonline = {};

try:
	fil = open(util.cfgPath+'/testing.cfg','r');
	testing = True;
	fil.close();
except Exception:
	testing = False;
	pass;



async def processTwitch(client,data,session,oauthToken,cnt):
	
				
	pass;

async def printEntry(client,entr,isRerun,sName,sGame,sURL,sTitle,sLogo):
	global testing;
	guild_id = entr.guild;
	channel_id = entr.channel;
	embed = entr.getEmbed(sName,sGame,sURL,sTitle,sLogo);
	if testing:
		guild_id = '196211645289201665';
		channel_id = '196211645289201665';
	try:
		ttext = entr.text;
		if isRerun:
			ttext = entr.text.replace("@here","Rerun!").replace("@everyone","Rerun!");
		messages = await client.get_guild(guild_id).get_channel(channel_id).history(limit=5).flatten();
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
			await client.get_guild(guild_id).get_channel(channel_id).send(content = entr.getYString(ttext,sName,sGame,sURL,sTitle,sLogo),embed=embed);
	except Exception as e:
		print(e);
		
async def startChecking(client):
	global EnableTwitch;
	global EnableYT;
	global stuff_lock;
	global checkStatusOnStart;
	global frequencyYT;
	global itemCountYT;
	global frequencyTW;
	global testing;
	global streamonline;
	if not EnableTwitch and not EnableYT:
		raise;
	
	if not util.TwitchAPI or not util.TwitchSECRET:
		EnableTwitch = False;
		print('WARNING: Twitch TOKENs not set');
	if not util.YTAPI:
		EnableYT = False;
		print('WARNING: Youtube TOKEN not set');	
	
	try:
		await client.wait_until_ready();
		session = aiohttp.ClientSession(); 
		cnt = 0;
				
		streamprinted = {};
		streams = {};
		
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
						oauthToken = await util.AuthMe(session);
						
					for row in util.DBcursor.execute('SELECT distinct lower(username) as username FROM twitch where userid is null'):
						newpeople[row['username']] = [];
						
					for row in util.DBcursor.execute('''SELECT lower(username) as username FROM twitch t
															where t.userid is not null 
															and not exists ( select * from twitch_person where id = t.userid )
													'''):
						newpeople[row['username']] = [];
					#print(newpeople)	
					if len(newpeople.keys()) > 0:
						lookURL = 'https://api.twitch.tv/helix/users?login='+'&login='.join(newpeople.keys())
						myjson = await fetch(session,lookURL,{'client-id':util.TwitchAPI,
																'Accept':'application/vnd.twitchtv.v5+json',
																'Authorization':'Bearer '+oauthToken});
						
								
						myjson = json.loads(myjson);
						print(myjson);
						myArray = myjson["data"];
						if myArray:
							for myEnt in myArray:
								data_user = TwitchUser(myEnt);
								newpeople[myEnt["display_name"].lower()] = myEnt["id"];
								
								util.DBcursor.execute('update twitch set userid = ? where lower(username) = ?',[data_user.id,data_user.display_name.lower()]);
								util.DBcursor.execute('''insert into twitch_person(id,login,display_name,type,broadcaster_type,description,profile_image_url,offline_image_url,view_count)
									 select ?,?,?,?,?,?,?,?,? from dual
									 where not exists (select * from twitch_person where id = ?) 
									 '''							 
								 ,[data_user.id,data_user.login,data_user.display_name,data_user.type,data_user.broadcaster_type,data_user.description,data_user.profile_image_url,data_user.offline_image_url,data_user.view_count,data_user.id]);
							
						util.DB.commit();
				except Exception as ex:
					traceback.print_exc(file=sys.stdout);
					logEx(ex);
				streams = {};
				ids = {};
				for row in util.DBcursor.execute('SELECT t.*,p.id as pers_id,p.last_check,p.last_check_status FROM twitch t left join twitch_person p on t.userid = p.id'):
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
							#print(html);
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
								sGame = '[Ding Dong!]';
								sURL = 'https://www.youtube.com/watch?v=oHg5SJYRHA0';
								sTitle = 'it has happened!';
								sLogo = None;
								embed = entr.getEmbed(n,sGame,sURL,sTitle,sLogo);
								if not testing:
									try:
										await client.get_guild(entr.guild).get_channel(entr.channel).send(content = entr.getYString(entr.text,n,sGame,sURL,sTitle,sLogo),embed=embed);
										print('timer {0} triggered entry: {1}:{2} - {3}'.format(entr.id, entr.fromtimeH, entr.fromtimeM, entr.days));
									except:
										traceback.print_exc(file=sys.stdout);
										print('timer broken');
										pass;
								else:
									try:
										await client.get_guild(196211645289201665).get_channel(196211645289201665).send(content = entr.getYString(entr.text,n,sGame,sURL,sTitle,sLogo),embed=embed);
									except Exception as e:
										print(e);
					if streamArray:
						try:
							#fetch metadata in first loop
							gamesToFetch = set([k['game_id'] for k in streamArray]);
							games = await util.getGames(gamesToFetch,session,oauthToken);
							#print(games);
							
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
									sName = streamjson['user_name'];
									
									sGame = games[streamjson['game_id']];
									
									sURL = 'https://www.twitch.tv/'+streamername;
									sTitle = streamjson['title'];
									sLogo = streamjson['thumbnail_url'].replace('{width}','300').replace('{height}','300');
									
									if((streamername in ['nilesy','hybridpanda', 'ravs_'] ) and cnt%2 == 0):
										try:
											viewcount = int(streamjson['viewer_count']);
											mydate = time.strftime('%Y-%m-%d %H:%M:%S');
											util.DBcursor.execute('insert into twitchstats(channel,date,viewcount,game) values(?,?,?,?)',(streamername,mydate,viewcount,sGame));
										except Exception as e:
											print(e);
									
									llist.append(streamername);
									if not streamonline[streamername]:
										for entr in streams[streamername]:
											#print(time.strftime('%X %x %Z ')+n+' print: '+str(entr.shouldprint(sGame)));
											try:
												#print(streamprinted[entr]);
												if (entr.shouldprint(sGame) and not streamprinted[entr]):
													await printEntry(client,entr,isRerun,sName,sGame,sURL,sTitle,sLogo);
													#sayWords(None, entr.getYString(n,sGame,sURL,sLogo,sTitle), entr.guild, entr.channel);
													streamprinted[entr] = True;
													logEx('sent Twitch message for '+sName);
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
						except Exception as e:
							logEx(e);
							print('streamArray: '+str(streamArray));
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
				ytWorks = True;
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
								ytWorks = True;
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
								sTitle = newestItem['snippet']['title'];
								#print("");
								newid = newestItem['snippet']['resourceId']['videoId'];
								oldid = ytUsrs[yt].lastID;
								oldTime = toDateTime(ytUsrs[yt].lastprinted);
								
								if(newid != ytUsrs[yt].lastID and (oldTime == 1 or oldTime < newestTime or ytUsrs[yt].changed == True)):
									ytUsrs[yt].lastID = newid;
									ytUsrs[yt].lastprinted = newestTimeAsString;
									ytUsrs[yt].save();
								sURL = 'https://www.youtube.com/watch?v='+	newid;
								if(newid != oldid):
									if oldid:
										print(oldid + '  -->  '+newid);
									for entr in ytentries[yt]:
										try:
											if (entr.shouldprint(newestTime)):
												embed = entr.getEmbed(ytUsrs[yt].displayname,sURL,sTitle,thumb);
												print(entr.getYString(entr.text,ytUsrs[yt].displayname,sURL,sTitle,thumb))
												if not testing:
													await client.get_guild(entr.guild).get_channel(entr.channel).send(content = entr.getYString(entr.text,ytUsrs[yt].displayname,sURL,sTitle,thumb),embed=embed);
												else:
													try:
														await client.get_guild(196211645289201665).get_channel(196211645289201665).send(content = entr.getYString(entr.text,ytUsrs[yt].displayname,sURL,sTitle,thumb),embed=embed);
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

















